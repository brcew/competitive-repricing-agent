# Architecture Documentation

## System Overview

The Competitive Pricing Multi-Agent System is a two-tier AI architecture designed to optimize pricing decisions while maintaining strict cost efficiency and safety constraints.

### Core Principle

**LLMs for Intelligence, Code for Safety**

The system separates concerns:
- **LLMs provide**: Market analysis, strategic thinking, decision recommendations
- **Python enforces**: Financial constraints, rate limits, budget caps, data validation

This architectural pattern demonstrates understanding of when to trust LLMs and when **NOT** to trust them.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         USER / OPERATOR                              │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          MAIN COORDINATOR                            │
│                            (main.py)                                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  • Schedules orchestrator (hourly) and workers (15min)         │ │
│  │  • Monitors budget guard (stops at 14,350/14,400 calls)        │ │
│  │  • Tracks costs ($0.003/day with 60% savings vs single model)  │ │
│  │  • Manages rate limits and watchlist cap adaptation            │ │
│  │  • Generates audit trail logs for all decisions                │ │
│  └────────────────────────────────────────────────────────────────┘ │
└────────────┬──────────────────────────────────────┬──────────────────┘
             │                                      │
             ▼                                      ▼
┌────────────────────────────────┐  ┌────────────────────────────────┐
│   ORCHESTRATOR AGENT           │  │      WORKER AGENTS             │
│ (llama-3.3-70b-versatile)      │  │  (llama-3.1-8b-instant)        │
│                                │  │                                │
│ Cadence: Hourly (or 1min demo)│  │ Cadence: 15min/SKU (or 15s)    │
│ Cost: $0.59/$0.79 per 1M tokens│  │ Cost: $0.05/$0.08 per 1M tokens│
│                                │  │                                │
│ Responsibilities:              │  │ Responsibilities:              │
│ • Gather market intelligence   │  │ • Fetch competitor price       │
│ • Analyze conversion trends    │  │ • Analyze price gap            │
│ • Identify low-margin SKUs     │  │ • Propose action:              │
│ • Identify active competition  │  │   - MATCH (match competitor)   │
│ • Update watchlist (ADD/REMOVE)│  │   - UNDERCUT_50 (undercut $0.50)│
│ • Respect watchlist cap (code) │  │   - HOLD (no change)           │
│ • NEVER sets prices            │  │ • Submit to margin safety check│
│                                │  │ • Execute or HOLD if rejected  │
└────────────┬───────────────────┘  └───────────┬────────────────────┘
             │                                   │
             │                                   │
             └───────────────┬───────────────────┘
                             │
                             ▼
             ┌───────────────────────────────────┐
             │    DETERMINISTIC SAFETY LAYER     │
             ├───────────────────────────────────┤
             │ margin_check_tool.py              │
             │ • 12% margin floor (hard coded)   │
             │ • 5% gap threshold                │
             │ • Overrides LLM to HOLD if unsafe │
             │ • NEVER bypassed                  │
             ├───────────────────────────────────┤
             │ budget_guard.py                   │
             │ • Daily: 14,350/14,400 calls      │
             │ • Minute: 25/30 calls             │
             │ • Stops system before limit       │
             ├───────────────────────────────────┤
             │ rate_limit_tracker.py             │
             │ • Monitors RPM/TPM from headers   │
             │ • Calculates headroom percent     │
             │ • Shrinks watchlist cap if needed │
             └───────────────────────────────────┘
                             │
                             ▼
             ┌───────────────────────────────────┐
             │        DATA LAYER                 │
             ├───────────────────────────────────┤
             │ PostgreSQL (prod) / SQLite (dev)  │
             │                                   │
             │ Tables:                           │
             │ • skus (800 products)             │
             │ • watchlist (active monitoring)   │
             │ • competitor_prices (simulated)   │
             │ • conversion_metrics (7 days)     │
             │ • pricing_decisions (audit trail) │
             │ • orchestrator_runs (strategy log)│
             └───────────────────────────────────┘
```

## Component Details

### 1. Main Coordinator (`main.py`)

**Purpose**: Orchestrates the entire system lifecycle

**Responsibilities**:
- Schedule orchestrator agent (hourly or 1min in demo mode)
- Schedule worker agents (15min per SKU or 15sec in demo mode)
- Monitor budget guard before every API call
- Track costs and generate reports
- Handle rate limit feedback
- Manage graceful shutdown (SIGINT, SIGTERM)

**Key Methods**:
- `run_orchestrator_cycle()` - Executes orchestrator logic
- `run_worker_cycle()` - Processes all watchlist SKUs
- `_log_system_status()` - Comprehensive status reporting

**Configuration**:
```python
DEMO_MODE=false  # Production: 15min/60min intervals
DEMO_MODE=true   # Demo: 15sec/1min intervals (60x faster)
```

### 2. Orchestrator Agent (`orchestrator_agent.py`)

**Model**: `llama-3.3-70b-versatile` (large, expensive, smart)

**Cadence**: Hourly (or 1 minute in demo mode)

**Input**: System-wide intelligence
- Current watchlist size and SKUs
- SKUs with declining conversion rates
- SKUs with low margins (near floor)
- SKUs with active competitive pressure

**Output**: Watchlist changes
```
ADD: SKU-001, SKU-042, SKU-156
REMOVE: SKU-999, SKU-888
KEEP: 12 existing SKUs
```

**Safety**: Watchlist cap enforced in code (not LLM judgment)
```python
# LLM can suggest 20 additions
# Code enforces cap of 15 total
# Result: Only top 5 additions accepted
```

**Cost**: ~$0.000532 per call (800 tokens × 70B pricing)

### 3. Worker Agent (`worker_agent.py`)

**Model**: `llama-3.1-8b-instant` (small, cheap, frequent)

**Cadence**: Every 15 minutes per watchlist SKU

**Input**: Single SKU context
- Our current price
- Cost (for margin calculation)
- Competitor price
- Current margin percentage
- Price gap

**Output**: Pricing decision
```python
{
    "action": "MATCH" | "UNDERCUT_50" | "HOLD",
    "new_price": 94.99,  # or None for HOLD
    "reasoning": "Competitor undercut by $5, matching to stay competitive",
    "margin_check_passed": True,
    "tokens_used": 145
}
```

**Safety**: All decisions pass through `margin_check_tool`
```python
if not margin_check_passed:
    action = "HOLD"  # Override to safety
    new_price = None
    reasoning = "[OVERRIDDEN] " + original_reasoning
```

**Cost**: ~$0.000010 per call (150 tokens × 8B pricing)

### 4. Margin Safety Checker (`margin_check_tool.py`)

**Purpose**: THE MOST CRITICAL COMPONENT

This is where financial safety is enforced deterministically.

**Rules** (hard-coded, never bypassed):
1. **Margin Floor**: New price must maintain ≥12% margin
   ```
   margin = (price - cost) / price × 100
   if margin < 12.0:
       REJECT
   ```

2. **Gap Threshold**: Price change must be ≥5% gap from competitor
   ```
   gap = (our_price - competitor_price) / our_price × 100
   if abs(gap) < 5.0:
       REJECT
   ```

3. **HOLD Exemption**: HOLD actions always pass (no price change = no risk)

**Test Coverage**: 21 unit tests validate all scenarios

**Interview Defense**:
> "Every pricing decision, regardless of what the LLM suggests, passes through a deterministic Python margin checker. Even if the LLM proposes matching a competitor at $85, if that would violate the 12% margin floor, the system automatically overrides to HOLD. This separation of LLM intelligence from financial safety is the core architectural principle."

### 5. Budget Guard (`budget_guard.py`)

**Purpose**: Prevent exceeding Groq free tier limits

**Limits** (Groq Free Tier 2026):
- Daily: 14,400 requests per day (RPD)
- Minute: 30 requests per minute (RPM)

**Safety Buffers**:
- Stops at 14,350 daily (50-call buffer)
- Pauses at 25 per minute (5-call buffer)

**Behavior**:
```python
# At 11,520 calls (80%):
status = "WARNING"

# At 14,350 calls:
status = "EXHAUSTED"
can_make_call = False
# System stops gracefully
```

**Reset Logic**:
- Daily counter resets at midnight UTC
- Minute counter resets every 60 seconds

### 6. Rate Limit Tracker (`rate_limit_tracker.py`)

**Purpose**: Monitor API rate limits and adapt watchlist cap

**Data Source**: Groq API response headers
```
x-ratelimit-limit-requests: 30
x-ratelimit-remaining-requests: 18
x-ratelimit-limit-tokens: 12000
x-ratelimit-remaining-tokens: 8500
```

**Calculations**:
```python
# Headroom: How close are we to limits?
rpm_headroom = remaining / limit × 100
tpm_headroom = remaining / limit × 100
headroom = min(rpm_headroom, tpm_headroom)

# Watchlist cap adjustment
if headroom < 20%:
    new_cap = current_cap × 0.8  # Reduce by 20%
elif headroom > 50%:
    new_cap = current_cap + 1     # Conservative growth
```

**Result**: System automatically scales watchlist size based on API pressure

### 7. Cost Tracker (`cost_tracker.py`)

**Purpose**: Track and analyze API costs

**Groq Pricing (2026)**:
- Llama 3.1 8B: $0.05/$0.08 per 1M tokens (input/output)
- Llama 3.3 70B: $0.59/$0.79 per 1M tokens (input/output)

**Tracked Metrics**:
- Per-call costs (input + output tokens)
- Worker agent total costs
- Orchestrator agent total costs
- Daily/monthly projections
- Budget status (SAFE/WARNING/CRITICAL/EXHAUSTED)

**Cost Comparison** (see `cost_comparison.py`):
```
Two-Tier Approach:    $0.003167/day (actual)
Single Model (70B):   $0.007820/day (hypothetical)
Savings:              59.49% (cost efficiency)
```

### 8. Logging & Audit Trail (`logging_config.py`)

**Purpose**: Comprehensive structured logging

**Modes**:
- **Console**: Human-readable colored output for development
- **JSON**: Machine-readable for log aggregation (production)

**Audit Events Logged**:
1. **Pricing Decisions** - Every worker decision with full context
2. **Watchlist Changes** - Orchestrator add/remove actions
3. **Safety Violations** - Margin check failures
4. **Budget Warnings** - Threshold alerts
5. **Rate Limit Adaptations** - Cap adjustments
6. **System Cycles** - Aggregate metrics

**Benefits**:
- Compliance-ready audit trail
- Operational visibility
- Pattern analysis capability
- Debugging support

## Data Flow

### Orchestrator Flow

```
1. Gather Intelligence
   ├─ Query declining conversion SKUs
   ├─ Query low-margin SKUs
   └─ Query SKUs with active competition

2. Build Prompt
   ├─ Include current watchlist state
   ├─ Include intelligence data
   └─ Request ADD/REMOVE decisions

3. Call LLM (70B)
   ├─ Temperature: 0.4 (balanced)
   └─ Max tokens: 500

4. Parse Response
   ├─ Extract ADD list
   ├─ Extract REMOVE list
   └─ Extract reasoning

5. Enforce Cap (CODE)
   ├─ Calculate: current - removals + adds
   ├─ If > cap: trim additions
   └─ Log cap enforcement

6. Execute Changes
   ├─ Deactivate removed SKUs
   ├─ Activate added SKUs
   └─ Log to audit trail

7. Store Run Record
   ├─ Save to orchestrator_runs table
   ├─ Include rate limit context
   └─ Record token usage
```

### Worker Flow

```
1. Fetch Data
   ├─ Get SKU from database
   ├─ Fetch competitor price (simulator)
   └─ Calculate current margin

2. Check Competitor Status
   ├─ If unavailable: return HOLD
   └─ If available: continue

3. Build Prompt
   ├─ Include our price, cost, margin
   ├─ Include competitor price, gap
   └─ Request MATCH/UNDERCUT_50/HOLD decision

4. Call LLM (8B)
   ├─ Temperature: 0.3 (consistent)
   └─ Max tokens: 150

5. Parse Response
   ├─ Extract action
   ├─ Extract reasoning
   └─ Default to HOLD if malformed

6. Calculate New Price
   ├─ MATCH: price = competitor_price
   ├─ UNDERCUT_50: price = competitor_price - 0.50
   └─ HOLD: price = None

7. Margin Safety Check (CODE) ⭐ CRITICAL
   ├─ Calculate proposed margin
   ├─ Check: margin >= 12%?
   ├─ Check: gap >= 5%?
   └─ If fail: Override to HOLD

8. Store Decision
   ├─ Save to pricing_decisions table
   ├─ Include margin check result
   └─ Log to audit trail

9. Return Decision
   └─ Full context for coordinator
```

## Safety Architecture

### Layer 1: Input Validation

All inputs validated before processing:
- SKU exists in database
- Prices are positive numbers
- Cost < Price (basic sanity)

### Layer 2: LLM Decision

LLM analyzes and proposes action:
- Uses market intelligence
- Considers competitive position
- Suggests pricing strategy

**NOT TRUSTED FOR**: Financial constraints

### Layer 3: Deterministic Enforcement ⭐

Python code enforces hard constraints:
- Margin floor: 12% (NEVER violated)
- Gap threshold: 5% (NEVER violated)
- Watchlist cap: 15 SKUs (NEVER exceeded)
- Budget limits: 14,350 calls/day (NEVER exceeded)

**This is the "interview answer" layer**

### Layer 4: Audit Trail

All decisions logged:
- What LLM suggested
- What safety checks said
- What actually happened
- Why (if overridden)

## Error Handling

### Graceful Degradation

System defaults to HOLD on any failure:

```python
try:
    decision = llm_call()
except Exception:
    return HOLD  # Safe fallback

try:
    competitor_price = fetch_price()
except Exception:
    return HOLD  # Safe fallback

if margin_check_fails:
    return HOLD  # Safe override
```

**Philosophy**: Better to miss an opportunity than make a bad decision

### Error Scenarios

1. **Network Failure**: Return HOLD
2. **LLM Timeout**: Return HOLD  
3. **Malformed Response**: Return HOLD
4. **Database Error**: Log and skip cycle
5. **Budget Exhausted**: Stop system gracefully
6. **Rate Limit Hit**: Pause and retry

## Scaling Considerations

### Current Scale
- 800 SKUs in database
- 15 SKUs on active watchlist
- ~50 worker calls per hour
- ~1 orchestrator call per hour

### Scaling to 10,000 SKUs

**Challenges**:
1. Worker calls would scale linearly (10,000 × 4 per hour = 40,000 calls/day)
2. Exceeds free tier budget
3. Database queries need optimization
4. Async coordination becomes complex

**Solutions**:
1. **Task Queue**: Replace async loops with Celery/RQ
2. **Paid Tier**: Move to paid Groq tier or other providers
3. **Database**: Add indexes, query optimization, connection pooling
4. **Caching**: Cache competitor prices (reduce fetches)
5. **Smarter Watchlist**: More selective SKU monitoring

### What Changes at Scale

**Would Keep**:
- Two-tier architecture (cost-efficient)
- Margin safety checker (safety-critical)
- Audit trail (compliance)

**Would Change**:
- Async loops → Task queue (Celery)
- SQLite → PostgreSQL with replication
- Structured logging → APM integration (Datadog/NewRelic)
- Competitor simulator → Real scraper/data feed

## Testing Strategy

### Unit Tests (41 total)

**T16: Margin Safety (21 tests)**
- Margin calculations
- Floor enforcement
- Gap threshold
- Edge cases
- Real-world scenarios

**T17: Worker Agent (12 tests)**
- LLM response parsing
- Prompt building
- Decision flow
- Margin check override
- Error handling

**T18: Orchestrator (8 tests)**
- LLM response parsing
- Watchlist cap enforcement
- Prompt building
- Complete cycle
- Error handling

### Integration Tests

**No real API calls in tests** - All mocked

Benefits:
- Fast execution (< 15 seconds total)
- Zero cost
- Deterministic results
- CI/CD friendly

### Manual Testing

**Demo Mode**: 60x faster cycles for live demonstration
```bash
python run_demo.py
# Worker: 15 seconds (vs 15 min)
# Orchestrator: 1 minute (vs 60 min)
```

## Deployment

### Local Development

```bash
# SQLite, no Docker
python main.py
```

### Production (Docker)

```bash
# PostgreSQL via Docker Compose
docker-compose up
```

### Environment Variables

```bash
# Required
GROQ_API_KEY=your_key_here

# Optional (with defaults)
WATCHLIST_CAP=15
MARGIN_FLOOR_PERCENT=12
COMPETITOR_GAP_THRESHOLD_PERCENT=5
DEMO_MODE=false
LOG_LEVEL=INFO
STRUCTURED_LOGS=true
```

## Monitoring

### Metrics to Watch

1. **Budget Status**: Daily call count vs limit
2. **Cost Tracking**: Actual spend vs projections
3. **Rate Limit Headroom**: How close to API limits
4. **Watchlist Size**: Current vs cap
5. **Decision Distribution**: MATCH vs UNDERCUT vs HOLD percentages
6. **Safety Overrides**: How often margin check rejects LLM

### Health Indicators

**Healthy System**:
- Budget status: SAFE or WARNING
- Rate limit headroom: >20%
- Safety overrides: <5% of decisions
- Watchlist utilization: 80-100% of cap

**Unhealthy System**:
- Budget status: CRITICAL or EXHAUSTED
- Rate limit headroom: <10%
- Safety overrides: >20% (LLM suggesting unsafe actions)
- Watchlist utilization: 100% with many unmonitored high-priority SKUs

## Limitations

### Current Limitations

1. **Simulated Competitor Data**: Uses random walk + undercut simulator
2. **No Real Price Changes**: Decisions logged but not executed
3. **SQLite in Dev**: Single-writer limitation
4. **Free Tier Only**: Limited to 14,400 calls/day
5. **No A/B Testing**: Can't validate decision quality vs manual pricing
6. **Simple Scheduler**: Async loops instead of task queue

### Known Issues

1. **Deprecation Warnings**: Pydantic v2 Field syntax, datetime.utcnow()
2. **No Authentication**: API endpoints would need auth in production
3. **No Web UI**: Command-line only
4. **Limited Observability**: Logs only, no APM

### Future Enhancements

1. **Real Competitor Scraping**: Replace simulator with actual data
2. **Execution Layer**: Actually change prices (with approval workflow)
3. **Web Dashboard**: Monitor system state, view decisions, override
4. **A/B Testing**: Validate AI decisions vs human baseline
5. **Multi-Competitor Support**: Track multiple competitors per SKU
6. **ML Enhancements**: Learn optimal decision thresholds over time

## Portfolio Talking Points

### For Technical Interviews

> "I built a two-tier multi-agent system with a critical architectural principle: LLMs provide intelligence, Python enforces safety. Every pricing decision passes through a deterministic margin checker—21 unit tests validate this. Even if the LLM proposes a price change, if it violates the 12% margin floor, the system automatically overrides to HOLD."

### For Cost-Conscious Discussion

> "The two-tier architecture saves 60% on API costs compared to using only the large model. I track this with automated daily cost reports. The system runs entirely on Groq's free tier (14,400 calls/day) while maintaining production-grade safety and monitoring."

### For System Design

> "The architecture demonstrates several production patterns: rate limit adaptation, budget guards with safety buffers, graceful degradation to HOLD on any failure, comprehensive audit trails, and deterministic constraint enforcement. All 41 unit tests run without API calls—zero cost, deterministic, CI/CD ready."

### For Business/MBA Programs

> "The system automatically generates cost comparison reports showing 60% savings from smart architecture choices. At scale, this pattern could save tens of thousands monthly while maintaining decision quality. The key insight is using the right tool for each job—expensive models for strategy, cheap models for execution."

## References

- **SCHEMA.md**: Database design and query patterns
- **MARGIN_SAFETY.md**: Detailed margin safety specification
- **DEMO_MODE_GUIDE.md**: Demo mode usage guide
- **SIMULATOR.md**: Competitor price simulator details
- **T14_COMPLETION_SUMMARY.md**: Structured logging details
- **T15_COMPLETION_SUMMARY.md**: Cost comparison details

## Conclusion

This architecture demonstrates:
- ✅ **Cost-conscious AI design** (60% savings)
- ✅ **Safety-first engineering** (deterministic constraints)
- ✅ **Production-ready patterns** (rate limits, budgets, audit trails)
- ✅ **Testing discipline** (41 tests, zero API cost)
- ✅ **Clear separation of concerns** (LLM intelligence vs code safety)

**Perfect for graduate school portfolio (Oxford, ETH Zurich, UCL) - demonstrates both technical depth and business awareness.**
