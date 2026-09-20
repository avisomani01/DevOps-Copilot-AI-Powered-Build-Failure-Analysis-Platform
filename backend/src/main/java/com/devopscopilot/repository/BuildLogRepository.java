package com.devopscopilot.repository;

import com.devopscopilot.entity.BuildLog;
import java.util.UUID;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BuildLogRepository extends JpaRepository<BuildLog, UUID> {
    Page<BuildLog> findByUserIdOrderByUploadedAtDesc(UUID userId, Pageable pageable);
    Optional<BuildLog> findByIdAndUserId(UUID id, UUID userId);
    long countByUserId(UUID userId);
}
