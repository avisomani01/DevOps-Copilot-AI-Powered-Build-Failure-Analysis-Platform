package com.devopscopilot.security;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.devopscopilot.config.JwtProperties;
import com.devopscopilot.entity.User;
import io.jsonwebtoken.JwtException;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

class JwtServiceTest {
    private final JwtService jwtService = new JwtService(new JwtProperties(
            "dGVzdC1qd3Qtc2VjcmV0LWtleS13aXRoLWVub3VnaC1ieXRlcy1mb3ItaHMyNTYtMjAyNg==", 60));

    @Test
    void generatesTokenWhoseSubjectIsUserEmail() {
        User user = User.create("Asha", "asha@example.com", "hash");
        ReflectionTestUtils.setField(user, "id", UUID.randomUUID());
        String token = jwtService.generateToken(user);
        assertEquals("asha@example.com", jwtService.extractEmail(token));
    }

    @Test
    void rejectsTamperedToken() {
        User user = User.create("Asha", "asha@example.com", "hash");
        ReflectionTestUtils.setField(user, "id", UUID.randomUUID());
        String token = jwtService.generateToken(user);
        assertThrows(JwtException.class, () -> jwtService.extractEmail(token + "tampered"));
    }
}
