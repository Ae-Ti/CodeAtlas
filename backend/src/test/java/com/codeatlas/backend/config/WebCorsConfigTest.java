package com.codeatlas.backend.config;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 프론트를 5173 이 아닌 포트에 띄우면 모든 POST 가 403 으로 막히던 회귀를 고정합니다.
 *
 * <p>발견 경위 — #51/#52 를 검증하려고 프론트를 5174 에 한 벌 더 띄웠더니 화면은 정상인데
 * Agent 질의·NL2SQL·답변 생성만 죽었습니다. 원인은 이렇습니다.
 *
 * <ul>
 *   <li>브라우저는 같은 출처라도 <b>POST 에는 {@code Origin} 헤더를 붙이고 GET 에는 안 붙입니다.</b>
 *       그래서 논문·대시보드·그래프(전부 GET)는 멀쩡하고 POST 만 403 이 됩니다 — 앱이
 *       살아있어 보이는 채로 AI 기능만 전부 죽는, 원인을 찾기 어려운 모양이 됩니다.</li>
 *   <li>vite 프록시를 거쳐도 {@code changeOrigin: true} 가 바꾸는 건 Host 뿐이라
 *       {@code Origin} 은 그대로 백엔드에 도달합니다. "프록시를 쓰니 CORS 와 무관하다"가
 *       성립하지 않습니다.</li>
 *   <li>vite 는 5173 이 사용 중이면 <b>말없이</b> 다음 포트로 올라갑니다. 시연 당일 5173 을
 *       물고 있는 프로세스 하나로 그대로 재현됩니다.</li>
 * </ul>
 *
 * <p>그래서 이 테스트는 두 가지를 같이 봅니다 — <b>localhost 면 포트가 무엇이든 통과</b>하고,
 * <b>localhost 가 아니면 막힌다</b>는 것. 포트 와일드카드를 열면서 문을 너무 크게 연 건
 * 아닌지가 나머지 절반이라 함께 고정합니다.
 *
 * <p>허용 목록은 하드코딩하지 않고 {@code application.yml} 의 기본값을 그대로 읽습니다.
 * 하드코딩하면 설정을 되돌려도 테스트가 통과해 버려서, 정작 막으려던 회귀를 못 막습니다.
 * Spring 컨텍스트·DB·Ollama 없이 도는 것은 나머지 테스트와 같습니다.
 */
class WebCorsConfigTest {

    /** {@link CorsRegistry#getCorsConfigurations()} 가 protected 라 하위 클래스로 꺼냅니다. */
    private static class ExposedRegistry extends CorsRegistry {
        Map<String, CorsConfiguration> configs() {
            return getCorsConfigurations();
        }
    }

    private static CorsConfiguration apiConfig() throws IOException {
        ExposedRegistry registry = new ExposedRegistry();
        new WebCorsConfig(shippedDefaultOrigins()).addCorsMappings(registry);
        CorsConfiguration config = registry.configs().get("/api/**");
        assertThat(config).as("/api/** 매핑이 등록돼 있어야 합니다").isNotNull();
        return config;
    }

    /** application.yml 의 {@code codeatlas.cors.allowed-origins} 기본값을 읽습니다. */
    private static String[] shippedDefaultOrigins() throws IOException {
        String yml;
        try (InputStream in = WebCorsConfigTest.class.getResourceAsStream("/application.yml")) {
            assertThat(in).as("application.yml 이 테스트 classpath 에 있어야 합니다").isNotNull();
            yml = new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
        Matcher line = Pattern.compile("(?m)^\\s*allowed-origins:\\s*(.+)$").matcher(yml);
        assertThat(line.find())
                .as("application.yml 에 codeatlas.cors.allowed-origins 가 있어야 합니다")
                .isTrue();
        String value = line.group(1).replaceAll("\\s+#.*$", "").trim();
        // ${ENV:기본값} 형태면 기본값만 꺼냅니다. 평문이면 그대로 씁니다 — 설정을 어느 형태로
        // 되돌리든 아래 단언이 실제 허용 목록을 보고 실패해야 하기 때문입니다.
        Matcher placeholder = Pattern.compile("^\\$\\{[^:}]+:(.*)}$").matcher(value);
        if (placeholder.matches()) {
            value = placeholder.group(1);
        }
        return value.trim().split("\\s*,\\s*");
    }

    @Test
    @DisplayName("vite 기본 포트 5173 은 허용된다")
    void allowsDefaultVitePort() throws IOException {
        assertThat(apiConfig().checkOrigin("http://localhost:5173")).isEqualTo("http://localhost:5173");
    }

    @Test
    @DisplayName("5173 이 아닌 포트도 허용된다 — 이게 막히면 모든 POST 가 403 이 된다")
    void allowsAnyLocalhostPort() throws IOException {
        CorsConfiguration config = apiConfig();
        // 5174: vite 가 5173 을 못 잡았을 때 올라가는 포트. 4173: vite preview.
        assertThat(config.checkOrigin("http://localhost:5174")).isEqualTo("http://localhost:5174");
        assertThat(config.checkOrigin("http://localhost:4173")).isEqualTo("http://localhost:4173");
        assertThat(config.checkOrigin("http://127.0.0.1:5174")).isEqualTo("http://127.0.0.1:5174");
    }

    @Test
    @DisplayName("localhost 가 아니면 막힌다 — 포트 와일드카드가 문을 넓히지 않았는지")
    void rejectsNonLocalhostOrigins() throws IOException {
        CorsConfiguration config = apiConfig();
        assertThat(config.checkOrigin("http://evil.example.com")).isNull();
        // localhost 를 접두어로 삼은 사칭 호스트 — 패턴이 호스트 경계를 지키는지
        assertThat(config.checkOrigin("http://localhost.evil.example.com")).isNull();
        assertThat(config.checkOrigin("http://notlocalhost:5173")).isNull();
    }

    @Test
    @DisplayName("POST 가 허용 메서드에 있다 — 403 이 POST 에서만 났던 자리")
    void allowsPost() throws IOException {
        assertThat(apiConfig().checkHttpMethod(org.springframework.http.HttpMethod.POST))
                .contains(org.springframework.http.HttpMethod.POST);
    }
}
