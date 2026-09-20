package com.devopscopilot.dto.log;

import java.time.Instant;
import java.util.UUID;

public record BuildLogDetailResponse(UUID id, String originalFilename, String sourceType, String uploadStatus,
                                     String contentSha256, Instant uploadedAt) {
}
