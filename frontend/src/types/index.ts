export type ErrorCategory = "MAVEN_DEPENDENCY" | "GRADLE_DEPENDENCY" | "JAVA_COMPILATION" | "PYTHON_MODULE" | "DOCKER_BUILD" | "JENKINS_PIPELINE" | "TEST_FAILURE" | "CONFIGURATION" | "UNKNOWN";

export interface BuildHistoryItem { id: string; filename: string; category: ErrorCategory; status: "COMPLETED" | "PENDING" | "FAILED"; uploadedAt: string; }
