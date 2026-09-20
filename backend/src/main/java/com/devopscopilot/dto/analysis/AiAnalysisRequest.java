package com.devopscopilot.dto.analysis;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiAnalysisRequest(@JsonProperty("log_content") String logContent,
                                @JsonProperty("source_type") String sourceType) {
}
