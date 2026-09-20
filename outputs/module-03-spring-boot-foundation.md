# Module 3: Spring Boot Backend Foundation

The runnable backend source is in `backend/`. It uses Java 21, Spring Boot 3.3, Maven, PostgreSQL, JPA, Flyway, and Bean Validation.

## Layered design

```text
controller  -> HTTP boundary and response codes
service     -> business rules (added with each feature)
repository  -> database queries only
entity      -> JPA mapping for the SQL schema
dto         -> request and response contracts; never expose entities directly
exception   -> consistent API error responses
config      -> application configuration and external-client wiring
```

The service layer is intentionally empty at this point: the next modules add feature-specific services rather than adding placeholder classes with no responsibility.

## Important classes

- `DevOpsCopilotApplication` starts Spring Boot and registers typed application configuration.
- `AiServiceProperties` holds the FastAPI base URL and timeouts. Module 8 will use it for the analysis integration.
- `WebConfig` creates one reusable `RestClient` for internal calls to the AI service.
- `SystemController` exposes `GET /api/v1/system/health`, useful for local checks and deployment probes.
- `GlobalExceptionHandler` converts validation failures, missing resources, and unexpected exceptions into the same `ApiError` JSON shape.
- JPA entities map directly to the Flyway schema. Enums keep status/category values type-safe in Java and aligned with PostgreSQL constraints.
- Repositories contain only persistence queries; controllers should not access them directly once services are added.

## Configuration and startup

The defaults target a local database. Override them through environment variables:

```powershell
$env:DB_URL = 'jdbc:postgresql://localhost:5432/devops_copilot'
$env:DB_USERNAME = 'devops_user'
$env:DB_PASSWORD = 'change_me'
$env:AI_SERVICE_URL = 'http://localhost:8000'
mvn spring-boot:run
```

Flyway automatically applies `src/main/resources/db/migration/V1__initial_schema.sql`. Hibernate uses `ddl-auto: validate`, which verifies the mapping but never changes the database schema itself.

For now the health endpoint is public because authentication is deliberately scheduled for Module 6. Spring Security and JWT will then protect every application route except authentication and health endpoints.

## Verification note

The source tree and Maven XML were checked locally. This workspace has Java 25 installed but does not have the `mvn` command or Maven wrapper, so the Maven test lifecycle could not be executed here. Use Maven 3.9+ with JDK 21 (or the installed JDK 25) to run `mvn test`.
