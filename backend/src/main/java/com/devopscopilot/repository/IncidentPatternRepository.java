package com.devopscopilot.repository;

import com.devopscopilot.entity.ErrorCategory;
import com.devopscopilot.entity.IncidentPattern;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IncidentPatternRepository extends JpaRepository<IncidentPattern, UUID> {
    Optional<IncidentPattern> findByFingerprint(String fingerprint);
    List<IncidentPattern> findTop10ByErrorCategoryOrderByLastSeenAtDesc(ErrorCategory errorCategory);
}
