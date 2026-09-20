package com.devopscopilot.repository;

import com.devopscopilot.entity.Analysis;
import com.devopscopilot.entity.AnalysisStatus;
import com.devopscopilot.entity.ErrorCategory;
import java.util.Optional;
import java.util.UUID;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AnalysisRepository extends JpaRepository<Analysis, UUID> {
    Optional<Analysis> findByBuildLogId(UUID buildLogId);
    long countByBuildLogUserIdAndStatus(UUID userId, AnalysisStatus status);
    long countByBuildLogUserIdAndStatusAndErrorCategory(UUID userId, AnalysisStatus status, ErrorCategory errorCategory);

    @Query("select a.errorCategory, count(a) from Analysis a where a.buildLog.user.id = :userId and a.status = :status group by a.errorCategory order by count(a) desc")
    List<Object[]> countCategoriesByUserAndStatus(@Param("userId") UUID userId, @Param("status") AnalysisStatus status);

    @Query(value = "select a from Analysis a join fetch a.buildLog where a.buildLog.user.id = :userId and a.status = :status and (:category is null or a.errorCategory = :category) order by a.analyzedAt desc",
           countQuery = "select count(a) from Analysis a where a.buildLog.user.id = :userId and a.status = :status and (:category is null or a.errorCategory = :category)")
    Page<Analysis> searchCompletedByUser(@Param("userId") UUID userId, @Param("status") AnalysisStatus status,
                                         @Param("category") ErrorCategory category, Pageable pageable);
}
