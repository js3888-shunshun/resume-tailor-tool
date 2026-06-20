# Deploying AI Resume Tailor (Render)

The app runs as a single Docker container. It is **stateless**: each browser keeps
its own material library (in `localStorage`), and a shared username/password gates
access. All logged-in users' AI calls bill to the one `ANTHROPIC_API_KEY` you set.

## What you need
- A GitHub repo with this code (already pushed).
- An [Anthropic API key](https://console.anthropic.com/).
- A free [Render](https://render.com) account.

## Steps (Render Blueprint)
1. Push this repo to GitHub (done).
2. On Render: **New +  →  Blueprint**, pick this repo. Render reads `render.yaml`
   and creates a Docker web service.
3. When prompted, set the environment variables (they are marked `sync: false`):
   - `ANTHROPIC_API_KEY` — your Anthropic key.
   - `APP_USERNAME` — the shared login name you'll give out (e.g. `team`).
   - `APP_PASSWORD` — the shared password.
4. Deploy. First build takes a few minutes (it installs the tectonic LaTeX engine
   and pre-warms its package bundle). When live you get a URL like
   `https://ai-resume-tailor.onrender.com`.

(No Blueprint? **New +  →  Web Service**, choose **Docker**, then add the same env
vars manually.)

## Using it
- Open the URL, sign in with `APP_USERNAME` / `APP_PASSWORD`.
- **Material Library → Parse PDF**: upload your resume. It's stored in *your*
  browser only; other users never see it. Click **Save**.
- Then **One-Click** (or the Tailor / Cover Letter tabs) as usual.

## Notes
- **Free tier sleeps** after ~15 min idle; the first request then takes ~30–60s to
  wake. Upgrade the plan to keep it always-on.
- **Cost**: every generation calls Claude and bills to your key. Since the site is
  gated by the shared password, only people you give it to can spend it. Watch your
  Anthropic usage; rotate `APP_PASSWORD` if it leaks.
- **Local dev**: leave `APP_PASSWORD` unset and the login is skipped; the app falls
  back to `backend/data/materials.json` and your local `.env` key.

## Run the container locally
```bash
docker build -t resume-tailor .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e APP_USERNAME=team -e APP_PASSWORD=secret \
  resume-tailor
# open http://localhost:8000
```
