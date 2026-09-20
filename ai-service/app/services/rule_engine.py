import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RuleMatch:
    category: str
    confidence: float
    summary: str
    root_cause: str
    fixes: list[str]
    patterns: tuple[str, ...]
    source_hints: tuple[str, ...] = ()


RULES = (
    RuleMatch(
        "MAVEN_DEPENDENCY", 92,
        "Maven could not resolve one or more project dependencies.",
        "The dependency coordinates are wrong, the required repository is unavailable, or the dependency is not published.",
        ["Check the groupId, artifactId, and version in pom.xml.", "Run mvn -U clean verify to refresh dependency metadata.", "Verify repository credentials and network access if using a private repository."],
        (r"Could not resolve dependencies", r"Could not find artifact", r"Non-resolvable parent POM", r"Failed to execute goal"),
        ("MAVEN",),
    ),
    RuleMatch(
        "GRADLE_DEPENDENCY", 92,
        "Gradle could not resolve one or more project dependencies.",
        "A declared dependency or repository configuration cannot be resolved.",
        ["Check the dependency notation and version in build.gradle.", "Confirm repositories { mavenCentral() } or your private repository configuration.", "Run ./gradlew build --refresh-dependencies."],
        (r"Could not resolve all files", r"Execution failed for task .*dependencies", r"Searched in the following locations", r"Could not find [\w.:-]+"),
        ("GRADLE",),
    ),
    RuleMatch(
        "JAVA_COMPILATION", 90,
        "Java compilation failed before the build could complete.",
        "The source code references a missing symbol, has incompatible types, or contains a syntax error.",
        ["Read the first compiler error; later errors may be consequences.", "Check imports, method signatures, and class names around the reported file and line.", "Confirm the configured Java version matches the project requirements."],
        (r"cannot find symbol", r"incompatible types", r"Compilation failure", r"error: ';' expected"),
    ),
    RuleMatch(
        "PYTHON_MODULE", 93,
        "Python could not import a required module.",
        "The package is missing from the active environment, or the application is using a different interpreter or virtual environment.",
        ["Activate the intended virtual environment.", "Install the missing package with pip install <package>.", "Add the package to requirements.txt and rebuild the environment."],
        (r"ModuleNotFoundError:", r"ImportError:", r"No module named ['\"]"),
    ),
    RuleMatch(
        "DOCKER_BUILD", 88,
        "The Docker image build failed.",
        "A Dockerfile instruction, build context path, command, or base image could not be processed.",
        ["Inspect the first failed Dockerfile step shown in the log.", "Verify COPY paths exist inside the build context and are not excluded by .dockerignore.", "Check base image names, tags, and registry access."],
        (r"Dockerfile", r"failed to solve", r"COPY failed", r"executor failed running"),
    ),
    RuleMatch(
        "JENKINS_PIPELINE", 86,
        "The Jenkins pipeline reported a failed stage or command.",
        "A pipeline step returned a non-zero exit code, often because an underlying build or script failed.",
        ["Find the first stage marked failed and inspect its preceding command output.", "Check Jenkins credentials, environment variables, and agent tools used by that stage.", "Fix the underlying command before changing the pipeline failure handling."],
        (r"Finished: FAILURE", r"hudson\.AbortException", r"script returned exit code"),
    ),
    RuleMatch(
        "TEST_FAILURE", 85,
        "The build failed because one or more automated tests failed.",
        "The observed application behavior did not match a test assertion or test setup failed.",
        ["Open the first failed test and compare expected versus actual values.", "Run the failing test locally with verbose output.", "Check test data, mocks, timing assumptions, and recent code changes."],
        (r"Tests run: .*Failures: [1-9]", r"AssertionError", r"FAILED .*test"),
    ),
    RuleMatch(
        "CONFIGURATION", 82,
        "The build failed because required configuration is missing or invalid.",
        "An environment variable, property, credential, or configuration file value is absent or malformed.",
        ["Compare required settings with the environment used by the build.", "Do not commit secrets; provide them through CI secret management.", "Validate property names and file paths used by the failing command."],
        (r"environment variable .* not set", r"configuration .* not found", r"Invalid configuration"),
    ),
)

ERROR_LINE_PATTERN = re.compile(r"(?i)(error|exception|failure|failed|cannot|could not|traceback|fatal|not found|no module).*")


def _extract_errors(log_content: str, limit: int = 12) -> list[str]:
    matches = [line.strip() for line in log_content.splitlines() if ERROR_LINE_PATTERN.search(line)]
    return matches[:limit] or [line.strip() for line in log_content.splitlines()[-5:] if line.strip()]


def _normalise_for_fingerprint(error: str) -> str:
    """Keep incident fingerprints stable across line numbers, IDs, and versions."""
    normalised = error.lower()
    normalised = re.sub(r"\b\d+(?:\.\d+){1,3}\b", "<version>", normalised)
    normalised = re.sub(r"\b\d+\b", "<number>", normalised)
    normalised = re.sub(r"[a-f0-9]{8,}", "<id>", normalised)
    return re.sub(r"\s+", " ", normalised).strip()


def _best_rule(log_content: str, source_type: str) -> tuple[RuleMatch | None, list[str]]:
    """Score every matching rule instead of returning the first broad regex match."""
    source = source_type.upper()
    candidates: list[tuple[int, RuleMatch, list[str]]] = []
    for rule in RULES:
        matches = [pattern for pattern in rule.patterns if re.search(pattern, log_content, re.IGNORECASE)]
        if not matches:
            continue
        # Specific evidence is worth more than a catch-all phrase. A supplied source
        # type can break otherwise ambiguous dependency-resolution ties.
        score = len(matches) * 20 + max(len(pattern) for pattern in matches)
        if source in rule.source_hints:
            score += 30
        candidates.append((score, rule, matches))
    if not candidates:
        return None, []
    _, rule, matches = max(candidates, key=lambda candidate: (candidate[0], candidate[1].confidence))
    return rule, matches


def analyze_with_rules(log_content: str, source_type: str = "GENERIC") -> dict:
    extracted_errors = _extract_errors(log_content)
    rule, matching_patterns = _best_rule(log_content, source_type)
    if rule:
        matched_error = next(
            (line for line in extracted_errors if any(re.search(pattern, line, re.IGNORECASE) for pattern in matching_patterns)),
            extracted_errors[0] if extracted_errors else rule.category,
        )
        # Multiple independent signals merit more confidence; cap confidence so
        # rule-based classifications never claim certainty.
        confidence = min(98, rule.confidence + max(0, len(matching_patterns) - 1) * 2)
        fingerprint = hashlib.sha256(f"{rule.category}:{_normalise_for_fingerprint(matched_error)}".encode()).hexdigest()
        return {
            "error_category": rule.category,
            "confidence_score": confidence,
            "summary": rule.summary,
            "root_cause": rule.root_cause,
            "extracted_errors": extracted_errors,
            "suggested_fixes": rule.fixes,
            "fingerprint": fingerprint,
            "analyzer_type": "RULE_BASED",
            "llm_enrichment_applied": False,
        }

    key_error = extracted_errors[0] if extracted_errors else "No recognizable error line"
    return {
        "error_category": "UNKNOWN", "confidence_score": 35,
        "summary": "The log contains a failure, but it does not match a known rule.",
        "root_cause": "More context is needed to identify a reliable root cause.",
        "extracted_errors": extracted_errors,
        "suggested_fixes": ["Start with the earliest error in the log.", "Re-run the build with verbose logging enabled.", "Check recent dependency, configuration, or source-code changes."],
        "fingerprint": hashlib.sha256(f"UNKNOWN:{_normalise_for_fingerprint(key_error)}".encode()).hexdigest(),
        "analyzer_type": "RULE_BASED", "llm_enrichment_applied": False,
    }
