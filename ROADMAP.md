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

### M3 — Experience matching & selection (Step 3)  ⬅️ Next
**Goal:** JD profile + material library → preliminary selection (no rewrite yet).
- [ ] Category-intersection filter to build the candidate pool
- [ ] `scoring.py`: standalone scoring function (keyword overlap), **swappable interface**
- [ ] Sort by score + priority, cap bullets per experience (configurable `target_bullet_count`)
- [ ] Output `SelectionResult` (pre-rewrite)
- **Acceptance:** Pure functions, unit-testable without an LLM; given a mock JD
  profile, stably selects the expected bullets; scoring function has its own test.

### M4 — Content rewriting module (Step 4)
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

### M8 — Frontend integration + `/generate` wiring
**Goal:** End-to-end flow plus a minimal frontend.
- [ ] `POST /generate`: chain Step 2-7, return two PDF links + intermediate results
- [ ] `GET /materials` / `PUT /materials`
- [ ] Frontend (minimal Vite React): JD input → show JD profile / selection → download PDFs
- **Acceptance:** From the frontend, paste a JD, click once, see intermediate
  results and download both PDFs.

---

## Changelog
> Reverse chronological. Format: `date — milestone — what was done / acceptance result`
- 2026-06-14 — M2 — ✅ Real-key end-to-end verified with a synthetic MLE JD; output parsed cleanly into `JDProfile` (primary=MLE, secondary=[AI,DE]). Connected GitHub remote `js3888-shunshun/resume-tailor-tool` (branch main), pushed all commits.
- 2026-06-14 — M2 — ✅ Done (mock acceptance). Added injectable-mock `LLMClient` (JSON parse + fence tolerance + retry), `jd_analysis` prompt, `step2_jd_analysis.analyze_jd`, `POST /jd/analyze`. pytest 11/11; no key→503, empty→422.
- 2026-06-14 — M1 — ✅ Done. Skeleton + 3 Pydantic schema groups + sample library + FastAPI `/health` + startup detection. venv created, pytest 5/5, `/health` 200. git initialized & committed (c0cb74e).

## Backlog / Future (Phase 2+, do not build yet)
- LinkedIn cold message generation
- Company-info search injected into the cover letter (`company_context`)
- Embedding semantic retrieval to replace keyword scoring (swap `scoring.py`)
- Upload existing resume → LLM auto-decompose into the material library
- Auto-add content when one page but visibly sparse (the Step 6.4 TODO)

## Current blockers / awaiting user
- [x] Set `ANTHROPIC_API_KEY` (needed from M2) — configured, real call verified
- [x] GitHub remote — connected `js3888-shunshun/resume-tailor-tool`, branch main
- [ ] Install tectonic or pdflatex (needed from M5)
- [ ] Provide the existing resume `.tex` source as the resume-template blueprint (needed for M5)
