package com.devopscopilot.controller;

import com.devopscopilot.dto.incident.IncidentSearchResponse;
import com.devopscopilot.dto.log.PageResponse;
import com.devopscopilot.config.LocalWorkspace;
import com.devopscopilot.service.IncidentSearchService;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/incidents")
public class IncidentController {
    private final IncidentSearchService incidentSearchService;
    public IncidentController(IncidentSearchService incidentSearchService) { this.incidentSearchService = incidentSearchService; }
    @GetMapping
    public ResponseEntity<PageResponse<IncidentSearchResponse>> search(
            @RequestParam(required = false) String category, @PageableDefault(size = 20) Pageable pageable) {
        return ResponseEntity.ok(incidentSearchService.search(LocalWorkspace.EMAIL, category, pageable));
    }
}
