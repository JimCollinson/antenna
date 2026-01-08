# Antenna

An AI-powered product marketing flywheel that continuously:

- **Gathers intelligence** on the landscape, ICPs, and opportunities
- **Synthesises** that intelligence into strategic direction
- **Executes communications** at scale with authentic voice — and importantly, a human in the loop
- **Learns from outcomes** to improve over time

Not just social listening or content automation — a product marketing operating system. A 10x multiplier for small marketing teams and start-ups.

All powered by AI. Driven through markdown and Obsidian. Modular, extensible, and human readable.

## Architecture

```
INTELLIGENCE → STRATEGY → EXECUTION → LEARNING
       ↑                                   │
       └───────────────────────────────────┘
```

Each layer feeds the next. Learning feeds back into Intelligence. The system compounds over time.

### Layer 1: Intelligence (Sensors)

Agents that gather and synthesise understanding of the world.

| Agent | Purpose |
|-------|---------|
| **Resonance Listener** | Find conversations where our message would land |
| **Landscape Scanner** | Track trends, competitor moves, shifting narratives |
| **ICP Researcher** | Profile customers, track how they talk, where they gather |
| **Gap Detector** | Spot unmet needs and opportunities |

### Layer 2: Strategy (Synthesis)

Agents that turn intelligence into direction.

| Agent | Purpose |
|-------|---------|
| **Opportunity Scorer** | Prioritise signals — "Today's top opportunities" |
| **Positioning Refiner** | Adjust messaging based on what's resonating |
| **Narrative Architect** | Develop stories, analogies, talking points |

### Layer 3: Execution (Action)

Agents that create and distribute.

| Agent | Purpose |
|-------|---------|
| **Response Drafter** | Create responses ready for human review |
| **Content Generator** | Longer-form: threads, posts, articles |
| **Voice Keeper** | Ensure everything sounds authentic |
| **Distribution Orchestrator** | Right content, right place, right time |

### Layer 4: Learning (Feedback)

Agents that measure and improve the system.

| Agent | Purpose |
|-------|---------|
| **Performance Analyst** | Track what's working |
| **Feedback Integrator** | Close the loop — feed learning back into the system |

## Current State (MVP)

Building toward the vision one component at a time. Starting with the core opportunity-to-response loop:

```
LISTEN → SCORE → DRAFT → [HUMAN REVIEW]
```

**Working now:**

- ✅ **Resonance Listener (Twitter)** — Search for conversations matching keywords
- ✅ **Signal Storage** — Markdown files with full metadata, Obsidian-friendly
- ✅ **Deduplication** — Avoid re-processing seen conversations

**Coming next:**

- 🔲 **Opportunity Scorer** — Prioritise signals based on ICP fit
- 🔲 **Response Drafter** — Generate drafts using voice and positioning
- 🔲 **Daily Review** — Summarised briefings for efficient processing

## Setup

### Prerequisites

- Python 3.9+
- Apify account (for Twitter scraping)

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Create a `config.yaml` file based on `config.example.yaml`:

```yaml
apify:
  api_token: "your_apify_token"

paths:
  signals_inbox: "./Signals/Inbox"
  signals_scored: "./Signals/Scored"
  signals_ready: "./Signals/Ready"
  context: "./Context"

twitter:
  tweets_per_query: 20
  min_likes: 0
  min_replies: 0
  language: "en"
  search_queries:
    - '"your keyword"'
    - '"another phrase"'
```

Your `config.yaml` stays private — it contains your API keys and proprietary search queries.

## Usage

### Twitter Listener

```bash
python twitter_listener.py /path/to/config.yaml
```

Finds conversations matching your search queries and saves them as signal files.

### Signal Format

Each signal is a markdown file with YAML frontmatter:

```yaml
---
id: "1234567890"
source: twitter
url: https://twitter.com/user/status/1234567890
author: "@username"
author_followers: 5432
detected_at: 2025-01-08T15:30:00Z
keywords_matched:
  - "decentralised storage"
engagement:
  likes: 12
  retweets: 3
  replies: 5
status: unscored
---

## Original Tweet

The tweet content appears here...

## Author Context

Bio and other context about the author...
```

## Workspace Structure

**Storage:** Markdown files with YAML frontmatter. Works beautifully with Obsidian, git-friendly, fully portable.

**Configuration:** External YAML keeps your proprietary data (API keys, search queries, ICP details) separate from the code.

**Execution:** Run manually, schedule via cron, or integrate into automation tools.

```
your-workspace/
├── config.yaml          # Private configuration
├── Context/             # ICP profile, voice guidelines, positioning
│   ├── ICP Profile.md
│   ├── Voice Guidelines.md
│   └── Positioning.md
├── Signals/
│   ├── Inbox/           # New, unscored signals
│   ├── Scored/          # Prioritised, awaiting draft
│   ├── Ready/           # Drafted, ready for review
│   └── Archive/
│       ├── Posted/      # Successfully posted
│       └── Rejected/    # Decided not to engage
├── Daily Review/        # Generated briefings
└── Learning/            # Patterns and feedback logs
```

## Privacy

This repository contains only generic scripts. Your configuration, search queries, ICP profiles, voice guidelines, and signals stay in your private workspace.

## Licence

MIT
