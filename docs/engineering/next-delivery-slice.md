# Next Delivery Slice — Land the Live-Tutoring Vertical

> Implementation-ready specification. Companion context:
> `docs/engineering/current-project-state.md`. Status: READY FOR IMPLEMENTATION.

## Outcome

A developer cloning `main` can run the complete live-tutoring loop — student app
camera → backend vision tutor → spoken Socratic hints — from committed code, with
the new unit tests and smoke script tracked in the repository and CI definitions
under version control.

## Current behavior (with evidence)

The entire live-tutor vertical exists only in the working tree at `f4861d1`:

- Modified: `.env.example`, `pyproject.toml`, `src/ai/llm_service.py`
  (`generate_with_image`, content-block messages), `src/api/main.py`
  (`load_dotenv`, `/api/v1/tutor/vision`, live router registration).
- Untracked: `.github/` (ci.yml + deploy.yml), `mobile/` (Expo student app),
  `scripts/test_live_tutor.py`, `src/api/live_tutor.py`, `src/api/live_ws.py`,
  `tests/api/` (24 unit tests using FakeLLM).
- `pytest tests/api -q --no-cov` currently passes (verified 2026-08-22).
- `mobile/.expo/` is untracked and NOT gitignored.
- Legacy scaffold tests break collection: `orchestrator/orchestrator.py:18`
  imports `get_config`, absent from `orchestrator/config.py`.

If this working tree is lost, the feature is lost. That is the risk this slice retires.

## Acceptance criteria

1. All WIP listed above is committed on `main` in logical units (backend vision +
   WS; tests; mobile app; CI workflows).
2. `.gitignore` contains `mobile/.expo/` BEFORE any commit stages `mobile/`;
   no Expo build artifacts land in git history.
3. `.venv/bin/python -m pytest tests/api -q --no-cov` → ≥ 24 passed, 0 failed.
4. `.venv/bin/python -m uvicorn src.api.main:app` boots with no import errors
   (with and without `DATABASE_URL` set).
5. `.venv/bin/python scripts/test_live_tutor.py` connects to the local server and
   completes the handshake + frame exchange (AI calls may be skipped without a key;
   document whichever mode was verified).
6. `pytest --collect-only -q` is clean overall: the three legacy files
   (`tests/test_agents.py`, `tests/test_communication.py`,
   `tests/test_orchestrator.py`) are either fixed trivially or explicitly excluded
   from default discovery (e.g. `collect_ignore` in `tests/conftest.py`) with a
   comment pointing at the scaffold quarantine backlog item (#8).
7. No unrelated files are staged; existing behavior of committed code is unchanged
   except where the WIP already defines it.

## In scope

- Committing existing working-tree content (as-is or with minimal lint-level fixes).
- `.gitignore` addition for `mobile/.expo/`.
- Collection-error triage per criterion 6.
- Commit message hygiene and logical grouping.

## Out of scope

- Authentication/authorization changes.
- Safety-filter or parental-control fixes (backlog #2).
- Parent-monitoring integration or DB persistence for live sessions (backlog #3/#4).
- Coverage-gate tuning or CI workflow edits beyond what already exists (backlog #6).
- Any refactor of legacy scaffolding beyond test collection exclusion (backlog #8).
- Dependency additions/upgrades.

## Architecture path

No new architecture. The slice preserves the WIP's shape:

- Entry points: FastAPI app `src/api/main.py` (registers `src/api/live_ws.router`);
  student app `mobile/App.tsx`; smoke script `scripts/test_live_tutor.py`.
- Data flow: phone camera → base64 JPEG frames over `/ws/live/{session_id}` →
  `LiveTutorSession` buffer (memory-only) → DeepSeek vision model
  (`LLMService.generate_with_image`) → observation/intervention + Q&A events →
  expo-speech playback on device.
- Persistence: none for live sessions (by design); children/sessions tables via
  `src/api/models.py` remain unchanged.

## Likely files and symbols

`.gitignore`; `mobile/**` (esp. `mobile/src/liveClient.ts`, `mobile/App.tsx`,
`mobile/package.json`, `mobile/package-lock.json`, `mobile/app.json`);
`src/api/live_tutor.py` (`LiveTutorSession`, `LiveTutorConfig`);
`src/api/live_ws.py` (`live_tutor_websocket`); `src/api/main.py`
(`tutor_vision`, lifespan); `src/ai/llm_service.py` (`generate_with_image`,
`DeepSeekProvider.vision_model`); `scripts/test_live_tutor.py`;
`tests/api/test_live_tutor.py`, `tests/api/test_llm_vision.py`;
`.github/workflows/{ci,deploy}.yml`; `pyproject.toml`; `.env.example`;
possibly `tests/conftest.py` (collection exclusion).

## Test plan

1. Unit/integration: `pytest tests/api -q --no-cov` (≥ 24 pass).
2. Regression guard: `pytest tests/unit tests/ai -q --no-cov` — no NEW failures vs
   baseline (2 known env-dependent failures in `test_tutoring_integration.py`).
3. Collection: `pytest --collect-only -q` exits clean after criterion 6.
4. Runtime: boot server locally; run smoke script; verify `connected` →
   `config_applied` → frames accepted → `tutor_response`/`error` event path.
5. Mobile: `cd mobile && npm install && npm start` launches Expo Go without errors.
6. Git hygiene: `git status` clean after landing; `git log --stat` shows only
   intended files; confirm zero `.expo/` paths in history
   (`git log --all --name-only | grep -c '\.expo/'` → 0).

Format/lint/typecheck: tools absent from `.venv` (ruff/mypy/black) — install dev
extras first if desired (`pip install -r requirements-dev.txt`); not a gate for
this slice since no code is authored.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Committing `.expo/` artifacts | Add ignore line first; verify with `git status` before staging |
| CI goes red when workflows land (80% coverage gate; deprecated actions) | Known issue → backlog #6. Do not "fix" by weakening gates silently in this slice; note it in the PR/summary |
| First push to `main` publishes image to GHCR (deploy.yml) | Do not push without owner confirmation; flag in summary |
| Smoke script requires `DEEPSEEK_API_KEY` | Verify handshake/frame path without key if necessary and record which mode passed |
| Trivially "fixing" scaffold imports could mask deeper drift | Prefer explicit collection exclusion + pointer to backlog #8 over editing scaffold internals |

## Revert path

All commits are additive; `git revert <landing commits>` restores prior state.
No migrations, no data changes, no external side effects unless pushed (GHCR note above).

## Open decisions

None blocking implementation. Deferred to owner (do not decide unilaterally):
whether pushing to `origin/main` now is acceptable given deploy.yml's GHCR publish,
and whether CI coverage gate stays as-is until backlog #6.
