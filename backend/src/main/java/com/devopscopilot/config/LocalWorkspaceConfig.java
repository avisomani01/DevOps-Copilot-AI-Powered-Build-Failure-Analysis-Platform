package com.devopscopilot.config;

import com.devopscopilot.entity.User;
import com.devopscopilot.repository.UserRepository;
import java.util.UUID;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.password.PasswordEncoder;

@Configuration
public class LocalWorkspaceConfig {
    @Bean
    CommandLineRunner createLocalWorkspaceUser(UserRepository users, PasswordEncoder passwordEncoder) {
        return arguments -> users.findByEmailIgnoreCase(LocalWorkspace.EMAIL)
                .orElseGet(() -> users.save(User.create("Local workspace", LocalWorkspace.EMAIL,
                        passwordEncoder.encode(UUID.randomUUID().toString()))));
    }
}
