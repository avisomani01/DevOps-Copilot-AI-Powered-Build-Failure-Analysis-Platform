package com.devopscopilot.dto.incident;

import java.time.Instant;
import java.util.UUID;

public record IncidentSearchResponse(UUID analysisId, UUID buildLogId, String filename, String category,
                                     String summary, String rootCause, int occurrenceCount, Instant analyzedAt) {
}
