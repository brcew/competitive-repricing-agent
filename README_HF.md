---
title: Competitive Pricing Agent
emoji: 🤖💰
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# 🤖 Competitive Pricing Multi-Agent System

A two-tier AI agent system for automated competitive pricing decisions, demonstrating production-ready AI engineering patterns.

## 🎯 Key Features

- **60% Cost Savings**: Two-tier architecture (70B for strategy, 8B for execution)
- **Deterministic Safety**: 12% margin floor enforced in Python (never violated by LLM)
- **Production Patterns**: Rate limiting, budget guards, audit trails
- **107 Tests**: Comprehensive test coverage with zero API cost

## 🏗️ Architecture

```
Orchestrator Agent (llama-3.3-70b) → Strategic Decisions (hourly)
    ↓
Worker Agents (llama-3.1-8b) → Pricing Decisions (15min/SKU)
    ↓
Margin Safety Checker (Python) → 12% floor enforcement
    ↓
Execute or HOLD → Database + Audit Trail
```

## 🛡️ Safety Mechanisms

1. **Margin Floor**: Hard-coded 12% minimum (LLM cannot override)
2. **Gap Threshold**: Only reprices if gap > 5%
3. **Budget Guard**: Stops before hitting API limits
4. **Rate Limiter**: Adapts to API capacity

## 📊 Demo

This Space demonstrates:
- Real-time pricing decisions
- Margin safety enforcement
- System statistics dashboard
- Decision audit trail

## 🔗 Links

- [GitHub Repository](https://github.com/yourusername/competitive-repricing-agent)
- [Full Documentation](https://github.com/yourusername/competitive-repricing-agent#readme)

## ⚙️ Configuration

This demo uses simulated competitor prices. For production use:
1. Replace simulator with real competitor data
2. Connect to production database
3. Set up proper API rate limits
4. Implement approval workflows
