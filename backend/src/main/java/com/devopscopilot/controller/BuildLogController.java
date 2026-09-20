package com.devopscopilot.controller;

import com.devopscopilot.dto.log.BuildLogDetailResponse;
import com.devopscopilot.dto.log.BuildLogResponse;
import com.devopscopilot.dto.log.PageResponse;
import com.devopscopilot.config.LocalWorkspace;
import com.devopscopilot.service.BuildLogService;
import java.net.URI;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

@RestController
@RequestMapping("/api/v1/logs")
public class BuildLogController {
    private final BuildLogService buildLogService;
    public BuildLogController(BuildLogService buildLogService) { this.buildLogService = buildLogService; }

    @PostMapping(consumes = "multipart/form-data")
    public ResponseEntity<BuildLogResponse> upload(@RequestParam("file") MultipartFile file) {
        BuildLogResponse response = buildLogService.upload(LocalWorkspace.EMAIL, file);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest().path("/{id}").buildAndExpand(response.id()).toUri();
        return ResponseEntity.created(location).body(response);
    }

    @GetMapping
    public PageResponse<BuildLogResponse> list(@PageableDefault(size = 20, sort = "uploadedAt") Pageable pageable) {
        return buildLogService.list(LocalWorkspace.EMAIL, pageable);
    }

    @GetMapping("/{logId}")
    public ResponseEntity<BuildLogDetailResponse> getById(@PathVariable UUID logId) {
        return ResponseEntity.status(HttpStatus.OK).body(buildLogService.getOwnedLog(LocalWorkspace.EMAIL, logId));
    }
}
