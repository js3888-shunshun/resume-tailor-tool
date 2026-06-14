# AI Resume Tailor — Development Roadmap

> This is the project's **single source of truth**.
> Before each work session, read it to confirm the current milestone; after each
> session, update the relevant checkboxes and the Changelog.
> Off-mainline ideas go to "Backlog / Future" — do not inject them into the
> current milestone.

**One-line definition:** Given a target job description (JD) plus the user's
material library, automatically select and rewrite the most relevant experiences
to produce a strictly one-page tailored resume PDF (LaTeX) and a matching cover
letter. It also serves as a vehicle for learning AI-agent concepts — the core is
the Step 6 "compile-check-fix" loop.

**Phase 1 (MVP) boundaries:**
- ✅ In scope: JD analysis, experience selection, content rewriting, LaTeX
  rendering, one-page compile loop, cover letter.
- ❌ Out of scope: LinkedIn cold messages, company-info search, embedding
  retrieval, upload-resume auto-decompose. (Only leave extension points for
  these in the data structures / code interfaces.)

---

## Guiding principles (apply to every milestone)

1. Each pipeline step = an independent module/function with strict Pydantic
   schema I/O, individually testable.
2. All LLM calls go through the `llm` module; prompt templates live in separate
   files/constants.
3. Easily-swappable parts (scoring, retrieval) are isolated functions so they can
   later be replaced (e.g. embeddings).
4. Variable/function names in English; comments may be mixed CN/EN. **All `.md`
   docs are English-only.**
5. A milestone is "done" only when its acceptance criteria pass; then tick the
   boxes here and append a Changelog entry.

---

## Milestones

### M1 — Skeleton + Schema + Sample data  ✅ Done
**Goal:** A runnable backend skeleton, all Pydantic models, a sample library.
- [x] Project layout + git init + `.gitignore` + `.env.example`
- [x] `requirements.txt` (fastapi, uvicorn, anthropic, pydantic, jinja2, pypdf, pytest, ...)
- [x] All Pydantic schemas: materials / jd_profile / selection
- [x] A valid sample `materials.sample.json` (used for development throughout)
- [x] FastAPI skeleton + `GET /health` + startup detection of pdflatex/tectonic
- [x] `config.py` reads `.env` (API key, model, paths)
- [x] Initial `README.md`
- **Acceptance:** ✅ All passed — app boots and `/health` returns 200;
  `materials.sample.json` validates; pytest 5/5.

### M2 — JD analysis module (Step 2)  ✅ Done (incl. real-key end-to-end)
**Goal:** Raw JD text → structured JD profile.
- [x] `llm/client.py`: wraps the Anthropic call, JSON parsing (tolerates code
  fences) + retry + **injectable mock responder**
- [x] Prompt template (`llm/prompts/jd_analysis.py`): JSON-only, category enum
  fixed to `[AI, DS, DE, MLE, SDE]`
- [x] `pipeline/step2_jd_analysis.py`: returns `JDProfile`
- [x] `POST /jd/analyze` endpoint
- **Acceptance:** ✅ Mock returns a valid `JDProfile`; bad category rejected;
  no key → 503 clear error; empty input → 422. pytest 11/11.
- **Real verification:** ✅ 2026-06-14 ran a real JD (Acme Robotics MLE),
  output parsed cleanly into `JDProfile`, primary=MLE / secondary=[AI, DE].

### M2.5 — Minimal web UI (JD analysis)  ✅ Done
**Goal:** Bring the frontend forward (user wants an early, demoable MVP). A
zero-build single page served by FastAPI itself, wrapping existing endpoints.
This supersedes the original "frontend last" plan: the UI now grows
incrementally, one thin vertical slice per later milestone.
- [x] `app/static/index.html`: paste JD → Analyze → render `JDProfile`
  (category badges, highlight-keyword chips, skills, responsibilities, raw JSON)
- [x] Live backend status line (calls `/health`: API key / model / LaTeX)
- [x] Served at `GET /` (same-origin, no CORS, no npm/build step)
- **Acceptance:** ✅ `GET /` returns the page (200, text/html); the page calls
  `/jd/analyze` and renders the profile; pytest 11/11 unaffected.
- **Note:** When the UI later needs richer interactions it can be migrated to
  Vite + React (see Backlog); for now zero-build wins for fast demos.

### M3 — Experience matching & selection (Step 3)  ✅ Done
**Goal:** JD profile + material library → preliminary selection (no rewrite yet).
- [x] Category-intersection filter to build the candidate pool
- [x] `scoring.py`: standalone keyword-overlap scorer with **swappable `Scorer`
  interface** (word-boundary matching; highlight keywords weighted 2× skills)
- [x] Sort by score + priority, cap bullets per item, global `target_bullet_count`
  trim that never empties a group
- [x] Output `SelectionResult` (pre-rewrite) with per-bullet score + matched keywords
- [x] `POST /select` endpoint; `GET /materials` pulled forward (UI needs titles)
- [x] UI slice: "Selected experiences" panel in `index.html` (score badges +
  matched-keyword chips), chained after Analyze; configurable target-bullets input
- **Acceptance:** ✅ Pure functions, no LLM; scoring + selection unit-tested
  (word-boundary, no-double-count, ordering, trim-keeps-one, category filter,
  skills/education). pytest 19/19. Live `/select` + `/materials` verified.

### M3.5 — Resume ingestion / auto-decompose  ✅ Done (pulled forward from Backlog)
**Goal:** Upload an existing resume → LLM decomposes it into the material library,
so selection runs on the user's real experiences instead of sample data.
- [x] `text_extract.py`: extract text from PDF (pypdf) / txt / tex / md
- [x] `llm/prompts/resume_decompose.py`: resume text → MaterialsLibrary JSON
  (no fabrication, id conventions, category inference, skill_tags/metrics/priority)
- [x] `pipeline/ingest.py::decompose_resume()` (injectable mock; 8k token budget)
- [x] `POST /materials/ingest` (file and/or pasted text → preview, not saved)
- [x] `PUT /materials` (save reviewed library to gitignored `data/materials.json`)
- [x] `/health` now reports `materials_source` = "user" | "sample"
- [x] UI: "Step 1 — Your material library" card (upload/paste → Build → preview →
  Save); status line shows whether selection uses YOUR library or the sample
- **Acceptance:** ✅ decompose unit-tested with mock (happy/empty/bad-schema/no-key);
  text extraction tested; live PUT→GET→health roundtrip flips source sample→user;
  ingest empty→422. pytest 25/25. (Real-resume LLM decompose: user to verify.)
- **Dep added:** `python-multipart` (file uploads).

### M4 — Content rewriting module (Step 4)  ⬅️ Next
> UI slice: show before/after text for each rewritten bullet in the selection panel.
**Goal:** Selected bullets + JD profile → rewritten results (with matched_keywords).
- [ ] Batch all bullets into one LLM call, return a JSON array
- [ ] Prompt constraints: no fabrication, use JD keywords, similar length, label matched keywords
- [ ] Output conforms to the selection & rewrite schema
- **Acceptance:** Rewritten length close to original; `matched_keywords` only
  contains keywords actually present; schema validates.

### M5 — LaTeX template + rendering (Step 5)
**Goal:** Rewrite result → `.tex` file (page count not yet handled).
- [ ] `resume.tex.j2` template (based on the user's existing resume style)
- [ ] Jinja2 env + custom LaTeX-escape filter (`& % _ # $`, etc.)
- [ ] Keyword highlight: define `\hlkw` in preamble, wrap matched_keywords
- [ ] Output `.tex` to a temp directory
- **Acceptance:** Renders valid `.tex`; bullets with special chars don't break
  compilation; if LaTeX is installed, produces a PDF.
- **⚠️ Dependency:** Need tectonic (recommended, single binary) or pdflatex;
  need the user's existing resume `.tex` as the template blueprint.

### M6 — Compile + one-page check loop (Step 6, core agent loop)
**Goal:** `.tex` → compile → check page count → compress & retry if too long,
implemented as a state machine / loop.
- [ ] Compile wrapper (capture logs/errors)
- [ ] Read page count via pypdf
- [ ] > 1 page: pick longest / lowest-priority bullets → LLM compress → re-render & re-compile
- [ ] Max iterations (default 5); on exceed, return best-effort + notice
- [ ] Compile failure: capture log, locate suspected escape issue, log in detail
- [ ] Structured logging of every iteration's input/output/state change
- **Acceptance:** Deliberately oversized content compresses to one page within
  ≤5 iterations or reports failure clearly; readable logs throughout; compile
  errors traceable to specific content.

### M7 — Cover letter generation (Step 7)
**Goal:** JD profile + rewritten experience summary + basic info → cover letter PDF.
- [ ] LLM generates the body; reserve a `company_context` field (Phase 2)
- [ ] Separate simple LaTeX template + same escaping
- [ ] Render & compile to PDF
- **Acceptance:** Produces a structurally sound cover letter PDF; special chars
  don't break compilation.

### M8 — End-to-end `/generate` wiring + UI polish
**Goal:** Chain the whole pipeline behind one call and finish the UI.
(The frontend itself was brought forward to M2.5 and grows each milestone; this
milestone is the final integration + polish, not the first frontend.)
- [ ] `POST /generate`: chain Step 2-7, return two PDF links + intermediate results
- [ ] `GET /materials` / `PUT /materials` (+ a basic material-editing UI)
- [ ] Single "Generate" button in `index.html`: JD → profile → selection → both PDFs to download
- **Acceptance:** From the page, paste a JD, click once, see intermediate
  results and download both PDFs.

---

## Changelog
> Reverse chronological. Format: `date — milestone — what was done / acceptance result`
- 2026-06-14 — M3.5 — ✅ Done (pulled forward from Backlog at user request — they wanted real resume data, not the sample). Added text extraction, `decompose_resume` LLM step, `POST /materials/ingest` + `PUT /materials`, `/health.materials_source`, and a "Step 1 — Your material library" UI card (upload/paste → preview → save). pytest 25/25; live PUT→GET→health roundtrip verified; added `python-multipart`.
- 2026-06-14 — M3 — ✅ Done. Added swappable keyword `scoring.py`, `step3_selection.select_experiences` (category filter → score → per-item cap → global trim keeping ≥1/group), `POST /select`, pulled `GET /materials` forward. UI gained a "Selected experiences" panel (score badges + matched-keyword chips) chained after Analyze. pytest 19/19; live endpoints verified.
- 2026-06-14 — M2.5 — ✅ Done. Brought the frontend forward per user request (eager to demo MVP). Zero-build single page `app/static/index.html` served at `GET /`, wraps `/jd/analyze` + `/health` status line. Strategy change: UI now grows incrementally per milestone, superseding "frontend last". pytest 11/11.
- 2026-06-14 — M2 — ✅ Real-key end-to-end verified with a synthetic MLE JD; output parsed cleanly into `JDProfile` (primary=MLE, secondary=[AI,DE]). Connected GitHub remote `js3888-shunshun/resume-tailor-tool` (branch main), pushed all commits.
- 2026-06-14 — M2 — ✅ Done (mock acceptance). Added injectable-mock `LLMClient` (JSON parse + fence tolerance + retry), `jd_analysis` prompt, `step2_jd_analysis.analyze_jd`, `POST /jd/analyze`. pytest 11/11; no key→503, empty→422.
- 2026-06-14 — M1 — ✅ Done. Skeleton + 3 Pydantic schema groups + sample library + FastAPI `/health` + startup detection. venv created, pytest 5/5, `/health` 200. git initialized & committed (c0cb74e).

## Backlog / Future (Phase 2+, do not build yet)
- LinkedIn cold message generation
- Company-info search injected into the cover letter (`company_context`)
- Embedding semantic retrieval to replace keyword scoring (swap `scoring.py`)
- ~~Upload existing resume → LLM auto-decompose into the material library~~
  (DONE — pulled forward to M3.5)
- Auto-add content when one page but visibly sparse (the Step 6.4 TODO)
- Editable preview before saving the ingested library (currently view-only JSON)

## Current blockers / awaiting user
- [x] Set `ANTHROPIC_API_KEY` (needed from M2) — configured, real call verified
- [x] GitHub remote — connected `js3888-shunshun/resume-tailor-tool`, branch main
- [ ] Install tectonic or pdflatex (needed from M5)
- [ ] Provide the existing resume `.tex` source as the resume-template blueprint (needed for M5)
