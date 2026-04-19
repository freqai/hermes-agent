# Self-Evolving Trading Agent

A multi-modal AI trading agent that evolves strategies based on K-line pattern recognition using MLLM (Multi-Modal Large Language Models).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    TradingAgent (main.py)                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Data Hunter  │  │ Multi-Agent  │  │   Strategy   │       │
│  │              │  │   System     │  │   Manager    │       │
│  │ - 波动监控    │  │ - Visual     │  │ - 策略存储    │       │
│  │ - K 线捕获     │←→│   Judge      │←→│ - 进化逻辑    │       │
│  │ - 快照生成    │  │ - Evolution  │  │ - 生命周期    │       │
│  └──────────────┘  │   Architect  │  └──────────────┘       │
│                    └──────────────┘                          │
└─────────────────────────────────────────────────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────────┐
│  Candidates DB  │    │  Strategies Store   │
│  data/candidates│    │  strategies/        │
│  - K 线图 PNG     │    │  - base_pattern.png │
│  - 元数据 JSON    │    │  - manifest.json    │
└─────────────────┘    └─────────────────────┘
```

## Core Features

### 🎯 Event-Driven Evolution
- **Trigger**: Volatility > 20% (configurable)
- **Not time-based**: Only evolves when meaningful market events occur
- **Efficient**: No unnecessary API calls or computations

### 👁️ MLLM-Powered Pattern Recognition
- **VisualJudge**: Compares current K-line with strategy patterns
- **EvolutionArchitect**: Analyzes failures and selects new base patterns
- **No vector embeddings**: Pure visual reasoning via GPT-4o

### 🧬 Self-Evolution Mechanism
```
Performance Tracking → Failure Detection → Pattern Selection → Strategy Update
     ↓                      ↓                    ↓                  ↓
Last 10 trades        ≥4 failures         MLLM analysis       Replace base image
```

### 📊 Strategy Storage Format
```
strategies/
└── event_20231027_143022_1/
    ├── base_pattern.png    # K-line pattern image
    ├── manifest.json       # Strategy params + performance log
    └── (optional files)
```

## Installation

```bash
cd trading-agent
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
```

## Usage

### 1. Capture Volatility Events (Hunter Mode)
```bash
# Run in background to continuously capture volatility events
python agents/hunter_agent.py
```

This monitors the market and saves K-line snapshots before significant price movements.

### 2. Initialize Strategy from Captured Pattern
```bash
# List available candidates
python main.py --mode init --candidate event_20231027_143022_1

# Or specify custom parameters
python main.py --mode init \
  --candidate event_20231027_143022_1 \
  --symbol BTC/USDT \
  --threshold 0.25
```

### 3. Run Trading Monitor
```bash
# Continuous monitoring with auto-evolution
python main.py --mode monitor \
  --symbol BTC/USDT \
  --threshold 0.20
```

### 4. Manual Operations
```bash
# Scan current market against all strategies
python main.py --mode scan

# Force evolution check
python main.py --mode evolve
```

## Configuration

Edit `config.py` or use environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key for MLLM |
| `VOLATILITY_THRESHOLD` | 0.20 | Trigger volatility (20%) |
| `EVOLUTION_WINDOW` | 10 | Check last N trades |
| `FAILURE_THRESHOLD` | 4 | Failures before evolution |
| `SIMILARITY_THRESHOLD` | 0.85 | MLLM match confidence |
| `TIMEFRAME` | "1h" | K-line timeframe |
| `LOOKBACK_BARS` | 50 | Bars per chart |
| `EXCHANGE_ID` | "binance" | Exchange to use |
| `SYMBOL` | "BTC/USDT" | Trading pair |

## How Evolution Works

### Step 1: Capture Candidate Patterns
When price moves >20%, the Hunter captures the K-line pattern **before** the move.

### Step 2: Create Initial Strategy
```bash
python main.py --mode init --candidate <event_id>
```
This creates a strategy with:
- Base pattern image
- Entry/exit parameters
- Empty performance log

### Step 3: Live Monitoring
Every cycle:
1. Fetch current K-line chart
2. VisualJudge compares with all strategy patterns
3. If match > threshold → Execute trade signal
4. Record outcome (success/missed)

### Step 4: Automatic Evolution
When a strategy has ≥4 failures in last 10 opportunities:
1. EvolutionArchitect analyzes failed cases
2. Compares candidate patterns from recent events
3. Selects best replacement pattern
4. Updates strategy's base image
5. Resets performance tracking

## Project Structure

```
trading-agent/
├── config.py                 # Configuration
├── main.py                   # Main orchestrator
├── requirements.txt          # Dependencies
├── README.md                # This file
├── agents/
│   ├── hunter_agent.py      # Volatility capture
│   └── multi_agent_system.py # MLLM agents
├── core/
│   └── strategy_manager.py  # Strategy lifecycle
├── data/
│   └── candidates/          # Captured patterns
└── strategies/              # Active strategies
```

## Example Strategy Manifest

```json
{
  "strategy_id": "event_20231027_143022_1",
  "created_at": "2024-01-15T10:30:00",
  "base_chart_path": "strategies/event_20231027_143022_1/base_pattern.png",
  "params": {
    "entry_condition": "Visual pattern match > 0.85",
    "position_size": 0.1,
    "stop_loss": 0.05,
    "take_profit": 0.20
  },
  "performance": {
    "total_trades": 15,
    "successful_captures": 11,
    "missed_opportunities": 4,
    "last_10_results": [...]
  },
  "evolution_history": []
}
```

## Advantages Over Traditional Approaches

| Feature | This Agent | Traditional ML |
|---------|-----------|----------------|
| **Pattern Recognition** | MLLM visual reasoning | Technical indicators |
| **Strategy Storage** | Images + JSON | Code + weights |
| **Evolution Trigger** | Performance-based | Scheduled retraining |
| **Interpretability** | Fully visual | Black box |
| **Adaptation Speed** | Immediate | Days/weeks |
| **Infrastructure** | Minimal | GPU clusters |

## Warnings

⚠️ **This is experimental software**. Do not use with real money without:
- Extensive backtesting
- Paper trading validation
- Risk management overlays
- Understanding of the code

⚠️ **MLLM Limitations**:
- Model hallucinations possible
- Image consistency critical
- API rate limits apply
- Token costs accumulate

## License

MIT
