# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EVA (Enhanced Voice Assistant) is a multimodal, multilingual voice assistant built on the LangGraph state-machine framework. It supports desktop (WSL/Linux) and mobile (React web app) clients with voice, vision, and tool-use capabilities. Python 3.10+ backend, Next.js frontend.

## Commands

### Run EVA (backend)
```bash
python app/main.py
```
Entry point calls `EVA()` which builds a LangGraph, compiles it, and runs the conversation loop indefinitely.

### React frontend (react-eva/)
```bash
cd react-eva && npm install && npm run dev
```
Runs on http://localhost:3000. Requires EVA backend running on port 8080 in mobile mode.

### Setup / Install
```bash
pip install -r requirements.txt
pip install git+https://github.com/wenet-e2e/wespeaker.git
python setup.py  # Creates data directories, SQLite DB tables, validates module imports
```

### Tests
No automated test suite exists. `tests/` contains exploratory Jupyter notebooks only.

## Architecture

### Core Loop (`app/core/eva.py`)

EVA is a LangGraph `StateGraph` with these nodes flowing in a cycle:

```
initialize → [setup (first-run only)] → converse → action → sense → converse → ...
```

- **converse**: Builds prompt via `PromptConstructor`, calls `agent.respond()`, sends speech to client, routes to action or sense
- **action**: Executes tool calls in parallel via `ThreadPoolExecutor`, routes back to converse with results
- **sense**: Gets next user input (speech + vision) from client, detects "bye"/"exit" for termination
- **setup**: Two-step first-run flow collecting user name, photo ID, voice ID, and "core life desire"

State is tracked in `EvaState` TypedDict with status enum: `THINKING | WAITING | ACTION | END | ERROR | SETUP`.

### Client Layer (`app/client/`)

Two client implementations sharing the same interface (`initialize_modules`, `send`, `receive`, `start`, `send_over`, `deactivate`):

- **WSLClient**: Direct hardware access — local microphone, webcam (OpenCV/V4L2), speakers. Desktop only.
- **MobileClient**: Runs a FastAPI/uvicorn server on port 8080 with WebSocket (`/ws/{client_id}`) and file download endpoints. Communicates with the React frontend.

`DataManager` queues and processes incoming WebSocket messages by type (audio → STT transcription, frontImage/backImage → vision description, over → end-of-turn).

### LLM Agent (`app/utils/agent/`)

- **ChatAgent** (`chatagent.py`): Primary reasoning engine. Supports 9+ model providers (Claude, ChatGPT, Groq, Gemini, Mistral, Ollama, Grok, DeepSeek, Qwen). Output is structured JSON via `JsonOutputParser` → `AgentOutput` (analysis, strategy, response, premeditation, action list).
- **SmallAgent** (`smallagent.py`): Lightweight model for memory summarization. Pickle-safe with lazy LLM init.
- **PromptConstructor** (`constructor.py`): Assembles prompts with XML-tagged sections: `<PERSONA>`, `<TOOLS>`, `<CONVERSATION_HISTORY>`, `<CONTEXT>`, `<INSTRUCTIONS>`.

### Prompt Design

All prompts use **first-person perspective** ("I am EVA", "I see", "I hear") — this is an intentional design choice for self-awareness. Prompt templates are Markdown files in `app/utils/prompt/` loaded via `load_prompt(name)` and updated via `update_prompt(name, text)`.

### Tools (`app/tools/`)

Tools extend LangChain `BaseTool`. Each tool file is auto-discovered and instantiated by `ToolManager`. Tools are filtered by `client` attribute ("desktop", "mobile", "all", "none" to disable). Two-phase execution: `_run()` returns data dict for the LLM, optional `run_client()` triggers client-side UI actions (play music, show video, display images).

To add a new tool: create a `.py` file in `app/tools/` following the LangChain `BaseTool` template. To disable: set `client = "none"`.

### Subsystems in `app/utils/`

| Module | Purpose | Key pattern |
|--------|---------|-------------|
| `stt/` | Speech-to-text (faster-whisper, Whisper, Groq) | `Transcriber` dispatches to model; runs voice ID in parallel thread |
| `tts/` | Text-to-speech (ElevenLabs, OpenAI, Coqui) | `Speaker` factory; `speak()` for realtime, `get_audio()` for file output |
| `vision/` | Webcam + face recognition + image description | `Watcher.glance()` detects scene changes (>40% pixel diff); `Describer` runs face ID + vision model in parallel |
| `memory/` | Session history + SQLite logging | Async writes via threads; auto-summarizes after 10 entries using `SmallAgent` |
| `extension/` | Discord/Midjourney image gen, browser window launcher | `MidjourneyServer` polls Discord API; `Window` writes temp HTML + opens in Chromium |

### Identity System (`app/core/ids.py`)

Singleton `IDManager` reads the `ids` SQLite table mapping voice ID filenames (`void`) and photo ID filenames (`pid`) to user names. Used by both `VoiceIdentifier` (wespeaker cosine similarity, threshold 0.7) and face `Identifier` (face_recognition library).

## Configuration

- **`app/config/config.py`**: Central `eva_configuration` dict — set device mode, language, model choices for chat/vision/STT/TTS/summarization
- **`.env`**: API keys (OpenAI, Anthropic, Google, Groq, ElevenLabs, Tavily, Discord/Midjourney)
- **`app/data/`**: Runtime data — `database/eva.db` (SQLite), `pids/` (face photos), `voids/` (voice samples), `media/audio/` (generated TTS files)

## Key Conventions

- Module initialization uses `functools.partial` for deferred construction with a `tqdm` progress bar (`app/core/functions.py`)
- Memory writes are always asynchronous (threaded) to avoid blocking the conversation loop
- The React frontend uses push-to-talk (spacebar) and sends audio as base64 MP3 via WebSocket
- Session IDs rotate each turn for cache revalidation on audio downloads
- `.bak` extension on tool files means disabled (e.g., `epad.bak`, `gmail_reader.bak`)
