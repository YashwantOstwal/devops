package com.example.cicd;

import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AppController {

    private final String environment;

    public AppController(@Value("${spring.profiles.active:development}") String environment) {
        this.environment = environment;
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of(
                "status", "UP",
                "service", "cicd-demo");
    }

    @GetMapping("/api/version")
    public Map<String, String> version() {
        return Map.of(
                "app", "cicd-demo",
                "version", "1.0.1",
                "environment", environment);
    }
    
    // @GetMapping("/api/quality-demo")
    // public String qualityDemo() {
    //     String value = null;
    //     return value.toUpperCase(); // SonarQube should flag the null dereference
    // }

}
