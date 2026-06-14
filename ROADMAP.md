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

### M3 — Experience matching & selection (Step 3)  ✅ Done (revised to experience-level)
**Goal:** JD profile + material library → preliminary selection (no rewrite yet).
**Design (revised per user feedback):** the unit of selection is the EXPERIENCE,
not the bullet. Experiences are scored AS A WHOLE (category fit + keyword breadth)
and the top N experiences / top M projects are kept; a selected experience keeps
ALL its bullets. Targets are **section counts** (`target_experiences`,
`target_projects`), not a bullet count. Bullet-level trimming for one-page fit is
deferred to the Step 6 compile loop.
- [x] Category-intersection filter to build the candidate pool
- [x] `scoring.py`: `score_bullet` (keyword overlap, word-boundary) as an ingredient,
  plus `score_experience` (category fit + distinct-keyword breadth). Swappable
  `ExperienceScorer` interface for later embedding upgrade.
- [x] `step3_selection.select_experiences(target_experiences, target_projects)` —
  rank whole experiences/projects, keep top-N, all bullets travel together
- [x] `SelectionResult` carries experience-level `score` + `matched_keywords`
- [x] `POST /select` (section-count targets); `GET /materials` for UI titles
- [x] UI: "Selected experiences" panel — per-experience score + JD-keyword chips +
  its full bullet list; "Experiences" / "Projects" count inputs
- **Acceptance:** ✅ Pure functions, no LLM; unit-tested (bullet word-boundary,
  experience category+keyword score, distinct keywords, whole-experience kept,
  section-count limit, ranking, category filter, skills). pytest 34/34. Live
  `/select` on the real "Joy Sun" library: 2 experiences (7 & 2 bullets, intact),
  1 project, experience-level scores 10/8/3.

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
  ingest empty→422. (Real-resume LLM decompose verified by user: saved "Joy Sun"
  library — 3 experiences / 2 projects / 24 skills / 16 bullets.)
- **Dep added:** `python-multipart` (file uploads).
- **M3.5b — Structured editable library (added per user feedback):** the raw-JSON
  preview was replaced with a fully **editable, scrollable** library editor in the
  UI (per-experience/project/skill, fixed format, **tagged/untagged badges** per
  bullet, category toggles, add/remove items & bullets, inline tag editing).
  Plus **append mode**: re-upload a newer resume → `merge_libraries()` adds only new
  experiences/bullets/skills into the saved library. `materials_merge.py` is a pure,
  tested module (6 tests: bullet-append, new-item, skill-cat-union, edu-dedup,
  id-renumber, no-base-mutation). pytest 31/31.

### M4 — Content rewriting module (Step 4)  ✅ Done (ATS-oriented, whole-experience)
**Goal:** Tailor the selected experiences to the JD for ATS fit. Runs AFTER
selection, on the user's finalized (manually adjustable) working set.
- [x] **Whole-experience rewrite** (revised per user feedback — 1:1 bullet rewrite
  only changed syntax). `rewrite_selected` sends each experience's full bullet set +
  JD in one batched call; the LLM amplifies JD-relevant points, condenses/drops weak
  ones (bullet count can shrink), surfaces JD keywords/skills for ATS, uses strong
  action verbs, quantifies where the original supports it — never fabricating.
- [x] Output goes to `rewritten_bullets` (originals kept in `selected_bullets` for
  before→after); fallback to originals if the model omits an experience.
- [x] Prompt (`llm/prompts/rewrite.py`): senior-recruiter/ATS framing, truthfulness absolute.
- [x] `POST /rewrite` enriches the prompt with title/org context from the library.
- [x] UI: prominent "Polish to JD" CTA; experience-level before→after two-column
  panel with bullet-count delta and the JD keywords surfaced.
- **Acceptance:** ✅ Unit-tested (count change, exp+proj batching, missing fallback,
  context titles, dict-wrap, no-op, missing-key). pytest 44/44. Real call: 3 bullets
  → 2 (dropped an irrelevant "team meetings" line; amplified the ML one to
  "Built an LLM-powered… applying RAG… 30%", strong verbs, kept the real metric).
- **M4-rev2 (per user feedback — richer, not shorter):** flipped the prompt from
  condense→**enrich**: aim 4-6 strong bullets/experience, expand detail, and the
  user explicitly opted into *realistic embellishment* — may add plausible,
  conservative, interview-defensible figures/details built on the real experience
  (not a different job). Also `/select` now returns ALL experiences in `ranked_*`
  (no category pre-filter) so the user can manually add ANY experience; auto-select
  still only picks score>0. Verified: 1 sparse bullet → 6 enriched bullets with
  realistic metrics; all 5 library experiences addable.
- **Note:** embellishment now adds invented-but-plausible numbers by design — the
  UI flags "review the after for accuracy".
- **M4-rev3 (editable after + finalize):** the "after" column is now fully editable
  (per-bullet textarea, add/remove bullet), backed by a client-side `REWRITE_DRAFT`.
  A "Finalize draft" button drops empty bullets and snapshots `FINAL_DRAFT` — the
  vetted content M5 will consume. Frontend-only.

### M5 — LaTeX template + rendering (Step 5)  ⬅️ Next
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
- 2026-06-14 — M4-rev3 — ✅ Done. Made the "after" column editable (per-bullet textarea, add/remove) backed by client-side REWRITE_DRAFT; "Finalize draft" snapshots FINAL_DRAFT (empty bullets dropped) as the vetted input for M5. Frontend-only; pytest 44/44.
- 2026-06-14 — M4-rev2 — ✅ Done (per user feedback). Rewrite now ENRICHES (4-6 bullets, expand detail) with opt-in realistic embellishment (plausible figures/details on the real experience); UI flags "review for accuracy". `/select` returns ALL experiences in ranked_* (no category filter) so any can be manually added; auto-select still score>0. pytest 44/44; verified 1 bullet → 6 enriched, all 5 experiences addable.
- 2026-06-14 — M4-rev — ✅ Done. Reworked rewriting from 1:1 (only changed syntax) to ATS-oriented WHOLE-EXPERIENCE rewrite: amplify JD-relevant points, condense/drop weak ones (bullet count can shrink), surface JD keywords/skills, strong verbs, quantify where supported, no fabrication. Output to `rewritten_bullets`; UI shows experience-level before→after with count delta. pytest 44/44; real call dropped an irrelevant bullet and lifted ATS keywords while keeping the real metric.
- 2026-06-14 — M4 — ✅ Done. Content rewriting after selection: `step4_rewrite.rewrite_selected` (one batched LLM call, JSON array, id-mapped write-back, original fallback), `rewrite.py` prompt (truthful/keyword-aware/length-preserving), `POST /rewrite`. UI: prominent "Polish to JD" CTA on the working selection + before→after panel. pytest 43/43; real call kept metrics and used JD keywords only where applicable.
- 2026-06-14 — M3-rev2 — ✅ Done (transparency + manual override per user feedback). score_experience now returns a breakdown (category_score, keyword_score, matched_categories); SelectionResult also returns `ranked_experiences/projects` (all candidates, not just top-N). UI: each pick shows a "why" line (matched JD categories + keywords, or "category only" when no keyword) and the score split on hover; user can remove any pick and add others from a ranked dropdown. pytest 37/37; verified live (selected 2 of 5 ranked, breakdown correct).
- 2026-06-14 — M3-rev — ✅ Done. Reworked Step 3 from bullet-level to EXPERIENCE-level per user feedback: experiences scored & selected as whole units (all bullets kept together), targets are section counts (`target_experiences`/`target_projects`) not bullet count. Added `score_experience`, rewrote `select_experiences`, updated `/select` + UI (two count inputs, per-experience score). pytest 34/34; verified live on real library.
- 2026-06-14 — M3.5d — ✅ Done (fixes + restyle per user feedback). (1) Bug fix: consecutive text appends lost earlier ones — append now merges into the client's CURRENT in-memory library (`base_library` form field) instead of the saved disk copy; regression-tested via TestClient with monkeypatched decompose (pytest 32/32). (2) Library view de-skeuomorphed: dropped the faux-PDF paper/serif look for a clean on-theme card view. (3) Switched the whole UI to a light, minimal theme with color accents; removed all emoji.
- 2026-06-14 — M3.5c — ✅ Done (UI restructure per user feedback). Left-sidebar TAB layout: "Material Library" vs "Tailor to JD". Library now shows a concise, resume-like (paper/serif) view by default — title+org+dates with bullets listed underneath, skill tags hidden behind a per-experience "show tags" toggle. Manual add via paste → Parse & append. Granular editing moved behind an "Edit mode" toggle (reuses the form editor). Frontend-only; backend unchanged; pytest 31/31.
- 2026-06-14 — M3.5b — ✅ Done. Replaced raw-JSON preview with a structured, scrollable, EDITABLE library editor (tagged/untagged badges, category toggles, add/remove items+bullets, inline tag edit). Added append-mode resume merge via tested `materials_merge.merge_libraries`. User has saved their real "Joy Sun" library. pytest 31/31.
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
