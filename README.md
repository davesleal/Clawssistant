# Clawssistant

**The open-source, Claude AI-powered home assistant.**

Replace Google Home, Alexa, and Siri with a private, local-first, genuinely intelligent assistant that runs on hardware you own.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

---

## What Is This?

Clawssistant is a fully open-source voice assistant that uses **Claude** as its AI brain. It integrates with **Home Assistant** for device control, runs an entirely local voice pipeline for privacy, and supports full multi-turn conversations — not just simple commands.

Think of it as: **Home Assistant's device ecosystem + Claude's intelligence + complete privacy**, all running on a Raspberry Pi or similar hardware.

### Key Capabilities

- **Smart home control** — lights, climate, locks, media, sensors, cameras via Home Assistant
- **Full conversations** — ask Claude anything, get thoughtful multi-turn responses by voice
- **Code assistance** — developer mode with Claude Code-style read/write/run capabilities
- **Local voice pipeline** — wake word, speech-to-text, and text-to-speech all run on-device
- **Multi-room** — ESP32 satellite devices in every room via Wyoming protocol
- **Extensible** — MCP servers, plugin skills, custom connectors, REST API
- **Privacy first** — no telemetry, no cloud requirement, your data stays local

## Why Not Just Use Google Home / Alexa / Siri?

| | Clawssistant | Google Home | Alexa | Apple Home |
|---|---|---|---|---|
| Open Source | MIT | No | No | No |
| AI Brain | Claude | Google AI | Alexa AI | Siri |
| Local Processing | Yes | No | No | Partial |
| Privacy | Full control | Low | Low | Medium |
| Full Conversations | Yes | Limited | Limited | Limited |
| Code Assistance | Yes | No | No | No |
| MCP Extensibility | Yes | No | No | No |
| Vendor Lock-in | None | Google | Amazon | Apple |
| Cost | HW + API key | Subscription | Subscription | Hardware |

---

## Architecture

```
Companion Apps (Mobile / Web / CLI)
         |
    REST + WebSocket API
         |
    Conversation Manager (multi-turn context, user profiles, memory)
         |
    Claude Brain (Anthropic API / MCP tools / local fallback)
         |
    Skill Framework (weather, timers, media, routines, code, custom)
         |
    Integration Layer (Home Assistant, MQTT, CalDAV, IMAP, SIP)
         |
    Device Layer (Matter, Zigbee, Z-Wave, WiFi, Bluetooth, IR)
         |
    Voice Pipeline (Wake Word -> STT -> NLU -> TTS)
         |
    Hardware (RPi 5, HA Yellow/Green, x86, ESP32 satellites)
```

### Voice Pipeline (All Local, All Open Source)

| Stage | Technology | Notes |
|-------|-----------|-------|
| Wake Word | [openWakeWord](https://github.com/dscripka/openWakeWord) | Custom wake word training supported |
| Speech-to-Text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Runs locally on RPi 5 or better |
| AI Brain | Claude via [Anthropic API](https://docs.anthropic.com/) | MCP tool use for device actions |
| Text-to-Speech | [Piper](https://github.com/rhasspy/piper) | High-quality local neural TTS |
| Satellite | [Wyoming Protocol](https://github.com/rhasspy/wyoming) | ESP32 room satellites |

### Claude Brain

- **Online:** Anthropic API with tool use + MCP for device control, queries, conversations
- **Offline fallback:** Local models via Ollama/llama.cpp for basic command parsing
- **Developer mode:** Claude Code-style interaction — read, write, and execute code by voice

---

## Hardware

### Hub (Pick One)

| Hardware | RAM | Best For |
|----------|-----|----------|
| **Raspberry Pi 5** | 4-8 GB | Recommended starting point |
| Home Assistant Yellow | 2-8 GB | Purpose-built, includes Zigbee |
| Home Assistant Green | 4 GB | Budget option |
| Mini PC (x86) | 8-16 GB | Best performance, local LLMs |

### Room Satellites

| Hardware | Cost | Notes |
|----------|------|-------|
| **ESP32-S3-BOX-3** | ~$40 | Built-in mic, speaker, screen |
| ESP32 + INMP441 + MAX98357 | ~$10 | Cheapest DIY option |
| Raspberry Pi Zero 2W | ~$15 | More capable, local wake word |

### Audio

- **Microphones:** ReSpeaker 2-Mic/4-Mic HAT, USB conference mics, INMP441 (I2S)
- **Speakers:** Any 3.5mm, USB, Bluetooth, or I2S speaker
- **Hi-Fi:** HiFiBerry DAC for quality audio output

---

## Quick Start

### Prerequisites

- Python 3.12+
- An [Anthropic API key](https://console.anthropic.com/)
- Optional: Home Assistant instance for device control

### Installation

```bash
# Clone the repo
git clone https://github.com/davesleal/Clawssistant.git
cd Clawssistant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Copy and configure
cp config.example.yaml config.yaml
# Edit config.yaml — add your Anthropic API key

# Run
python -m clawssistant
```

### Configuration

All configuration lives in `config.yaml`. Minimal setup:

```yaml
# config.yaml
assistant:
  name: Clawssistant
  wake_word: clawssistant

claude:
  api_key: ${ANTHROPIC_API_KEY}  # or set env var
  model: claude-sonnet-4-6

homeassistant:
  url: http://homeassistant.local:8123
  token: ${HA_TOKEN}
```

See [config.example.yaml](config.example.yaml) for all options.

---

## Project Structure

```
clawssistant/
  core/           # Runtime, Claude brain, conversation manager, memory
  voice/          # Wake word, STT, TTS, audio I/O, satellite protocol
  integrations/   # Home Assistant, MQTT, calendar, media connectors
  skills/         # Pluggable skill modules (lights, climate, timers, etc.)
  mcp/            # MCP server definitions for tool access
  api/            # FastAPI REST + WebSocket server
satellite/        # ESP32 satellite firmware (ESPHome + custom)
web/              # Web dashboard frontend
tests/            # Test suite
hardware/         # Open hardware designs (3D prints, PCBs, BOMs)
docs/             # Documentation
```

---

## Skills

Skills are pluggable Python modules. Built-in skills include:

| Skill | Description |
|-------|-------------|
| `core.lights` | On/off, brightness, color, scenes |
| `core.climate` | Thermostat, fan, humidity |
| `core.media` | Music, TV, volume, playback |
| `core.timers` | Timers, alarms, reminders |
| `core.weather` | Current conditions and forecasts |
| `core.routines` | "Good morning" / "Good night" sequences |
| `core.shopping_list` | Shopping list management |
| `core.calendar` | Events, daily briefing |
| `core.security` | Arm/disarm, cameras, locks |
| `core.notifications` | Push notifications, TTS announcements |
| `dev.code` | Read/write/run code with Claude |
| `dev.shell` | Shell commands with approval |

**Custom skills:** drop a Python file in `skills/` that implements `ClawssistantSkill` and it's live. Hot-reloadable, no restart needed.

---

## MCP Integration

Clawssistant uses Anthropic's [Model Context Protocol](https://modelcontextprotocol.io/) as its extensibility backbone. Claude communicates with devices and services through MCP tool servers.

**Built-in MCP servers:**
- `clawssistant-home` — device control (lights, switches, climate, locks)
- `clawssistant-media` — media playback across rooms
- `clawssistant-system` — system health and configuration
- `clawssistant-memory` — user preferences and conversation memory
- `clawssistant-code` — file operations for developer mode

Any MCP-compatible server can be added as a skill.

---

## Roadmap

- **Phase 1 — Foundation:** Core runtime, Claude brain, basic voice pipeline, Home Assistant integration, CLI
- **Phase 2 — Smart Home:** Full HA entity support, Matter/Thread, MQTT, skill framework, multi-room satellites
- **Phase 3 — Intelligence:** Proactive suggestions, natural language routines, speaker ID, offline fallback
- **Phase 4 — Advanced:** Developer mode, VoIP calls, security integration, custom hardware, community marketplace

See [CLAUDE.md](CLAUDE.md) for the full architecture document and detailed roadmap.

---

## Development

```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=clawssistant --cov-report=term-missing

# Lint and format
ruff check .
ruff format .
```

### Tech Stack

- **Python 3.12+** with asyncio/uvloop
- **FastAPI** for REST + WebSocket API
- **Anthropic SDK** for Claude integration
- **MCP SDK** for tool servers
- **faster-whisper** for local STT
- **Piper** for local TTS
- **openWakeWord** for wake word detection
- **SQLite** for local state and memory

---

## Security

Clawssistant controls physical devices in your home. Security is not optional.

- **Auth enabled by default** — API requires token authentication out of the box
- **Localhost-only by default** — API binds `127.0.0.1`, not `0.0.0.0`
- **Tiered action confirmation** — sensitive actions (unlock, disarm) require PIN or companion app approval
- **Skill sandboxing** — community plugins run in isolated subprocesses with declared capabilities
- **MCP capability scoping** — tool servers only get access to the entities they need
- **Audit logging** — all tool calls and device actions are logged
- **Zero telemetry** — no data collection, no phone-home, ever

See [SECURITY.md](SECURITY.md) for the full security model, threat boundaries, and vulnerability reporting.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. Quick version:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes with tests
4. Run `ruff check . && ruff format . && pytest tests/`
5. Submit a PR

All PRs require tests and must pass CI. Security-sensitive changes get additional review. Discuss major changes in an issue first.

---

## Name

**Clawssistant** = Claws + Assistant. The "claws" evoke Claude's name while suggesting the assistant grabs hold of your smart home with capable, precise control.

## License

[MIT](LICENSE) — free to use, modify, distribute, and build upon commercially.

## Links

- [Architecture & Vision (CLAUDE.md)](CLAUDE.md)
- [Security Policy (SECURITY.md)](SECURITY.md)
- [Contributing Guide (CONTRIBUTING.md)](CONTRIBUTING.md)
- [Anthropic API Docs](https://docs.anthropic.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Home Assistant](https://www.home-assistant.io/)
