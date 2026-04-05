# ObsidianLLM

A local knowledge base that clips web articles, processes them with an LLM, and organizes the results as a browsable wiki — all running on your machine.

![ClipView](https://github.com/BeamusWayne/ObsidianLLM/raw/main/docs/clip.png)

## What it does

1. **Clip** — paste a URL, the server fetches and strips it to clean Markdown
2. **Ingest** — an LLM reads the article and writes structured wiki pages to `wiki/`
3. **Browse** — explore the wiki and the entity graph in the browser

## Features

- Multi-backend LLM chain — Ollama (local), Claude API, or any OpenAI-compatible endpoint
- Fallback chain with named presets: `["preset:qwen-plus", "preset:glm-5", "ollama"]`
- Parallel ingest workers with per-file size routing
- Manual ingest: single-file hover button, batch select, or "process all pending"
- Auto-ingest toggle per session
- Image vision: articles with embedded images get described by a vision model
- Wiki graph view — entities and relationships rendered as a force-directed graph
- Dark / light / system theme

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python · FastAPI · Uvicorn |
| Scraping | Trafilatura |
| Frontend | Vue 3 · Vite |
| LLM | Ollama / Anthropic Claude / OpenAI-compatible |

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+
- At least one LLM backend:
  - [Ollama](https://ollama.com) running locally (`ollama serve`), **or**
  - A Claude API key, **or**
  - Any OpenAI-compatible endpoint (DashScope, OpenRouter, etc.)

### Install

```bash
git clone https://github.com/BeamusWayne/ObsidianLLM.git
cd ObsidianLLM

# Python deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Config
cp settings.json.example settings.json
# Edit settings.json — set your backend and API keys
```

### Run

```bash
bash start.sh
# Open http://localhost:8000
```

`start.sh` builds the frontend, then starts the server. Subsequent runs skip the npm install if nothing changed.

## Configuration

Copy `settings.json.example` to `settings.json` and edit:

```json
{
  "mode": "ollama",
  "fallback_chain": ["ollama"],
  "ollama": {
    "base_url": "http://localhost:11434",
    "text_model": "qwen3.5:9b",
    "vision_model": "qwen3-vl:8b"
  },
  "claude": {
    "api_key": "sk-ant-...",
    "text_model": "claude-sonnet-4-6"
  },
  "custom": {
    "base_url": "https://api.example.com/v1",
    "api_key": "sk-...",
    "text_model": "your-model"
  },
  "custom_presets": [
    {
      "name": "qwen-plus",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key": "sk-...",
      "text_model": "qwen-plus"
    }
  ],
  "parallel": {
    "enabled": true,
    "workers": 3,
    "size_threshold_chars": 3000,
    "small_backend": "ollama",
    "large_backend": "custom"
  }
}
```

### Fallback chain

The system tries backends in order. If one returns a billing/quota error it automatically moves to the next. You can reference named presets directly in the chain:

```json
"fallback_chain": ["preset:qwen-plus", "preset:glm-5", "ollama"]
```

Presets are defined in `custom_presets` and each acts as an independent OpenAI-compatible endpoint.

## Project layout

```
ObsidianLLM/
├── server.py           # FastAPI app + routes
├── start.sh            # Build frontend + start server
├── scripts/
│   ├── clip.py         # URL fetch + Markdown extraction
│   ├── ingest.py       # LLM processing + wiki writer
│   ├── llm.py          # Multi-backend LLM wrapper
│   └── query.py        # Wiki query
├── frontend/
│   └── src/
│       └── views/
│           ├── ClipperView.vue   # Clip & Ingest panel
│           ├── WikiView.vue      # Wiki browser
│           ├── GraphView.vue     # Entity graph
│           └── SettingsView.vue  # Backend config
├── raw/                # Clipped articles + images (gitignored)
├── wiki/               # Generated wiki pages (gitignored)
└── settings.json       # Your config (gitignored)
```

## License

MIT
