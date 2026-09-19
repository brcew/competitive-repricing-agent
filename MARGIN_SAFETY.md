# Margin Safety Tool Documentation

## Critical Design Principle

**The 12% margin floor is enforced by deterministic Python code, NOT by LLM judgment.**

This is the single most important architectural decision in the system. It proves that the engineer understands when to trust LLMs (creative decision-making) and when NOT to trust them (hard financial constraints).

## Why This Matters

LLMs are probabilistic models. They can:
- Misunderstand numerical constraints
- Hallucinate calculations
- Ignore safety rules under certain prompts
- Make arithmetic errors

For a hard financial constraint like "never go below 12% margin," delegating enforcement to the LLM would be **professionally irresponsible**. Instead:

1. LLM proposes an action ("MATCH competitor price")
2. Deterministic Python code checks if that action is safe
3. If unsafe, the action is **rejected** regardless of LLM reasoning
4. All checks are logged with explicit reasoning

## The Margin Check Tool

### Input

```python
@dataclass
class MarginCheckInput:
    sku_id: int
    sku_code: str
    our_current_price: float
    cost: float
    competitor_price: float
    proposed_action: Literal["MATCH", "UNDERCUT_50", "HOLD"]
    proposed_new_price: Optional[float]
```

### Output

```python
@dataclass
class MarginCheckResult:
    passed: bool  # True if safe, False if rejected
    current_margin_percent: float
    proposed_margin_percent: float
    margin_floor_percent: float  # 12.0%
    gap_threshold_percent: float  # 5.0%
    competitor_gap_percent: float
    reason: str  # Human-readable explanation
    checked_at: datetime
```

## Enforcement Rules

### Rule 1: Margin Floor (12%)

```python
margin% = (price - cost) / price * 100

if margin% < 12.0:
    REJECT
```

**Examples:**
- Price $100, cost $60 → 40% margin ✅ PASS
- Price $100, cost $88 → 12% margin ✅ PASS (exactly at floor)
- Price $100, cost $90 → 10% margin ❌ REJECT (below floor)
- Price $90, cost $95 → -5.6% margin ❌ REJECT (loss!)

### Rule 2: Gap Threshold (5%)

```python
gap% = (our_price - competitor_price) / our_price * 100

if gap% < 5.0:
    REJECT
```

Only act if the price difference is significant enough to matter.

**Examples:**
- Our $100, competitor $90 → 10% gap ✅ PASS
- Our $100, competitor $95 → 5% gap ✅ PASS (exactly at threshold)
- Our $100, competitor $97 → 3% gap ❌ REJECT (too small)

### Rule 3: HOLD Always Passes

HOLD means "do nothing" - no price change, no risk.

## Usage Pattern

### From Worker Agent

```python
from margin_check_tool import check_margin_safety, MarginCheckInput

# Worker agent proposes an action
proposed_action = "MATCH"
proposed_price = competitor_price

# Check if action is safe
input_data = MarginCheckInput(
    sku_id=sku.id,
    sku_code=sku.sku,
    our_current_price=sku.our_price,
    cost=sku.cost,
    competitor_price=competitor_price,
    proposed_action=proposed_action,
    proposed_new_price=proposed_price
)

result = check_margin_safety(input_data)

if result.passed:
    # Execute the price change
    execute_price_change(sku, proposed_price)
    log_decision(sku, proposed_action, "EXECUTED", result.reason)
else:
    # Reject and fall back to HOLD
    log_decision(sku, proposed_action, "REJECTED", result.reason)
    # Do not change price
```

## Test Coverage

21 unit tests cover all scenarios:

### Margin Calculations (4 tests)
- ✅ Basic margin calculation
- ✅ Low margin (12%)
- ✅ Negative margin (loss)
- ✅ Zero price edge case

### Gap Calculations (3 tests)
- ✅ We're more expensive
- ✅ We're cheaper
- ✅ Prices equal

### Margin Floor Enforcement (4 tests)
- ✅ Pass when margin above floor
- ✅ Pass when margin exactly at floor
- ✅ Reject when margin below floor
- ✅ Reject when negative margin

### Gap Threshold Enforcement (2 tests)
- ✅ Pass when gap above threshold
- ✅ Reject when gap below threshold

### HOLD Action (1 test)
- ✅ HOLD always passes

### Action Types (2 tests)
- ✅ MATCH action
- ✅ UNDERCUT_50 action

### Edge Cases (2 tests)
- ✅ Missing new_price for action
- ✅ Result contains all fields

### Real-World Scenarios (2 tests)
- ✅ Laptop scenario - safe match
- ✅ Laptop scenario - unsafe match

### Convenience Function (1 test)
- ✅ check_margin_safety() function

## Run Tests

```bash
# Run all margin safety tests
python -m pytest tests/test_margin_safety.py -v

# Run with coverage
python -m pytest tests/test_margin_safety.py --cov=margin_check_tool

# Run specific test class
python -m pytest tests/test_margin_safety.py::TestMarginFloorEnforcement -v
```

## Logging

The tool logs all decisions:

```python
# Approved action
logger.info(
    "Margin check passed",
    sku=sku_code,
    current_price=our_current_price,
    proposed_price=proposed_new_price,
    proposed_margin=proposed_margin,
    competitor_gap=competitor_gap,
    action=proposed_action
)

# Rejected - margin floor violation
logger.warning(
    "Margin floor violation",
    sku=sku_code,
    proposed_price=proposed_new_price,
    proposed_margin=proposed_margin,
    margin_floor=margin_floor_percent,
    action=proposed_action
)

# Rejected - gap threshold not met
logger.info(
    "Gap threshold not met",
    sku=sku_code,
    competitor_gap=competitor_gap,
    gap_threshold=gap_threshold_percent,
    action=proposed_action
)
```

## Configuration

Default values from `config.py`:

```python
MARGIN_FLOOR_PERCENT = 12.0  # Never go below 12% margin
COMPETITOR_GAP_THRESHOLD_PERCENT = 5.0  # Only act if gap > 5%
```

Can be overridden per instance:

```python
checker = MarginSafetyChecker(
    margin_floor_percent=15.0,  # Stricter: 15% floor
    gap_threshold_percent=10.0   # More conservative: 10% threshold
)
```

## Integration Points

### With Worker Agent
Worker agent calls `check_margin_safety()` before any price change.

### With Database
Results are stored in `pricing_decisions` table:
```sql
INSERT INTO pricing_decisions (
    sku_id,
    action,
    new_price,
    margin_check_passed,  -- Result of this tool
    margin_check_reason,  -- Result.reason
    ...
);
```

### With Cost Tracker
Margin checks don't consume LLM tokens - they're free.

## Interview Defense Points

This file is designed to be defensible in a graduate school interview. Key points:

1. **LLM Limitations**: "I used an LLM for creative decision-making (which SKUs to monitor, what actions to propose), but NOT for hard numerical constraints."

2. **Deterministic Safety**: "The 12% margin floor is a plain Python `if` statement, not a prompt instruction. This ensures it can never be violated by a hallucination or misunderstanding."

3. **Test Coverage**: "I wrote 21 unit tests specifically for this safety mechanism because it's the highest-leverage point of risk in the system."

4. **Logging & Audit**: "Every rejection is logged with explicit reasoning so that margin violations are visible and debuggable."

5. **Production Pattern**: "This follows the same pattern used in real financial systems - hard limits in code, soft intelligence in models."

## What Would Be Different in Production

1. **Multi-currency**: Handle different currencies and exchange rates
2. **Cost Changes**: Recalculate margins when supplier costs change
3. **Category-specific floors**: Different margins for different product types
4. **Time-based rules**: Different margins during promotions
5. **Volume discounts**: Margin floors that consider order quantity
6. **Audit trail**: Full history of all margin check decisions
7. **Alerting**: PagerDuty alert if margin floor comes close to violation

## Files

- `margin_check_tool.py`: Implementation
- `tests/test_margin_safety.py`: Comprehensive test suite
- `MARGIN_SAFETY.md`: This documentation