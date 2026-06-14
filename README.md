# AI Resume Tailor

Given a target job description (JD), automatically selects and rewrites the most
relevant experiences from a personal "material library" to generate a strictly
one-page tailored resume PDF (LaTeX) and a matching cover letter. It is also a
project for learning AI-agent concepts — the core is the Step 6
"compile-check-fix" loop.

> Development mainline: see [`ROADMAP.md`](./ROADMAP.md). Every phase has a
> verifiable milestone.

## Project structure

```
job application tool/
├── ROADMAP.md              # mainline source of truth
├── requirements.txt
├── .env.example
└── backend/
    ├── app/
    │   ├── main.py         # FastAPI entrypoint (/health, /jd/analyze, startup checks)
    │   ├── config.py       # reads .env
    │   ├── latex_tools.py  # detects tectonic/pdflatex
    │   ├── materials_store.py   # Step 1: material library read/write/validate
    │   ├── schemas/        # all Pydantic models
    │   ├── llm/            # centralized LLM client + prompt templates
    │   ├── pipeline/       # pipeline steps (Step 2..7)
    │   ├── routers/        # FastAPI routers
    │   └── static/         # zero-build single-page web UI (served at /)
    ├── data/
    │   └── materials.sample.json   # sample library for development
    └── tests/
```

## Requirements

- Python 3.11+ (tested on 3.13)
- Node 18+ (frontend, only needed at M8)
- A LaTeX engine (needed from M5): **Tectonic** recommended (single binary,
  auto-fetches packages)
  - `winget install TectonicProject.Tectonic` or `scoop install tectonic`
  - Alternative: MiKTeX (provides pdflatex): https://miktex.org/download

## Quick start

```powershell
# 1. Create a virtual environment and install dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configure the API key (needed from M2)
Copy-Item .env.example .env
# Edit .env and set ANTHROPIC_API_KEY

# 3. Start the backend
cd backend
uvicorn app.main:app --reload

# 4. Open the web UI
# Browser: http://127.0.0.1:8000/
```

## Web UI

A zero-build single page is served by the backend itself at
**http://127.0.0.1:8000/** (no npm, no separate dev server). Start the backend,
open that URL, paste a JD, and click **Analyze JD** to see the structured
`JDProfile`. The page grows with each milestone (selection → rewrite → PDFs).

For low-level/debug access, the interactive Swagger UI is at
**http://127.0.0.1:8000/docs**.

## Preparing the material library

Two ways to create `backend/data/materials.json`:

1. **Upload your resume (recommended):** in the web UI, "Step 1 — Your material
   library" → upload a PDF/TXT/TeX or paste text → **Parse resume** (Claude
   decomposes it) → review/edit in the structured editor → **Save library**.
   - The editor is fully editable: edit any field, toggle categories, add/remove
     experiences/projects/skills/bullets, edit skill tags. Each bullet shows a
     **tagged / untagged** badge so you can spot what still needs tags.
   - **Append mode:** to fold a newer resume version into your saved library,
     pick **Append to saved** before parsing — only new experiences/bullets/skills
     are added (duplicates are skipped).
2. **Hand-author** `backend/data/materials.json` following the schema in
   `backend/app/schemas/materials.py`.

If no saved library exists, the system falls back to `materials.sample.json`
(a fictional sample) so the pipeline runs with demo data first. The web UI's
status line shows whether selection is using **your** library or the **sample**.

## Running tests

```powershell
cd backend
pytest
```

## Current progress

See the Changelog in `ROADMAP.md`. Current: **M2 done; M3 next**.
