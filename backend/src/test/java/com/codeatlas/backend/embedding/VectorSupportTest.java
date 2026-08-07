package com.codeatlas.backend.embedding;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class VectorSupportTest {

    @Test
    @DisplayName("float[]을 pgvector 리터럴로 변환한다")
    void formatsVectorLiteral() {
        assertThat(VectorSupport.toVectorLiteral(new float[] {0.1f, -0.25f, 3.0f}))
                .isEqualTo("[0.1,-0.25,3.0]");
    }

    @Test
    @DisplayName("빈 벡터도 유효한 리터럴을 만든다")
    void formatsEmptyVector() {
        assertThat(VectorSupport.toVectorLiteral(new float[0])).isEqualTo("[]");
    }
}
