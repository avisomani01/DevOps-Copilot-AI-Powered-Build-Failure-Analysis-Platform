package com.devopscopilot.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.devopscopilot.dto.log.BuildLogResponse;
import com.devopscopilot.entity.BuildLog;
import com.devopscopilot.entity.User;
import com.devopscopilot.exception.InvalidLogException;
import com.devopscopilot.repository.BuildLogRepository;
import com.devopscopilot.repository.UserRepository;
import java.nio.charset.StandardCharsets;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;

@ExtendWith(MockitoExtension.class)
class BuildLogServiceTest {
    @Mock private BuildLogRepository buildLogRepository;
    @Mock private UserRepository userRepository;
    private BuildLogService buildLogService;

    @BeforeEach void setUp() { buildLogService = new BuildLogService(buildLogRepository, userRepository); }

    @Test
    void rejectsEmptyFile() {
        MockMultipartFile file = new MockMultipartFile("file", "build.java", "text/plain", new byte[0]);
        assertThrows(InvalidLogException.class, () -> buildLogService.upload("asha@example.com", file));
    }

    @Test
    void detectsMavenAndStoresValidTextLog() {
        MockMultipartFile file = new MockMultipartFile("file", "maven.txt", "text/plain", "[ERROR] Maven could not resolve dependencies".getBytes(StandardCharsets.UTF_8));
        when(userRepository.findByEmailIgnoreCase("asha@example.com")).thenReturn(Optional.of(User.create("Asha", "asha@example.com", "hash")));
        when(buildLogRepository.save(any(BuildLog.class))).thenAnswer(invocation -> invocation.getArgument(0));
        BuildLogResponse response = buildLogService.upload("asha@example.com", file);
        assertEquals("MAVEN", response.sourceType());
        assertEquals("UPLOADED", response.uploadStatus());
    }

    @Test
    void acceptsJavaSourceFiles() {
        MockMultipartFile file = new MockMultipartFile("file", "App.java", "text/x-java", "class App {}".getBytes(StandardCharsets.UTF_8));
        when(userRepository.findByEmailIgnoreCase("asha@example.com")).thenReturn(Optional.of(User.create("Asha", "asha@example.com", "hash")));
        when(buildLogRepository.save(any(BuildLog.class))).thenAnswer(invocation -> invocation.getArgument(0));
        assertEquals("JAVA", buildLogService.upload("asha@example.com", file).sourceType());
    }
}
