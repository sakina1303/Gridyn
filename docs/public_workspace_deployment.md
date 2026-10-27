# Public research workspace deployment

The marketing site stays public. The workspace requires a Supabase Auth session.
The FastAPI service owns all calculations and writes JSON records through the
visitor's JWT to Supabase Postgres. Row Level Security scopes every record to
`auth.uid()`; the application never uses a service-role key. Local development
continues to use SQLite.

## Before enabling the workspace

1. Create a Supabase project with email confirmation enabled. Review its region,
   plan, data retention, privacy policy, and any applicable terms.
2. Run `backend/supabase_schema.sql` in that project's SQL editor. Confirm the
   `gridyn_objects` table has Row Level Security enabled and the four owner-only
   policies are present.
3. Configure Supabase Auth's Site URL as `https://gridyn.vercel.app` and allow
   `https://gridyn.vercel.app/?open=workspace` as a redirect URL.
4. Import this repository as a **second Vercel project** for the FastAPI service,
   with repository root `./` and the `FastAPI` preset. The root `app.py`,
   `requirements.txt`, `.python-version`, and `vercel.json` serve this project.
   Set the backend variables from `backend/.env.example`. Never set a secret or
   service-role key in the frontend project.
5. In the existing Gridyn Vercel frontend project, set the three `VITE_` values
   from `frontend/.env.example` and redeploy. The frontend project root remains
   `frontend/` with the Vite preset. `VITE_GRIDYN_API_BASE_URL` must be the
   verified production URL of the FastAPI project.
6. Verify sign-up, email confirmation, sign-in, site creation, synthetic dataset,
   data readiness, a validated run, report download, and sign-out. Use two
   accounts to verify that neither can list, read, or delete the other's data.

The website must not advertise the workspace as live before these checks pass.
Observed CSV uploads are limited to 2 MB and require the user to acknowledge
authorization. Normalized records persist in that account until the site and
its datasets are deleted. No raw source CSV is stored by the API. Site-specific
field reliability, savings, and operator acceptance remain unknown.
