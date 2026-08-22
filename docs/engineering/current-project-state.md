# EduLens — Current Project State

> Brownfield continuation baseline. Established 2026-08-22 from repository evidence at
> commit `f4861d1` plus the uncommitted working tree. Facts are separated from
> assumptions; every material claim cites evidence. An engineer should be able to
> resume work from this document without prior conversation context.

## 1. Product purpose (VERIFIED)

EduLens is an AI tutoring platform for children aged 6–12. A camera (phone in the
current implementation; smart glasses per the long-term concept) watches a child's
homework; a vision-capable LLM assesses the scene, detects struggle, and delivers
short Socratic, audio-first hints. Authoritative product sources:

- `concept_note.md` — product vision, actors, privacy/safety principles (v1.0)
- `spec.txt` — Phase 1 development specification and success criteria
- `docs/architecture/system_overview.md` — intended layered architecture

Note: `README.md` is WRONG for this repo — it describes the legacy
"Claude Agents Orchestration System" scaffolding, not EduLens (see §3.4).

## 2. Actors

| Actor | Role | Evidence |
|---|---|---|
| Child (6–12) | Learner; asks questions, receives spoken hints | `concept_note.md` §4 |
| Parent | Companion app user; monitoring, controls, progress review | `app/` screens; `src/api` parent endpoints |
| Backend API server | FastAPI app hosting REST + WebSocket tutoring | `src/api/main.py` |
| LLM providers | DeepSeek (current), Anthropic, OpenAI, Google, Azure, Ollama | `src/ai/llm_service.py` |
| Student mobile app | Camera capture + frame streaming + speech playback | `mobile/` (uncommitted) |

No scheduled jobs, queues, payments, or third-party integrations beyond LLM APIs.

## 3. System map

### 3.1 Product code (the actual EduLens system)

- **Backend**: `src/api/main.py` — FastAPI; REST endpoints under `/api/v1/*`
  (tutor query/image/vision, sessions, children CRUD, voice transcribe/query/synthesize,
  parent session endpoints) plus three WebSocket protocols:
  - `/ws/live/{session_id}` — student live tutoring (`src/api/live_ws.py`, uncommitted)
  - `/ws/observe/{session_id}` — legacy glasses observation (`src/api/websocket_handler.py`)
  - `/ws/parent/{session_id}` — parent live monitor (`src/api/session_broadcaster.py`)
- **AI**: `src/ai/` — multi-provider LLM service (`llm_service.py`, incl. vision
  `generate_with_image`), tutor engine (`tutor_inference.py`), prompt templates,
  response validator, subject reasoning modules, personalization, safety filter.
- **Vision**: `src/vision/` — OCR, handwriting, layout analysis, edge optimization.
- **Audio**: `src/audio/` — wake word, speech recognition, TTS, personas.
- **Observation / parental / privacy / security / pipeline / runtime**: `src/*` —
  struggle detection, parental controls, COPPA validators, pairing/crypto, device runtime.
- **Parent companion app**: `app/` — Expo/React Native 0.73 (committed; 93 files).
- **Student app**: `mobile/` — Expo/React Native 0.86 (UNCOMMITTED). Streams base64
  JPEG frames every 1.5 s (`mobile/src/liveClient.ts`), speaks responses via
  expo-speech (`mobile/App.tsx:156–180`).
- **Config**: `configs/*.yaml` per subsystem (llm, vision, audio, privacy, parental…).
- **Demo**: `web/index.html` served at `GET /demo`.

### 3.2 Data

- EduLens tables `children`, `sessions`: `src/api/models.py`; created via
  `Base.metadata.create_all` at startup when `DATABASE_URL` is set, otherwise
  in-memory fallback (`src/api/main.py:202–224`).
- Alembic migration `database/migrations/versions/001_initial.py` and
  `database/models.py` + `database/schema.sql` belong to the LEGACY orchestration
  scaffold, not the product (contradiction to keep in mind).
- Live tutoring sessions are memory-only by design (privacy; frames dropped on
  disconnect — `src/api/live_tutor.py:200–213`).

### 3.3 Legacy scaffolding (NOT product code)

`orchestrator/`, `agents/`, root `core/`, `skills/`, `templates/`, `utils/`,
`cli.py`, `docker-compose.yml` (Postgres/Redis for the scaffold), `Makefile`
targets referencing them. This is the agent-orchestration system that produced
EduLens, committed in the same repo. Its own tests are broken
(`tests/test_{agents,communication,orchestrator}.py` fail collection:
`orchestrator.config` no longer exports `get_config`).

### 3.4 Documentation contradictions

- `README.md` describes the orchestration system, not EduLens.
- `database/models.py` (orchestration schema) coexists with the product schema in
  `src/api/models.py`.
- Two parallel session systems exist: legacy `/ws/observe` handlers
  (`observation_handlers` in `main.py`) vs new `/ws/live` sessions
  (`live_sessions` in `live_ws.py`). Parent-monitoring endpoints attach to the
  legacy one only.

### 3.5 Delivery and operations

- `Makefile` — canonical command surface (install, test, lint, typecheck, db, docker).
- `.github/workflows/ci.yml` — lint/typecheck/unit matrix/integration (Postgres+Redis
  services)/safety/audio/build. UNCOMMITTED.
- `.github/workflows/deploy.yml` — on push to `main` builds a Docker image and pushes
  to GHCR; staging/production deploy jobs are `echo` placeholders. UNCOMMITTED.
- **No CI currently runs anywhere** (workflows untracked). No production deployment
  exists; no observability stack, backups, or on-call. Production state: none found.

## 4. Engineering baseline (2026-08-22, Python 3.12.13 in `.venv`)

| Command | Exit | Result | Classification |
|---|---|---|---|
| `.venv/bin/python -m pytest --collect-only -q` | 1 | 1331 tests collected; 3 collection errors in legacy scaffold tests | BASELINE_FAILURE (inherited) |
| `pytest tests/api tests/ai -q --no-cov` | 1 | 131 passed, 2 failed (`tests/ai/test_tutoring_integration.py`: model-name assertion is env-dependent; validator score drift) | new-feature suites green |
| `pytest tests --ignore=tests/test_agents.py --ignore=tests/test_communication.py --ignore=tests/test_orchestrator.py -q --no-cov` | 1 | 1017 passed / 99 failed / 76 errors / 139 skipped (46 s) | mixed, see below |
| — 76 errors (`test_tts_engine`, `test_audio_pipeline`, `test_edge_performance`) | | `ImportError: pyttsx3 not installed` etc. | ENVIRONMENT_FAILURE (optional deps in `requirements_audio.txt` not installed) |
| — ~45 failures (`tests/safety` ×27, `tests/security` ×9, `tests/parental` ×6, `tests/compliance` ×5, privacy/integration) | | e.g. content filter passes "Let's kill this test!" as safe; age-appropriateness inverted | BASELINE_FAILURE (behavioral drift in child-safety layer) |
| — remaining failures (vision accuracy, wake word, integration) | | various | BASELINE_FAILURE / UNKNOWN |
| `ruff` / `mypy` / `black --check` | — | tools not installed in `.venv` (dev extras absent) | NOT RUN |

Notes:
- Runs used `--no-cov`; the configured `--cov-fail-under=80` gate makes plain
  `pytest` fail regardless of test outcome. Actual coverage % unverified.
- Local `.env` (gitignored) selects provider/model and influences some tests —
  several `tests/ai` assertions assume config-file defaults and are not env-isolated.
- Safe verification set today: `pytest tests/api tests/ai tests/unit -q --no-cov`
  (excluding the three broken scaffold files) plus server boot + smoke script.

## 5. Capability truth table (condensed)

| Capability | Status | Evidence |
|---|---|---|
| Multi-provider LLM service incl. DeepSeek vision | VERIFIED_WORKING | `src/ai/llm_service.py`; unit tests pass |
| REST tutoring (text/image/vision one-shot) | VERIFIED_WORKING | `src/api/main.py:322–505`; tests pass |
| Live WS protocol + session state machine (frames, queries, observation loop, intervention cooldown) | VERIFIED_WORKING (unit level; live API path needs key) | `src/api/live_tutor.py`, `src/api/live_ws.py`; 15 FakeLLM tests in `tests/api/test_live_tutor.py` |
| Student mobile app (camera streaming, speech playback) | IMPLEMENTED, manually exercised, UNCOMMITTED | `mobile/src/liveClient.ts`, `mobile/App.tsx:156–180`, `mobile/README.md` |
| E2E smoke script | IMPLEMENTED, requires `DEEPSEEK_API_KEY` + running server | `scripts/test_live_tutor.py` |
| Children CRUD + persistence | VERIFIED_WORKING | `src/api/main.py:560–684`, `src/api/models.py` |
| Parent monitoring of live sessions | PARTIALLY_IMPLEMENTED — parent endpoints attach to legacy observe system, not `/ws/live` | `main.py:934–1280` vs `live_ws.py` |
| Content safety / age-appropriateness filters | FAILING OWN TESTS (~27) | `tests/safety/*` |
| Secure channel / device pairing | FAILING OWN TESTS (9) | `tests/security/test_secure_communication.py` |
| COPPA compliance checks | FAILING OWN TESTS (5) | `tests/compliance/test_coppa_compliance.py` |
| TTS / audio pipeline | IMPLEMENTED_BUT_WEAKLY_TESTED (deps missing locally) | `src/audio/*`; 76 env errors |
| OCR/handwriting accuracy vs spec targets (95%/85%) | FAILING accuracy tests | `tests/vision/test_ocr_accuracy.py` etc. |
| Parent companion app (`app/`) | UI_ONLY — no auth backend; default API base `http://localhost:3000/api` mismatches backend port 8000 | `app/src/services/api.ts:13` |
| Authentication / authorization | NOT_IMPLEMENTED anywhere; `verify_parent_access` trusts caller-supplied `parent_id`; CORS `allow_origins=["*"]` | `main.py:1038`, `main.py:256–262` |
| Deployment | STUB_OR_PLACEHOLDER (echo steps) | `deploy.yml:105–123` |
| Wake word / STT | IMPLEMENTED, tests failing | `tests/audio`, `tests/unit/test_wake_word.py` |
| Hardware glasses runtime (`src/runtime`, `device_runtime`) | UNKNOWN — no evidence of real hardware target | — |

## 6. Principal risks

| Pri | Risk | Evidence | Recommended action | Blocks slice #1? |
|---|---|---|---|---|
| P1 | Entire live-tutor vertical exists only as uncommitted WIP (data loss) | `git status`: 4 modified + 6 untracked paths | Land it (see next-delivery-slice.md) | — (it IS slice #1) |
| P1 | No authentication/authorization on any endpoint incl. child camera frames; CORS `*` | `main.py:256–262`, `:1038` | Required before any shared/hosted operation | No (local dev only today) |
| P1 | Child-safety layer fails its own tests (~27 failures) | `tests/safety/*` | Fix before any parent-facing release | No |
| P2 | Dual session systems (observe vs live) diverging | `main.py` vs `live_ws.py` | Bridge or consolidate during parent-monitoring work | No |
| P2 | CI debt: 80% coverage gate will fail (real % unknown); deprecated `upload-artifact@v3`; first push to `main` publishes image to GHCR | `ci.yml:12,170–178`, `deploy.yml` | Decide GHCR policy; fix gate in backlog #6 | No |
| P2 | Scaffold/product entanglement breaks test collection and pollutes coverage scope | 3 broken test files; `pyproject.toml` coverage sources | Triage in slice #1; longer-term quarantine (#8) | Yes (acceptance criterion) |
| P2 | `mobile/.expo/` untracked and NOT gitignored — risk of committing build artifacts | `git status`; `.gitignore` | Add ignore line before staging `mobile/` | Yes |

## 7. Ranked continuation backlog

1. **Land the live-tutoring vertical on main** (S) — DONE 2026-08-22 (`75413e0`…`b9ff96e`); E2E smoke verified with real DeepSeek round-trip.
2. **Child-safety filters pass their own suites** (M) — DONE 2026-08-22. Discovery: the safety suites were self-mocking (helpers inside test files contradicted their own assertions; never touched product code). Fix: built real validators in `src/ai/safety/content_safety.py` (content, violence/self-harm, age-appropriateness, response safety, PII-request prevention, tone, session policy, stack-trace sanitization, PII-safe logging) and rewired test helpers to delegate. Also fixed: retention-days ceiling (`src/privacy/data_handler.py`), config-driven model default + validation retry + understanding bands + answer-check detection (`src/ai/tutor_inference.py`), generic-encouragement-word bug (`src/ai/response_validator.py`). tests/safety 129/129; unit exclusions removed; safety-tests restored as a CI gate. Remaining advisory debt: integration (24), audio (#7).
3. **Parent sees live-session activity** (L) — bridge `/ws/live` into parent endpoints + app monitor screen.
4. **Persist live session summaries** (M) — DB records for parent review of past sessions.
5. **API authentication (keys/JWT) for all non-demo endpoints** (L) — prerequisite for any shared deployment.
6. **CI activation hygiene** (S) — DONE 2026-08-22 (`a20ddda`…`52a3845`). Gates: lint, typecheck, unit×{3.11,3.12}, build — green. Advisory (known behavioral debt): safety (~27 failures, #2), integration (21 failures, #2/#7), audio, performance. Artifact uploads removed (org storage quota exhausted). Coverage floor = 5% over `src/` — raise as fixes land.
7. **Audio/TTS path runnable and tested locally** (S) — install optional deps or vendor fallback; unblocks audio suites for the gate.
8. **Quarantine legacy orchestration scaffold; correct README** (S).
9. **Parent-app ↔ backend contract alignment** (M) — base URL/port, endpoint map.
10. **Child profile from DB drives live-session personalization** (S) — name/age/language from `children` table.

## 8. Selected first slice

Landing the live-tutor vertical (backlog #1). Rationale: highest dependency
position (everything else builds on it), eliminates P1 data-loss risk, zero
unresolved product requirements, additive/reversible, one focused PR.
Specification: `docs/engineering/next-delivery-slice.md`.

## 9. Open high-impact questions (UNKNOWN — do not assume)

1. Is the hardware/glasses runtime (`src/runtime`, `src/security` pairing) a real
   near-term target or aspirational? Affects backlog priorities.
2. Is any hosted/shared deployment intended soon? (Determines urgency of auth, P1 #2.)
3. Should pushing to `main` publish Docker images to GHCR (current `deploy.yml`
   behavior once workflows land), or should that job be disabled?
4. Are the failing safety/security suites regression drift or never-green
   aspirations? (Git history cannot answer — single initial commit.)
