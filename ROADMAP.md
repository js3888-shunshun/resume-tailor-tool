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
- **M4-rev4 (preview/edit modes):** polished result now opens in a clean read-only
  PREVIEW (single bullet list per experience, "show original" collapsible); an
  Edit/Preview toggle switches to per-bullet editing where textareas auto-grow to
  fit all text (no inner scroll), with per-bullet delete and add. Frontend-only.

### M5 — LaTeX template + rendering (Step 5)  ✅ Done
**Goal:** Rewrite result → `.tex` file (page count not yet handled).
- [x] `render/templates/resume.tex.j2` — built from the user's own resume `.tex`
  (same preamble: 10pt a4, 0.5in margin, titlesec uppercase sections, enumitem).
- [x] Jinja2 env with LaTeX-safe delimiters (`\VAR{}`, `\BLOCK{}`) + single-pass
  `latex_escape` filter (`& % $ # _ { } ~ ^ \`) so specials never re-escape.
- [x] Keyword highlight: `\newcommand{\hlkw}` (bold) in preamble; `render_bullet`
  escapes then word-boundary, case-insensitive wraps matched_keywords (longest
  first, never double-wraps).
- [x] Pure renderer over a self-contained `ResumeDocument` (schemas/render.py);
  `/render` router assembles it from (library + finalized rewrite). Omits empty
  segments (blank location/dates/sections) so nothing dangles.
- [x] `render/compile.py` — best-effort tectonic/pdflatex compile (ready for when
  an engine is installed); `POST /render` returns `.tex` always + compiles a PDF
  if an engine is present; `GET /render/pdf` downloads it.
- [x] UI: "Resume document (Step 5)" card after Finalize — Generate, bold-keywords
  toggle, Download .tex, Download PDF (when compiled), live .tex source.
- **Acceptance:** ✅ Renderer pure-function tested (escape order, keyword highlight
  boundary/overlap/escape-then-highlight, balanced braces, omitted sections,
  skills escaping). pytest 55/55. Live `/render` on the real "Joy Sun" library →
  valid one-page `.tex`, balanced braces, `\hlkw` on JD keywords, `%`/`&`/`$`/`_`
  escaped; `pdf_available:false` (no engine yet, as expected).
- **⚠️ Dependency (PDF only):** install tectonic (`winget install
  TectonicProject.Tectonic`) or pdflatex to turn the `.tex` into a PDF in-app.
- **M5-rev (schema completion + JD-tailored skills):**
  - ✅ Added the missing header fields — `PersonalInfo.location`,
    `Education.location`/`gpa`, `Project.organization`/`start_date`/`end_date` —
    updated the decompose prompt to extract them (GPA out of `details`), the
    render router/template to use them, and the library editor to expose them
    (so existing saved data can be completed without re-uploading).
  - ✅ JD-tailored SKILLS: new `step4_skills.tailor_skills` (LLM regroups &
    prioritizes the library's skills into labeled, JD-relevant `SkillGroup`s,
    surfacing JD skills, trimming irrelevant ones; truthful to the inventory).
    Returned by `/rewrite` (Polish step), editable in the polish panel (add/edit/
    remove groups), carried into `FINAL_DRAFT` and rendered two-up like the user's
    resume (`\textbf{label:} a, b \hfill ...`); flat list is the fallback.
  - Project heading layout fixed (\\textbf{title} | org \\hfill date) vs experience
    (\\textbf{org} | \\textit{title} | location \\hfill date) via `RenderEntry.kind`.
  - pytest 64/64. Live: real `/rewrite` regrouped 50 skills → 5 JD groups (ML & AI
    first, finance skills dropped for an MLE JD); grouped render two-up verified.

### M6 — One-page auto-fit loop (Step 6)  ✅ Done
**Goal:** `.tex` → compile → check page count → adjust to land on EXACTLY one page,
as a deterministic loop. (Re-scoped per user: typography-only, zero-LLM — mimic a
person nudging spacing. Loosen to fill a sparse page; tighten to fit a full one.
If even the tightest spacing overflows, report "too long, trim manually" rather
than spending tokens to rewrite. LLM content-compression intentionally NOT built.)
- [x] Compile wrapper already captures logs/errors (M5-compile-fix); `count_pages`
  via pypdf added to `render/compile.py`.
- [x] Parameterised spacing: `render/layout.py` (`Layout` dataclass + `TIGHT`/
  `LOOSE`/`DEFAULT` presets + `layout_for(scale)` interpolation); template knobs
  (`\linespread`, `\parskip`, itemize `topsep`/`itemsep`, section spacing) are now
  `\VAR{layout.*}`; `render_resume(doc, layout=None)`.
- [x] `render/fit.py` `fit_to_one_page`: check tightest (overflow?) → check loosest
  (fits? use it) → binary-search the largest scale that stays 1 page (≤5 iters);
  compiles the winner to `output/resume.pdf`. Returns status fit/overflow/no_engine/error.
- [x] `/render` gained `fit_one_page` (default on) + `fit_status`/`pages` in the
  result; UI got a "fit to one page" toggle and a ✓/⚠ status line.
- **Acceptance:** ✅ pytest 80/80 (+test_layout, +test_fit with a mocked height
  model covering overflow / loosest-fits / binary-search-fills / cleanup). Live
  end-to-end on real tectonic: sparse doc → `fit` scale=1.0 (fills the page),
  oversized doc → `overflow` flagged (PDF still returned at tightest), ~2.5–4s per
  generate. No LLM tokens used.

### M7 — Cover letter generation (Step 7)  ✅ Done
**Goal:** JD profile + rewritten experience summary + basic info → cover letter PDF.
- [x] `llm/prompts/cover_letter.py` — first-person, sincere, one page (3-4 paras,
  ~250-330 words). HARD rules per user: NO em/en dashes, NO parentheses, and a
  banned-AI-cliche list ("excited to", "leverage", "delve", "Furthermore", …).
- [x] `pipeline/step7_cover_letter.py` `generate_cover_letter`: builds a truthful
  background summary from the library (focused on the finalized selection when
  given), one LLM call, `_sanitize` strips dashes/parens as a safety net.
- [x] `schemas.CoverLetterDocument` + `render/cover_letter.py` + a simple
  `cover_letter.tex.j2` (reuses the LaTeX-safe env + `latex_escape`).
- [x] `POST /cover-letter` (+ `GET /cover-letter/pdf`), registered in main.
- [x] UI: its own left sidebar tab "Cover Letter" — generate, preview, download
  PDF/.tex named `CoverLetter_<Company>_<Role>`; one-page status.
- **Acceptance:** ✅ pytest 84/84 (sanitizer, mock-LLM generation, real-content
  grounding, render escaping/balance). Live on real library + an MLE JD: 1 page,
  4 paragraphs, zero em-dashes/parens/banned phrases, grounded in real experiences
  (ByteDance DiD, ESG factors, RAG) — natural and specific.

### M8 — End-to-end `/generate` wiring + UI polish  ✅ Done (functional; visual restyle pending per user)
**Goal:** Chain the whole pipeline behind one call and finish the UI.
- [x] `POST /generate` (`routers/generate.py`): chains Step 2-7 by COMPOSING the
  existing endpoint functions (analyze → select → rewrite + tailor_skills → render
  endpoint with fit → cover-letter endpoint), so behaviour matches the tabs exactly.
  Returns profile, selection, rewritten exps/projs, skill_groups, `resume`
  (RenderResult) and `cover` (CoverLetterResult). PDFs at `/render/pdf` + `/cover-letter/pdf`.
- [x] `GET`/`PUT /materials` already exist (M3.5); library editor in the Library tab.
- [x] One-click "One-Click" left tab: JD textarea + targets + toggles (bold / fit /
  cover) + optional cover personalization; one button renders both PDFs side by side
  with download links named `Resume_…` / `CoverLetter_…` and a one-page/overflow status.
  Defaults 3 exp / 1 proj so the default result fits one page.
- **Acceptance:** ✅ pytest 89/89 (+test_generate: chaining wires rewrite→render &
  →cover, cover can be skipped). Live end-to-end on real library + MLE JD: full run
  ~42–62s, profile+selection+5 skill groups, resume PDF (3/1 → fit one page; 4/2 →
  overflow flagged), cover PDF 1 page / 4 paras. UI shows both previews + downloads.
- **Note:** visual/style polish intentionally deferred — user will adjust the UI look next.

---

## Changelog
> Reverse chronological. Format: `date — milestone — what was done / acceptance result`
- 2026-06-19 — M9 (deploy: public site, shared login) — ✅ Done. Made the server STATELESS so it runs on Render for a few people: (1) Per-request library — `/select /rewrite /render /cover-letter /generate` take `library` in the body (browser-`localStorage`, file/sample fallback); frontend keeps the library client-side, Save writes localStorage, every call sends it. (2) Shared login — `APP_USERNAME`/`APP_PASSWORD` env; `/api/login` sets an HttpOnly cookie (so the PDF iframes are authorised too), `require_auth` gates all API routers, frontend shows a login overlay; auth disabled when `APP_PASSWORD` unset (local). (3) Owner's key for all — `make_client` dep builds the LLMClient from an optional `X-Anthropic-Key` header, else the server's `ANTHROPIC_API_KEY`. (4) Multi-user-safe PDFs — results now return the compiled PDF as `pdf_base64` (no shared file); each request compiles to a unique `uuid` stem (incl. the fit-probe) and cleans up; frontend previews/downloads from a blob URL. (5) Deploy — `Dockerfile` (installs + pre-warms tectonic), `.dockerignore` (excludes `.env`, personal `materials.json`, Windows `tools/`), `render.yaml`, `DEPLOY.md`. pytest 89/89; live verified end-to-end: login→401 when out / 200+cookie in; authed `/render` with library-in-body returns a valid inline `%PDF-`; per-request files cleaned up.
- 2026-06-19 — download-fix — ✅ Done (user: a downloaded PDF arrived as an unopenable "json file"). Root cause: the Download links pointed straight at `GET /render/pdf` / `/cover-letter/pdf`; if the PDF wasn't compiled at click time those endpoints return a JSON 404 body, and the anchor's `download="...pdf"` saved that JSON under a .pdf name. Fix: all four download buttons (resume, cover, both One-Click) now go through `savePdf(url, name)` which fetches the bytes, verifies a real `%PDF-` header, and only then saves a fresh `application/pdf` blob — otherwise it shows "PDF not ready, click Generate again" instead of saving junk. Frontend-only.
- 2026-06-19 — M4-rev5 + polish — ✅ Done (per user). (1) Rewrite QUANTIFIES HEAVILY: most bullets should carry a concrete number; when an experience is thin on numbers, ADD 3-4 plausible, conservative, interview-defensible figures even if the original had none (pairs with M5 auto-bolding of numbers). Live: a 2-bullet, number-less experience → 4 bullets with 9 numeric tokens, all realistic. (2) Skills labels avoid "&" (use "and"/one word); each group capped at 4-5 short skills to render on one line (4-6 groups). (3) UI: hid the native `<summary>` disclosure triangle on collapsible sections. pytest 89/89.
- 2026-06-19 — M8 — ✅ Done (functional; visual restyle deferred per user). One-click end-to-end: `POST /generate` (`routers/generate.py`) chains Step 2-7 by COMPOSING the existing endpoint functions (analyze_jd → select_experiences → rewrite_selected + tailor_skills → /render endpoint with one-page fit → /cover-letter endpoint), returning profile, selection, rewritten exps/projs, skill_groups, resume (RenderResult) and cover (CoverLetterResult); both PDFs served at the existing GET routes. New "One-Click" left tab: JD textarea + targets + toggles (bold/fit/cover) + optional cover personalization, one button → both PDFs previewed side by side with `Resume_…`/`CoverLetter_…` downloads and one-page/overflow status; defaults 3 exp / 1 proj so the default fits one page. pytest 89/89 (+test_generate). Live: full run ~42-62s; 3/1 → resume fits one page, cover 1 page / 4 paras.
- 2026-06-19 — M7-rev — ✅ Done (quality pass per user's 4-paragraph template). Rewrote the cover-letter prompt to the standard structure: P1 Intro (school+major, role, honest specific reason), P2 Why-this-company (MOST important: use company notes + raw JD to name a concrete value/product/project or a person spoken with, no generic praise, no fabrication), P3 Why-you (exactly TWO abilities, one real example each, explain not restate), P4 Thank-you. Targets ~400-460 words to FILL one page; expanded banned-cliche list. Added grounding inputs: raw `jd_text` + `company_notes` (the request and UI now pass them; UI got a "Why this company" textarea). Optional `recruiter`/`company_address` recipient lines — rendered only when provided (per user), and the salutation uses the recruiter name when given. pytest 87/87; live on real library + MLE JD with notes naming a contact → 1 page, 4 paras, 408 words, name-drops the contact and the eval-harness culture in P2, two explained abilities in P3, zero dashes/parens/cliches.
- 2026-06-19 — M7 — ✅ Done. Cover letter (Step 7): `prompt/cover_letter.py` writes a one-page, first-person, sincere letter with HARD rules per user — no em/en dashes, no parentheses, banned AI-cliche list — grounded in the candidate's real background + the JD. `step7_cover_letter.generate_cover_letter` (truthful background from library/finalized selection, `_sanitize` strips dashes/parens as a net), `CoverLetterDocument` + `render/cover_letter.py` + `cover_letter.tex.j2`, `POST /cover-letter` + `GET /cover-letter/pdf`. UI: dedicated left "Cover Letter" tab (generate/preview/download), PDF+.tex named `CoverLetter_<Company>_<Role>`. Also: resume PDF/.tex download now named `Resume_<Company>_<Role>` from the JD profile. pytest 84/84; live on real library + MLE JD → 1 page, 4 paras, zero dashes/parens/banned phrases, grounded in real experiences.
- 2026-06-19 — M6 — ✅ Done (re-scoped to typography-only per user, zero-LLM). One-page auto-fit: the template's vertical spacing is parameterised (`render/layout.py`: `Layout` + TIGHT/LOOSE/DEFAULT + `layout_for(scale)`; template knobs `\linespread`/`\parskip`/itemize/section-spacing are `\VAR{layout.*}`). `render/fit.py` `fit_to_one_page` compiles at varying `scale` and counts pages via pypdf: tightest-overflow → report `overflow` (UI asks to trim, no token spend); loosest-fits → use it; else binary-search the loosest spacing that stays one page (≤5 iters) so the page is filled evenly. `/render` gained `fit_one_page` (default on) + `fit_status`/`pages`; UI has a toggle + ✓/⚠ status. Decision: LLM content-compress/expand NOT built — user prefers manual trim over token cost; filling sparse pages is done purely by loosening spacing. pytest 80/80; live: sparse→fit scale 1.0, oversized→overflow, ~2.5–4s.
- 2026-06-18 — M5-compile-fix — ✅ Done (bug: PDF generation 500'd on real runs). `compile.py` ran tectonic/pdflatex with `text=True` but no encoding, so on a Chinese Windows Python decoded their UTF-8 output with GBK → `UnicodeDecodeError` in the reader thread → `proc.stdout/stderr` came back `None` → `log += proc.stdout + proc.stderr` raised `TypeError`, which `try_compile` didn't catch (it only caught `CompileError`), 500'ing `/render`. Fix: force `encoding="utf-8", errors="replace"`, guard the concat with `(... or "")`, and broaden `try_compile` to swallow ANY exception (degrade to tex-only, never 500). Verified live: bullets with en/em-dash, curly quotes, ≥, → now return `pdf_available=True` over HTTP. Reverted the `start.bat --reload` from the previous entry — its watcher+worker orphans and re-holds port 8000 (the documented reason this project runs without reload). pytest 71/71 (+test_compile.py).
- 2026-06-18 — M5-bullets+bold — ✅ Done (per user feedback). (1) Rewrite now targets exactly 3-4 dense bullets per experience (was 4-6), instructed to CONSOLIDATE so the 3-4 still cover all essential info (responsibility, methods/tools, scale, impact) rather than dropping facts. (2) Bolding in the PDF broadened: `matched_keywords` now also carries the core methods/tools/techniques (not just JD keywords) so they bold via `\hlkw`; and `render_bullet` auto-bolds standalone numbers/metrics (`30\%`, `\$1.2M`, `12x`, `1,000`) via `_NUMBER_RE` on the escaped text, skipping digits already inside a keyword (S3) or another `\hlkw`. Verified live: `Built a \hlkw{RAG} ... \hlkw{30\%} ... \hlkw{12x} ... \hlkw{1,000}`. Also added `--reload` (+`*.j2`) to `start.bat` so edits no longer need a manual restart. pytest 68/68.
- 2026-06-18 — M5-spacing-fix — ✅ Done (follow-up: changes weren't showing). Two causes: (1) the running `start.bat` server had no `--reload`, so it served pre-edit code — restarted it. (2) The saved `materials.json` parked GPA (`GPA: 3.9/4.0`) and the undergrad city (`Chengdu, China`) inside education `details`, so they rendered as bullets regardless of the new fields — migrated the data in place (GPA → `gpa` field, dropped the city bullet). Also switched the GPA separator from `\hspace{2em}` to ` | ` per the requested `Major | GPA: x` look. Verified via live `POST /render`: GPA on the major line, no education location, skills one-per-line. pytest 66/66.
- 2026-06-18 — M5-spacing — ✅ Done (per user feedback on PDF density). Tightened the LaTeX layout to fit more on one page: `\setlist[itemize]` with `topsep=1pt, itemsep=0pt, parsep=0pt` so bullet spacing matches normal line spacing; `\titlespacing` cut from `{10pt}{5pt}` to `{4pt}{2pt}`. Education reworked — dropped the school location, moved the date to the school row, and `gpa` is now a separate `RenderEducation` field rendered on the major's line. Technical Skills now renders one labeled group per line (was two-up `\hfill`). pytest 66/66; sample compile stays 1 page.
- 2026-06-15 — M5-pdf — ✅ Done. In-app PDF export + preview. Bundled the tectonic single binary into `backend/tools/` (gitignored, ~50MB, downloaded from the project's GitHub release); `detect_latex_engine` now finds a bundled/`RESUME_TAILOR_TECTONIC` tectonic before PATH. `/render` compiles on every generate; UI "Generate & preview PDF" embeds `/render/pdf` in an iframe (cache-busted) with a Download PDF link. Live: real "Joy Sun" library compiled to a 1-page PDF in the user's exact template (en-dash dates, bold JD keywords, two-up grouped skills). pytest 66/66.
- 2026-06-15 — M5-rev — ✅ Done. (1) Completed the resume header schema: added `PersonalInfo.location`, `Education.location/gpa`, `Project.organization/start_date/end_date`; updated decompose prompt (GPA out of details), render router/template, and the library editor inputs. (2) JD-tailored skills: `step4_skills.tailor_skills` (LLM regroups/prioritizes/trims the library skills into labeled `SkillGroup`s), returned by `/rewrite`, editable in the polish panel, carried into FINAL_DRAFT, rendered two-up like the user's resume. (3) Fixed project vs experience heading layout via `RenderEntry.kind`. pytest 64/64; live real `/rewrite` turned 50 skills into 5 JD-relevant groups (ML&AI first, finance dropped for an MLE JD).
- 2026-06-15 — M5 — ✅ Done. LaTeX rendering (Step 5): `resume.tex.j2` modeled on the user's own resume; Jinja2 env with `\VAR{}`/`\BLOCK{}` delimiters + single-pass `latex_escape`; `\hlkw` bold keyword highlight (`render_bullet`, word-boundary/longest-first/no double-wrap); pure renderer over a self-contained `ResumeDocument`; `/render` assembles it from library + finalized rewrite (omits blank segments), best-effort tectonic/pdflatex compile, `GET /render/pdf`. UI: "Resume document" card (Generate, keyword toggle, Download .tex/PDF). pytest 55/55; live render on real library produced a valid one-page .tex with balanced braces and escaped specials (`pdf_available:false` — no engine installed yet). Logged schema gaps (location/gpa/project meta) for M6/M8.
- 2026-06-14 — M4-rev4 — ✅ Done. Polished-result panel got a preview/edit toggle: clean read-only preview by default; Edit mode gives per-bullet auto-growing textareas (full text visible, no inner scroll) with delete/add. Frontend-only; pytest 44/44.
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
- [x] Provide the existing resume `.tex` source as the resume-template blueprint — received; `resume.tex.j2` modeled on it (M5)
- [x] LaTeX engine — bundled tectonic 0.16.9 into `backend/tools/` (gitignored); in-app PDF export + preview working. Other machines: drop a `tectonic.exe` in `backend/tools/` or set `RESUME_TAILOR_TECTONIC`.
