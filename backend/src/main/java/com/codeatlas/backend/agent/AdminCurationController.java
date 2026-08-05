package com.codeatlas.backend.agent;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * ⚠️ 인증 없는 내부용 엔드포인트입니다. 데모/개발 환경에서만 쓰고,
 * 실제 배포 시에는 최소한 profile 분리나 admin 인증을 추가하세요.
 *
 * chunk 1건당 Qwen3 호출이 한 번씩 들어가므로 대상이 많으면 수 분 이상 걸립니다.
 * 진행 상황은 서버 로그(CurationBatchService)에서 확인하세요.
 */
@RestController
public class AdminCurationController {

    private final CurationBatchService curationBatchService;

    public AdminCurationController(CurationBatchService curationBatchService) {
        this.curationBatchService = curationBatchService;
    }

    @PostMapping("/api/admin/curate-pending")
    public CurationBatchService.BatchResult curatePending(
            // 기본값은 AgentQueryController 라이브 경로와 동일 기준 (후보 20개 → 상위 5개)
            @RequestParam(defaultValue = "20") int candidatesPerChunk,
            @RequestParam(defaultValue = "5") int selectedPerChunk
    ) {
        return curationBatchService.curateAllPendingChunks(candidatesPerChunk, selectedPerChunk);
    }
}
