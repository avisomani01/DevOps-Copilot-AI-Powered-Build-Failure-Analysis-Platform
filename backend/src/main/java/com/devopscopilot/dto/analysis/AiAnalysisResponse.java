package com.devopscopilot.dto.analysis;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.util.List;

public record AiAnalysisResponse(
        @JsonProperty("error_category") String errorCategory,
        @JsonProperty("confidence_score") BigDecimal confidenceScore,
        String summary,
        @JsonProperty("root_cause") String rootCause,
        @JsonProperty("extracted_errors") List<String> extractedErrors,
        @JsonProperty("suggested_fixes") List<String> suggestedFixes,
        String fingerprint,
        @JsonProperty("analyzer_type") String analyzerType
) {
}
