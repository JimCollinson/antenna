# Marketing OS (Antenna)

An AI-powered product marketing system that continuously:

- **Listens** for conversations where your message would resonate
- **Scores** signals based on ICP fit and relevance
- **Generates** daily briefings for human review
- **Learns** from outcomes to improve over time

All powered by AI. Driven through markdown and Obsidian. Modular, extensible, and human readable.

## Current State (v0.2)

```
LISTEN → SCORE → DAILY BRIEFING → [HUMAN REVIEW]
```

**Working now:**

- ✅ **Bluesky Listener** — Search for conversations via free API
- ✅ **YouTube Listener** — Search for videos via YouTube Data API v3 (free)
- ✅ **In-Memory Scoring** — Score signals against ICP criteria
- ✅ **Daily Briefing** — Single consolidated report with top 10 opportunities
- ✅ **Recency Filter** — YouTube limited to recent content (configurable)
- ✅ **Deduplication** — Avoid duplicate signals within a run

**Known Limitations:**

- Keyword matching produces noise (e.g., "walled gardens" matches actual gardens)
- Bluesky short posts less useful than YouTube long-form content
- Scoring is rule-based, not AI-powered yet
- No learning loop implemented

**Coming Next:**

- 🔲 **AI Research Layer** — Dynamic query generation based on ICP understanding
- 🔲 **AI-Powered Scoring** — Use LLM to evaluate relevance contextually
- 🔲 **Response Drafter** — Generate draft responses for high-priority signals
- 🔲 **Twitter Listener** — When API access is available

## Setup

### Prerequisites

- Python 3.9+
- YouTube Data API key (free from Google Cloud Console)
- Bluesky account (for authenticated search)

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Create `config.yaml` in the project root (parent of Scripts folder):

```yaml
# API Credentials
bluesky:
  username: "your.handle"
  password: "your-app-password"

youtube:
  api_key: "your-youtube-api-key"  # From Google Cloud Console

# Listener Settings
listener:
  bluesky:
    enabled: true
    posts_per_query: 15
    language: "en"
  
  youtube:
    enabled: true
    videos_per_query: 10
    max_age_days: 30  # Only recent content

# Scorer Settings
scorer:
  thresholds:
    high: 70
    medium: 50
```

Search queries are defined separately in `queries/bluesky.yaml` and `queries/youtube.yaml`.

## Usage

### Run the Marketing OS

```bash
cd Scripts
python marketing_os.py
```

Options:
```bash
python marketing_os.py                    # Run all enabled platforms
python marketing_os.py --platform youtube # YouTube only
python marketing_os.py --platform bluesky # Bluesky only
python marketing_os.py --dry-run          # Preview without API calls
```

### Output

Each run generates a Daily Briefing in `Daily Review/`:

```
Daily Review/
└── 2026-Jan-12 - Daily Briefing (1541).md
```

The briefing contains:
- Top 10 opportunities ranked by score
- Full post/video content (no truncation)
- Score breakdown per signal
- Run statistics

## Project Structure

```
Marketing OS/
├── config.yaml              # API keys and settings (private, not committed)
├── Context/                 # ICP profile, voice guidelines, positioning
│   ├── ICP Profile.md
│   ├── Voice Guidelines.md
│   ├── Positioning.md
│   └── Current Priorities.md
├── queries/                 # Search queries by platform
│   ├── bluesky.yaml
│   └── youtube.yaml
├── Daily Review/            # Generated briefings
├── Scripts/                 # This repository
│   ├── marketing_os.py      # Main script
│   ├── requirements.txt
│   └── README.md
└── Learning/                # (Future) Patterns and feedback
```

## Architecture Vision

```
INTELLIGENCE → STRATEGY → EXECUTION → LEARNING
       ↑                                   │
       └───────────────────────────────────┘
```

### Layer 1: Intelligence (Current Focus)
- Resonance Listener — Find relevant conversations
- ICP Researcher — Understand how ICPs talk and where they gather

### Layer 2: Strategy
- Opportunity Scorer — Prioritise signals
- Positioning Refiner — Adjust messaging based on what resonates

### Layer 3: Execution
- Response Drafter — Create responses for human review
- Voice Keeper — Ensure authentic voice

### Layer 4: Learning
- Performance Analyst — Track what's working
- Feedback Integrator — Improve the system over time

## Privacy

Your `config.yaml` contains API keys and stays private. The Scripts folder can be committed to git separately.

## Licence

MIT
