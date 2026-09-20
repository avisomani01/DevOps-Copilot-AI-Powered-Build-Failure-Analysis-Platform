package com.devopscopilot.dto.dashboard;

import java.util.List;

public record DashboardResponse(long totalUploads, long successfulAnalyses, long failedAnalyses,
                                List<CategoryCountResponse> commonCategories) {
}
