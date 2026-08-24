package com.codeatlas.backend.upload;

import com.codeatlas.backend.agent.CurationBatchService;
import com.codeatlas.backend.embedding.EmbeddingBackfillService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.FileSystemUtils;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 업로드 작업 — 논문·저장소를 카탈로그에 넣는 전 과정을 한 작업으로 묶어 순서대로 돌린다.
 *
 * <pre>
 *   [scripts/upload_pipeline.py]  ARXIV_META → EPRINT → REPO_CLONE → CODE_BLOCKS → LATEX_SPLIT → INGEST
 *   [이 서비스]                   EMBEDDING(EmbeddingBackfillService) → CURATION(CurationBatchService)
 * </pre>
 *
 * 파이썬 단계는 이미 있는 적재 도구(ingest.py·latex2chunks.py)를 그대로 쓰기 위해 서브프로세스로
 * 돌리고, 그 stdout 의 {@code ##STAGE} 줄로 진행 단계를, 나머지 줄로 로그를 화면에 올린다.
 * 작업은 한 번에 하나만 돈다 — LLM(분리·큐레이션)이 직렬이라 병렬로 돌려도 빨라지지 않고,
 * 큐레이션 배치 자체가 동시 실행을 막는다.
 *
 * 작업 상태는 메모리에만 둔다. 재기동하면 목록이 사라지지만 적재된 데이터는 DB 에 남아 있고,
 * 같은 arXiv ID 로 다시 올리면 upsert 된다(ingest.py 규칙).
 */
@Service
public class UploadJobService {

    private static final Logger log = LoggerFactory.getLogger(UploadJobService.class);
    private static final Pattern STAGE_LINE = Pattern.compile("^##STAGE (\\S+)\\s*(.*)$");
    private static final Pattern RESULT_LINE = Pattern.compile("^##RESULT paperId=(\\d+)(?: chunks=(\\d+))?(?: blocks=(\\d+))?");
    private static final int MAX_LOG_LINES = 400;

    public enum Status { QUEUED, RUNNING, DONE, FAILED, CANCELED }

    /** 화면이 타임라인으로 그리는 단계 목록. 파이썬이 찍는 이름과 일치해야 한다. */
    public static final List<String> ARXIV_STAGES = List.of(
            "ARXIV_META", "EPRINT", "REPO_CLONE", "CODE_BLOCKS", "LATEX_SPLIT", "INGEST", "EMBEDDING", "CURATION");
    public static final List<String> JSON_STAGES = List.of("VALIDATE", "INGEST", "EMBEDDING", "CURATION");

    public static class Job {
        public final String id;
        public final String type;               // "arxiv" | "json"
        public final String label;              // 화면용 한 줄 (arXiv ID + 저장소, 또는 파일명)
        public final List<String> stages;
        public final Instant createdAt = Instant.now();
        public volatile Status status = Status.QUEUED;
        public volatile String stage = null;
        public volatile String stageMessage = null;
        public volatile Instant startedAt, finishedAt;
        public volatile Long paperId;
        public volatile Integer chunks, codeBlocks, mappings;
        public volatile String error;
        public final List<String> logLines = Collections.synchronizedList(new ArrayList<>());
        final Map<String, String> args;     // 파이썬 인자 또는 JSON 본문
        volatile Process currentProcess;    // 파이썬 단계가 도는 동안만 non-null — cancel 용
        final AtomicBoolean canceled = new AtomicBoolean(false);

        Job(String type, String label, List<String> stages, Map<String, String> args) {
            this.id = UUID.randomUUID().toString().substring(0, 8);
            this.type = type;
            this.label = label;
            this.stages = stages;
            this.args = args;
        }

        void log(String line) {
            if (logLines.size() >= MAX_LOG_LINES) {
                logLines.remove(0);
            }
            logLines.add(line);
        }

        void enter(String stage, String message) {
            this.stage = stage;
            this.stageMessage = message;
            log("▶ " + stage + (message == null || message.isBlank() ? "" : " — " + message));
        }
    }

    private final Map<String, Job> jobs = Collections.synchronizedMap(new LinkedHashMap<>());
    private final ExecutorService worker = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "upload-job");
        t.setDaemon(true);
        return t;
    });

    private final EmbeddingBackfillService embeddingBackfillService;
    private final CurationBatchService curationBatchService;
    private final JdbcTemplate jdbcTemplate;
    private final Path scriptsDir;
    private final Path workRoot;
    private final int candidatesPerChunk;
    private final int selectedPerChunk;
    private final long pythonTimeoutMinutes;

    public UploadJobService(
            EmbeddingBackfillService embeddingBackfillService,
            CurationBatchService curationBatchService,
            JdbcTemplate jdbcTemplate,
            @Value("${codeatlas.upload.scripts-dir:}") String scriptsDir,
            @Value("${codeatlas.upload.work-dir:}") String workDir,
            @Value("${codeatlas.upload.candidates-per-chunk:20}") int candidatesPerChunk,
            @Value("${codeatlas.upload.selected-per-chunk:5}") int selectedPerChunk,
            @Value("${codeatlas.upload.python-timeout-minutes:60}") long pythonTimeoutMinutes
    ) {
        this.embeddingBackfillService = embeddingBackfillService;
        this.curationBatchService = curationBatchService;
        this.jdbcTemplate = jdbcTemplate;
        this.scriptsDir = scriptsDir.isBlank() ? locateScriptsDir() : Path.of(scriptsDir);
        this.workRoot = workDir.isBlank()
                ? Path.of(System.getProperty("java.io.tmpdir"), "codeatlas-upload")
                : Path.of(workDir);
        this.candidatesPerChunk = candidatesPerChunk;
        this.selectedPerChunk = selectedPerChunk;
        this.pythonTimeoutMinutes = pythonTimeoutMinutes;
    }

    /** backend/ 에서 띄우든 저장소 루트에서 띄우든 scripts/ 를 찾는다. */
    private static Path locateScriptsDir() {
        Path dir = Path.of(System.getProperty("user.dir")).toAbsolutePath();
        while (dir != null) {
            Path candidate = dir.resolve("scripts");
            if (Files.exists(candidate.resolve("upload_pipeline.py"))) {
                return candidate;
            }
            dir = dir.getParent();
        }
        throw new IllegalStateException("scripts/upload_pipeline.py 를 찾지 못했습니다 — codeatlas.upload.scripts-dir 를 지정하세요");
    }

    // ── 제출 ─────────────────────────────────────────────────────

    public Job submitArxiv(String arxivId, String githubUrl, String relationType) {
        // URL·버전 접미사를 걷어내고 신형 ID 형식만 통과시킨다 — 이 값이 arXiv URL 두 곳과
        // SQL 리터럴(paper_id_of)에 들어가므로 형식 검증으로 그 부류의 문제를 통째로 막는다 (#54 리뷰).
        String normalized = arxivId == null ? "" : arxivId.trim()
                .replaceFirst("^https?://arxiv\\.org/(abs|pdf)/", "")
                .replaceFirst("\\.pdf$", "")
                .replaceFirst("v\\d+$", "");
        if (!normalized.matches("\\d{4}\\.\\d{4,5}")) {
            throw new IllegalArgumentException("arXiv ID 형식이 아닙니다 (예: 1505.04597): " + arxivId);
        }
        if (githubUrl == null || !githubUrl.matches("https?://github\\.com/[^/\\s]+/[^/\\s]+/?")) {
            throw new IllegalArgumentException("GitHub 저장소 URL 형식이 아닙니다: " + githubUrl);
        }
        String relation = (relationType == null || relationType.isBlank()) ? "OFFICIAL" : relationType;
        Job job = new Job("arxiv", normalized + " ← " + githubUrl.trim(), ARXIV_STAGES,
                Map.of("arxiv", normalized, "github", githubUrl.trim(), "relation", relation));
        return enqueue(job);
    }

    public Job submitJson(String fileName, String jsonBody) {
        if (jsonBody == null || jsonBody.isBlank()) {
            throw new IllegalArgumentException("업로드할 JSON 이 비어 있습니다");
        }
        Job job = new Job("json", fileName == null || fileName.isBlank() ? "ingest.json" : fileName, JSON_STAGES,
                Map.of("json", jsonBody));
        return enqueue(job);
    }

    private Job enqueue(Job job) {
        jobs.put(job.id, job);
        worker.submit(() -> run(job));
        return job;
    }

    public Optional<Job> get(String id) {
        return Optional.ofNullable(jobs.get(id));
    }

    /**
     * 파이썬 단계가 도는 작업을 취소한다. EMBEDDING·CURATION(JVM 내부)은 중단할 수 없다 —
     * 취소 가능 여부를 돌려주고, 화면이 그 이유를 보여준다.
     */
    public boolean cancel(String id) {
        Job job = jobs.get(id);
        if (job == null || job.status != Status.RUNNING) {
            return false;
        }
        Process p = job.currentProcess;
        if (p == null) {
            return false;   // 파이썬 단계가 아님 — 임베딩·큐레이션은 곧 끝난다
        }
        job.canceled.set(true);
        p.destroyForcibly();
        return true;
    }

    public List<Job> list() {
        List<Job> all = new ArrayList<>(jobs.values());
        Collections.reverse(all);
        return all;
    }

    // ── 실행 ─────────────────────────────────────────────────────

    private void run(Job job) {
        job.status = Status.RUNNING;
        job.startedAt = Instant.now();
        try {
            Path work = Files.createDirectories(workRoot.resolve(job.id));
            if ("arxiv".equals(job.type)) {
                runPython(job, List.of("upload_pipeline.py",
                        "--arxiv", job.args.get("arxiv"),
                        "--github", job.args.get("github"),
                        "--relation", job.args.get("relation"),
                        "--work", work.toString()));
            } else {
                Path file = work.resolve("ingest.json");
                Files.writeString(file, job.args.get("json"), StandardCharsets.UTF_8);
                job.enter("VALIDATE", "ingest.py --dry-run");
                runPython(job, List.of("ingest.py", file.toString(), "--dry-run"));
                job.enter("INGEST", "ingest.py");
                runPython(job, List.of("ingest.py", file.toString()));
            }

            job.enter("EMBEDDING", "새 chunk·code block 임베딩 (nomic-embed-text)");
            EmbeddingBackfillService.BackfillResult emb = embeddingBackfillService.backfillPending();
            job.log("   임베딩: chunk " + emb.chunks() + "건, code block " + emb.codeBlocks() + "건");

            job.enter("CURATION", "chunk 당 Qwen3 1회 — 설명 생성 (chunk 수 × 15~30초)");
            CurationBatchService.BatchResult cur = curateWithWait(job);
            job.log("   큐레이션 배치: chunk " + cur.chunksCurated() + "건, 건너뜀 " + cur.chunksSkipped()
                    + "건, 매핑 " + cur.mappingsCreated() + "건 (다른 논문의 pending 이 있었다면 함께 처리됨)");
            // 배치는 pending 전체를 돌므로, 이 작업의 수치는 업로드한 논문 기준으로 다시 센다 (#54 리뷰)
            if (job.paperId != null) {
                job.mappings = jdbcTemplate.queryForObject("""
                        SELECT count(*) FROM paper_code_mappings m
                        JOIN paper_chunks pc ON pc.id = m.paper_chunk_id
                        WHERE pc.paper_id = ?
                        """, Integer.class, job.paperId);
            } else {
                job.mappings = cur.mappingsCreated();
            }

            job.status = Status.DONE;
            job.stage = "DONE";
            job.log("✅ 완료" + (job.paperId != null ? " — paperId " + job.paperId : ""));
        } catch (Exception e) {
            if (job.canceled.get()) {
                job.status = Status.CANCELED;
                job.error = "사용자가 취소했습니다";
                job.log("⏹ 취소됨");
            } else {
                log.error("업로드 작업 실패 {}", job.id, e);
                job.status = Status.FAILED;
                job.error = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
                job.log("❌ " + job.error);
            }
        } finally {
            job.finishedAt = Instant.now();
            cleanupWorkDir(job);
        }
    }

    /**
     * 시연 전 점검이 curate-pending 을 직접 부르는 것과 겹치면 배치 가드(IllegalStateException)에
     * 걸린다 — 적재·임베딩까지 끝난 작업을 그 이유로 실패시키지 않고, 끝날 때까지 기다렸다 잇는다.
     */
    private CurationBatchService.BatchResult curateWithWait(Job job) throws InterruptedException {
        long deadline = System.currentTimeMillis() + TimeUnit.MINUTES.toMillis(120);
        boolean loggedWait = false;
        while (true) {
            try {
                return curationBatchService.curateAllPendingChunks(candidatesPerChunk, selectedPerChunk);
            } catch (IllegalStateException e) {
                if (System.currentTimeMillis() > deadline) {
                    throw new IllegalStateException("다른 큐레이션 배치가 120분 안에 끝나지 않았습니다", e);
                }
                if (!loggedWait) {
                    job.log("   다른 큐레이션 배치가 진행 중 — 끝나면 이어서 실행합니다");
                    loggedWait = true;
                }
                Thread.sleep(10_000);
            }
        }
    }

    /**
     * 클론한 저장소·LaTeX 소스는 수백 MB 가 될 수 있어 쌓아두지 않는다 — 성공하면 작업 디렉터리
     * 전체를, 실패하면 큰 것(repo·eprint)만 지우고 중간 JSON 은 사후 확인용으로 남긴다 (#54 리뷰).
     */
    private void cleanupWorkDir(Job job) {
        Path work = workRoot.resolve(job.id);
        try {
            if (job.status == Status.DONE) {
                FileSystemUtils.deleteRecursively(work);
            } else if (Files.exists(work)) {
                FileSystemUtils.deleteRecursively(work.resolve("repo"));
                FileSystemUtils.deleteRecursively(work.resolve("eprint"));
                job.log("   중간 파일 보관: " + work);
            }
        } catch (IOException e) {
            log.warn("작업 디렉터리 정리 실패 {}", work, e);
        }
    }

    private void runPython(Job job, List<String> scriptAndArgs) throws IOException, InterruptedException {
        List<String> cmd = new ArrayList<>();
        cmd.add("python3");
        cmd.add(scriptsDir.resolve(scriptAndArgs.get(0)).toString());
        cmd.addAll(scriptAndArgs.subList(1, scriptAndArgs.size()));

        ProcessBuilder pb = new ProcessBuilder(cmd).directory(scriptsDir.toFile()).redirectErrorStream(true);
        pb.environment().putIfAbsent("PYTHONUNBUFFERED", "1");
        Process p = pb.start();
        job.currentProcess = p;
        // 전체 타임아웃 — LLM 이 물리면 스크립트가 몇 시간을 붙잡을 수 있고, 워커가 하나라
        // 그 뒤의 작업이 전부 정지한다. /api/agent/answer 의 60초 하드 타임아웃과 같은 이유 (#54 리뷰).
        AtomicBoolean timedOut = new AtomicBoolean(false);
        Thread watchdog = new Thread(() -> {
            try {
                if (!p.waitFor(pythonTimeoutMinutes, TimeUnit.MINUTES)) {
                    timedOut.set(true);
                    p.destroyForcibly();
                }
            } catch (InterruptedException ignored) {
                // 프로세스가 정상 종료해 감시가 더 필요 없는 경우
            }
        }, "upload-watchdog-" + job.id);
        watchdog.setDaemon(true);
        watchdog.start();
        String lastLine = "";
        try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = r.readLine()) != null) {
                Matcher stage = STAGE_LINE.matcher(line);
                Matcher result = RESULT_LINE.matcher(line);
                if (stage.matches()) {
                    job.enter(stage.group(1), stage.group(2));
                } else if (result.find()) {
                    job.paperId = Long.parseLong(result.group(1));
                    if (result.group(2) != null) job.chunks = Integer.parseInt(result.group(2));
                    if (result.group(3) != null) job.codeBlocks = Integer.parseInt(result.group(3));
                    job.log("   적재 완료 — paperId " + job.paperId);
                } else if (!line.isBlank()) {
                    job.log(line);
                    lastLine = line.trim();
                }
            }
        }
        int code = p.waitFor();
        job.currentProcess = null;
        watchdog.interrupt();
        if (timedOut.get()) {
            throw new IllegalStateException(scriptAndArgs.get(0) + " 가 " + pythonTimeoutMinutes + "분 안에 끝나지 않아 중단했습니다");
        }
        if (code != 0) {
            throw new IllegalStateException(lastLine.isBlank() ? scriptAndArgs.get(0) + " 실패 (exit " + code + ")" : lastLine);
        }
    }
}
