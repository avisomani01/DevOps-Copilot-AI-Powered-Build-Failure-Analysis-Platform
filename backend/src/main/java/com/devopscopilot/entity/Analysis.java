package com.devopscopilot.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "analyses")
public class Analysis {
    @Id @GeneratedValue private UUID id;
    @OneToOne(fetch = FetchType.LAZY, optional = false) @JoinColumn(name = "build_log_id", nullable = false, unique = true) private BuildLog buildLog;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "incident_pattern_id") private IncidentPattern incidentPattern;
    @Enumerated(EnumType.STRING) @Column(nullable = false, length = 30) private AnalysisStatus status = AnalysisStatus.PENDING;
    @Enumerated(EnumType.STRING) @Column(name = "error_category", length = 50) private ErrorCategory errorCategory;
    @Column(name = "confidence_score", precision = 5, scale = 2) private BigDecimal confidenceScore;
    @Column(columnDefinition = "TEXT") private String summary;
    @Column(name = "root_cause", columnDefinition = "TEXT") private String rootCause;
    @JdbcTypeCode(SqlTypes.JSON) @Column(name = "extracted_errors", nullable = false, columnDefinition = "jsonb") private List<String> extractedErrors;
    @JdbcTypeCode(SqlTypes.JSON) @Column(name = "suggested_fixes", nullable = false, columnDefinition = "jsonb") private List<String> suggestedFixes;
    @Enumerated(EnumType.STRING) @Column(name = "analyzer_type", length = 30) private AnalyzerType analyzerType;
    @Column(name = "failure_reason", columnDefinition = "TEXT") private String failureReason;
    @Column(name = "analyzed_at") private Instant analyzedAt;
    @Column(name = "created_at", nullable = false, updatable = false) private Instant createdAt;
    @Column(name = "updated_at", nullable = false) private Instant updatedAt;

    protected Analysis() { }
    @PrePersist void initializeTimestamps() { createdAt = Instant.now(); updatedAt = createdAt; }
    @PreUpdate void updateTimestamp() { updatedAt = Instant.now(); }
    public static Analysis create(BuildLog buildLog) {
        Analysis analysis = new Analysis();
        analysis.buildLog = buildLog;
        analysis.extractedErrors = List.of();
        analysis.suggestedFixes = List.of();
        return analysis;
    }
    public void complete(IncidentPattern incident, ErrorCategory category, BigDecimal confidence, String summary,
                         String rootCause, List<String> errors, List<String> fixes, AnalyzerType type) {
        status = AnalysisStatus.COMPLETED;
        incidentPattern = incident;
        errorCategory = category;
        confidenceScore = confidence;
        this.summary = summary;
        this.rootCause = rootCause;
        extractedErrors = List.copyOf(errors);
        suggestedFixes = List.copyOf(fixes);
        analyzerType = type;
        analyzedAt = Instant.now();
        failureReason = null;
    }
    public void fail(String reason) { status = AnalysisStatus.FAILED; failureReason = reason; analyzedAt = Instant.now(); }
    public UUID getId() { return id; }
    public AnalysisStatus getStatus() { return status; }
    public ErrorCategory getErrorCategory() { return errorCategory; }
    public BigDecimal getConfidenceScore() { return confidenceScore; }
    public String getSummary() { return summary; }
    public String getRootCause() { return rootCause; }
    public List<String> getExtractedErrors() { return extractedErrors; }
    public List<String> getSuggestedFixes() { return suggestedFixes; }
    public AnalyzerType getAnalyzerType() { return analyzerType; }
    public String getFailureReason() { return failureReason; }
    public Instant getAnalyzedAt() { return analyzedAt; }
    public IncidentPattern getIncidentPattern() { return incidentPattern; }
    public BuildLog getBuildLog() { return buildLog; }
}
