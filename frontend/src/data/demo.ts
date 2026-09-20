import type { BuildHistoryItem } from "../types";

export const history: BuildHistoryItem[] = [
  { id: "a1", filename: "maven-build-2026-07-28.txt", category: "MAVEN_DEPENDENCY", status: "COMPLETED", uploadedAt: "Today, 10:42 AM" },
  { id: "a2", filename: "docker-api-build.txt", category: "DOCKER_BUILD", status: "COMPLETED", uploadedAt: "Yesterday, 4:15 PM" },
  { id: "a3", filename: "jenkins-release.log", category: "JENKINS_PIPELINE", status: "PENDING", uploadedAt: "Jul 25, 11:08 AM" },
];
