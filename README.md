# Competitive Pricing Multi-Agent System

A two-tier agent system for automated competitive pricing decisions, built as a demonstration of cost-aware AI engineering architecture.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                      │
│                 (llama-3.3-70b-versatile)                 │
│                     Hourly Cadence                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Reads conversion data & margin trends             │   │
│  │ • Decides WHICH SKUs need attention                 │   │
│  │ • Updates watchlist (max 15 SKUs)                  │   │
│  │ • Never sets prices directly                       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     WORKER AGENTS                          │
│                  (llama-3.1-8b-instant)                   │
│                   15-min per SKU                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Fetches competitor price + our price + margin    │   │
│  │ • Decides: MATCH | UNDERCUT_50 | HOLD             │   │
│  │ • Enforces 12% margin floor (deterministic)        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Principles

- **Cost-Tiering**: Large model (70b) for infrequent complex decisions, small model (8b) for frequent simple decisions
- **Deterministic Safety**: Financial constraints enforced by Python code, not LLM judgment
- **Free Tier Compatible**: Runs entirely on Groq's free API tier while tracking hypothetical paid costs
- **Production Patterns**: Rate limiting, error handling, audit logging, graceful degradation

## Quick Start

### Prerequisites

Before running, you need:
- **Python 3.11+** installed on your system
- **Groq API Key** (free tier) - Get one at [console.groq.com](https://console.groq.com)
- **Docker & Docker Compose** (optional, only for production PostgreSQL mode)

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/competitive-repricing-agent.git
   cd competitive-repricing-agent
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   # Copy the example file
   copy .env.example .env     # Windows
   # OR
   cp .env.example .env       # Linux/Mac
   ```

5. **Edit `.env` file** and add your Groq API key:
   ```env
   GROQ_API_KEY=your_actual_groq_api_key_here
   ```

### How to Run

#### Option 1: Demo Mode (Recommended for First Run) ⭐

**Best for testing and demonstrations** - compressed timing shows results in 5-10 minutes:

```bash
python run_demo.py
```

What happens:
- System initializes with SQLite database (no Docker needed)
- Seeds 20 sample SKUs with realistic data
- Orchestrator runs every **1 minute** (vs 60 minutes in production)
- Workers process watchlist SKUs every **15 seconds** (vs 15 minutes in production)
- You'll see real-time logging of agent decisions
- Press `Ctrl+C` to stop gracefully

**Expected output**:
```
2024-01-15 10:30:00 [info] System initialized in DEMO mode
2024-01-15 10:30:00 [info] Database seeded with 20 SKUs
2024-01-15 10:30:00 [info] Starting orchestrator and worker loops
2024-01-15 10:30:15 [info] Orchestrator analyzing market conditions...
2024-01-15 10:30:20 [info] Watchlist updated: 12 SKUs selected
2024-01-15 10:30:35 [info] Worker processing SKU: WIDGET-001
2024-01-15 10:30:37 [info] Decision: MATCH competitor price at $29.99
...
```

#### Option 2: Local Development Mode

**For development without Docker**:

```bash
python main.py
```

- Uses SQLite database (`competitive_pricing.db` in project root)
- Production timing (slow - orchestrator every 60 min, workers every 15 min)
- Good for development and debugging

#### Option 3: Production Mode (Docker)

**For production deployment with PostgreSQL**:

```bash
# Start PostgreSQL and the pricing agent
docker-compose up

# Or run in background
docker-compose up -d

# View logs
docker-compose logs -f pricing-agent

# Stop the system
docker-compose down
```

### Verify It's Working

1. **Check the logs** - you should see:
   - `"System initialized"`
   - `"Orchestrator starting"`
   - `"Worker agents starting"`
   - Agent decision logs

2. **Check the database**:
   ```bash
   # View sample data
   python show_samples.py
   
   # Inspect database contents
   python inspect_data_local.py
   ```

3. **View the Web UI** (optional):
   ```bash
   cd ui
   # Open index.html in your browser
   start index.html     # Windows
   open index.html      # Mac
   xdg-open index.html  # Linux
   ```

### Run Integration Tests

Before committing changes, verify everything works:

```bash
python run_integration_test.py
```

This tests:
- ✓ Budget guard enforcement
- ✓ Rate limiting
- ✓ Margin floor safety
- ✓ Orchestrator decision making
- ✓ Worker pricing logic
- ✓ Database operations

### Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'groq'`
- **Fix**: Run `pip install -r requirements.txt`

**Issue**: `GROQ_API_KEY not set`
- **Fix**: Verify `.env` file exists and contains `GROQ_API_KEY=your_key_here`

**Issue**: `Connection timeout` or API errors
- **Fix**: Check internet connection and verify Groq API is accessible
- Check free tier limits at [console.groq.com](https://console.groq.com)

**Issue**: `Port 5432 already in use` (Docker mode)
- **Fix**: Stop existing PostgreSQL or change port in `docker-compose.yml`

**Issue**: Nothing happens / no output
- **Fix**: Check `LOG_LEVEL=INFO` in `.env` file
- Enable demo mode: `DEMO_MODE=true` in `.env`

4. **Demo Mode Details**:
   
   Demo mode uses compressed timing for rapid testing and demonstrations:
   - **Worker interval**: 15 seconds (vs 15 minutes in production)
   - **Orchestrator interval**: 1 minute (vs 60 minutes in production)
   - All safety checks remain active (margin floor, budget guard, rate limits)
   - Full audit trail still logged to database
   
   Enable demo mode in two ways:
   ```bash
   # Method 1: Using run_demo.py launcher
   python run_demo.py
   
   # Method 2: Set environment variable
   DEMO_MODE=true python main.py
   
   # Method 3: Add to .env file
   echo "DEMO_MODE=true" >> .env
   python main.py
   ```
   
   **Use case**: Demonstrate the full system cycle (orchestrator + workers) in 5-10 minutes instead of waiting hours.

## Cost Analysis

The system demonstrates significant cost savings through model tiering:

- **Two-tier approach**: ~$X.XX/day (15 SKUs × 96 worker calls + 24 orchestrator calls)
- **Single large model**: ~$Y.YY/day (15 SKUs × 96 calls, all 70b)
- **Savings**: Z% reduction while maintaining decision quality

## What I'd Do Differently with Real Data

1. **Competitor Data**: Replace simulator with actual scraping (respecting ToS) or paid data feeds
2. **Validation**: A/B testing against manual pricing decisions to validate agent performance
3. **Scaling**: Proper task queue (Celery/RQ) instead of async loops for >1000 SKUs
4. **Monitoring**: Real APM integration, not just structured logging

## Project Status

This is a portfolio/demonstration project. It uses simulated competitor data to avoid ToS violations while maintaining realistic system behavior and interfaces.

## Before Pushing to GitHub

### Pre-Push Checklist

Before pushing your code to GitHub, ensure:

1. **✓ Remove sensitive data**:
   ```bash
   # Check that .env is in .gitignore
   cat .gitignore | findstr .env
   
   # Verify .env is NOT staged for commit
   git status
   ```

2. **✓ Use .env.example** - Never commit your actual `.env` file with API keys

3. **✓ Test the setup flow**:
   ```bash
   # Simulate a fresh clone
   python run_integration_test.py
   ```

4. **✓ Verify .gitignore** includes:
   ```
   .env
   *.db
   __pycache__/
   *.pyc
   logs/
   venv/
   .pytest_cache/
   ```

5. **✓ Update README** with your actual GitHub URL:
   - Replace `https://github.com/yourusername/competitive-repricing-agent.git`
   - Update any other placeholder links

6. **✓ Test the Quick Start** commands work from scratch

### Initial Git Commands

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit: Competitive pricing multi-agent system"

# Add your GitHub remote
git remote add origin https://github.com/yourusername/competitive-repricing-agent.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### What Gets Committed vs Ignored

**✓ COMMITTED** (tracked in Git):
- Source code (`.py` files)
- Configuration templates (`.env.example`)
- Documentation (`.md` files)
- Dependencies (`requirements.txt`)
- Database schema (`db/init.sql`)
- Docker configuration
- UI files

**✗ IGNORED** (not tracked):
- `.env` (contains secrets)
- `*.db` (local SQLite files)
- `__pycache__/` (Python cache)
- `venv/` (virtual environment)
- `logs/` (runtime logs)
- IDE settings (`.vscode/`, `.idea/`)

## Troubleshooting

### Integration Test Failures

1. **"GROQ_API_KEY not set"**:
   - Copy `.env.example` to `.env`
   - Add your Groq API key: `GROQ_API_KEY=your_actual_key_here`

2. **"Module not found" errors**:
   - Install dependencies: `pip install -r requirements.txt`
   - Consider using a virtual environment: `python -m venv venv && venv\Scripts\activate`

3. **"Connection timeout" or network errors**:
   - Check internet connectivity
   - Verify Groq API is accessible from your network
   - Check if you have reached Groq's free tier limits

4. **"Model not found" errors**:
   - Verify the model names in `config.py` match current Groq offerings
   - Check [console.groq.com](https://console.groq.com) for available models

5. **"Unauthorized" or API key errors**:
   - Ensure your Groq API key is valid and not expired
   - Check that you have access to the models specified in config.py

## Web UI

A stunning **Matrix-inspired web interface** is available in the `ui/` folder:

```bash
cd ui
start index.html  # Or open in any browser
```

**Features**:
- Matrix digital rain background
- Cyberpunk/futuristic aesthetic  
- Live price intelligence dashboard
- AI recommendation engine
- Competitor network monitoring
- Interactive charts and analytics
- Real-time search and filtering

See [ui/README.md](ui/README.md) for complete UI documentation.

## Architecture Documentation

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed agent specifications, tool interfaces, and system contracts.

See [SCHEMA.md](SCHEMA.md) for complete database schema documentation.