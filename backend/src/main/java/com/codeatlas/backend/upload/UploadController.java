package com.codeatlas.backend.upload;

import com.codeatlas.backend.common.NotFoundException;
import com.codeatlas.backend.upload.UploadJobService.Job;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;

/**
 * 업로드 페이지용 API. 인증 없는 내부용 — curate-pending 과 같은 전제(로컬 데모 환경).
 *
 *   POST /api/admin/upload              {arxivId, githubUrl, relationType?}  → 작업 생성
 *   POST /api/admin/upload/ingest-json  본문 = ingest JSON, ?fileName=       → 작업 생성
 *   GET  /api/admin/upload/{id}          작업 상태 (화면이 2초마다 폴링)
 *   GET  /api/admin/upload               작업 목록 (최신순)
 */
@RestController
public class UploadController {

    private final UploadJobService service;

    public UploadController(UploadJobService service) {
        this.service = service;
    }

    public record ArxivUploadRequest(String arxivId, String githubUrl, String relationType) {}

    public record JobView(
            String id, String type, String label, String status, String stage, String stageMessage,
            List<String> stages, Instant createdAt, Instant startedAt, Instant finishedAt,
            Long paperId, Integer chunks, Integer codeBlocks, Integer mappings, String error,
            List<String> log
    ) {
        static JobView of(Job j, boolean withLog) {
            return new JobView(j.id, j.type, j.label, j.status.name(), j.stage, j.stageMessage, j.stages,
                    j.createdAt, j.startedAt, j.finishedAt, j.paperId, j.chunks, j.codeBlocks, j.mappings, j.error,
                    withLog ? List.copyOf(j.logLines) : List.of());
        }
    }

    @PostMapping("/api/admin/upload")
    public JobView submitArxiv(@RequestBody ArxivUploadRequest request) {
        return JobView.of(service.submitArxiv(request.arxivId(), request.githubUrl(), request.relationType()), false);
    }

    @PostMapping(value = "/api/admin/upload/ingest-json", consumes = "application/json")
    public JobView submitJson(@RequestBody String body, @RequestParam(required = false) String fileName) {
        return JobView.of(service.submitJson(fileName, body), false);
    }

    @GetMapping("/api/admin/upload/{id}")
    public JobView get(@PathVariable String id) {
        return service.get(id).map(j -> JobView.of(j, true))
                .orElseThrow(() -> new NotFoundException("업로드 작업을 찾을 수 없습니다: " + id));
    }

    @GetMapping("/api/admin/upload")
    public List<JobView> list() {
        return service.list().stream().map(j -> JobView.of(j, false)).toList();
    }
}
