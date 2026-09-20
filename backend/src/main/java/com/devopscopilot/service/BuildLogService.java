package com.devopscopilot.service;

import com.devopscopilot.dto.log.BuildLogDetailResponse;
import com.devopscopilot.dto.log.BuildLogResponse;
import com.devopscopilot.dto.log.PageResponse;
import com.devopscopilot.entity.BuildLog;
import com.devopscopilot.entity.LogSourceType;
import com.devopscopilot.entity.User;
import com.devopscopilot.exception.InvalidLogException;
import com.devopscopilot.exception.ResourceNotFoundException;
import com.devopscopilot.repository.BuildLogRepository;
import com.devopscopilot.repository.UserRepository;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Locale;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

@Service
public class BuildLogService {
    private static final long MAX_LOG_SIZE_BYTES = 2L * 1024 * 1024;
    private final BuildLogRepository buildLogRepository;
    private final UserRepository userRepository;

    public BuildLogService(BuildLogRepository buildLogRepository, UserRepository userRepository) {
        this.buildLogRepository = buildLogRepository;
        this.userRepository = userRepository;
    }

    @Transactional
    public BuildLogResponse upload(String authenticatedEmail, MultipartFile file) {
        validateFileMetadata(file);
        byte[] bytes = readBytes(file);
        String content = decodeUtf8(bytes);
        if (content.isBlank() || content.indexOf('\0') >= 0) throw new InvalidLogException("Log file must contain readable text");

        User user = userRepository.findByEmailIgnoreCase(authenticatedEmail)
                .orElseThrow(() -> new ResourceNotFoundException("Authenticated user no longer exists"));
        String filename = sanitizeFilename(file.getOriginalFilename());
        BuildLog saved = buildLogRepository.save(BuildLog.create(user, filename, normalizeContentType(file.getContentType()),
                content, sha256(bytes), detectSourceType(filename, content)));
        return toResponse(saved);
    }

    @Transactional(readOnly = true)
    public PageResponse<BuildLogResponse> list(String authenticatedEmail, Pageable pageable) {
        User user = userRepository.findByEmailIgnoreCase(authenticatedEmail)
                .orElseThrow(() -> new ResourceNotFoundException("Authenticated user no longer exists"));
        Page<BuildLog> page = buildLogRepository.findByUserIdOrderByUploadedAtDesc(user.getId(), pageable);
        return new PageResponse<>(page.map(this::toResponse).getContent(), page.getNumber(), page.getSize(),
                page.getTotalElements(), page.getTotalPages());
    }

    @Transactional(readOnly = true)
    public BuildLogDetailResponse getOwnedLog(String authenticatedEmail, UUID logId) {
        User user = userRepository.findByEmailIgnoreCase(authenticatedEmail)
                .orElseThrow(() -> new ResourceNotFoundException("Authenticated user no longer exists"));
        BuildLog log = buildLogRepository.findByIdAndUserId(logId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Build log not found"));
        return new BuildLogDetailResponse(log.getId(), log.getOriginalFilename(), log.getSourceType().name(),
                log.getUploadStatus().name(), log.getContentSha256(), log.getUploadedAt());
    }

    private void validateFileMetadata(MultipartFile file) {
        if (file == null || file.isEmpty()) throw new InvalidLogException("Please choose a non-empty text-based file");
        if (file.getSize() > MAX_LOG_SIZE_BYTES) throw new InvalidLogException("File must not exceed 2 MB");
    }

    private byte[] readBytes(MultipartFile file) {
        try { return file.getBytes(); }
        catch (IOException exception) { throw new InvalidLogException("Unable to read uploaded file"); }
    }

    private String decodeUtf8(byte[] bytes) {
        try {
            return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
        } catch (CharacterCodingException exception) { throw new InvalidLogException("Log file must be UTF-8 plain text"); }
    }

    private String sanitizeFilename(String originalFilename) {
        String filename = StringUtils.cleanPath(originalFilename);
        filename = filename.substring(filename.lastIndexOf('/') + 1).substring(filename.lastIndexOf('\\') + 1);
        if (filename.isBlank() || filename.length() > 255) throw new InvalidLogException("Invalid file name");
        return filename;
    }

    private String normalizeContentType(String contentType) { return contentType == null ? "text/plain" : contentType.substring(0, Math.min(100, contentType.length())); }
    private String sha256(byte[] content) { try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content)); } catch (NoSuchAlgorithmException exception) { throw new IllegalStateException("SHA-256 is unavailable", exception); } }

    private LogSourceType detectSourceType(String filename, String content) {
        String text = content.toLowerCase(Locale.ROOT);
        String name = filename.toLowerCase(Locale.ROOT);
        if (text.contains("maven") || text.contains("pom.xml")) return LogSourceType.MAVEN;
        if (text.contains("gradle") || text.contains("build.gradle")) return LogSourceType.GRADLE;
        if (text.contains("dockerfile") || text.contains("docker build")) return LogSourceType.DOCKER;
        if (text.contains("jenkins") || text.contains("hudson.")) return LogSourceType.JENKINS;
        if (name.endsWith(".py") || text.contains("modulenotfounderror") || text.contains("traceback")) return LogSourceType.PYTHON;
        if (name.endsWith(".java") || text.contains("javac") || text.contains("cannot find symbol")) return LogSourceType.JAVA;
        return LogSourceType.GENERIC;
    }

    private BuildLogResponse toResponse(BuildLog log) { return new BuildLogResponse(log.getId(), log.getOriginalFilename(), log.getSourceType().name(), log.getUploadStatus().name(), log.getUploadedAt()); }
}
