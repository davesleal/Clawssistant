# Clawssistant

## Project Vision

Clawssistant is a fully open-source, Claude AI-powered home assistant designed to
replace Google Home, Apple Home, and Alexa. It runs on open/commodity hardware,
prioritizes local processing for privacy, and uses Claude as the conversational brain
for natural language understanding, device control, code assistance, and general-purpose
conversation.

**License:** MIT — free to use, modify, distribute, and build upon commercially.

### Why Clawssistant Exists

- Google Home, Alexa, and Siri are closed, cloud-dependent, privacy-hostile, and
  increasingly ad-driven
- Home Assistant proved open-source smart home works at massive scale but its built-in
  voice pipeline lacks a capable AI brain
- Claude is uniquely suited — tool use, long context, nuanced reasoning, and Anthropic's
  Model Context Protocol (MCP) for extensible tool access
- No project has built the full-stack open alternative: open hardware + open voice
  pipeline + capable AI brain + smart home control + general conversation

### Core Principles

1. **Local-first, cloud-optional** — voice processing, device control, and basic
   intelligence run entirely on-device. Claude API is used for advanced reasoning
   when available, with graceful degradation when offline.
2. **Privacy by design** — no telemetry, no data collection, no cloud requirement.
   Users own their data. Audio is processed locally and never stored unless explicitly
   configured.
3. **Open everything** — MIT licensed code, open hardware designs, documented protocols,
   community-driven development.
4. **Home Assistant native** — first-class integration with Home Assistant as the device
   management backbone, but not hard-coupled to it.
5. **Conversation-first** — not just a command parser. Full multi-turn conversations
   with Claude on demand, including code help, brainstorming, and general assistance.
6. **Extensible by default** — MCP servers, plugin skills, custom connectors, and a
   public API make it easy to add any integration.

---

## Architecture

### System Layers

```
+------------------------------------------------------------------+
|                        Companion Apps                             |
|              (Mobile App / Web Dashboard / CLI)                   |
+------------------------------------------------------------------+
|                      REST + WebSocket API                         |
+------------------------------------------------------------------+
|                    Conversation Manager                           |
|        (Multi-turn context, user profiles, memory)                |
+------------------------------------------------------------------+
|                        Claude Brain                               |
|  (Anthropic API / MCP tools / local model fallback)               |
+------------------------------------------------------------------+
|                      Skill Framework                              |
|  (Weather, Timers, Media, Routines, Code, Custom skills)          |
+------------------------------------------------------------------+
|                    Integration Layer                               |
|  (Home Assistant API, MQTT, REST, CalDAV, IMAP, SIP/VoIP)        |
+------------------------------------------------------------------+
|                      Device Layer                                  |
|  (Matter/Thread, Zigbee, Z-Wave, WiFi, Bluetooth, IR)            |
+------------------------------------------------------------------+
|                     Voice Pipeline                                 |
|  (Wake Word -> STT -> NLU -> TTS -> Audio Output)                 |
+------------------------------------------------------------------+
|                       Hardware                                     |
|  (RPi 4/5, HA Yellow/Green, x86/ARM, ESP32 satellites)           |
+------------------------------------------------------------------+
```

### Voice Pipeline (All Open Source)

Clawssistant uses a two-tier voice architecture: thin satellite devices in each room
handle wake word detection and audio I/O, while the central hub runs the heavy
processing (STT, Claude brain, TTS).

| Stage | Technology | Where It Runs | Notes |
|-------|-----------|---------------|-------|
| Wake Word | microWakeWord / openWakeWord | Satellite (on-device) | Runs on ESP32-S3 / XMOS, no cloud needed |
| Audio Capture | XMOS XU316 (Voice PE) | Satellite | Echo cancellation, noise suppression, auto gain |
| Audio Transport | Wyoming Protocol | Network | Streams audio from satellite to hub |
| Speech-to-Text | faster-whisper / Whisper.cpp | Hub | Runs locally on RPi 5 / N100, or HA Cloud |
| Natural Language | Claude (API) / local fallback | Hub → Cloud | Anthropic conversation agent with tool use |
| Text-to-Speech | Piper TTS | Hub | High-quality local neural TTS |
| Audio Output | Wyoming Protocol → Speaker | Satellite | Response audio streamed back to room |
| Satellite Protocol | ESPHome + Wyoming | Network | HA Voice PE, ESP32-S3-BOX-3, or DIY |

**Home Assistant Integration:**
Clawssistant registers as a **conversation agent** in Home Assistant's Assist pipeline.
This means the Voice PE and any Wyoming satellite work out of the box — HA routes the
transcribed text to Claude (via the Anthropic conversation integration or our custom
agent), and Claude's response is sent back through TTS to the satellite.

**MCP Bridge:**
Home Assistant's built-in MCP Server integration exposes HA entities and services to
Claude. This means Claude can control devices, read sensor states, and trigger
automations through MCP tools — no custom integration code needed for basic device
control.

### Claude Brain

The AI core uses Claude via the Anthropic API with tool use (function calling) to
interact with the home and perform complex reasoning.

**Primary mode (cloud):**
- Anthropic API with tool use for device control, queries, and actions
- MCP servers for extensible tool access (file systems, databases, APIs, code execution)
- Conversation memory via local SQLite or vector store
- Per-user profiles with personalized context
- Streaming responses for low-latency voice interaction

**Fallback mode (local):**
- Smaller local models (e.g. via llama.cpp, Ollama) for basic command parsing
- Intent classification + slot filling for device commands when offline
- Cached responses for common queries
- Automatic switchover when API is unavailable

**Developer mode:**
- Full Claude Code-style interaction — read, write, and execute code
- Repository exploration and modification
- Shell command execution with user approval
- Project scaffolding and debugging assistance

### Device and Integration Layer

**Smart Home Protocols:**
- **Matter/Thread** — native support, the future standard
- **Zigbee** — via zigbee2mqtt or ZHA (Zigbee Home Automation)
- **Z-Wave** — via Z-Wave JS
- **WiFi** — direct integration with Shelly, Tuya (local), ESPHome, WLED
- **Bluetooth/BLE** — proximity detection, BLE devices
- **IR** — Broadlink and similar IR blasters for legacy devices

**Software Integrations:**
- **Home Assistant** — primary integration via REST API and WebSocket
- **MQTT** — universal message bus for IoT devices
- **CalDAV/CardDAV** — calendar and contacts (Nextcloud, Google, Apple)
- **IMAP/SMTP** — email reading and sending
- **SIP/VoIP** — phone calls and intercom
- **Media** — MPD, Spotify Connect, AirPlay, Chromecast, DLNA
- **REST/Webhook** — generic connector for any HTTP API
- **MCP Servers** — any MCP-compatible tool server

### Skill Framework

Skills are pluggable modules that give Clawssistant specific capabilities:

**Built-in Skills:**
- `core.lights` — light control (on/off, brightness, color, scenes)
- `core.climate` — thermostat, fan, humidity control
- `core.media` — play music, control TV, volume, playback
- `core.timers` — set timers, alarms, reminders
- `core.weather` — current conditions and forecasts
- `core.routines` — "Good morning" / "Good night" automation sequences
- `core.shopping_list` — add/remove/read shopping list items
- `core.calendar` — read events, create events, daily briefing
- `core.intercom` — room-to-room communication
- `core.security` — arm/disarm, camera snapshots, door lock control
- `core.energy` — energy monitoring and optimization suggestions
- `core.notifications` — push notifications to phones, TTS announcements

**Developer Skills:**
- `dev.code` — read, write, run code with Claude assistance
- `dev.shell` — execute shell commands with approval
- `dev.git` — git operations and repository management
- `dev.debug` — log analysis and troubleshooting

**Custom Skills:**
- Any Python module that implements the `ClawssistantSkill` interface
- Hot-reloadable — drop a file in `skills/` and it's live
- MCP server skills — wrap any MCP server as a skill
- Community skill repository for sharing

### Conversation Manager

- **Multi-turn context** — remembers conversation state across exchanges
- **Per-user profiles** — voice identification (speaker diarization), personal
  preferences, custom wake words
- **Household model** — shared context for the home (who's home, routines, preferences)
- **Long-term memory** — stores important facts and preferences in local database
- **Context injection** — automatically includes relevant state (time of day, who's
  home, recent events, device states) in Claude prompts
- **Conversation modes:**
  - **Command mode** — quick device control ("turn off the kitchen lights")
  - **Chat mode** — extended conversation ("let's talk about dinner plans")
  - **Developer mode** — code assistance and system administration
  - **Briefing mode** — proactive morning/evening summaries

---

## Hardware Targets

### Two-Tier Architecture

Clawssistant runs as a hub-and-satellite system:

- **Hub** — runs Home Assistant, Claude brain, STT, TTS. Needs real compute.
- **Satellites** — one per room. Handle wake word detection and audio I/O. Thin clients.

### Hub Options (pick one)

| Hardware | CPU | RAM | Local STT | Local LLM | Price | Best For |
|----------|-----|-----|-----------|-----------|-------|----------|
| Home Assistant Green | 1.8 GHz Cortex-A55 (RK3566) | 4 GB | Slow (~5-8s) | No | ~$100 | Cloud-first setups (HA Cloud or Anthropic API handles heavy work) |
| Raspberry Pi 5 | 2.4 GHz Cortex-A76 | 4-8 GB | Usable (~2-3s) | Marginal | ~$80 | Balanced: local STT + cloud Claude |
| Mini PC (x86) | Intel N100+ 3.4 GHz | 8-16 GB | Fast (~1s) | Yes (7B models) | ~$150 | Fully local processing, power users |
| Home Assistant Yellow | RPi CM4 | 2-8 GB | Slow-usable | No | ~$135 | Built-in Zigbee, HA-optimized |

**Recommendation:**
- If using Claude API (cloud) for the brain → **HA Green works fine.** STT can be
  offloaded to HA Cloud ($6.50/mo) or run locally with acceptable latency.
- If you want everything local → **RPi 5 (8GB) minimum**, N100 mini PC ideal.
- The hub choice depends on your privacy/latency/cost tradeoffs, not the satellites.

### Satellite Devices (one per room)

| Hardware | Price | Wake Word | Audio Quality | Setup | Notes |
|----------|-------|-----------|---------------|-------|-------|
| **HA Voice Preview Edition** | ~$59 | On-device (microWakeWord via XMOS) | Excellent (XMOS echo cancellation, noise suppression, dual-mic array) | Plug and play | **Recommended.** Hardware mute switch, rotary dial, LED ring, 3.5mm out, Grove port. ESPHome firmware, fully open source. |
| ESP32-S3-BOX-3 | ~$45 | On-device (microWakeWord) | Good (built-in mic + speaker, touch screen) | Plug and play | Great budget option with a screen |
| DIY ESP32-S3 + INMP441 + MAX98357 | ~$10 | On-device or server-side | Basic (no echo cancellation) | Soldering required | Cheapest, for tinkerers |
| Re-purposed tablets | ~$0 | App-based | Varies | App install | Wall-mounted dashboard + voice via companion app |

**Why the Voice PE is the default recommendation:**
- XMOS XU316 audio processor handles echo cancellation, noise suppression, and auto
  gain — critical for reliable voice in real rooms with ambient noise
- microWakeWord runs on-device (no network round-trip for wake word detection)
- Hardware mute switch physically cuts mic power (privacy by design)
- Rotary dial + multifunction button + LED ring for non-voice interaction
- 3.5mm stereo jack for external speakers (media playback)
- Grove port for sensor expansion
- Fully open-source firmware (ESPHome), easy to flash custom firmware
- $59 is competitive with DIY builds when you factor in time, 3D printing, and
  audio quality

### Audio Hardware (Hub-Direct, if not using satellites)

Only needed if running Clawssistant directly on the hub without satellites:

- **Microphones:** ReSpeaker 2-Mic/4-Mic Pi HAT, USB conference mics
- **Speakers:** Any 3.5mm/USB/Bluetooth speaker, HiFiBerry DAC for quality audio
- **Arrays:** ReSpeaker 6-Mic Circular Array for far-field voice capture

---

## Technology Stack

### Core Runtime
- **Language:** Python 3.12+ (primary), Rust (performance-critical components)
- **Async framework:** asyncio with uvloop
- **Process manager:** systemd service units
- **Configuration:** YAML (Home Assistant style)
- **Database:** SQLite (local state), optional PostgreSQL for multi-node

### AI / ML
- **Claude API:** Anthropic conversation integration (built into HA) + anthropic Python SDK
- **MCP:** Home Assistant MCP Server integration exposes entities/services to Claude;
  additional MCP servers for custom tools
- **Local STT:** faster-whisper (CTranslate2 backend) or HA Cloud Whisper
- **Local TTS:** Piper (ONNX runtime)
- **Wake word:** microWakeWord (on-device, used by Voice PE) + openWakeWord (server-side)
- **Local LLM fallback:** llama-cpp-python / Ollama (requires N100+ hardware)
- **Speaker ID:** pyannote.audio or speechbrain (optional)
- **Voice satellite firmware:** ESPHome with voice_assistant component

### Networking
- **API server:** FastAPI (REST + WebSocket)
- **MQTT:** aiomqtt client
- **mDNS/DNS-SD:** zeroconf for device discovery
- **Wyoming protocol:** for voice satellite communication

### Frontend
- **Web dashboard:** React or Svelte (lightweight, fast)
- **Mobile companion:** React Native or Flutter
- **CLI:** Rich (Python TUI library)

---

## Project Structure (Planned)

```
clawssistant/
  core/                    # Core runtime and orchestration
    brain.py               # Claude integration and prompt management
    conversation.py        # Multi-turn conversation manager
    memory.py              # Long-term memory and user profiles
    config.py              # Configuration management
    events.py              # Event bus
  voice/                   # Voice pipeline
    wake_word.py           # Wake word detection (openWakeWord)
    stt.py                 # Speech-to-text (faster-whisper)
    tts.py                 # Text-to-speech (Piper)
    audio.py               # Audio I/O management
    satellite.py           # Wyoming satellite protocol
  integrations/            # External service connectors
    homeassistant.py       # Home Assistant REST/WS client
    mqtt.py                # MQTT client
    calendar.py            # CalDAV integration
    media.py               # Media player integrations
  skills/                  # Pluggable skill modules
    __init__.py            # Skill base class and loader
    lights.py              # Light control skill
    climate.py             # Climate/thermostat skill
    timers.py              # Timers and alarms
    weather.py             # Weather queries
    routines.py            # Automation routines
    code.py                # Developer mode / code skill
  mcp/                     # MCP server definitions
    home_tools.py          # Home control MCP tools
    system_tools.py        # System management tools
  api/                     # REST + WebSocket API
    server.py              # FastAPI application
    routes/                # API route definitions
    ws.py                  # WebSocket handlers
  satellite/               # ESP32 satellite firmware
    esphome/               # ESPHome YAML configs
    custom/                # Custom ESP32 firmware (C++)
  web/                     # Web dashboard frontend
  tests/                   # Test suite
  docs/                    # Documentation
  hardware/                # Hardware designs and BOMs
    3d_prints/             # Enclosure STL files
    pcb/                   # Custom PCB designs (KiCad)
    bom/                   # Bills of materials
```

---

## MCP Integration Strategy

Clawssistant uses Anthropic's Model Context Protocol (MCP) as its primary
extensibility mechanism. Claude communicates with the home and external services
through MCP tool servers.

### Home Assistant's Built-in MCP Server

Home Assistant now includes an **MCP Server integration** that exposes HA entities and
services as MCP tools. This means Claude can control devices, read sensor states, and
trigger automations through the standard MCP protocol — no custom server needed for
basic device control.

**What HA's MCP Server provides out of the box:**
- All exposed entities (lights, switches, climate, locks, sensors, etc.)
- Service calls (turn_on, turn_off, set_temperature, etc.)
- Entity state queries
- Automation triggers

**Home Assistant also has an Anthropic Conversation integration** that registers Claude
as a conversation agent directly in HA's Assist pipeline. This means Voice PE satellites
can talk to Claude without any Clawssistant middleware — HA handles the routing.

### Clawssistant-Specific MCP Servers

On top of HA's built-in MCP, Clawssistant adds:

- **clawssistant-memory** — read/write user preferences and conversation memory
- **clawssistant-system** — system health, logs, configuration management
- **clawssistant-media** — enhanced media control (multi-room, queue management)
- **clawssistant-code** — file read/write/execute for developer mode
- **clawssistant-routines** — natural language routine creation and management

### Community MCP Servers (Examples)

- Spotify / music service control
- Calendar and task management
- Email reading and drafting
- Web search and information retrieval
- Weather data providers
- Shopping and grocery APIs
- Recipe databases
- Fitness and health trackers
- Security camera snapshots

### How It Works (End-to-End Voice Flow)

```
Voice PE Satellite          Home Assistant Hub            Cloud
─────────────────          ──────────────────           ─────
1. Wake word detected
   (microWakeWord on XMOS)

2. Audio streamed ─────────► 3. faster-whisper (STT)
   via Wyoming protocol        transcribes to text

                             4. HA Assist pipeline
                                routes to Claude
                                conversation agent

                             5. Context injected ─────► 6. Claude API
                                (time, user, devices,      receives prompt
                                 history, memory)          + MCP tools

                                                        7. Claude decides:
                                                           - tool calls
                                                           - or conversation

                             8. MCP tools execute ◄──── 9. Tool results
                                (HA entities/services)     returned

                            10. Claude response ◄────── 11. Final response
                                                            synthesized

                            12. Piper TTS converts
                                response to audio

13. Audio played ◄─────────  via Wyoming protocol
    on satellite speaker
```

**Key insight:** Home Assistant is already the orchestration layer for the voice
pipeline. Clawssistant doesn't need to reimplement STT/TTS routing — it plugs into
HA's Assist pipeline as a conversation agent and adds the Claude brain, memory,
multi-turn context, and enhanced skills on top.

---

## Security Architecture

### Threat Model

Clawssistant runs in a home network environment controlling physical devices. The security
model assumes:

- **The local network is semi-trusted** — other devices on the network may be compromised
- **The audio environment is untrusted** — TVs, visitors, recordings could produce audio
- **Community skills/MCP servers are untrusted code** — sandboxed by default
- **The Anthropic API is trusted** — but the network path to it may not be

### Trust Boundaries

```
Untrusted              | Boundary                  | Trusted
                       |                           |
Internet ------------> | Firewall + TLS            | API Server
Audio environment ---> | Wake Word + Speaker ID    | Voice Pipeline
Community skills ----> | Subprocess sandbox        | Core Runtime
MCP tool results ----> | Input validation          | Claude Brain
Companion apps ------> | Token auth + rate limit   | Conversation Manager
```

### Security Layers

**1. Network Security**
- API binds `127.0.0.1` by default — must explicitly opt into network exposure
- TLS support for all HTTP/WebSocket endpoints
- No UPnP — never auto-opens router ports
- mDNS for local discovery only
- Rate limiting on all API endpoints

**2. Authentication & Authorization**
- Token-based API authentication (enabled by default)
- Per-user voice profiles with optional speaker verification
- Sensitive action classification with tiered confirmation:
  - Low risk (lights, weather): voice command only
  - Medium risk (thermostat, locks): voice confirmation
  - High risk (unlock, disarm): PIN or companion app
  - Critical (shell exec, config changes): companion app only
- Home Assistant tokens via environment variables, never in config files

**3. Skill & Plugin Sandboxing**
- Community skills run in isolated subprocesses
- `skill.yaml` manifest declares required capabilities (filesystem, network, devices)
- Skills cannot access capabilities they haven't declared
- File integrity checking (checksums on load)
- Hot-reload directory has restricted write permissions
- No `eval()` / `exec()` / `shell=True` in skill code

**4. MCP Server Isolation**
- Each MCP server gets scoped capabilities (weather server can't unlock doors)
- All tool calls logged to audit trail with timestamps and parameters
- Tool call rate limiting per server
- MCP servers run as separate processes with minimal system access

**5. Voice Pipeline Security**
- Audio buffers processed in memory, never persisted by default
- Optional speaker verification via pyannote.audio/speechbrain
- Wake word sensitivity tuning to reduce false triggers
- Command confirmation for destructive actions
- No always-listening recording

**6. Data Security**
- Zero telemetry, zero phone-home
- SQLite memory database with optional encryption at rest
- Conversation history stored locally only
- API keys loaded from environment, never logged or exposed via API
- `.gitignore` excludes config.yaml, secrets.yaml, .env, database files

### Security Checklist for Development

All code contributions must:
- Validate all external input (API requests, voice transcriptions, MCP results)
- Use parameterized queries for database operations
- Validate file paths to prevent directory traversal
- Avoid `eval()`, `exec()`, `subprocess(shell=True)` without security review
- Never log secrets, tokens, or API keys
- Declare minimal capabilities in skill manifests

See [SECURITY.md](SECURITY.md) for vulnerability reporting and the full security policy.

---

## Key Features Roadmap

### Phase 1 — Foundation
- [ ] Core runtime with configuration system
- [ ] Claude brain with Anthropic API integration
- [ ] Basic voice pipeline (wake word + STT + TTS)
- [ ] Home Assistant integration (lights, switches, climate)
- [ ] Single-room operation on Raspberry Pi 5
- [ ] CLI interface for testing and development
- [ ] Basic web dashboard

### Phase 2 — Smart Home
- [ ] Full Home Assistant entity support
- [ ] Matter/Thread native support
- [ ] MQTT integration
- [ ] Skill framework with built-in skills (timers, weather, media, routines)
- [ ] Multi-room via ESP32 Wyoming satellites
- [ ] Conversation memory and user profiles
- [ ] Mobile companion app (basic)

### Phase 3 — Intelligence
- [ ] Proactive suggestions and automations
- [ ] Energy monitoring and optimization
- [ ] Natural language routine creation ("every morning at 7am, turn on the coffee maker")
- [ ] Calendar integration and daily briefings
- [ ] Shopping list with smart suggestions
- [ ] Speaker identification for per-user responses
- [ ] Local LLM fallback for offline operation

### Phase 4 — Advanced
- [ ] Developer mode (Claude Code-style code assistance)
- [ ] Phone call capability (SIP/VoIP)
- [ ] Security system integration (cameras, alarms, locks)
- [ ] Multi-node deployment (distributed across rooms)
- [ ] Custom hardware designs (3D printed enclosures, custom PCBs)
- [ ] Community skill marketplace
- [ ] Voice cloning for custom TTS voices (with consent)

---

## Development Guidelines

### Code Style
- Python: follow PEP 8, use type hints everywhere, format with `ruff`
- Use `async/await` for all I/O operations
- Docstrings on public APIs (Google style)
- Tests required for all new features (pytest + pytest-asyncio)

### Configuration
- All user-facing config in YAML files (like Home Assistant)
- Environment variables for secrets (API keys)
- Sensible defaults — should work out of the box with minimal config

### Testing
```bash
# Run full test suite
pytest tests/

# Run with coverage
pytest tests/ --cov=clawssistant --cov-report=term-missing

# Run specific test module
pytest tests/test_brain.py -v

# Lint and format
ruff check .
ruff format .
```

### Running Locally (Development)
```bash
# Clone the repo
git clone https://github.com/davesleal/Clawssistant.git
cd Clawssistant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Copy and edit config
cp config.example.yaml config.yaml
# Add your Anthropic API key to config.yaml

# Run the assistant
python -m clawssistant
```

### Contributing
- Fork the repo, create a feature branch, submit a PR
- All PRs require tests and must pass CI
- Discuss major changes in an issue first
- Follow the code style guidelines
- Sign-off commits (DCO) for license compliance

---

## Competitive Comparison

| Feature | Clawssistant | Google Home | Alexa | Apple Home | HA Voice |
|---------|-------------|-------------|-------|------------|----------|
| Open Source | MIT | No | No | No | Yes (HA) |
| AI Brain | Claude | Google AI | Alexa AI | Siri | Limited |
| Local Processing | Yes (primary) | No | No | Partial | Yes |
| Privacy | Full control | Low | Low | Medium | High |
| Custom Hardware | Yes | No | No | No | Yes |
| Full Conversations | Yes (Claude) | Limited | Limited | Limited | No |
| Code Assistance | Yes | No | No | No | No |
| MCP Extensibility | Yes | No | No | No | No |
| Vendor Lock-in | None | Google | Amazon | Apple | None |
| Cost | API key only | Subscription | Subscription | Hardware | Free |

---

## Naming

**Clawssistant** = Claws + Assistant. The "claws" evoke Claude's name while suggesting
the assistant grabs hold of your smart home with capable, precise control. The playful
name makes it approachable and memorable.

---

## Community and Governance

- **Repository:** GitHub (MIT license)
- **Discussions:** GitHub Discussions for feature requests and brainstorming
- **Chat:** Discord server for real-time community interaction
- **Releases:** Semantic versioning, stable releases quarterly
- **Governance:** Benevolent dictator model initially, transition to elected maintainer
  council as community grows
- **Hardware designs:** Open Source Hardware Association (OSHWA) certified where possible
