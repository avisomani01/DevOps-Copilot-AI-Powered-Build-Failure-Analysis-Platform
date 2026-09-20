# Module 5: React Frontend Shell

The frontend is implemented in `frontend/` with React, TypeScript, Vite, Tailwind CSS, React Router, and Axios.

## Screens

| Route | Purpose |
|---|---|
| `/login` | Sign-in form; its submit flow is a temporary route transition until Module 6 connects JWT authentication. |
| `/register` | Registration placeholder, ready for the same auth API. |
| `/dashboard` | Upload/analysis totals, common-category summary, and an upload call to action. |
| `/upload` | `.txt` file selection and upload guidance, including a clear warning to remove secrets. |
| `/history` | Responsive table of prior uploads and statuses. |
| `/analysis/:id` | Plain-language root cause, fixes, analysis metadata, and PDF-download action. |

`AppLayout` provides a responsive sidebar that becomes a horizontally scrollable navigation bar on small screens. Reusable `StatusBadge` prevents status-color rules from being repeated across pages.

## API readiness

`src/api/client.ts` creates the single Axios client used by future feature APIs. It reads `VITE_API_BASE_URL`, defaults to the Spring Boot `/api/v1` route, and automatically attaches the `accessToken` from local storage. Module 6 will replace the temporary login navigation with real JWT handling.

The current dashboard, history, and analysis content is intentionally demo data. This lets the interface be reviewed early while later modules replace each page's local data with backend responses.

## Run locally

```powershell
cd frontend
pnpm install
pnpm dev
```

The app starts at `http://localhost:5173`. For a production check, run `pnpm build`.

## Verification

The project configuration and all 10 TypeScript React page/component files were checked for presence. Node.js 24 and pnpm 11 are available in this workspace. Dependencies were not installed here, so the Vite build and browser rendering should be run after `pnpm install` on a development machine.
