package com.devopscopilot.service;

import com.devopscopilot.dto.analysis.AiAnalysisRequest;
import com.devopscopilot.dto.analysis.AiAnalysisResponse;
import com.devopscopilot.dto.analysis.AnalysisResponse;
import com.devopscopilot.entity.Analysis;
import com.devopscopilot.entity.AnalyzerType;
import com.devopscopilot.entity.BuildLog;
import com.devopscopilot.entity.ErrorCategory;
import com.devopscopilot.entity.IncidentPattern;
import com.devopscopilot.entity.User;
import com.devopscopilot.exception.ResourceNotFoundException;
import com.devopscopilot.repository.AnalysisRepository;
import com.devopscopilot.repository.BuildLogRepository;
import com.devopscopilot.repository.IncidentPatternRepository;
import com.devopscopilot.repository.UserRepository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClient;

@Service
public class AnalysisService {
    private final BuildLogRepository buildLogRepository;
    private final AnalysisRepository analysisRepository;
    private final IncidentPatternRepository incidentPatternRepository;
    private final UserRepository userRepository;
    private final RestClient aiServiceRestClient;

    public AnalysisService(BuildLogRepository buildLogRepository, AnalysisRepository analysisRepository,
                           IncidentPatternRepository incidentPatternRepository, UserRepository userRepository,
                           RestClient aiServiceRestClient) {
        this.buildLogRepository = buildLogRepository;
        this.analysisRepository = analysisRepository;
        this.incidentPatternRepository = incidentPatternRepository;
        this.userRepository = userRepository;
        this.aiServiceRestClient = aiServiceRestClient;
    }

    @Transactional
    public AnalysisResponse analyze(String authenticatedEmail, UUID buildLogId) {
        User user = findUser(authenticatedEmail);
        BuildLog log = findOwnedLog(buildLogId, user);
        return analysisRepository.findByBuildLogId(log.getId()).map(this::toResponse).orElseGet(() -> createAnalysis(log));
    }

    @Transactional(readOnly = true)
    public AnalysisResponse getAnalysis(String authenticatedEmail, UUID buildLogId) {
        BuildLog log = findOwnedLog(buildLogId, findUser(authenticatedEmail));
        Analysis analysis = analysisRepository.findByBuildLogId(log.getId())
                .orElseThrow(() -> new ResourceNotFoundException("No analysis exists for this build log"));
        return toResponse(analysis);
    }

    private AnalysisResponse createAnalysis(BuildLog log) {
        Analysis analysis = analysisRepository.save(Analysis.create(log));
        log.markAnalyzing();
        try {
            AiAnalysisResponse aiResponse = aiServiceRestClient.post().uri("/api/v1/analyze")
                    .body(new AiAnalysisRequest(log.getLogContent(), log.getSourceType().name()))
                    .retrieve().body(AiAnalysisResponse.class);
            applyResult(analysis, aiResponse);
            log.markAnalyzed();
        } catch (Exception exception) {
            analysis.fail("AI analysis service is unavailable. Please try again later.");
            log.markFailed();
        }
        return toResponse(analysis);
    }

    private void applyResult(Analysis analysis, AiAnalysisResponse response) {
        if (response == null || response.fingerprint() == null || response.fingerprint().isBlank()) {
            throw new IllegalStateException("AI service returned an incomplete analysis");
        }
        ErrorCategory category = ErrorCategory.valueOf(response.errorCategory());
        AnalyzerType analyzerType = AnalyzerType.valueOf(response.analyzerType());
        List<String> fixes = response.suggestedFixes() == null ? List.of() : response.suggestedFixes();
        List<String> errors = response.extractedErrors() == null ? List.of() : response.extractedErrors();
        Optional<IncidentPattern> matchingIncident = incidentPatternRepository.findByFingerprint(response.fingerprint());
        IncidentPattern incident;
        if (matchingIncident.isPresent()) {
            incident = matchingIncident.get();
            incident.recordOccurrence();
        } else {
            incident = incidentPatternRepository.save(IncidentPattern.create(response.fingerprint(), category,
                    truncate(response.summary(), 255), response.rootCause(), fixes));
        }
        analysis.complete(incident, category, response.confidenceScore(), response.summary(), response.rootCause(), errors, fixes, analyzerType);
    }

    private User findUser(String email) {
        return userRepository.findByEmailIgnoreCase(email)
                .orElseThrow(() -> new ResourceNotFoundException("Authenticated user no longer exists"));
    }

    private BuildLog findOwnedLog(UUID logId, User user) {
        return buildLogRepository.findByIdAndUserId(logId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Build log not found"));
    }

    private AnalysisResponse toResponse(Analysis analysis) {
        int occurrences = analysis.getIncidentPattern() == null ? 0 : analysis.getIncidentPattern().getOccurrenceCount();
        return new AnalysisResponse(analysis.getId(), analysis.getBuildLog().getId(), analysis.getStatus().name(),
                analysis.getErrorCategory() == null ? null : analysis.getErrorCategory().name(), analysis.getConfidenceScore(),
                analysis.getSummary(), analysis.getRootCause(), analysis.getExtractedErrors(), analysis.getSuggestedFixes(),
                analysis.getAnalyzerType() == null ? null : analysis.getAnalyzerType().name(), analysis.getFailureReason(), occurrences,
                analysis.getAnalyzedAt());
    }

    private String truncate(String value, int maxLength) {
        if (value == null || value.isBlank()) return "Build failure";
        return value.length() <= maxLength ? value : value.substring(0, maxLength);
    }
}
