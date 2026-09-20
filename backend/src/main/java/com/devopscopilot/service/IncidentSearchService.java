package com.devopscopilot.service;

import com.devopscopilot.dto.incident.IncidentSearchResponse;
import com.devopscopilot.dto.log.PageResponse;
import com.devopscopilot.entity.Analysis;
import com.devopscopilot.entity.AnalysisStatus;
import com.devopscopilot.entity.ErrorCategory;
import com.devopscopilot.entity.User;
import com.devopscopilot.exception.InvalidLogException;
import com.devopscopilot.exception.ResourceNotFoundException;
import com.devopscopilot.repository.AnalysisRepository;
import com.devopscopilot.repository.UserRepository;
import java.util.Locale;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class IncidentSearchService {
    private final UserRepository userRepository;
    private final AnalysisRepository analysisRepository;
    public IncidentSearchService(UserRepository userRepository, AnalysisRepository analysisRepository) { this.userRepository = userRepository; this.analysisRepository = analysisRepository; }

    @Transactional(readOnly = true)
    public PageResponse<IncidentSearchResponse> search(String email, String categoryValue, Pageable pageable) {
        User user = userRepository.findByEmailIgnoreCase(email).orElseThrow(() -> new ResourceNotFoundException("Authenticated user no longer exists"));
        ErrorCategory category = parseCategory(categoryValue);
        Page<Analysis> page = analysisRepository.searchCompletedByUser(user.getId(), AnalysisStatus.COMPLETED, category, pageable);
        return new PageResponse<>(page.map(this::toResponse).getContent(), page.getNumber(), page.getSize(), page.getTotalElements(), page.getTotalPages());
    }

    private ErrorCategory parseCategory(String value) {
        if (value == null || value.isBlank()) return null;
        try { return ErrorCategory.valueOf(value.trim().toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException exception) { throw new InvalidLogException("Unknown error category"); }
    }
    private IncidentSearchResponse toResponse(Analysis analysis) {
        return new IncidentSearchResponse(analysis.getId(), analysis.getBuildLog().getId(), analysis.getBuildLog().getOriginalFilename(),
                analysis.getErrorCategory().name(), analysis.getSummary(), analysis.getRootCause(),
                analysis.getIncidentPattern() == null ? 0 : analysis.getIncidentPattern().getOccurrenceCount(), analysis.getAnalyzedAt());
    }
}
