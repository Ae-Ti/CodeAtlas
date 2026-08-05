package com.codeatlas.backend.embedding;

/**
 * pgvector 바인딩 헬퍼.
 * JDBC 드라이버는 vector 타입을 모르므로, 문자열 리터럴로 넘긴 뒤 SQL에서 {@code ?::vector} 로 캐스팅합니다.
 */
public final class VectorSupport {

    private VectorSupport() {}

    /** float[] → pgvector 리터럴 {@code [0.1,0.2,...]} */
    public static String toVectorLiteral(float[] embedding) {
        StringBuilder sb = new StringBuilder(embedding.length * 12 + 2);
        sb.append('[');
        for (int i = 0; i < embedding.length; i++) {
            if (i > 0) {
                sb.append(',');
            }
            sb.append(embedding[i]);
        }
        return sb.append(']').toString();
    }
}
