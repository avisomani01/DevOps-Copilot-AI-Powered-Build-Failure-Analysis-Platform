package com.devopscopilot.dto.log;

import java.time.Instant;
import java.util.UUID;

public record BuildLogResponse(UUID id, String originalFilename, String sourceType, String uploadStatus, Instant uploadedAt) {
}
