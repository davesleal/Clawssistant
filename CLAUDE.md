# Clawssistant

## Project Vision

Clawssistant is a fully open-source, AI-native home operating system powered by Claude.
It replaces Google Home, Apple Home, and Alexa — not by being a better voice assistant,
but by being the intelligent platform that runs your home. Claude is the kernel: it
thinks, remembers, learns, connects, and acts. Voice is one interface. The home is its
domain. But it's not limited to smart home commands — it has memory, storage, internet
access, connectors to any service, and the ability to grow with the user.

It runs on open/commodity hardware, prioritizes local processing for privacy, and
scales from a plug-and-play starter setup to a fully autonomous, offline-capable
home intelligence system.

**License:** MIT — free to use, modify, distribute, and build upon commercially.

### Why Clawssistant Exists

- Google Home, Alexa, and Siri are closed, cloud-dependent, privacy-hostile, and
  increasingly ad-driven
- Home Assistant proved open-source smart home works at massive scale but its built-in
  voice pipeline lacks a capable AI brain — and building on top of it creates a
  dependency that limits future growth
- Claude is uniquely suited — tool use, long context, nuanced reasoning, and Anthropic's
  Model Context Protocol (MCP) for extensible tool access
- No project has built the full-stack open alternative: an AI-native home OS with open
  hardware + open voice pipeline + capable AI brain + smart home control + persistent
  memory + general conversation + internet access + extensible connectors

### Core Principles

1. **Local-first, cloud-optional** — voice processing, device control, and basic
   intelligence run entirely on-device. Claude API is used for advanced reasoning
   when available, with graceful degradation when offline.
2. **Privacy by design** — no telemetry, no data collection, no cloud requirement.
   Users own their data. Audio is processed locally and never stored unless explicitly
   configured.
3. **Open everything** — MIT licensed code, open hardware designs, documented protocols,
   community-driven development.
4. **Platform-independent** — Clawssistant owns the stack. Home Assistant is a
   first-class connector (the best one for day one), but it's one adapter among many.
   You can run Clawssistant with HA, without HA (direct MQTT, Zigbee2MQTT, Matter),
   or alongside HA. No single dependency gates the project's future.
5. **Conversation-first** — not just a command parser. Full multi-turn conversations
   with Claude on demand, including code help, brainstorming, and general assistance.
6. **Extensible by default** — MCP servers, plugin skills, custom connectors, and a
   public API make it easy to add any integration.
7. **Grows with the user** — start with the Balanced tier and HA as your connector.
   As needs grow, add direct protocol adapters, more memory, offline capabilities,
   and custom skills. The architecture scales from one room to a whole home without
   re-platforming.

---

## Architecture

### ClawsOS — The AI-Native Home Operating System

Clawssistant is structured as an operating system where the AI brain is the kernel,
not an app running on someone else's platform. Every traditional OS concept has an
AI-native equivalent:

| Traditional OS | ClawsOS Equivalent | What It Does |
|----------------|-------------------|--------------|
| Kernel | Claude Brain | Orchestrates everything — reasoning, decisions, tool use |
| Memory management | Memory System | Working memory (conversation), episodic (events), semantic (facts), procedural (learned routines) |
| Filesystem | Local Storage | SQLite, vector DB, config files, knowledge base |
| Device drivers | Connectors/Adapters | HA adapter, MQTT adapter, Zigbee2MQTT adapter, Matter adapter, REST adapter |
| Networking stack | Network Layer | Internet access, LAN discovery, MQTT bus, WebSocket, MCP |
| User space / Apps | Skills | Pluggable capabilities — like apps, but AI-native |
| Shell / GUI | I/O Interfaces | Voice (primary), web dashboard, mobile app, CLI, API |
| Process scheduler | Event Loop | asyncio + task scheduling + connector polling |
| Permissions | Security Layer | Tiered action risk, sandboxed skills, scoped connectors |

### System Layers

```
+------------------------------------------------------------------+
|                      I/O Interfaces                               |
|     Voice Pipeline / Web Dashboard / Mobile App / CLI / API       |
+------------------------------------------------------------------+
|                      REST + WebSocket API                         |
+------------------------------------------------------------------+
|                    Conversation Manager                           |
|        (Multi-turn context, user profiles, modes)                 |
+------------------------------------------------------------------+
|                     Claude Brain (Kernel)                         |
|  (Anthropic API / MCP tools / local model fallback)               |
+------------------------------------------------------------------+
|                      Memory System                                |
|  Working (context) / Episodic (events) / Semantic (facts) /       |
|  Procedural (routines) — SQLite + Vector DB                       |
+------------------------------------------------------------------+
|                      Skill Framework                              |
|  (Weather, Timers, Media, Routines, Code, Custom skills)          |
+------------------------------------------------------------------+
|                    Connector Layer                                 |
|  Home Assistant / MQTT / Zigbee2MQTT / Matter / REST / CalDAV /   |
|  IMAP / SIP / Media services / Internet / Any MCP server          |
+------------------------------------------------------------------+
|                      Device Layer                                  |
|  (Matter/Thread, Zigbee, Z-Wave, WiFi, Bluetooth, IR)            |
+------------------------------------------------------------------+
|                       Hardware                                     |
|  (RPi 5 + AI HAT+, N100, x86/ARM, ESP32 satellites)              |
+------------------------------------------------------------------+
```

**Key architectural decision:** Home Assistant is a connector, not the foundation.
On day one, HA is the easiest and most capable connector — it already speaks to
hundreds of device types. But Clawssistant can also connect directly via MQTT,
Zigbee2MQTT, Matter, or raw REST APIs. If HA changes direction, Clawssistant
continues without it.

### Voice Pipeline (All Open Source)

Clawssistant owns its voice pipeline. Two-tier architecture: thin satellite devices
in each room handle wake word detection and audio I/O, while the central hub runs
the heavy processing (STT, Claude brain, TTS).

| Stage | Technology | Where It Runs | Notes |
|-------|-----------|---------------|-------|
| Wake Word | microWakeWord / openWakeWord | Satellite (on-device) | Runs on ESP32-S3 / XMOS, no cloud needed |
| Audio Capture | XMOS XU316 (Voice PE) | Satellite | Echo cancellation, noise suppression, auto gain |
| Audio Transport | Wyoming Protocol | Network | Streams audio from satellite to hub |
| Speech-to-Text | faster-whisper / Whisper.cpp | Hub | CPU: 2-3s (RPi 5) / <1s (N100). With AI HAT+: sub-second on any RPi 5 |
| Natural Language | Claude (API) / local fallback | Hub → Cloud | Claude brain with tool use via MCP |
| Text-to-Speech | Piper TTS | Hub | High-quality local neural TTS |
| Audio Output | Wyoming Protocol → Speaker | Satellite | Response audio streamed back to room |
| Satellite Protocol | ESPHome + Wyoming | Network | Voice PE, ESP32-S3-BOX-3, or DIY |

**HA Compatibility (optional, not required):**
Clawssistant can also register as a conversation agent in Home Assistant's Assist
pipeline for users who want both systems. But the voice pipeline runs independently
of HA — Clawssistant manages Wyoming satellites, STT, TTS, and Claude routing
directly.

**MCP Bridge:**
Home Assistant's built-in MCP Server integration can expose HA entities to Claude
as one connector. Clawssistant also connects to devices directly via its own
MQTT, Zigbee2MQTT, and Matter connectors — no HA required for device control.

### Claude Brain

The AI core uses Claude via the Anthropic API with tool use (function calling) to
interact with the home and perform complex reasoning.

**Primary mode (cloud):**
- Anthropic API with tool use for device control, queries, and actions
- MCP servers for extensible tool access (file systems, databases, APIs, code execution)
- Conversation memory via local SQLite or vector store
- Per-user profiles with personalized context
- Streaming responses for low-latency voice interaction

**Fallback mode (local/offline):**
- **With AI HAT+ 2 (RPi 5):** Small LLMs (1-1.5B params: Qwen 2.5, Llama 3.2) run
  on the Hailo-10H NPU for intent classification and device command parsing. Handles
  "turn on the lights" and "what's the temperature?" reliably offline. Not suitable
  for general conversation — use Claude API for that.
- **With N100 Mini PC:** Larger models (7B) via llama.cpp / Ollama for better offline
  conversation quality and more complex reasoning.
- Intent classification + slot filling for device commands when offline
- Cached responses for common queries
- Automatic switchover when Claude API is unavailable

**Developer mode:**
- Full Claude Code-style interaction — read, write, and execute code
- Repository exploration and modification
- Shell command execution with user approval
- Project scaffolding and debugging assistance

### Memory System

The memory system is what makes Clawssistant an OS rather than a stateless voice
assistant. It persists knowledge across conversations, learns user patterns, and
builds a model of the home over time.

**Memory types:**

| Type | What It Stores | Storage | Example |
|------|---------------|---------|---------|
| **Working** | Current conversation context, active tasks, recent device states | In-memory (RAM) | "User asked to dim the lights 30 seconds ago" |
| **Episodic** | Timestamped events — what happened and when | SQLite | "Kitchen motion sensor triggered at 2:13 AM on Tuesday" |
| **Semantic** | Facts about the home, users, preferences, relationships | SQLite + Vector DB | "Dave prefers 68°F at night", "The guest bedroom is upstairs" |
| **Procedural** | Learned routines, patterns, and automations | SQLite | "Every weekday at 7am, Dave's alarm goes off, then coffee maker starts" |

**How memory works in practice:**
- Claude receives relevant memory as context with every prompt (time of day, who's
  home, recent events, user preferences, learned patterns)
- New facts are extracted from conversations and stored automatically
  ("Remember I like it warmer on weekends" → semantic memory)
- Event patterns are detected over time and surfaced as routine suggestions
  ("You turn on the porch light every evening at sunset — want me to automate that?")
- Memory is local-only, encrypted at rest, and never sent to any cloud service
  except as part of the Claude API prompt (which the user controls)
- Per-user memory isolation — each household member has their own preferences
- Shared household memory for common facts (room names, device locations, routines)

**Storage backends:**
- **SQLite** — default, zero-config, works everywhere
- **Vector DB (ChromaDB)** — optional, enables semantic search over memories
  ("What did we talk about regarding the garden?")
- **PostgreSQL** — optional, for multi-node deployments where multiple hubs share
  memory

### Connector Layer

Connectors are how ClawsOS talks to the outside world. Each connector is an adapter
that translates between Clawssistant's internal model and an external system. Home
Assistant is a connector. MQTT is a connector. The internet is a connector.

**Device Protocol Connectors:**
- **Matter/Thread** — native support, the future standard
- **Zigbee** — via Zigbee2MQTT (direct, no HA needed) or ZHA
- **Z-Wave** — via Z-Wave JS
- **WiFi** — direct integration with Shelly, Tuya (local), ESPHome, WLED
- **Bluetooth/BLE** — proximity detection, BLE devices
- **IR** — Broadlink and similar IR blasters for legacy devices

**Platform Connectors:**
- **Home Assistant** — the richest day-one connector. REST API + WebSocket + MCP
  Server. Speaks to 2000+ device types. Recommended starting point, not required.
- **MQTT** — universal message bus. Works standalone via Zigbee2MQTT, Tasmota,
  ESPHome, or any MQTT-speaking device — no HA needed.
- **Internet** — HTTP client for web APIs, search, information retrieval. Claude
  can look things up, check services, pull weather data directly.
- **CalDAV/CardDAV** — calendar and contacts (Nextcloud, Google, Apple)
- **IMAP/SMTP** — email reading and sending
- **SIP/VoIP** — phone calls and intercom
- **Media** — MPD, Spotify Connect, AirPlay, Chromecast, DLNA
- **REST/Webhook** — generic connector for any HTTP API
- **MCP Servers** — any MCP-compatible tool server becomes a connector
- **Filesystem** — local file read/write for developer mode, configs, exports

**Connector interface:** every connector implements `discover()`, `read_state()`,
`execute()`, `subscribe()`. Claude doesn't need to know whether a light is
controlled via HA, MQTT, or Matter — it says "turn on the kitchen light" and the
right connector handles it. New connectors are Python modules dropped into
`connectors/`.

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

The conversation manager is the interface between users and the Claude kernel. It
pulls from the memory system to give Claude rich context on every interaction.

- **Multi-turn context** — remembers conversation state across exchanges (working
  memory)
- **Per-user profiles** — voice identification (speaker diarization), personal
  preferences, custom wake words (semantic memory)
- **Household model** — shared context for the home (who's home, routines,
  preferences) — built over time from episodic + semantic memory
- **Context injection** — automatically includes relevant state (time of day, who's
  home, recent events, device states, user preferences, learned patterns) in every
  Claude prompt
- **Proactive intelligence** — the system notices patterns in episodic memory and
  suggests automations ("You've turned on the porch light at sunset three days in a
  row — want me to make that automatic?")
- **Conversation modes:**
  - **Command mode** — quick device control ("turn off the kitchen lights")
  - **Chat mode** — extended conversation ("let's talk about dinner plans")
  - **Developer mode** — code assistance and system administration
  - **Briefing mode** — proactive morning/evening summaries

---

## Hardware Targets

### Two-Tier Architecture

Clawssistant runs as a hub-and-satellite system:

- **Hub** — runs ClawsOS (Claude brain, memory, connectors, STT, TTS). Needs real
  compute. Optionally also runs Home Assistant as a connector.
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

### AI Accelerator (Optional — for RPi 5 hubs)

The Raspberry Pi AI HAT+ family adds a dedicated neural processing unit (NPU) to the
Pi 5. This dramatically accelerates Whisper speech-to-text and enables offline intent
parsing — the two biggest barriers to a responsive, local-first voice assistant.

| Accelerator | NPU Chip | TOPS | Dedicated RAM | Price | Key Benefit |
|-------------|----------|------|---------------|-------|-------------|
| AI HAT+ | Hailo-8L | 13 (INT8) | — | ~$70 | Sub-second Whisper STT (hybrid: encoder on NPU, decoder on CPU) |
| AI HAT+ | Hailo-8 | 26 (INT8) | — | ~$110 | Faster STT + multi-model pipelines |
| **AI HAT+ 2** | **Hailo-10H** | **40 (INT4)** | **8 GB LPDDR4X** | **~$130** | **Sub-second STT + offline LLM fallback (1-1.5B models)** |

**Why this matters for Clawssistant:**
- **Sub-second STT** — Whisper on the NPU drops transcription from 2-3s (CPU) to under
  1s. This is the single biggest latency improvement you can make.
- **CPU freed up** — with STT offloaded to the NPU, the Pi 5's CPU is available for
  Home Assistant, TTS, event processing, and skill execution.
- **Offline intent parsing** (AI HAT+ 2 only) — small LLMs (Qwen 2.5 1.5B, Llama 3.2 1B)
  run on the Hailo-10H's dedicated 8GB RAM for device command parsing when Claude API
  is unreachable. These models handle "turn on the kitchen lights" reliably but are NOT
  suitable for general conversation.
- **Minimal power** — the NPU draws ~2.5W during inference.
- **Pi 5 RAM not consumed** — models load into the HAT's dedicated 8GB, so even a
  Pi 5 2GB works as a hub.

**Honest limitations:**
- 1-1.5B parameter models cannot replace Claude for multi-turn conversation. They're
  useful for intent classification and slot filling only.
- 25-40 second cold start delay when the model was previously unloaded.
- Hailo llama.cpp integration is still a community effort, not official.
- Piper TTS already runs fast enough on CPU; the NPU doesn't help with TTS.

### Recommended Configurations

Pick a tier based on your priorities:

**🟢 Starter** — Plug and play, cloud-assisted (~$160 per room)
```
Hub:       HA Green ($100) — HAOS pre-installed, plug in and go
Satellite: Voice PE ($59) — auto-discovered by HA
Brain:     Claude API (cloud)
STT:       HA Cloud ($6.50/mo) or slow local (~5-8s)
Setup:     ~15 minutes. Plug in, paste API key, done.
Best for:  Non-technical users, existing HA Green owners
```

**🔵 Balanced** — Fast local STT, cloud brain (~$190 + satellite)
```
Hub:       RPi 5 4GB ($60) + AI HAT+ 13 TOPS ($70)
Satellite: Voice PE ($59)
Brain:     Claude API (cloud)
STT:       Sub-second on NPU (Whisper encoder on Hailo-8L)
Setup:     ~30 minutes. Flash HAOS, attach HAT (4 screws), configure.
Best for:  Fast voice response, audio stays local
```

**🟣 Local-First** — Maximum privacy, offline capable (~$250 + satellite)
```
Hub:       RPi 5 4GB ($60) + AI HAT+ 2 ($130)
Satellite: Voice PE ($59)
Brain:     Claude API when online; local 1.5B intent model when offline
STT:       Sub-second on NPU, CPU free for everything else
Setup:     ~45 minutes. Flash HAOS, attach HAT, configure LLM fallback.
Best for:  Privacy maximalists, unreliable internet, fully autonomous
```

**Note:** RPi 5 only needs 2-4GB because the AI HAT+ 2's models load into its own
dedicated 8GB RAM, not the Pi's system memory.

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
- **Configuration:** YAML
- **Database:** SQLite (local state + memory), optional PostgreSQL for multi-node
- **Vector DB:** ChromaDB (optional, for semantic memory search)

### AI / ML
- **Claude API:** anthropic Python SDK with tool use and streaming
- **MCP:** ClawsOS core MCP servers + optional HA MCP Server + community servers
- **Local STT:** faster-whisper (CTranslate2 backend)
- **Local TTS:** Piper (ONNX runtime)
- **Wake word:** microWakeWord (on-device, used by Voice PE) + openWakeWord (server-side)
- **NPU acceleration:** Raspberry Pi AI HAT+ (Hailo-8L/8/10H) for hardware-accelerated
  Whisper STT and offline intent models. AI HAT+ 2 includes 8GB dedicated RAM for
  model loading without impacting system memory.
- **Local LLM fallback:** llama-cpp-python / Ollama — 7B models on N100, 1-1.5B
  intent models on RPi 5 + AI HAT+ 2
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
  core/                    # ClawsOS kernel
    brain.py               # Claude integration and prompt management
    conversation.py        # Multi-turn conversation manager
    config.py              # Configuration management
    events.py              # Event bus and task scheduler
    scheduler.py           # Cron-like task scheduling (routines, checks)
  memory/                  # Memory system (the OS's "RAM + disk")
    __init__.py            # Memory manager — coordinates all memory types
    working.py             # Working memory (current session context)
    episodic.py            # Episodic memory (timestamped events)
    semantic.py            # Semantic memory (facts, preferences, knowledge)
    procedural.py          # Procedural memory (learned routines, patterns)
    store.py               # Storage backends (SQLite, ChromaDB, Postgres)
  voice/                   # Voice I/O pipeline
    wake_word.py           # Wake word detection (openWakeWord)
    stt.py                 # Speech-to-text (faster-whisper)
    tts.py                 # Text-to-speech (Piper)
    audio.py               # Audio I/O management
    satellite.py           # Wyoming satellite protocol (owned by ClawsOS)
  connectors/              # Connector layer (the OS's "device drivers")
    __init__.py            # Connector base class and registry
    homeassistant.py       # Home Assistant connector (REST + WS + MCP)
    mqtt.py                # MQTT connector (standalone, no HA needed)
    matter.py              # Matter/Thread connector
    zigbee2mqtt.py         # Zigbee2MQTT direct connector
    calendar.py            # CalDAV connector
    email.py               # IMAP/SMTP connector
    media.py               # Media player connectors
    internet.py            # HTTP client, web search, information retrieval
    sip.py                 # SIP/VoIP connector
  skills/                  # Skill framework (the OS's "apps")
    __init__.py            # Skill base class and loader
    lights.py              # Light control skill
    climate.py             # Climate/thermostat skill
    timers.py              # Timers and alarms
    weather.py             # Weather queries
    routines.py            # Automation routines
    code.py                # Developer mode / code skill
  mcp/                     # MCP server definitions
    home_tools.py          # Home control MCP tools
    memory_tools.py        # Memory read/write MCP tools
    system_tools.py        # System management tools
    internet_tools.py      # Web access MCP tools
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
extensibility mechanism. MCP servers are how ClawsOS extends its capabilities —
each MCP server is essentially a "driver" that gives Claude access to new tools.

### ClawsOS Core MCP Servers

These ship with Clawssistant and provide the OS-level capabilities:

- **clawssistant-home** — device control, entity state queries, scene activation
  (uses whichever connectors are configured: HA, MQTT, Matter, etc.)
- **clawssistant-memory** — read/write user preferences, conversation memory,
  semantic search over past interactions
- **clawssistant-system** — system health, logs, configuration management,
  connector status, storage usage
- **clawssistant-media** — enhanced media control (multi-room, queue management)
- **clawssistant-code** — file read/write/execute for developer mode
- **clawssistant-routines** — natural language routine creation and management
- **clawssistant-internet** — web search, HTTP requests, information retrieval

### Home Assistant as MCP Source (Optional)

If you run HA as a connector, its built-in MCP Server integration can expose HA
entities and services to Claude. This is a convenient shortcut — HA already speaks
to 2000+ device types. But it's one MCP source among many, not the primary one.

**What HA's MCP Server provides:**
- All exposed entities (lights, switches, climate, locks, sensors, etc.)
- Service calls (turn_on, turn_off, set_temperature, etc.)
- Entity state queries
- Automation triggers

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
Voice PE Satellite           ClawsOS Hub                  Cloud
─────────────────          ──────────────────           ─────
1. Wake word detected
   (microWakeWord on XMOS)

2. Audio streamed ─────────► 3. faster-whisper (STT)
   via Wyoming protocol        transcribes to text
                                (NPU-accelerated if AI HAT+)

                             4. Conversation manager
                                loads context from
                                memory system

                             5. Context injected ─────► 6. Claude API
                                (time, user, devices,      receives prompt
                                 memory, preferences,      + MCP tools
                                 learned patterns)

                                                        7. Claude decides:
                                                           - tool calls
                                                           - or conversation
                                                           - or memory write

                             8. Connectors execute ◄─── 9. Tool results
                                (HA, MQTT, Matter,         returned
                                 internet, filesystem)

                            10. Claude response ◄────── 11. Final response
                                Memory updated              synthesized

                            12. Piper TTS converts
                                response to audio

13. Audio played ◄─────────  via Wyoming protocol
    on satellite speaker
```

**Key insight:** Clawssistant owns the entire pipeline. It manages Wyoming satellites
directly, runs STT/TTS, and routes through the Claude brain with full memory context.
Home Assistant is an optional connector for device control, not the orchestration layer.
This means Clawssistant's future isn't gated by HA's roadmap.

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

The roadmap follows the "balanced start, grow at your pace" principle. Phase 1
works with HA as the primary connector. Each subsequent phase reduces HA
dependency and grows ClawsOS into a standalone platform.

### Phase 1 — Foundation (Balanced Tier)
- [ ] Core runtime with configuration system and event loop
- [ ] Claude brain with Anthropic API integration (kernel)
- [ ] Memory system — working + semantic memory (SQLite)
- [ ] Basic voice pipeline (wake word + STT + TTS) — ClawsOS-owned
- [ ] Home Assistant connector (first connector, easiest day-one path)
- [ ] MQTT connector (standalone, no HA required)
- [ ] Single-room operation on Raspberry Pi 5 + AI HAT+
- [ ] CLI interface for testing and development
- [ ] Basic web dashboard

### Phase 2 — Smart Home + Memory
- [ ] Full connector layer — HA, MQTT, Zigbee2MQTT, Matter
- [ ] Episodic memory (event logging, pattern detection)
- [ ] Procedural memory (learned routines, suggested automations)
- [ ] Skill framework with built-in skills (timers, weather, media, routines)
- [ ] Multi-room via Voice PE Wyoming satellites
- [ ] Per-user profiles with speaker identification
- [ ] Internet connector (web search, API access, information retrieval)
- [ ] Mobile companion app (basic)

### Phase 3 — Intelligence (the OS becomes smart)
- [ ] Proactive suggestions from pattern analysis ("you always do X at Y")
- [ ] Natural language routine creation ("every morning at 7am, start coffee")
- [ ] Energy monitoring and optimization suggestions
- [ ] Calendar + email connectors with daily briefings
- [ ] Shopping list with smart suggestions from conversation context
- [ ] Semantic memory search (ChromaDB) — "what did we discuss about the garden?"
- [ ] Local LLM fallback for offline operation (AI HAT+ 2)
- [ ] Connector marketplace — community-contributed connectors

### Phase 4 — Full Platform
- [ ] Developer mode (Claude Code-style code assistance)
- [ ] Phone call capability (SIP/VoIP connector)
- [ ] Security system integration (cameras, alarms, locks)
- [ ] Multi-node deployment (distributed hubs with shared memory)
- [ ] Custom hardware designs (3D printed enclosures, custom PCBs)
- [ ] Community skill marketplace
- [ ] Voice cloning for custom TTS voices (with consent)
- [ ] Run fully HA-free with direct Matter/Thread + Zigbee2MQTT

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
| Architecture | AI-native OS | Cloud app | Cloud app | Cloud app | Plugin |
| Open Source | MIT | No | No | No | Yes (HA) |
| AI Brain | Claude | Google AI | Alexa AI | Siri | Limited |
| Persistent Memory | Yes (4 types) | Limited | Limited | No | No |
| Local Processing | Yes (primary) | No | No | Partial | Yes |
| Privacy | Full control | Low | Low | Medium | High |
| Internet Access | Yes (connector) | Walled garden | Walled garden | Walled garden | No |
| Custom Hardware | Yes | No | No | No | Yes |
| Full Conversations | Yes (Claude) | Limited | Limited | Limited | No |
| Code Assistance | Yes | No | No | No | No |
| MCP Extensibility | Yes | No | No | No | No |
| Learns Over Time | Yes | No | Minimal | No | No |
| Vendor Lock-in | None | Google | Amazon | Apple | None |
| Runs Without Cloud | Yes (offline) | No | No | No | Yes |
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
