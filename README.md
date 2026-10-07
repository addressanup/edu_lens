# EduLens

**An AI learning companion for everyone.**

EduLens helps people understand what they are working on through camera-aware guidance, questions, and spoken explanations. Point a camera at learning material, ask a question, and work through the next step with an AI tutor.

The product vision covers independent study, everyday curiosity, and developing new skills. Guidance should adapt to a person's knowledge, goals, and preferred pace, without assuming a particular age or educational stage.

## What is in this repository

EduLens is an alpha-stage project. The current implementation includes:

- **Live camera tutoring:** a mobile client streams frames over WebSocket; the backend uses visual context to answer questions and offer hints.
- **Audio-first guidance:** the mobile client can read tutoring responses aloud.
- **Text and image questions:** a FastAPI backend exposes tutoring endpoints and a browser demo.
- **Learning components:** modules for OCR, handwriting recognition, subject reasoning, personalization, and progress tracking.
- **Configurable AI providers:** integrations for DeepSeek, OpenAI, Anthropic, Google, Azure OpenAI, and Ollama. Capabilities depend on the selected provider and model.

The general-audience positioning is the product direction. Some existing interfaces, prompts, and data models still reflect earlier audience assumptions; their migration is separate from this documentation update. This repository does not yet establish complete support for every subject or learning level.

## How it works

1. Start a learning session in the mobile app or browser demo.
2. Share a question or camera view of the material you are exploring.
3. The backend sends the relevant question and visual context to the configured AI service.
4. EduLens returns guidance; the mobile client can speak the response.

Live camera frames are held in backend memory for the session and cleared when it ends. Frames sent to an external AI provider are also subject to that provider's data handling. Smart glasses are a longer-term direction; the current mobile client uses a phone camera.

## Local setup

Use Python 3.11 or later. The mobile client also requires Node.js, npm, and an Expo-compatible device or emulator.

```bash
git clone https://github.com/addressanup/edu_lens.git
cd edu_lens
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` to select `LLM_PROVIDER` and set that provider's API key. The example defaults to DeepSeek. Camera tutoring requires a vision-capable model supported by your provider; check the configuration before starting a live session. Optional audio and security dependencies are listed in `requirements_audio.txt` and `requirements_security.txt`.

Start the backend:

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

- Browser demo: <http://127.0.0.1:8000/demo>
- API documentation: <http://127.0.0.1:8000/docs>
- Health endpoint: <http://127.0.0.1:8000/health>

To run the mobile client:

```bash
cd mobile
npm install
npm start
```

For a phone on a trusted local Wi-Fi network, start the backend with `--host 0.0.0.0` and set the app's server address to `http://<your-computer-LAN-IP>:8000`. Authentication is not yet implemented across the API, so this setup is for local development, not a public deployment.

## Repository map

| Path | Purpose |
| --- | --- |
| `src/api/` | REST API, WebSocket connections, and live tutoring sessions |
| `src/ai/` | AI providers, tutoring, reasoning, personalization, and safety |
| `src/vision/` | OCR, handwriting, and visual processing |
| `src/audio/` | Speech recognition, speech synthesis, and audio processing |
| `src/observation/` | Scene analysis and intervention logic |
| `mobile/` | Expo mobile camera-tutoring client |
| `app/` | Earlier companion application |
| `web/` | Browser demo |
| `configs/` | Subsystem configuration |
| `tests/` | Automated tests |
| `docs/` | Technical documentation and engineering history |

The root `agents/`, `orchestrator/`, `core/`, `templates/`, and `cli.py` belong to the development orchestration scaffold retained in the repository. The EduLens application code lives under `src/`; the scaffold is not the product.

## Development checks

Install development dependencies, then run the local gate:

```bash
pip install -r requirements-dev.txt
make test-gate
```

The gate covers unit, API, AI, safety, and audio suites. Additional integration and performance suites live under `tests/`. GitHub Actions workflows are currently absent; run checks locally before shipping changes. This README does not claim a fresh passing test run.

## Product direction

See [the product overview](concept_note.md) for the intended audience, experience, and development priorities. Historical specifications and engineering reports describe earlier milestones and may not reflect the current product direction.
