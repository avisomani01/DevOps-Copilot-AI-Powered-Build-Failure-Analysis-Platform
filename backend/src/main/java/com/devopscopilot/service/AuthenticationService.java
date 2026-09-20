package com.devopscopilot.service;

import com.devopscopilot.dto.auth.AuthResponse;
import com.devopscopilot.dto.auth.LoginRequest;
import com.devopscopilot.dto.auth.RegisterRequest;
import com.devopscopilot.config.JwtProperties;
import com.devopscopilot.entity.User;
import com.devopscopilot.exception.DuplicateResourceException;
import com.devopscopilot.repository.UserRepository;
import com.devopscopilot.security.JwtService;
import java.util.Locale;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthenticationService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final JwtProperties jwtProperties;

    public AuthenticationService(UserRepository userRepository, PasswordEncoder passwordEncoder, JwtService jwtService,
                                 JwtProperties jwtProperties) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
        this.jwtProperties = jwtProperties;
    }

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        String email = normalizeEmail(request.email());
        if (userRepository.existsByEmailIgnoreCase(email)) {
            throw new DuplicateResourceException("An account with this email already exists");
        }
        User user = User.create(request.fullName().trim(), email, passwordEncoder.encode(request.password()));
        return toResponse(userRepository.save(user));
    }

    @Transactional(readOnly = true)
    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByEmailIgnoreCase(normalizeEmail(request.email()))
                .orElseThrow(() -> new BadCredentialsException("Invalid email or password"));
        if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new BadCredentialsException("Invalid email or password");
        }
        return toResponse(user);
    }

    private AuthResponse toResponse(User user) {
        return new AuthResponse(jwtService.generateToken(user), "Bearer", jwtProperties.expirationMinutes() * 60,
                user.getId(), user.getFullName(), user.getEmail());
    }

    private String normalizeEmail(String email) { return email.trim().toLowerCase(Locale.ROOT); }
}
