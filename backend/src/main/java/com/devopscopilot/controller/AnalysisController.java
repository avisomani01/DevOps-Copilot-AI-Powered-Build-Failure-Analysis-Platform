package com.devopscopilot.controller;

import com.devopscopilot.dto.analysis.AnalysisResponse;
import com.devopscopilot.config.LocalWorkspace;
import com.devopscopilot.service.AnalysisService;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/logs/{logId}/analysis")
public class AnalysisController {
    private final AnalysisService analysisService;
    public AnalysisController(AnalysisService analysisService) { this.analysisService = analysisService; }

    @PostMapping
    public ResponseEntity<AnalysisResponse> analyze(@PathVariable UUID logId) {
        return ResponseEntity.ok(analysisService.analyze(LocalWorkspace.EMAIL, logId));
    }

    @GetMapping
    public ResponseEntity<AnalysisResponse> get(@PathVariable UUID logId) {
        return ResponseEntity.ok(analysisService.getAnalysis(LocalWorkspace.EMAIL, logId));
    }
}
