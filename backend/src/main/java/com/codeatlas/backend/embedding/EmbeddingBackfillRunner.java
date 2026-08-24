package com.codeatlas.backend.embedding;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * 기동 시 embedding 이 비어 있는 행을 채우는 스위치. 실제 작업은
 * {@link EmbeddingBackfillService} — 업로드 작업(UploadJobService)도 같은 서비스를
 * 호출하므로 seed 복원 후의 backfill 과 업로드 직후의 backfill 이 같은 코드를 탄다.
 *
 * 기본값은 꺼져 있고, application.yml 의
 *   codeatlas.embedding.backfill-on-startup: true
 * 또는 환경변수 CODEATLAS_EMBEDDING_BACKFILL=true 일 때만 동작합니다.
 */
@Component
@ConditionalOnProperty(name = "codeatlas.embedding.backfill-on-startup", havingValue = "true")
public class EmbeddingBackfillRunner implements ApplicationRunner {

    private final EmbeddingBackfillService service;

    public EmbeddingBackfillRunner(EmbeddingBackfillService service) {
        this.service = service;
    }

    @Override
    public void run(ApplicationArguments args) {
        service.backfillPending();
    }
}
