# GeoAttend

Geolocation + face-verification classroom attendance system. `docs/` has the
full product/architecture/API/security/UI specs, `PLAN.md` has the
phase-by-phase build plan, and `PROGRESS.md` tracks what's actually built and
verified so far — read that first if you're picking this project back up.

## Prerequisites

- Docker (with Docker Compose)
- Node.js 20+ and npm
- Python 3.10+ and [`uv`](https://docs.astral.sh/uv/)

## Setup

1. Clone the repo and start Postgres + Redis (Redis backs rate limiting, Phase 7):

   ```bash
   git clone <this-repo-url>
   cd beta
   docker compose up -d postgres redis
   ```

2. Backend (in its own terminal):

   ```bash
   cd backend
   cp .env.example .env
   uv run alembic upgrade head
   uv run python scripts/seed.py
   uv run uvicorn app.main:app --port 8001 --reload
   ```

3. Frontend (in a separate terminal):

   ```bash
   cd frontend
   cp .env.example .env.local
   npm install
   npm run dev -- --port 3000
   ```

4. Visit <http://localhost:3000>. Seeded accounts (all password `password123`):
   `student@example.com`, `faculty@example.com`, `admin@example.com`.

**Preferred if you're using VS Code:** Command Palette → "Tasks: Run Task" →
**"GeoAttend: Start All"** — runs Docker/backend/frontend, each in its own
dedicated terminal (backed by `scripts/start-{docker,backend,frontend}.sh`).

## Testing from a phone on the same network

Camera and geolocation features are best tested on a real phone rather than a
laptop (see `PROGRESS.md`'s Phase 5a log for why: laptops resolve location via
WiFi/IP triangulation, which is far less accurate than a phone's real GPS, and
can legitimately fail the app's accuracy check even when you're in the right
place). Browsers only allow camera/geolocation on a "secure context" (HTTPS,
or `localhost` itself) — a plain LAN IP over HTTP needs one extra step below.

1. Find this machine's LAN IP (make sure your phone is on the **same Wi-Fi**,
   not cellular data or an isolated guest network):
   - macOS: `ipconfig getifaddr en0`
   - Windows: `ipconfig` (look for the Wi-Fi adapter's IPv4 address)
   - Linux: `ip addr` or `hostname -I`

2. Point the frontend's API calls at that IP — edit `frontend/.env.local`:

   ```
   NEXT_PUBLIC_API_URL=http://<your-lan-ip>:8001/api/v1
   ```

3. Allow that origin in the backend's CORS — edit `backend/.env`:

   ```
   CORS_ALLOW_ORIGINS=["http://localhost:3000","http://<your-lan-ip>:3000"]
   ```

4. Restart both dev servers so they pick up the changes. The backend needs to
   bind to all interfaces, not just localhost:

   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

   The frontend already binds to all interfaces by default — just restart it
   normally (`npm run dev -- --port 3000`).

5. On your phone's Chrome, visit
   `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, enable it, add
   `http://<your-lan-ip>:3000` as the origin, then relaunch Chrome. (Only
   needed because this is plain HTTP over a LAN IP — skip this if you're
   instead using a real `https://` tunnel URL.)

6. Visit `http://<your-lan-ip>:3000` on your phone.

7. Once you're done, revert steps 2-3 back to `http://localhost:...` — they're
   only needed for phone testing.

If this machine runs the dev servers inside WSL2 on Windows, it isn't directly
reachable from other devices by default — you'll also need to forward the
ports from Windows to WSL2 (run in an **elevated** PowerShell):

```powershell
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=<wsl-ip>
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=<wsl-ip>
New-NetFirewallRule -DisplayName "WSL2 dev 3000" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "WSL2 dev 8001" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
```

Find `<wsl-ip>` via `hostname -I` inside WSL — it can change across reboots,
so you may need to redo this after restarting WSL/Windows. This needs local
admin rights on Windows; if you don't have them, a tunnel (e.g. `cloudflared
tunnel --url http://localhost:3000`, paired with a Next.js rewrite so the
backend doesn't need its own public URL) is the alternative — but corporate
networks often block these by port or domain category, which is exactly why
testing from an unrestricted network is worth doing in the first place.

## Tests and linting

```bash
# Backend
cd backend && uv run pytest
uv run ruff check . && uv run ruff format .

# Frontend
cd frontend && npm run build
npm run lint
```
