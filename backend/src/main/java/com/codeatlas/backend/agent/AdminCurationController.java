package com.codeatlas.backend.agent;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * ⚠️ 인증 없는 내부용 엔드포인트입니다. 데모/개발 환경에서만 쓰고,
 * 실제 배포 시에는 최소한 profile 분리나 admin 인증을 추가하세요.
 *
 * chunk 1건당 Qwen3 호출이 한 번씩 들어가므로 대상이 많으면 수 분 이상 걸립니다.
 * 진행 상황은 서버 로그(CurationBatchService) 또는 GET /api/admin/curate-status 로 봅니다.
 *
 * 배치는 한 번에 하나만 돕니다 — 이미 돌고 있으면 409 를 돌려줍니다.
 * curl 을 Ctrl-C 해도 서버 핸들러는 계속 돌기 때문에, 멈춘 것처럼 보인다고 다시 호출하면
 * 배치가 두 개가 되어 같은 chunk 를 중복 처리합니다(2026-08-08 에 실제로 발생).
 */
@RestController
public class AdminCurationController {

    private final CurationBatchService curationBatchService;

    public AdminCurationController(CurationBatchService curationBatchService) {
        this.curationBatchService = curationBatchService;
    }

    @PostMapping("/api/admin/curate-pending")
    public ResponseEntity<?> curatePending(
            // 기본값은 AgentQueryController 라이브 경로와 동일 기준 (후보 20개 → 상위 5개)
            @RequestParam(defaultValue = "20") int candidatesPerChunk,
            @RequestParam(defaultValue = "5") int selectedPerChunk
    ) {
        try {
            return ResponseEntity.ok(
                    curationBatchService.curateAllPendingChunks(candidatesPerChunk, selectedPerChunk));
        } catch (IllegalStateException alreadyRunning) {
            CurationBatchService.Progress p = curationBatchService.currentProgress();
            return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of(
                    "status", 409,
                    "error", "Conflict",
                    "message", alreadyRunning.getMessage(),
                    "progress", p != null ? Map.of("done", p.done(), "total", p.total()) : Map.of()));
        }
    }

    /** 배치가 도는지 / 어디까지 갔는지. 중복 호출 전에 이걸로 확인하세요. */
    @GetMapping("/api/admin/curate-status")
    public Map<String, Object> curateStatus() {
        CurationBatchService.Progress p = curationBatchService.currentProgress();
        return p == null
                ? Map.of("running", false)
                : Map.of("running", true, "done", p.done(), "total", p.total());
    }
}
