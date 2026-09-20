package com.devopscopilot.entity;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "incident_patterns")
public class IncidentPattern {
    @Id @GeneratedValue private UUID id;
    @Column(nullable = false, unique = true, length = 128) private String fingerprint;
    @Enumerated(EnumType.STRING) @Column(name = "error_category", nullable = false, length = 50) private ErrorCategory errorCategory;
    @Column(nullable = false) private String title;
    @Column(name = "root_cause", nullable = false) private String rootCause;
    @JdbcTypeCode(SqlTypes.JSON) @Column(name = "recommended_fixes", nullable = false, columnDefinition = "jsonb") private List<String> recommendedFixes;
    @Column(name = "occurrence_count", nullable = false) private int occurrenceCount;
    @Column(name = "first_seen_at", nullable = false) private Instant firstSeenAt;
    @Column(name = "last_seen_at", nullable = false) private Instant lastSeenAt;
    @Column(name = "created_at", nullable = false, updatable = false) private Instant createdAt;
    @Column(name = "updated_at", nullable = false) private Instant updatedAt;

    protected IncidentPattern() { }
    public static IncidentPattern create(String fingerprint, ErrorCategory category, String title, String rootCause,
                                         List<String> recommendedFixes) {
        IncidentPattern incident = new IncidentPattern();
        incident.fingerprint = fingerprint;
        incident.errorCategory = category;
        incident.title = title;
        incident.rootCause = rootCause;
        incident.recommendedFixes = List.copyOf(recommendedFixes);
        incident.occurrenceCount = 1;
        incident.firstSeenAt = Instant.now();
        incident.lastSeenAt = incident.firstSeenAt;
        incident.createdAt = incident.firstSeenAt;
        incident.updatedAt = incident.firstSeenAt;
        return incident;
    }
    public void recordOccurrence() { occurrenceCount++; lastSeenAt = Instant.now(); }
    public UUID getId() { return id; }
    public int getOccurrenceCount() { return occurrenceCount; }
}
