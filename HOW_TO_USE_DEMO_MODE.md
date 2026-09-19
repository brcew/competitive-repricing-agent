# 🚀 How to Use Demo Mode

Demo mode accelerates your competitive pricing agent system by **60× faster** for rapid testing and demonstrations.

---

## 📊 What is Demo Mode?

### Normal Production Timing
- **Worker Agents**: Run every **15 minutes** per SKU
- **Orchestrator Agent**: Runs every **60 minutes**
- **Full Cycle**: Takes ~1 hour to see complete system behavior

### Demo Mode Timing (60× Faster!)
- **Worker Agents**: Run every **15 seconds** per SKU ⚡
- **Orchestrator Agent**: Runs every **60 seconds** ⚡
- **Full Cycle**: Complete in ~5-10 minutes!

**All safety checks remain active** (margin floor, budget guard, rate limits)

---

## 🎯 When to Use Demo Mode

### ✅ Use Demo Mode For:
- Quick system demonstrations
- Testing changes rapidly
- Showing to recruiters/professors
- Creating demo videos
- Portfolio walkthroughs
- Debugging issues quickly

### ❌ Don't Use Demo Mode For:
- Actual production deployment
- Real pricing decisions
- Long-term monitoring
- Performance benchmarking

---

---

## 🌐 Interactive Web Demo Simulator (NEW!)

**Want to see the demo without running Python?** The web dashboard now includes an interactive simulator!

### Quick Access:
```bash
cd ui
npm run dev
# Open http://localhost:5173
# Scroll to "Live Demo Simulator"
# Click "Start Demo"
```

### Features:
- ✅ Visual timer and countdowns
- ✅ Live decision stream (updates every 15 seconds)
- ✅ Orchestrator alerts (every 60 seconds)
- ✅ Override examples highlighted
- ✅ Play/Pause/Reset controls
- ✅ Works in browser (no Python needed)

**Perfect for portfolio demos!** Read full guide: `ui/WEB_DEMO_GUIDE.md`

---

## 🔧 Python Backend Demo Mode

For running the actual system with real API calls and database updates:

## 🔧 Method 1: Using run_demo.py (Easiest)

### Step 1: Make sure you're in the project root
```bash
cd d:\Shahul\Mars\Shahul_projects\competitive-repricing-agent
```

### Step 2: Run the demo script
```bash
python run_demo.py
```

That's it! The system is now running in demo mode.

### What You'll See:
```
========================================
DEMO MODE ENABLED
========================================
Worker interval: 15 seconds (vs 15 minutes)
Orchestrator interval: 60 seconds (vs 60 minutes)
Speedup: 60× faster
========================================

Starting competitive pricing agent...
Budget: 0/14400 calls used (0.0%)
Watchlist: 0 SKUs active

[60s later]
Orchestrator cycle completed - Added 15 SKUs to watchlist

[15s later]
Worker cycle 1/15 - SKU LAP-0042: MATCH at $1199.99

[15s later]
Worker cycle 2/15 - SKU MOU-0156: UNDERCUT_50 at $42.49

...and so on every 15 seconds!
```

---

## 🔧 Method 2: Environment Variable

### Step 1: Set the environment variable

**Windows CMD:**
```cmd
set DEMO_MODE=true
python main.py
```

**Windows PowerShell:**
```powershell
$env:DEMO_MODE="true"
python main.py
```

**Git Bash / WSL:**
```bash
export DEMO_MODE=true
python main.py
```

### Step 2: The system runs in demo mode!

---

## 🔧 Method 3: Edit .env File (Permanent)

### Step 1: Open your .env file
```bash
notepad .env
```

### Step 2: Add this line
```
DEMO_MODE=true
```

### Step 3: Save and run normally
```bash
python main.py
```

### To disable later:
Change to `DEMO_MODE=false` or remove the line entirely.

---

## 📝 Complete Example

Here's a full walkthrough:

### 1. Open Terminal
```bash
cd d:\Shahul\Mars\Shahul_projects\competitive-repricing-agent
```

### 2. Check Your Setup
```bash
python validate_setup.py
```

You should see:
```
✓ Environment file exists
✓ GROQ_API_KEY is set
✓ Database is accessible
✓ Groq API is reachable
✓ All models are available
```

### 3. Run Demo Mode
```bash
python run_demo.py
```

### 4. Watch It Work

**Minute 0:00** - System starts
```
Starting competitive pricing agent...
Budget: 0/14400 calls used
```

**Minute 1:00** - Orchestrator runs (first time)
```
[Orchestrator] Analyzing 800 SKUs...
[Orchestrator] Added 15 SKUs to watchlist:
  - LAP-0042 (low margin: 13.5%)
  - MOU-0156 (competitor undercut)
  - KEY-0089 (declining conversion)
  ...
```

**Minute 1:15** - First worker run
```
[Worker] Processing LAP-0042...
  Our price: $1249.99
  Competitor: $1199.99
  Action: MATCH
  New price: $1199.99
  Margin: 14.2% ✓ PASSED
```

**Minute 1:30** - Second worker run
```
[Worker] Processing MOU-0156...
  Our price: $45.99
  Competitor: $42.99
  Action: UNDERCUT_50
  New price: $42.49
  Margin: 13.8% ✓ PASSED
```

**Minute 1:45** - Third worker run (override example!)
```
[Worker] Processing KEY-0089...
  Our price: $89.99
  Competitor: $79.99
  Action: MATCH (suggested by LLM)
  New price: $79.99
  Margin: 11.3% ✗ FAILED
  [OVERRIDE] Changed to HOLD - Margin below 12% floor
```

**Minute 2:00** - Second orchestrator run
```
[Orchestrator] Analyzing watchlist...
[Orchestrator] Removed 2 SKUs (stable prices)
[Orchestrator] Added 1 new SKU (new competitor activity)
[Orchestrator] Watchlist now: 14 SKUs
```

And it continues every 15 seconds (workers) and 60 seconds (orchestrator)!

---

## 📊 What to Monitor

### In the Terminal Output
Watch for these key events:

1. **Orchestrator Decisions**
   - Which SKUs added to watchlist
   - Which SKUs removed
   - Reasoning for changes

2. **Worker Decisions**
   - Pricing actions (MATCH, UNDERCUT_50, HOLD)
   - Margin check results
   - **Override examples** (when margin check rejects LLM)

3. **Budget Tracking**
   - API calls used
   - Percentage of daily limit
   - Warnings at 80%

4. **Safety Events**
   - Margin violations prevented
   - Budget limits enforced
   - Rate limit adaptations

### In the Database
You can inspect the database while it's running:

```bash
python inspect_data.py
```

Or for local SQLite:
```bash
python inspect_data_local.py
```

---

## ⏱️ Expected Timeline

### Demo Mode (Fast)
- **0:00** - System starts
- **1:00** - Orchestrator adds SKUs to watchlist
- **1:15** - First pricing decision
- **1:30** - Second pricing decision
- **2:00** - Orchestrator reviews watchlist
- **5:00** - ~20 pricing decisions completed
- **10:00** - Full system behavior visible

### Production Mode (Normal)
- **0:00** - System starts
- **60:00** - Orchestrator adds SKUs to watchlist
- **75:00** - First pricing decision
- **90:00** - Second pricing decision
- **120:00** - Orchestrator reviews watchlist
- **5 hours** - ~20 pricing decisions completed
- **24 hours** - Full system behavior visible

**Demo mode lets you see in 10 minutes what would take hours in production!**

---

## 🛑 How to Stop Demo Mode

### Press Ctrl+C in the terminal:
```
^C
Received shutdown signal...
Shutting down gracefully...
✓ Workers stopped
✓ Orchestrator stopped
✓ Database connections closed
✓ Logs flushed
Goodbye!
```

The system shuts down cleanly.

---

## 📸 Recording a Demo

Perfect for portfolio videos!

### Step 1: Start Screen Recording
Use OBS, ShareX, or Windows Game Bar (Win+G)

### Step 2: Open Two Windows
- **Left**: Terminal running `python run_demo.py`
- **Right**: Dashboard at `http://localhost:5173`

### Step 3: Narrate While It Runs
```
"Here you can see the orchestrator selecting 15 high-priority SKUs...
Now the workers are making pricing decisions every 15 seconds...
Watch here - the LLM suggested $79.99 but the margin checker rejected it...
The system automatically overrode to HOLD to protect the 12% margin floor..."
```

### Step 4: Stop After 5-10 Minutes
You'll have shown the complete system cycle!

---

## 🔍 Troubleshooting Demo Mode

### Problem: "DEMO_MODE environment variable not found"
**Solution**: The system defaults to production mode. This is fine - just use Method 1 (`python run_demo.py`)

### Problem: "Workers running too fast - hitting rate limits"
**Solution**: This shouldn't happen with 15 SKU watchlist, but if it does:
```bash
# In .env, add:
WATCHLIST_CAP=10
```

### Problem: "Budget exhausted too quickly"
**Solution**: Demo mode uses the same budget as production (14,400 calls/day). If you hit the limit:
- Wait for midnight UTC (budget resets)
- Or reduce watchlist cap
- Or use fewer demo runs per day

### Problem: "Not seeing any activity"
**Solution**: 
1. Check that SKUs are seeded: `python -c "from db_utils import get_session; print(len(list(get_session().execute('SELECT * FROM skus'))))"`
2. Check that competitor prices exist: `python inspect_data_local.py`
3. Verify Groq API key is set: `python validate_setup.py`

---

## 💡 Pro Tips

### Tip 1: Use for Interviews
> "Let me show you the system in action. I've enabled demo mode which runs 60× faster..."

### Tip 2: Create Test Scenarios
Before running demo mode, manually set up interesting scenarios:
```python
# Create a SKU that will definitely violate margin
python -c "from db_utils import *; update_sku_price('KEY-0089', 89.99, cost=80.00)"
```

### Tip 3: Monitor Logs
Save logs to a file for later review:
```bash
python run_demo.py > demo_log.txt 2>&1
```

### Tip 4: Side-by-Side Comparison
Run production and demo mode in separate terminals to show the speed difference!

---

## 📋 Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    DEMO MODE QUICK REF                      │
├─────────────────────────────────────────────────────────────┤
│ FASTEST:        python run_demo.py                         │
│ WITH ENV:       set DEMO_MODE=true & python main.py        │
│ PERMANENT:      Add DEMO_MODE=true to .env file            │
│                                                             │
│ TIMING:         15 sec (workers) / 60 sec (orchestrator)   │
│ SPEEDUP:        60× faster than production                 │
│ SAFETY:         All checks remain active                   │
│                                                             │
│ STOP:           Press Ctrl+C                               │
│ INSPECT:        python inspect_data_local.py               │
│ VALIDATE:       python validate_setup.py                   │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Checklist Before Running Demo

- [ ] Groq API key is set in `.env`
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Database is initialized (happens automatically on first run)
- [ ] SKUs are seeded (800 products - happens automatically)
- [ ] Port 5173 is free (for dashboard, if using)
- [ ] You have 5-10 minutes to watch it run

**Ready? Run `python run_demo.py` and enjoy the show!** 🚀

---

**Questions?** Email: urs.shahulsk@gmail.com  
**GitHub**: https://github.com/brcew
