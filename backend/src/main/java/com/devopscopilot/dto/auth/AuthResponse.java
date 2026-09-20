package com.devopscopilot.dto.auth;

import java.util.UUID;

public record AuthResponse(String accessToken, String tokenType, long expiresInSeconds, UUID userId, String fullName, String email) {
}
