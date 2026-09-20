package com.devopscopilot;

import com.devopscopilot.config.AiServiceProperties;
import com.devopscopilot.config.JwtProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties({AiServiceProperties.class, JwtProperties.class})
public class DevOpsCopilotApplication {

    public static void main(String[] args) {
        SpringApplication.run(DevOpsCopilotApplication.class, args);
    }
}
