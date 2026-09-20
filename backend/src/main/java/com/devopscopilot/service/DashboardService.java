package com.devopscopilot.service;

import com.devopscopilot.dto.dashboard.CategoryCountResponse;
import com.devopscopilot.dto.dashboard.DashboardResponse;
import com.devopscopilot.entity.AnalysisStatus;
import com.devopscopilot.entity.User;
import com.devopscopilot.exception.ResourceNotFoundException;
import com.devopscopilot.repository.AnalysisRepository;
import com.devopscopilot.repository.BuildLogRepository;
import com.devopscopilot.repository.UserRepository;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DashboardService {
    private final UserRepository userRepository;
    private final BuildLogRepository buildLogRepository;
    private final AnalysisRepository analysisRepository;

    public DashboardService(UserRepository userRepository, BuildLogRepository buildLogRepository, AnalysisRepository analysisRepository) {
        this.userRepository = userRepository;
        this.buildLogRepository = buildLogRepository;
        this.analysisRepository = analysisRepository;
    }

    @Transactional(readOnly = true)
    public DashboardResponse getDashboard(String email) {
        User user = userRepository.findByEmailIgnoreCase(email)
                .orElseThrow(() -> new ResourceNotFoundException("Authenticated user no longer exists"));
        List<CategoryCountResponse> categories = analysisRepository.countCategoriesByUserAndStatus(user.getId(), AnalysisStatus.COMPLETED)
                .stream().filter(row -> row[0] != null)
                .map(row -> new CategoryCountResponse(row[0].toString(), ((Number) row[1]).longValue()))
                .toList();
        return new DashboardResponse(buildLogRepository.countByUserId(user.getId()),
                analysisRepository.countByBuildLogUserIdAndStatus(user.getId(), AnalysisStatus.COMPLETED),
                analysisRepository.countByBuildLogUserIdAndStatus(user.getId(), AnalysisStatus.FAILED), categories);
    }
}
