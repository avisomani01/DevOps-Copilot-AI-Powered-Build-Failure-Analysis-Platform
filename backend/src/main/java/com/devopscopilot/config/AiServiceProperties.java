package com.devopscopilot.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.ai-service")
public record AiServiceProperties(String baseUrl, int connectTimeoutSeconds, int readTimeoutSeconds) {
}
