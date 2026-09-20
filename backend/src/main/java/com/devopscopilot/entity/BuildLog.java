package com.devopscopilot.entity;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "build_logs")
public class BuildLog {
    @Id @GeneratedValue private UUID id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false) @JoinColumn(name = "user_id", nullable = false) private User user;
    @Column(name = "original_filename", nullable = false, length = 255) private String originalFilename;
    @Column(name = "content_type", nullable = false, length = 100) private String contentType;
    @Column(name = "log_content", nullable = false, columnDefinition = "TEXT") private String logContent;
    @Column(name = "content_sha256", nullable = false, length = 64) private String contentSha256;
    @Enumerated(EnumType.STRING) @Column(name = "source_type", nullable = false, length = 30) private LogSourceType sourceType;
    @Enumerated(EnumType.STRING) @Column(name = "upload_status", nullable = false, length = 30) private UploadStatus uploadStatus;
    @Column(name = "uploaded_at", nullable = false, updatable = false) private Instant uploadedAt;

    protected BuildLog() { }
    @PrePersist void initializeUploadedAt() { uploadedAt = Instant.now(); }
    public void markAnalyzing() { uploadStatus = UploadStatus.ANALYZING; }
    public void markAnalyzed() { uploadStatus = UploadStatus.ANALYZED; }
    public void markFailed() { uploadStatus = UploadStatus.FAILED; }
    public static BuildLog create(User user, String originalFilename, String contentType, String logContent,
                                  String contentSha256, LogSourceType sourceType) {
        BuildLog buildLog = new BuildLog();
        buildLog.user = user;
        buildLog.originalFilename = originalFilename;
        buildLog.contentType = contentType;
        buildLog.logContent = logContent;
        buildLog.contentSha256 = contentSha256;
        buildLog.sourceType = sourceType;
        buildLog.uploadStatus = UploadStatus.UPLOADED;
        return buildLog;
    }
    public UUID getId() { return id; }
    public String getOriginalFilename() { return originalFilename; }
    public String getContentType() { return contentType; }
    public String getLogContent() { return logContent; }
    public String getContentSha256() { return contentSha256; }
    public LogSourceType getSourceType() { return sourceType; }
    public UploadStatus getUploadStatus() { return uploadStatus; }
    public Instant getUploadedAt() { return uploadedAt; }
}
