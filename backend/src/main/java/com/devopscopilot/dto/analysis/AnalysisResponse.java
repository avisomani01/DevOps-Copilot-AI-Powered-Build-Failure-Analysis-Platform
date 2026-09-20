package com.devopscopilot.dto.analysis;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record AnalysisResponse(UUID id, UUID buildLogId, String status, String errorCategory, BigDecimal confidenceScore,
                               String summary, String rootCause, List<String> extractedErrors, List<String> suggestedFixes,
                               String analyzerType, String failureReason, int incidentOccurrenceCount, Instant analyzedAt) {
}
