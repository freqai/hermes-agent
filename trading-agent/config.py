"""
Trading Agent Configuration
"""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Trading Settings
    VOLATILITY_THRESHOLD: float = 0.20  # 20% volatility trigger
    EVOLUTION_WINDOW: int = 10  # Check evolution every N trades
    FAILURE_THRESHOLD: int = 4  # Failures before evolution triggers
    SIMILARITY_THRESHOLD: float = 0.85  # MLLM similarity threshold for execution
    
    # Data Settings
    TIMEFRAME: str = "1h"
    LOOKBACK_BARS: int = 50  # Number of K-line bars to capture
    
    # Storage
    STRATEGIES_DIR: str = "./strategies"
    DATA_DIR: str = "./data"
    
    # Exchange
    EXCHANGE_ID: str = "binance"
    SYMBOL: str = "BTC/USDT"
    
    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
            VOLATILITY_THRESHOLD=float(os.getenv("VOLATILITY_THRESHOLD", "0.20")),
            EVOLUTION_WINDOW=int(os.getenv("EVOLUTION_WINDOW", "10")),
            FAILURE_THRESHOLD=int(os.getenv("FAILURE_THRESHOLD", "4")),
            SIMILARITY_THRESHOLD=float(os.getenv("SIMILARITY_THRESHOLD", "0.85")),
            TIMEFRAME=os.getenv("TIMEFRAME", "1h"),
            LOOKBACK_BARS=int(os.getenv("LOOKBACK_BARS", "50")),
            EXCHANGE_ID=os.getenv("EXCHANGE_ID", "binance"),
            SYMBOL=os.getenv("SYMBOL", "BTC/USDT"),
        )
