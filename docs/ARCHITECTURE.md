# Clawssistant Architecture Map

Complete visual blueprint of the autonomous agent system, product architecture,
data flow, and hardware footprint. This document is the single source of truth
for understanding how every piece connects.

---

## 1. Agentic Organization — Team Topology

```
                    ┌─────────────────────────────────┐
                    │       🎯 ORCHESTRATOR            │
                    │    Root Coordinator Agent         │
                    │  (runs every 15 min via cron)     │
                    │                                   │
                    │  • Scans board, dispatches work   │
                    │  • Resolves blocks & escalations  │
                    │  • Coordinates documentation      │
                    │  • Manages timeline & milestones  │
                    └───────────┬───────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────────┐
        │                       │                           │
        ▼                       ▼                           ▼
┌───────────────┐    ┌─────────────────┐         ┌─────────────────┐
│  📋 PM AGENT  │    │ 🔍 TRIAGE AGENT │         │ 🃏 WILDCARD     │
│               │    │                 │         │    AGENT         │
│ • User collab │    │ 3-perspective   │         │                 │
│ • Board mgmt  │    │ evaluation:     │         │ • Weekly scan   │
│ • Epics/stories│   │                 │         │ • Tech debt     │
│ • Blog coord  │    │ 👤 Researcher   │         │ • Security      │
│ • Timeline    │    │ 📊 Data Sci     │         │ • Dead code     │
└───────┬───────┘    │ ⚙️  Engineer     │         │ • Architecture  │
        │            └────────┬────────┘         └─────────────────┘
        │                     │
        │            ┌────────▼─────────────────────────────────┐
        │            │          TICKET LIFECYCLE                 │
        │            │  new → triage → scope → backlog → ready  │
        │            └────────┬─────────────────────────────────┘
        │                     │
        │            ┌────────▼────────┐
        │            │                 │
        │            │  🔺 TRIAD SQUAD │ ◄── The Executing Task Force
        │            │                 │
        │            │  ┌───────────┐  │
        │            │  │ 🏗️  Design │  │  Architecture, APIs, data models
        │            │  │ Engineer  │  │
        │            │  └───────────┘  │
        │            │  ┌───────────┐  │
        │            │  │ 💻 Software│  │  Implementation, tests, security
        │            │  │ Engineer  │  │
        │            │  └───────────┘  │
        │            │  ┌───────────┐  │
        │            │  │ 🎨 UX     │  │  Experience, a11y, DX, docs
        │            │  │ Engineer  │  │
        │            │  └───────────┘  │
        │            │                 │
        │            │  Works as ONE   │
        │            │  unit. All 3    │
        │            │  must agree.    │
        │            └────────┬────────┘
        │                     │
        │                     │ Opens PR
        │                     ▼
        │            ┌─────────────────┐
        │            │ 👨‍💻 SR. ENGINEER │
        │            │   Code Review   │
        │            │                 │
        │            │ • Correctness   │
        │            │ • Architecture  │
        │            │ • Test coverage │
        │            │ • Performance   │
        │            └────────┬────────┘
        │                     │
        │                     │ Approved
        │                     ▼
        │         ┌───────────────────────┐
        │         │  🔒 SECURITY PAIR     │ ◄── Both must approve
        │         │                       │
        │         │  ┌─────────────────┐  │
        │         │  │ 🛡️  Security Eng │  │  OWASP, code vulns, deps
        │         │  └─────────────────┘  │
        │         │  ┌─────────────────┐  │
        │         │  │ 🔐 InfoSec      │  │  Threat model, compliance
        │         │  └─────────────────┘  │
        │         └───────────┬───────────┘
        │                     │
        │                     │ Both approved
        │                     ▼
        │            ┌─────────────────┐
        │            │  🧪 QA AGENT    │
        │            │                 │
        │            │ • Test suite    │
        │            │ • Acceptance    │
        │            │ • Regression    │
        │            │ • Exploratory   │
        │            └────────┬────────┘
        │                     │
        │                     │ Passed
        │                     ▼
        │            ┌─────────────────┐
        │            │  🚀 DEPLOY      │
        │            │                 │
        │            │ • Merge PR      │
        │            │ • Close ticket  │
        │            │ • Update board  │
        │            └────────┬────────┘
        │                     │
        └─────────────────────┘
               Blog agent publishes release post
```

---

## 2. Ticket State Machine

```
                   ┌─────────┐
                   │   NEW   │ ◄── Issue/Discussion created
                   └────┬────┘
                        │ Triage agent activates
                        ▼
                   ┌──────────┐
                   │ TRIAGING │ ◄── 3-perspective evaluation
                   └────┬─────┘
                        │
                   ┌────▼──────────────┐
                   │ FEASIBILITY REVIEW│
                   └────┬──────────────┘
                        │
              ┌─────────┼──────────┐
              │                    │
         ┌────▼────┐         ┌────▼─────┐
         │ SCOPED  │         │ ARCHIVED │ ◄── Rejected (with context)
         └────┬────┘         └──────────┘
              │
         ┌────▼────┐
         │ BACKLOG │
         └────┬────┘
              │ Orchestrator dispatches
         ┌────▼────┐
         │  READY  │
         └────┬────┘
              │ Triad squad assigned
    ┌─────────▼──────────┐
    │    IN PROGRESS      │◄──────────────────┐
    └─────────┬──────────┘                    │
              │                               │
         ┌────▼────┐                          │
     ┌───│ BLOCKED │──── Orchestrator ────────┤
     │   └─────────┘     resolves             │
     │                                        │
     │   ┌─────────────┐                      │
     └──►│ CODE REVIEW │                      │
         └──────┬──────┘                      │
                │ Sr. engineer approves        │
                │ (or sends back) ────────────┘
         ┌──────▼────────────┐                │
         │ SECURITY REVIEW   │                │
         │ (sec + infosec)   │                │
         └──────┬────────────┘                │
                │ Both approve                │
                │ (or send back) ─────────────┘
         ┌──────▼──┐                          │
         │   QA    │                          │
         └──────┬──┘                          │
                │ QA passes                   │
                │ (or sends back) ────────────┘
         ┌──────▼──────┐
         │  DEPLOYING  │
         └──────┬──────┘
                │
         ┌──────▼──────┐
         │  DEPLOYED   │
         └──────┬──────┘
                │
         ┌──────▼──────┐
         │  ARCHIVED   │ ◄── With full context, learnings, and reason
         └─────────────┘
```

---

## 3. Data Graph — What Flows Where

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA FLOW MAP                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  GitHub Issues ──────────►  Triage Agent ──────► TicketContext       │
│  GitHub Discussions ─────►  PM Agent ───────────► (JSON in comments) │
│                                                     │                │
│                                                     ▼                │
│  TicketContext ───► Orchestrator ───► Dispatch Events                │
│  (handoff block)       │                 │                           │
│                        │                 ├──► agent-develop.yml      │
│                        │                 ├──► agent-review.yml       │
│                        │                 ├──► agent-security.yml     │
│                        │                 ├──► agent-qa.yml           │
│                        │                 └──► agent-deploy.yml       │
│                        │                                             │
│                        ▼                                             │
│  agents.yaml ─────► Agent Config                                    │
│  (YAML)               │                                             │
│                        ├──► Model selection                         │
│                        ├──► Token budgets                           │
│                        ├──► Response delays                         │
│                        └──► Capability constraints                  │
│                                                                      │
│  Anthropic API ◄──── Claude Brain ────► Tool Calls ──► GitHub API   │
│  (claude-sonnet-4-6)    │                                 │          │
│                          │                                ├► Issues  │
│                          │                                ├► PRs     │
│                          │                                ├► Labels  │
│                          │                                ├► Reviews │
│                          │                                └► Deploys │
│                          │                                           │
│                          └──► Blog Posts ──► docs/blog/_posts/*.md   │
│                                                  │                   │
│                                                  ▼                   │
│                                           GitHub Pages               │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              CONTEXT PRESERVATION                            │    │
│  │                                                              │    │
│  │  Every ticket carries a TicketContext JSON block in          │    │
│  │  GitHub issue comments. This contains:                      │    │
│  │                                                              │    │
│  │  • Ticket classification (type, priority, scope)            │    │
│  │  • Triage results (feasibility, research, estimates)        │    │
│  │  • Development state (branch, PR, implementation notes)     │    │
│  │  • Review history (code review, security, QA)               │    │
│  │  • Handoff chain (which agent → which agent, and why)       │    │
│  │  • Archive context (if archived: reason + learnings)        │    │
│  │                                                              │    │
│  │  This ensures ANY agent can pick up ANY ticket at ANY       │    │
│  │  point and have full context for the work.                  │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Product Architecture — Clawssistant Itself

```
┌──────────────────────────────────────────────────────────────────┐
│                      USER INTERFACES                              │
│                                                                    │
│  🗣️  Voice           📱 Mobile App        🖥️  Web Dashboard       │
│  (Wake Word →        (React Native/       (React/Svelte)          │
│   STT → NLU →        Flutter)                                     │
│   TTS)                                    🔲 CLI (Rich TUI)       │
└────────────────────────────┬─────────────────────────────────────┘
                              │
                    REST + WebSocket API
                       (FastAPI + uvicorn)
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                    CONVERSATION MANAGER                            │
│                                                                    │
│  Multi-turn Context ──── User Profiles ──── Long-term Memory     │
│        │                      │                    │               │
│        │              Speaker ID            SQLite / Vector DB     │
│        │              (pyannote)                                   │
│        └──────────────────────┘                                   │
└─────────────────────────────┬────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                        CLAUDE BRAIN                               │
│                                                                    │
│  ┌─────────────────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │ Anthropic API    │   │ MCP Servers  │   │ Local LLM        │  │
│  │ (primary)        │   │ (tools)      │   │ (fallback)       │  │
│  │                  │   │              │   │                  │  │
│  │ claude-sonnet-4-6│   │ home_tools   │   │ llama.cpp /      │  │
│  │ + tool use       │   │ system_tools │   │ Ollama           │  │
│  │ + streaming      │   │ memory_tools │   │                  │  │
│  └─────────────────┘   └──────────────┘   └──────────────────┘  │
└─────────────────────────────┬────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                      SKILL FRAMEWORK                              │
│                                                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 💡 Lights │ │ 🌡️ Climate│ │ 🎵 Media  │ │ ⏰ Timers │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 🌤️ Weather│ │ 📋 Routines│ │ 🔒 Security│ │ ⚡ Energy │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────────────────────────────────────────────┐           │
│  │        Custom Skills (hot-reloadable .py)         │           │
│  └──────────────────────────────────────────────────┘           │
└─────────────────────────────┬────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                    INTEGRATION LAYER                               │
│                                                                    │
│  ┌──────────────────┐  ┌──────┐  ┌────────┐  ┌───────────────┐  │
│  │ Home Assistant    │  │ MQTT │  │ CalDAV │  │ SIP / VoIP    │  │
│  │ (REST + WS)      │  │      │  │        │  │               │  │
│  └──────────────────┘  └──────┘  └────────┘  └───────────────┘  │
└─────────────────────────────┬────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                       DEVICE LAYER                                │
│                                                                    │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │ Matter │ │ Zigbee │ │ Z-Wave │ │  WiFi  │ │  BLE   │        │
│  │ Thread │ │ (z2m)  │ │ (ZWJS) │ │(Shelly)│ │        │        │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Voice Pipeline Detail

```
┌──────────────┐
│  Microphone   │  ReSpeaker / USB / INMP441 (I2S)
│  Array        │
└──────┬───────┘
       │ Raw PCM (16kHz, 16-bit, mono)
       ▼
┌──────────────┐
│  Wake Word    │  openWakeWord (TFLite)
│  Detection    │  Custom "Clawssistant" model
└──────┬───────┘
       │ Triggered
       ▼
┌──────────────┐
│   Voice      │  WebRTC VAD
│   Activity   │  Detects speech start/end
│   Detection  │
└──────┬───────┘
       │ Audio segment
       ▼
┌──────────────┐
│  Speech to   │  faster-whisper (CTranslate2)
│  Text (STT)  │  Runs locally on RPi 5 / x86
└──────┬───────┘
       │ Transcribed text
       ▼
┌──────────────┐
│  Claude      │  Anthropic API + MCP tools
│  Brain       │  Context: time, user, device states, history
└──────┬───────┘
       │ Response text
       ▼
┌──────────────┐
│  Text to     │  Piper TTS (ONNX)
│  Speech      │  High-quality neural voices
└──────┬───────┘
       │ Audio (WAV/PCM)
       ▼
┌──────────────┐
│  Speaker     │  3.5mm / USB / Bluetooth / I2S
│  Output      │  HiFiBerry DAC for quality
└──────────────┘
```

---

## 6. Hardware Footprint

```
┌─────────────────────────────────────────────────────────────────┐
│                     HARDWARE MAP                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    HUB (Central Unit)                     │    │
│  │                                                           │    │
│  │  RECOMMENDED OPTIONS:                                     │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │ 🥇 Raspberry Pi 5 (8GB)            ~$80          │    │    │
│  │  │    • ARM Cortex-A76 4-core                       │    │    │
│  │  │    • Runs STT + TTS + wake word locally          │    │    │
│  │  │    • Add ReSpeaker HAT for mic array             │    │    │
│  │  │    • microSD or NVMe for storage                 │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │ 🥈 Mini PC (Intel N100)             ~$150        │    │    │
│  │  │    • Best performance                            │    │    │
│  │  │    • Can run local LLM fallback                  │    │    │
│  │  │    • 16GB RAM ideal                              │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │ 🥉 HA Yellow / HA Green             ~$100-150    │    │    │
│  │  │    • Purpose-built for Home Assistant             │    │    │
│  │  │    • Built-in Zigbee (Yellow)                    │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  │                                                           │    │
│  │  NETWORK:   Ethernet (preferred) or WiFi                 │    │
│  │  STORAGE:   32GB+ microSD / NVMe SSD                     │    │
│  │  AUDIO:     USB mic + 3.5mm speaker (minimum)            │    │
│  │  RADIOS:    Zigbee dongle, Z-Wave stick (as needed)      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              SATELLITES (Per-Room Units)                  │    │
│  │                                                           │    │
│  │  ┌─────────────────────────────────────────────┐         │    │
│  │  │ 🎯 ESP32-S3-BOX-3                  ~$45     │         │    │
│  │  │    Built-in mic, speaker, touch screen       │         │    │
│  │  │    Runs openWakeWord locally                 │         │    │
│  │  │    Streams audio to hub via Wyoming          │         │    │
│  │  └─────────────────────────────────────────────┘         │    │
│  │  ┌─────────────────────────────────────────────┐         │    │
│  │  │ 💰 DIY ESP32 + INMP441 + MAX98357  ~$10     │         │    │
│  │  │    Cheapest option — breadboard prototype    │         │    │
│  │  │    3D-printed enclosure (STLs in hardware/)  │         │    │
│  │  └─────────────────────────────────────────────┘         │    │
│  │  ┌─────────────────────────────────────────────┐         │    │
│  │  │ 🔄 RPi Zero 2W                     ~$15     │         │    │
│  │  │    More capable, runs local wake word + VAD  │         │    │
│  │  │    USB mic + speaker                         │         │    │
│  │  └─────────────────────────────────────────────┘         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               MINIMUM TO GET STARTED                     │    │
│  │                                                           │    │
│  │  • Raspberry Pi 5 (4GB) .............. $60               │    │
│  │  • microSD card (32GB) ............... $8                │    │
│  │  • USB-C power supply ................ $12               │    │
│  │  • USB microphone .................... $10               │    │
│  │  • Any speaker (3.5mm) ............... $5                │    │
│  │  • Ethernet cable .................... $5                │    │
│  │  ─────────────────────────────────────────               │    │
│  │  TOTAL ............................... ~$100              │    │
│  │                                                           │    │
│  │  + Anthropic API key (pay-per-use, ~$3/month casual)     │    │
│  │  + Smart home devices you already own                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               SMART HOME RADIOS                          │    │
│  │                                                           │    │
│  │  Zigbee: Sonoff Zigbee 3.0 USB Dongle Plus ... $20      │    │
│  │  Z-Wave: Zooz ZST39 800LR Z-Wave Stick ...... $35      │    │
│  │  Matter: Built into WiFi (no extra hardware)             │    │
│  │  IR:     Broadlink RM4 Mini .................. $25      │    │
│  │                                                           │    │
│  │  (Only buy what you need for YOUR devices)               │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Security Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                   TRUST BOUNDARY MAP                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  UNTRUSTED                 BOUNDARY              TRUSTED          │
│  ─────────                 ────────              ───────          │
│                                                                   │
│  Internet ─────────────► [Firewall+TLS] ──────► API Server      │
│                                                                   │
│  Audio environment ────► [Wake Word +   ] ────► Voice Pipeline   │
│  (TV, visitors,           Speaker ID]                            │
│   recordings)                                                     │
│                                                                   │
│  Community skills ─────► [Subprocess    ] ────► Core Runtime     │
│  (third-party code)       Sandbox]                               │
│                                                                   │
│  MCP tool results ─────► [Input         ] ────► Claude Brain     │
│  (external data)          Validation]                            │
│                                                                   │
│  Companion apps ───────► [Token Auth +  ] ────► Conversation     │
│  (mobile, web)            Rate Limit]           Manager          │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              ACTION RISK TIERS                            │   │
│  │                                                            │   │
│  │  🟢 LOW RISK (voice command only)                         │   │
│  │     lights, weather, timers, music, shopping list          │   │
│  │                                                            │   │
│  │  🟡 MEDIUM RISK (voice confirmation required)             │   │
│  │     thermostat, garage door, routines, calendar            │   │
│  │                                                            │   │
│  │  🔴 HIGH RISK (PIN or app confirmation required)          │   │
│  │     door locks, alarm system, camera access                │   │
│  │                                                            │   │
│  │  ⛔ CRITICAL (companion app only)                         │   │
│  │     shell execution, config changes, skill install         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              AGENT SECURITY MODEL                         │   │
│  │                                                            │   │
│  │  Every PR must pass:                                      │   │
│  │  1. Sr. Engineer code review (quality + architecture)     │   │
│  │  2. Security Engineer scan (OWASP, vulns, deps)           │   │
│  │  3. InfoSec review (threat model, compliance, privacy)    │   │
│  │  4. QA validation (tests, acceptance criteria)            │   │
│  │                                                            │   │
│  │  Security + InfoSec are a PAIR — both must approve.       │   │
│  │  Either can BLOCK deployment unilaterally.                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Ontology — Concept Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     ONTOLOGY LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│                    ┌──────────────┐                               │
│                    │   HOME       │                               │
│                    │              │                               │
│                    │ • Rooms      │                               │
│                    │ • Residents  │                               │
│                    │ • Routines   │                               │
│                    │ • State      │                               │
│                    └──────┬───────┘                               │
│                           │                                       │
│              ┌────────────┼────────────┐                         │
│              │            │            │                         │
│        ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐                   │
│        │  DEVICE    │ │ USER   │ │ CONTEXT  │                   │
│        │            │ │        │ │          │                   │
│        │ • entity_id│ │ • name │ │ • time   │                   │
│        │ • domain   │ │ • voice│ │ • who's  │                   │
│        │ • state    │ │ • prefs│ │   home   │                   │
│        │ • attrs    │ │ • PIN  │ │ • weather│                   │
│        │ • room     │ │ • role │ │ • events │                   │
│        └─────┬──────┘ └───┬────┘ └────┬─────┘                   │
│              │            │            │                         │
│              └────────────┼────────────┘                         │
│                           │                                       │
│                    ┌──────▼───────┐                               │
│                    │ CONVERSATION │                               │
│                    │              │                               │
│                    │ • history    │                               │
│                    │ • intent     │                               │
│                    │ • mode       │                               │
│                    │ • memory     │                               │
│                    └──────┬───────┘                               │
│                           │                                       │
│              ┌────────────┼────────────┐                         │
│              │            │            │                         │
│        ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐                   │
│        │  SKILL    │ │ ACTION │ │  TOOL    │                   │
│        │           │ │        │ │  (MCP)   │                   │
│        │ • name    │ │ • verb │ │          │                   │
│        │ • domain  │ │ • target│ │ • server│                   │
│        │ • triggers│ │ • params│ │ • method│                   │
│        │ • manifest│ │ • risk  │ │ • schema│                   │
│        └───────────┘ └────────┘ └──────────┘                   │
│                                                                   │
│  RELATIONSHIPS:                                                   │
│  Home ──has──► Rooms ──contains──► Devices                       │
│  Home ──has──► Residents (Users)                                 │
│  User ──speaks──► Conversation ──invokes──► Skill                │
│  Skill ──calls──► Tool (MCP) ──controls──► Device                │
│  Context ──enriches──► Conversation                              │
│  Device ──belongs_to──► Room                                     │
│  Action ──has──► Risk Level ──requires──► Confirmation           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Agentic Workflow — Full Lifecycle

```
User files          Triage Agent evaluates       PM writes           Orchestrator
GitHub Issue  ────► from 3 perspectives    ────► epics/stories ────► dispatches
or Discussion       (researcher, data sci,       adds to board       triad squad
                     engineer)

     │                                                                    │
     │                                                                    ▼
     │                                                           ┌──────────────┐
     │    ◄─── User gets @tagged for clarification               │ 🔺 TRIAD     │
     │         PM collaborates until requirements clear           │    SQUAD      │
     │                                                            │              │
     │                                                            │ 🏗️ Design Eng │
     │                                                            │ 💻 SW Eng    │
     │                                                            │ 🎨 UX Eng    │
     │                                                            └──────┬───────┘
     │                                                                   │
     │                                                            Opens PR│
     │                                                                   ▼
     │                                                        Sr. Engineer Review
     │                                                              │
     │              ◄── If changes requested ──────────────────────┤
     │                   Triad addresses feedback                  │
     │                                                              │
     │                                                       ┌─────▼──────┐
     │                                                       │  SECURITY   │
     │                                                       │  PAIR       │
     │                                                       │  🛡️ Sec Eng │
     │              ◄── If blocked ────────────────────────── │  🔐 InfoSec │
     │                   Same engineer fixes                  └─────┬──────┘
     │                                                              │
     │                                                         ┌────▼────┐
     │              ◄── If QA fails ──────────────────────────│   QA    │
     │                   Same engineer fixes                   └────┬────┘
     │                                                              │
     │                                                         ┌────▼────┐
     │                                                         │ DEPLOY  │
     │                                                         └────┬────┘
     │                                                              │
     │         ◄── Blog post published about the release ───────────┘
     │
     ▼
  User sees result
  in next release
```

---

## 10. File Map — Where Everything Lives

```
clawssistant/
├── agents/                          # 🤖 AUTONOMOUS AGENT SYSTEM
│   ├── __init__.py
│   ├── agents.yaml                  # Agent config (models, delays, capabilities)
│   ├── base.py                      # Base agent class (think → act loop)
│   ├── config.py                    # Role definitions and capability declarations
│   ├── context.py                   # TicketContext — handoff preservation
│   ├── dispatch.py                  # Agent dispatch via workflow_dispatch
│   ├── github_ops.py                # GitHub API operations (issues, PRs, reviews)
│   ├── state.py                     # Ticket state machine + label scheme
│   ├── roles/
│   │   ├── orchestrator.py          # 🎯 Root coordinator (15-min cron)
│   │   ├── pm.py                    # 📋 Product manager (users, board, blog)
│   │   ├── triage.py                # 🔍 Multi-perspective triage
│   │   ├── triad.py                 # 🔺 Triad squad (design + SW + UX)
│   │   ├── engineer.py              # 💻 Solo engineer (legacy, triad preferred)
│   │   ├── reviewer.py              # 👨‍💻 Sr. engineer code review
│   │   ├── security.py              # 🛡️ Security + 🔐 InfoSec pair
│   │   ├── qa.py                    # 🧪 QA validation
│   │   ├── wildcard.py              # 🃏 Periodic codebase auditor
│   │   └── blog.py                  # 📝 Blog writer/publisher
│   └── scripts/
│       ├── __init__.py
│       ├── __main__.py
│       └── run_agent.py             # Unified CLI entry point
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                   # Standard CI (lint, test, typecheck)
│   │   ├── agent-orchestrator.yml   # 🎯 Every 15 min
│   │   ├── agent-triage.yml         # 🔍 On issue/discussion created
│   │   ├── agent-develop.yml        # 🔺 Dispatched for ready tickets
│   │   ├── agent-review.yml         # 👨‍💻 On PR opened
│   │   ├── agent-security.yml       # 🛡️🔐 Dispatched after review
│   │   ├── agent-qa.yml             # 🧪 Dispatched after security
│   │   ├── agent-deploy.yml         # 🚀 Dispatched after QA
│   │   ├── agent-wildcard.yml       # 🃏 Weekly cron
│   │   ├── agent-blog.yml           # 📝 On deploy or weekly
│   │   └── pages.yml                # GitHub Pages deployment
│   └── dependabot.yml
│
├── docs/
│   ├── ARCHITECTURE.md              # ← YOU ARE HERE
│   └── blog/
│       ├── _config.yml              # Jekyll config
│       ├── _layouts/
│       │   ├── default.html         # Base layout (dark theme)
│       │   └── post.html            # Blog post layout
│       ├── _posts/                  # Blog posts (auto-generated)
│       └── index.md                 # Blog home page
│
├── clawssistant/                    # 🏠 THE ACTUAL HOME ASSISTANT
│   ├── core/                        # Runtime, brain, conversation, memory
│   ├── voice/                       # Wake word, STT, TTS, audio I/O
│   ├── integrations/                # Home Assistant, MQTT, calendar
│   ├── skills/                      # Pluggable skill modules
│   ├── mcp/                         # MCP server definitions
│   └── api/                         # FastAPI REST + WebSocket
│
├── tests/                           # Test suite
│   ├── conftest.py                  # Shared fixtures
│   ├── fixtures/                    # Test data
│   ├── unit/                        # Unit tests
│   └── integration/                 # Integration tests
│
├── hardware/                        # Open hardware designs
│   ├── 3d_prints/                   # Enclosure STLs
│   ├── pcb/                         # KiCad PCB designs
│   └── bom/                         # Bills of materials
│
├── pyproject.toml                   # Python project config
├── Makefile                         # Dev commands
├── docker-compose.test.yml          # Test services (MQTT, HA, Redis)
├── .pre-commit-config.yaml          # Pre-commit hooks
├── CLAUDE.md                        # Project instructions
├── SECURITY.md                      # Security policy
└── README.md                        # Project overview
```
