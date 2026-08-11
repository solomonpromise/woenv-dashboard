# Deploying WOEnv Dashboard

A step-by-step guide for deploying this application publicly, written for
someone who has not deployed a backend or connected it to a frontend before.
Follow the steps in order — later steps depend on values produced by earlier
ones.

Budget about an hour for the first run.

---

## What you are deploying

Running locally, `docker compose up` starts everything on one machine and the
pieces find each other over a private network. In production they are three
separate services, on three different providers, that only know about each other
through URLs and passwords you supply.

| Piece | What it does | Where it goes | Why there |
| --- | --- | --- | --- |
| PostgreSQL | Stores wells, tests, envelopes and users | **Neon** | Free tier that does not expire |
| FastAPI backend | Parses workbooks, does the calculations, serves the API | **Render** | Long request timeout, needed for ingestion |
| React frontend | The dashboard you look at in a browser | **Vercel** | Free static hosting, never sleeps |

The browser loads the frontend from Vercel, and the JavaScript running in that
browser then calls the backend on Render directly. The frontend and backend are
never in contact with each other server-to-server — the user's browser is the
only thing that talks to both. This matters, and is the source of most of the
confusion later in this guide.

### Redis and Celery are not deployed

The local compose file used to run a Redis broker and a Celery worker. Nothing
in the application ever enqueued a task — `app/api/upload.py` ingests workbooks
synchronously inside the upload request — so the worker sat idle and the broker
existed only to serve it. Both were removed. `app/tasks/` remains in the
repository if background processing is wired up later.

---

## Before you start

You need three accounts, all free, all sign-in-with-GitHub:

- [neon.tech](https://neon.tech)
- [render.com](https://render.com)
- [vercel.com](https://vercel.com)

The code is already on GitHub at
`https://github.com/solomonpromise/woenv-dashboard` (private). Render and Vercel
will each ask permission to read it — private repositories are fine on both free
tiers.

### A concept you will need: environment variables

An environment variable is a named value handed to a program when it starts,
kept outside the source code. Passwords and URLs live there so they are not
committed to git, and so the same code can run locally and in production against
different databases.

You will set these through each provider's web dashboard. When this guide says
"set `DATABASE_URL`", it means add a variable with that exact name, spelled in
capitals, in the provider's environment-variable section.

---

## Step 1 — The database (Neon)

Do this first. Nothing else can start without a database to point at.

1. Sign in to [neon.tech](https://neon.tech) and create a project.
2. Name it `woenv`.
3. **Region: choose `AWS eu-central-1` (Europe, Frankfurt).** Pick the region
   nearest your users — Frankfurt is the right answer for users in Nigeria and
   West Africa, because the subsea cables serving that coast land in Europe.
   In step 2 you will place the backend in Frankfurt too.
4. Leave the PostgreSQL version at the default.

> **This choice is permanent.** Neon cannot move an existing project to another
> region. Changing your mind later means creating a second project and migrating
> the data by hand.

When the project is created, Neon shows a connection string. Copy it and keep it
somewhere safe for the next step. It looks like this:

```
postgresql://woenv_owner:npg_AbC123xyz@ep-cool-name-a1b2c3.eu-central-1.aws.neon.tech/neondb?sslmode=require
```

That single string encodes the username, password, host, database name and a
requirement to use TLS. Treat it as a password, because it contains one.

Use the **direct** connection string, not the one with `-pooler` in the
hostname. The backend is a long-running process that keeps its own connection
pool and already sets `pool_pre_ping=True`, which is what handles Neon dropping
idle connections. The pooler is for serverless callers that this app is not.

> **If a URL ever starts with `postgres://`**, change it to `postgresql://`.
> SQLAlchemy 2 rejects the shorter form outright. Neon gives you the correct
> form already; other providers do not.

Nothing else to do here. You never create tables by hand — the backend does that
on its first start.

---

## Step 2 — The backend (Render)

The backend needs to exist before the frontend, because the frontend has to be
told the backend's address when it is built.

There is a chicken-and-egg problem in this step: the backend needs to know the
frontend's address too (for CORS, explained in step 4), and you will not have
that until step 3. You will use a placeholder now and correct it in step 4.

### 2a. Create the service

1. In the Render dashboard choose **New → Blueprint**.
2. Connect your GitHub account and select `woenv-dashboard`.
3. Render finds [`render.yaml`](render.yaml) in the repository root and reads
   the whole service definition from it — region, instance type, Docker build
   settings, health check and which variables it needs. You do not configure
   those by hand.

The region is already set to `frankfurt` in that file, matching the Neon region
from step 1, so there is nothing to choose here.

> Render names its regions Oregon, Ohio, Virginia, Frankfurt and Singapore — it
> does not use AWS region codes, so you will not see `eu-central-1` anywhere in
> Render's interface. Neon's `AWS eu-central-1` and Render's `frankfurt` are the
> same city; that is the point of picking both.

> **Like Neon, this is permanent.** Render cannot move an existing service to
> another region. If you need somewhere other than Frankfurt, edit `region:` in
> `render.yaml` and push *before* creating the service.

### 2b. Fill in the values Render asks for

`render.yaml` marks four variables as `sync: false`, which means "do not store
this in git, prompt for it at deploy time". Render shows a form:

| Variable | What to enter |
| --- | --- |
| `DATABASE_URL` | The full Neon connection string from step 1 |
| `BACKEND_CORS_ORIGINS` | `["https://placeholder.vercel.app"]` — temporary, fixed in step 4 |
| `ADMIN_PASSWORD` | A strong password you choose now, for the first admin login |

`SECRET_KEY` is not in that list because `render.yaml` tells Render to generate
one. It is the key used to sign login tokens. Render generates it once and keeps
it across deploys, which is what you want: if it changed on every restart, every
signed-in user would be logged out each time the service redeployed.

> **`BACKEND_CORS_ORIGINS` must be a JSON array**, with the square brackets and
> double quotes exactly as shown. The backend parses it as a list, so a bare
> `https://placeholder.vercel.app` is not merely wrong, it prevents the service
> from starting at all. Include `https://`, and no trailing slash.

Click deploy. The first build takes roughly five minutes — it is building the
Docker image, which installs pandas and numpy.

### 2c. What happens on first start

Watch the log stream in Render. The container runs
[`backend/start.sh`](backend/start.sh), which does three things in order:

1. **`python -m scripts.migrate_schema`** — connects to Neon and creates every
   table. It is safe to re-run, so it executes on every start; on later boots it
   finds nothing to do. You should see `Schema migration complete`.
2. **`python -m scripts.seed_admin`** — runs only because you set
   `ADMIN_PASSWORD`. Creates the admin user. You should see
   `Created admin user 'admin'`. Render's free plan gives you no shell, so this
   environment-variable path is the only practical way to create that first user.
3. **`uvicorn`** — starts the API and binds the port Render assigns.

Then `Application startup complete` and a URL like
`https://woenv-api.onrender.com`.

### 2d. Verify before moving on

Open `https://woenv-api.onrender.com/health` in a browser. You want:

```json
{"status":"healthy"}
```

Confirm the login works too, substituting your own host and the password you
chose:

```bash
curl -X POST https://woenv-api.onrender.com/api/v1/auth/login -d "username=admin&password=YOUR_PASSWORD"
```

A long `access_token` string means the database, the schema, the admin user and
password hashing are all working. **Do not continue until you see one** — every
later step assumes a working backend, and debugging is far easier now than after
two more services are involved.

Write down your Render URL. Step 3 needs it.

---

## Step 3 — The frontend (Vercel)

1. In Vercel choose **Add New → Project** and import `woenv-dashboard`.
2. **Set Root Directory to `frontend`.** This is the one setting that is easy to
   miss and guaranteed to fail without. The repository holds both applications,
   and Vercel needs to know the React app lives in the `frontend` subdirectory.
3. Framework Preset should auto-detect as **Vite**. Leave the build command and
   output directory alone — [`frontend/vercel.json`](frontend/vercel.json)
   already specifies them, along with the SPA routing rule and cache headers.
4. Expand **Environment Variables** and add one:

   | Name | Value |
   | --- | --- |
   | `VITE_API_URL` | `https://woenv-api.onrender.com` |

5. Deploy. It takes about two minutes.

Two things about `VITE_API_URL` cause most of the problems people hit here:

> **It is read at build time, not at run time.** Vite substitutes the value
> directly into the JavaScript bundle during the build. Changing it later
> requires a **redeploy**, not a restart — editing the variable alone changes
> nothing, because the old value is already baked into the shipped file.

> **Give the origin only** — `https://woenv-api.onrender.com`, with no `/api/v1`
> and no trailing slash. The API client appends `/api/v1` itself
> ([`src/services/api.ts`](frontend/src/services/api.ts)). Including it yourself
> produces requests to `/api/v1/api/v1/...`, and every one returns 404.

When it finishes, Vercel gives you a URL like `https://woenv-dashboard.vercel.app`.
Open it. **You should see the login page, and logging in should fail.** That is
the expected state right now — the frontend is live but the backend is still
refusing to talk to it. Step 4 fixes exactly that.

---

## Step 4 — Introduce them (CORS)

### Why this step exists

Browsers enforce a rule called the same-origin policy: JavaScript loaded from
one origin may not read responses from a different origin unless that other
origin explicitly allows it. An "origin" is the scheme plus host —
`https://woenv-dashboard.vercel.app`.

Your dashboard is served from Vercel but calls an API on Render, so the browser
treats every call as cross-origin and demands the backend's permission first.
That permission is a response header, and `BACKEND_CORS_ORIGINS` is the list of
origins the backend will grant it to. Right now that list contains only the
placeholder from step 2, so the browser blocks everything.

Locally you never see this, because nginx serves the frontend and proxies `/api`
to the backend under one origin — nothing is cross-origin, so the rule never
applies.

### Do it

1. Copy your real Vercel production URL.
2. In Render: your service → **Environment** → edit `BACKEND_CORS_ORIGINS` to:

   ```
   ["https://woenv-dashboard.vercel.app"]
   ```

   Your actual URL, JSON array, `https://` included, no trailing slash.
3. Save. Render redeploys automatically, taking a minute or two.

---

## Step 5 — First login, then lock it down

1. Open your Vercel URL.
2. Log in as `admin` with the `ADMIN_PASSWORD` you set in step 2.

If the first request seems to hang for up to a minute, that is a cold start, not
a failure — see the free-tier notes below.

Once you are in:

3. **Delete `ADMIN_PASSWORD` from Render's environment variables.** The user
   exists in the database now, and `start.sh` only runs the seeding script when
   that variable is present, so removing it changes nothing operationally. It
   just means your admin password is no longer sitting in a dashboard.
4. Change the admin password from within the app if you want it different from
   the bootstrap one.

### Smoke test

Confirm the whole path works end to end, not just the login:

- The dashboard loads fleet totals without console errors
- **Upload a real field workbook** — this is the slowest and most fragile
  operation in the app, and the one most likely to hit a free-tier limit. Test
  it deliberately, with your largest workbook, before you rely on this deployment
- A well detail page renders its operating envelope chart
- Log out and back in

---

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Service won't start, log mentions parsing `BACKEND_CORS_ORIGINS` | Not a JSON array | Use `["https://your-app.vercel.app"]`, brackets and quotes included |
| Browser console: "blocked by CORS policy" | Origin missing from the allow-list | Check step 4; match the URL exactly, including `https://` and no trailing slash |
| Every API call 404s, paths show `/api/v1/api/v1/...` | `VITE_API_URL` includes `/api/v1` | Set the origin only, then **redeploy** Vercel |
| Frontend build fails on Vercel | Root Directory not set to `frontend` | Set it in Project Settings, redeploy |
| Login returns 401 with the right password | Seeding never ran | Confirm `Created admin user` in Render's logs; if absent, `ADMIN_PASSWORD` was unset at first boot |
| Backend logs a database connection error | Wrong or pooled connection string | Use Neon's direct string; ensure it starts `postgresql://` |
| First request of the day takes ~1 minute | Cold start | Expected on the free tier |
| Upload fails or the service restarts mid-ingestion | Out of memory | See below — this one is not a misconfiguration |

Render's log stream is the first place to look for anything backend-related.
Vercel's build logs cover anything that fails before the site loads at all.

---

## Free-tier limits worth knowing

**The backend sleeps.** Render spins a free service down after 15 minutes
without traffic. The next request wakes it, taking about a minute, during which
the login screen appears frozen. Only the backend does this — the Vercel
frontend is always instant, which makes the delay look like a broken dashboard
rather than a waking server.

**750 instance-hours per month, per workspace.** One service is comfortably
within this, especially one that sleeps. Two constantly-running free services
are not, and exceeding it suspends them until the next month.

**Uploaded files do not survive a restart.** The free plan has no persistent
disk, so `/app/uploads` is wiped whenever the service sleeps or redeploys. The
parsed data is safe in Postgres — what you lose is the ability to run
`scripts.reingest_uploads`, which re-reads the original files. Keep local copies
of every workbook. Re-uploading is idempotent by design, so recovery is just
uploading again.

**512 MB of RAM and 0.1 CPU is tight for ingestion.** `MAX_UPLOAD_SIZE` permits
50 MB and ingestion reads every sheet through pandas. A large workbook can
exhaust the instance and be killed mid-request. If that happens the honest fix is
a paid instance — this is a genuine resource ceiling, not something a setting
will solve. Lowering `MAX_UPLOAD_SIZE` only converts the crash into a clearer
rejection.

**Neon free.** 0.5 GB of storage, which is far more than this dataset needs.
Projects left inactive for 90 days become eligible for deletion, so an unused
demo deployment will not survive indefinitely.

**Do not use Render's own free PostgreSQL.** It is deleted 30 days after
creation. That is why this guide puts the database on Neon.

---

## Day-to-day

Both providers watch the `main` branch and redeploy on push. A `git push` gives
you a new backend and a new frontend with no further action.

The backend re-runs `scripts.migrate_schema` on every start, so schema changes
apply themselves on deploy.

Remember that frontend environment variables are compile-time. Changing
`VITE_API_URL` requires a redeploy for the new value to reach users.

---

## Alternative: Koyeb instead of Render

Koyeb is a reasonable substitute and is better in one respect: its free instance
sleeps only after **1 hour** of inactivity rather than 15 minutes, so users meet
cold starts far less often. Resources are otherwise identical — 512 MB RAM and
0.1 vCPU on both.

**It is not the default here because of its request timeout.** Koyeb caps HTTP
requests at **100 seconds** and returns 502 beyond that; raising it to 900
seconds requires their paid Scale plan. Render's limit is on the order of 100
minutes.

That distinction is decisive for this application specifically. Workbook
ingestion runs synchronously inside the upload request, and on 0.1 vCPU a large
workbook can plausibly exceed 100 seconds of parsing and inserting. On Koyeb
that returns 502 and the upload is lost, with no configuration that fixes it. A
slow cold start is an annoyance you wait out; an upload that cannot complete is
a feature that does not work.

If your workbooks are small enough that ingestion reliably finishes well inside
100 seconds, Koyeb's better sleep behaviour makes it the more pleasant option.
Time a real upload on Render first, then decide with a number rather than a
guess.

### Deploying to Koyeb

`render.yaml` is Render-specific and Koyeb ignores it, so the variables it
declares must be entered by hand. Keep the file as a checklist of what the
service needs. The Dockerfile and `start.sh` work unchanged — `start.sh` binds
`$PORT`, which Koyeb provides.

Create a Web Service from the GitHub repository, then set:

| Setting | Value | Why |
| --- | --- | --- |
| Builder | **Dockerfile** | Not the default buildpack |
| Work directory | `backend` | Makes `backend/` the build context, matching `backend/.dockerignore` |
| Dockerfile location | `Dockerfile` | Relative to the work directory |
| Region | **Frankfurt** | Free tier allows only Frankfurt or Washington D.C.; match your Neon region |
| Port | `8000` | Matches the `${PORT:-8000}` fallback in `start.sh` |
| Health check | HTTP, path `/health` | The default is a bare TCP check |
| Health check grace period | **90 seconds** | Important, see below |

Environment variables are the same set Render prompts for, minus the generated
one — you must produce `SECRET_KEY` yourself:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set `DATABASE_URL`, `SECRET_KEY`, `BACKEND_CORS_ORIGINS`, `ADMIN_PASSWORD` and
`UPLOAD_DIR=/app/uploads`. Steps 3 through 5 above are unchanged: point
`VITE_API_URL` at the Koyeb URL instead, and put the Vercel URL in
`BACKEND_CORS_ORIGINS`.

> **Raise the health-check grace period.** Koyeb's default is 5 seconds, and
> health checks that fail restart the container after 3 attempts. Because
> `start.sh` runs the schema migration against Neon before uvicorn binds the
> port, a cold start can easily exceed 5 seconds and put the service into a
> restart loop that looks like a crash. 90 seconds gives it room.

Koyeb's free tier also allows one instance per organisation, offers no
persistent volumes, and is limited to Frankfurt or Washington D.C.
