package com.devopscopilot.service;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.devopscopilot.config.JwtProperties;
import com.devopscopilot.dto.auth.RegisterRequest;
import com.devopscopilot.entity.User;
import com.devopscopilot.exception.DuplicateResourceException;
import com.devopscopilot.repository.UserRepository;
import com.devopscopilot.security.JwtService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.UUID;

@ExtendWith(MockitoExtension.class)
class AuthenticationServiceTest {
    @Mock private UserRepository userRepository;
    private AuthenticationService authenticationService;

    @BeforeEach
    void setUp() {
        authenticationService = new AuthenticationService(userRepository, new BCryptPasswordEncoder(),
                new JwtService(new JwtProperties("dGVzdC1qd3Qtc2VjcmV0LWtleS13aXRoLWVub3VnaC1ieXRlcy1mb3ItaHMyNTYtMjAyNg==", 60)),
                new JwtProperties("dGVzdC1qd3Qtc2VjcmV0LWtleS13aXRoLWVub3VnaC1ieXRlcy1mb3ItaHMyNTYtMjAyNg==", 60));
    }

    @Test
    void rejectsDuplicateEmail() {
        when(userRepository.existsByEmailIgnoreCase("asha@example.com")).thenReturn(true);
        assertThrows(DuplicateResourceException.class, () -> authenticationService.register(
                new RegisterRequest("Asha", "ASHA@example.com", "password123")));
    }

    @Test
    void registersNewUserWithNormalizedEmail() {
        when(userRepository.existsByEmailIgnoreCase("asha@example.com")).thenReturn(false);
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> {
            User user = invocation.getArgument(0);
            ReflectionTestUtils.setField(user, "id", UUID.randomUUID());
            return user;
        });
        assertDoesNotThrow(() -> authenticationService.register(new RegisterRequest("Asha", " ASHA@example.com ", "password123")));
    }
}
