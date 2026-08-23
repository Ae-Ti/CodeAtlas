package com.codeatlas.backend.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * vite dev server 에서 /api/** 를 호출할 수 있게 CORS를 엽니다.
 *
 * 허용 목록은 {@code allowedOriginPatterns} 로 읽습니다 — {@code http://localhost:[*]} 처럼
 * 포트 와일드카드를 쓰기 위해서입니다. 정확한 오리진만 받는 {@code allowedOrigins} 로 두면
 * 프론트를 5173 이 아닌 포트에 띄우는 순간 모든 POST 가 403 으로 막힙니다 (vite 프록시를
 * 거쳐도 브라우저의 Origin 헤더는 그대로 백엔드에 도달합니다).
 */
@Configuration
public class WebCorsConfig implements WebMvcConfigurer {

    private final String[] allowedOrigins;

    public WebCorsConfig(@Value("${codeatlas.cors.allowed-origins}") String[] allowedOrigins) {
        this.allowedOrigins = allowedOrigins;
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOriginPatterns(allowedOrigins)
                .allowedMethods("GET", "POST", "OPTIONS");
    }
}
