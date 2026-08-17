# wb-health-monitor

A spec-driven, test-driven data platform that turns **World Bank open health data** into a
benchmarking tool: it ingests World Development Indicators, curates them through a governed
pipeline, trains and evaluates models that surface where health systems under-perform relative to
their spending, and serves the result over an API plus a country-to-region dashboard.

Built by the training cohort as a collaborative team project.

---

## Local setup — get running in ~10 minutes

Everything runs in Docker, so you don't install Python or Postgres locally. Follow these steps in order.

### 0. Prerequisites (install once)

| You need | Notes |
|---|---|
| **Git** | `git --version` to check |
| **A GitHub account** | to fork and open pull requests |
| **Docker Desktop** | **installed and _running_** — this is the only heavy dependency. Check: `docker --version` and that the Docker whale icon is up |
| **A terminal + an editor** | VS Code, Cursor, or similar |
| *(optional)* Python 3.13 + [`uv`](https://docs.astral.sh/uv/) | only if you want to run lint/tests outside the container |
| *(optional)* GitHub CLI (`gh`) | convenient for forking/PRs |

> You do **not** need to install Python, Postgres, or any packages on your machine — the containers carry them.

### 1. Get the code

**Recommended — fork then clone** (this is how you'll contribute changes):

1. Click **Fork** on `https://github.com/sunilmogadati/wb-health-monitor` → creates `https://github.com/<your-username>/wb-health-monitor`.
2. Clone **your fork**:
   ```bash
   git clone https://github.com/<your-username>/wb-health-monitor.git
   cd wb-health-monitor
   ```
3. Add the shared repo as `upstream` so you can pull updates:
   ```bash
   git remote add upstream https://github.com/sunilmogadati/wb-health-monitor.git
   ```

*(If you were added as a collaborator instead, you can clone the shared repo directly:
`git clone https://github.com/sunilmogadati/wb-health-monitor.git`.)*

### 2. Create your local `.env`

Copy the template and fill it in:

```bash
cp .env.example .env
```

Open `.env` and set these values (a known-good local default):

```dotenv
# Host ports (change only if 8000 or 5432 are already used on your machine)
API_PORT=8000
POSTGRES_PORT=5432

ENVIRONMENT=local
LOG_LEVEL=INFO

# Database — the API reaches Postgres by the compose service name "db"
POSTGRES_HOST=db
POSTGRES_DB=wbhealth
POSTGRES_USER=wbhealth
POSTGRES_PASSWORD=wbhealth_local_dev
DATABASE_URL=postgresql+psycopg://wbhealth:wbhealth_local_dev@db:5432/wbhealth

# HTTP
CORS_ALLOWED_ORIGINS=http://localhost:3000
MAX_REQUEST_BODY_BYTES=1048576

# Connection pool
DB_POOL_MAX=5
DB_POOL_OVERFLOW=10
DB_POOL_ACQUIRE_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=1800
```

- **Never commit `.env`** — it is git-ignored on purpose. Only `.env.example` is committed.
- `POSTGRES_HOST=db` and `@db:5432` in `DATABASE_URL`: inside Docker, the API reaches the database by its **service name** (`db`), not `localhost`.
- `POSTGRES_PASSWORD` **must be set** — the Postgres container refuses to start without it.

### 3. Start the stack

```bash
make up
```

This builds the API image, starts the **app** and **db** containers, and waits until they are healthy.
The **first** run pulls the Postgres image and builds the API image, so it can take a few minutes.

### 4. Verify it's running

```bash
curl http://localhost:8000/api/v1/health
# → {"status":"alive","server_time_epoch":...}
```

Open in your browser:

- **API docs (Swagger):** http://localhost:8000/api/v1/docs
- **Health:** http://localhost:8000/api/v1/health

*(If you changed `API_PORT`, use that port instead of 8000.)*

You're set up. 🎉

---

## Everyday commands

Run `make help` to see them all. The ones you'll use most:

| Command | What it does |
|---|---|
| `make up` | Build + start the whole stack, wait for health |
| `make down` | Stop the stack **and delete its volumes** (clean slate) |
| `make logs` | Follow logs for every service |
| `make ps` | Show each service and its health |
| `make shell` | Open a shell **inside** the API container |
| `make migrate` | Apply database migrations to the latest (needs `DATABASE_URL`) |
| `make test` | Run the test suite |
| `make lint` / `make typecheck` / `make format` | Lint / type-check / auto-format |
| `make ci` | Run **everything CI runs** (lint + typecheck + format-check + test) |

Edits to `backend/` reload automatically — the source is bind-mounted into the container and
`uvicorn --reload` is on.

---

## Before you open a pull request

1. Write the **test first**, then the code (this project is test-driven — see the constitution).
2. Run the full check locally and get it green:
   ```bash
   make ci
   ```
3. Commit, push to your fork, and open a PR against `sunilmogadati/wb-health-monitor`.

You own your ticket end to end: research it, spec-check it, test it, build it, ship the PR.

---

## How we build (the method)

This project follows **Spec-Driven Development** (GitHub Spec Kit). The flow is
`constitution → specify → clarify → plan → tasks → implement`. Start here:

- **The rules:** [`.specify/memory/constitution.md`](.specify/memory/constitution.md) — read this first.
- **The commands:** `.claude/commands/` — `speckit.*` (the lifecycle), `rpi` (deep per-task loop),
  and `csi.*` (project gates like `preflight`, `status`, `feature-exit`).

*(The methodology is walked through in the cohort session.)*

---

## Project layout

```
backend/          FastAPI app (app/main.py), Alembic migrations, Dockerfile, pyproject.toml
tests/            the test suite
compose.yaml      the local stack: app (FastAPI) + db (Postgres 16)
Makefile          the dev commands above
.specify/         Spec Kit: constitution, templates, scripts
.claude/          commands, agents, and skills for the workflow
docs/adr/         architecture decision records (one decision per file)
.env.example      copy to .env (never commit .env)
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Cannot connect to the Docker daemon` | Start **Docker Desktop** and wait for it to be running, then `make up`. |
| `port is already allocated` / `address already in use` | Something else uses 8000 or 5432. Change `API_PORT` / `POSTGRES_PORT` in `.env`, then `make down && make up`. |
| `db` container unhealthy or the app won't start | Make sure `POSTGRES_PASSWORD` (and `POSTGRES_DB`, `POSTGRES_USER`) are set in `.env`. Then `make down && make up`. |
| Code changes don't show up | The app auto-reloads; if it's stuck, `make down && make up`. |
| Want a completely fresh database | `make down` deletes the DB volume; `make up` starts empty. |
| `DATABASE_URL is not set` when running `make migrate` | Ensure `DATABASE_URL` is filled in your `.env` (see step 2). |

Stuck for more than 15 minutes? Post in the cohort channel with the exact command and the error output.
