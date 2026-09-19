# 🚀 Quick Start Guide - Competitive Pricing Agent

## 📋 What You Need Before Starting

- [ ] Python 3.11 or higher installed
- [ ] Git installed (for GitHub)
- [ ] A free Groq API key from [console.groq.com](https://console.groq.com)
- [ ] 10 minutes of your time

## 🎯 Step-by-Step: Run the Program

### Step 1: Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed groq-0.x.x sqlalchemy-2.x.x ...
```

---

### Step 2: Configure Your API Key

```bash
# Copy the example environment file
copy .env.example .env    # Windows
# OR
cp .env.example .env      # Mac/Linux
```

**Then edit `.env` file** and replace `your_groq_api_key_here` with your actual key:

```env
GROQ_API_KEY=gsk_abc123xyz...your_actual_key_here
```

⚠️ **Important**: Never commit the `.env` file to Git! It contains your secret API key.

---

### Step 3: Run in Demo Mode (Fastest Way to See It Work!)

```bash
python run_demo.py
```

**What you'll see:**

```
╔══════════════════════════════════════════════════════════════╗
║       Competitive Pricing Agent - DEMO MODE                 ║
║  Compressed timing: 15 sec workers, 60 sec orchestrator    ║
╚══════════════════════════════════════════════════════════════╝

[2024-01-15 10:30:00] [info] Initializing database...
[2024-01-15 10:30:01] [info] Seeding 20 sample SKUs...
[2024-01-15 10:30:02] [info] System started successfully!
[2024-01-15 10:30:02] [info] Press Ctrl+C to stop

[2024-01-15 10:30:15] [info] 🤖 Orchestrator analyzing market...
[2024-01-15 10:30:18] [info] ✅ Watchlist updated: 12 SKUs selected
[2024-01-15 10:30:30] [info] 👷 Worker processing: WIDGET-001
[2024-01-15 10:30:32] [info] 💰 Decision: MATCH at $29.99 (margin: 15%)
[2024-01-15 10:30:45] [info] 👷 Worker processing: GADGET-005
[2024-01-15 10:30:47] [info] 💰 Decision: HOLD at $49.99 (margin safe)
...
```

**Demo mode runs for 5-10 minutes to show you a complete cycle.** Press `Ctrl+C` when you want to stop.

---

### Step 4: View the Results

#### Option A: Check the Database

```bash
python show_samples.py
```

Shows recent pricing decisions with timestamps and rationale.

#### Option B: View the Web UI

```bash
cd ui
start index.html    # Windows
# OR
open index.html     # Mac
```

You'll see a Matrix-inspired dashboard with:
- Live pricing intelligence
- Agent recommendations
- Market trends
- Competitor analysis

---

### Step 5: Run Integration Tests (Optional but Recommended)

```bash
python run_integration_test.py
```

This validates:
- ✓ API connectivity
- ✓ Budget guard works
- ✓ Rate limiting active
- ✓ Margin safety enforced
- ✓ Orchestrator logic
- ✓ Worker decision-making

**Expected output:**
```
Running integration tests...
✓ Budget guard initialized
✓ Rate limiter ready
✓ Orchestrator made valid decision
✓ Worker enforced 12% margin floor
✓ All 6 tests passed!
```

---

## 🐳 Alternative: Run with Docker (Production Mode)

If you have Docker installed:

```bash
# Start PostgreSQL + pricing agent
docker-compose up

# You'll see:
# - PostgreSQL starting on port 5432
# - Database initialization
# - Pricing agent connecting
# - Agent loops running

# Stop with:
docker-compose down
```

---

## 🎬 What Happens When It Runs?

### The System Architecture

```
┌─────────────────────────────────────────┐
│      ORCHESTRATOR (runs hourly)        │
│  - Analyzes all SKUs                    │
│  - Selects top 15 needing attention     │
│  - Updates watchlist                    │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│    WORKERS (run every 15 min per SKU)  │
│  - Compare competitor prices            │
│  - Decide: MATCH | UNDERCUT | HOLD      │
│  - Enforce 12% margin floor             │
│  - Update our price                     │
└─────────────────────────────────────────┘
```

### Demo Mode Timing

| Component    | Production | Demo Mode |
|--------------|------------|-----------|
| Orchestrator | 60 minutes | 60 seconds |
| Workers      | 15 minutes | 15 seconds |
| Purpose      | Real deployment | Testing & demos |

---

## ❓ Troubleshooting

### "ModuleNotFoundError: No module named 'groq'"

**Solution:**
```bash
pip install -r requirements.txt
```

---

### "GROQ_API_KEY not set"

**Solution:**
1. Verify `.env` file exists in project root
2. Open it and check `GROQ_API_KEY=...` is filled in
3. Make sure no extra spaces around the `=`

---

### "Rate limit exceeded" or API errors

**Solution:**
- You hit Groq's free tier limit (usually resets hourly)
- Wait 15-60 minutes and try again
- Check your usage at [console.groq.com](https://console.groq.com)

---

### "Nothing happens" / No output

**Solution:**
1. Check `.env` has `LOG_LEVEL=INFO`
2. Try demo mode: `DEMO_MODE=true` in `.env`
3. Run: `python run_demo.py` explicitly

---

### "Port 5432 already in use" (Docker mode)

**Solution:**
- Another PostgreSQL is running
- Stop it: `docker-compose down` or stop your local PostgreSQL
- Or change port in `docker-compose.yml`

---

## 🎯 Next Steps

1. ✅ Run the demo mode
2. ✅ Check the logs and understand agent decisions
3. ✅ Run integration tests
4. ✅ Explore the web UI
5. ✅ Read [ARCHITECTURE.md](ARCHITECTURE.md) for system details
6. ✅ Check [SCHEMA.md](SCHEMA.md) for database structure

---

## 🚀 Ready to Deploy?

See [README.md](README.md) for:
- Production deployment with Docker
- Environment configuration
- Monitoring and logging
- Scaling considerations

---

## 💡 Tips

- **Demo mode** is your friend for testing
- **Check logs** - they explain every decision
- **Margin floor (12%)** is hardcoded for safety - agents can't override it
- **Budget guard** prevents overspending on API calls
- **Rate limiter** protects against API throttling

---

## 📊 Understanding the Output

When you see:
```
[info] Worker processing: WIDGET-001
[info] Decision: MATCH at $29.99 (margin: 15%)
```

This means:
- ✅ Worker agent analyzed WIDGET-001
- ✅ Decided to match competitor price
- ✅ New price: $29.99
- ✅ Margin is safe at 15% (above 12% floor)
- ✅ Decision logged to database for audit

---

## 🎓 Learning Resources

- **System Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Database Schema**: [SCHEMA.md](SCHEMA.md)
- **Margin Safety**: [MARGIN_SAFETY.md](MARGIN_SAFETY.md)
- **Simulator Logic**: [SIMULATOR.md](SIMULATOR.md)
- **Web UI Guide**: [ui/README.md](ui/README.md)

---

**Questions?** Open an issue on GitHub!
