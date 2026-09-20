# Module 6: JWT Authentication

Authentication is now implemented across Spring Boot and React. All application APIs require a Bearer token, except the health check and authentication routes.

## API endpoints

### Register

`POST /api/v1/auth/register`

```json
{
  "fullName": "Asha Patel",
  "email": "asha@example.com",
  "password": "a-secure-password"
}
```

### Login

`POST /api/v1/auth/login`

```json
{
  "email": "asha@example.com",
  "password": "a-secure-password"
}
```

Both return `201 Created` (registration) or `200 OK` (login):

```json
{
  "accessToken": "eyJ...",
  "tokenType": "Bearer",
  "expiresInSeconds": 3600,
  "userId": "uuid",
  "fullName": "Asha Patel",
  "email": "asha@example.com"
}
```

Use subsequent APIs with:

```http
Authorization: Bearer <accessToken>
```

## Important implementation details

- Passwords are never stored in plain text; Spring Security's BCrypt encoder hashes them before the user row is saved.
- The token contains the user email, UUID, role, issued-at time, and expiry. It is signed with an HMAC SHA-256 key.
- The JWT filter validates a token once per request and loads the user from PostgreSQL before creating the security context.
- Sessions and CSRF are disabled because this is a stateless token API.
- CORS allows the local React development origin (`http://localhost:5173`).
- Invalid input returns `400`, duplicate email returns `409`, invalid credentials return `401`, and missing/invalid authentication returns a consistent `401` JSON response.
- The frontend's `AuthProvider` stores the access token and minimal user profile, protects feature routes, attaches the Bearer token through Axios, and supports sign-out.

## Configuration

Set these before deploying:

```powershell
$env:JWT_SECRET = '<a base64-encoded secret of at least 32 random bytes>'
$env:JWT_EXPIRATION_MINUTES = '60'
```

`application.yml` has a development-only fallback key so local startup is straightforward. Replace it in every non-local environment; never commit a real production key.

## Verification

Static checks confirmed the required backend and frontend authentication files exist and that the development JWT key decodes to 56 bytes, sufficient for HMAC SHA-256. Full Maven and Vite tests require installing the project dependencies first.
