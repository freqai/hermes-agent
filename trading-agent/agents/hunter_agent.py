"""
Data Hunter Agent - Captures K-line snapshots before significant volatility
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any
import ccxt
import pandas as pd
from PIL import Image
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from config import Config

class DataHunter:
    """Captures K-line data and images before volatility events"""
    
    def __init__(self, config: Config):
        self.config = config
        self.exchange = getattr(ccxt, config.EXCHANGE_ID)({
            'enableRateLimit': True,
        })
        self.candidate_dir = os.path.join(config.DATA_DIR, "candidates")
        os.makedirs(self.candidate_dir, exist_ok=True)
        
    def fetch_ohlcv(self, symbol: str = None, timeframe: str = None, limit: int = None) -> pd.DataFrame:
        """Fetch OHLCV data from exchange"""
        symbol = symbol or self.config.SYMBOL
        timeframe = timeframe or self.config.TIMEFRAME
        limit = limit or self.config.LOOKBACK_BARS + 10
        
        bars = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    
    def detect_volatility(self, df: pd.DataFrame, threshold: float = None) -> bool:
        """Detect if price movement exceeds threshold"""
        threshold = threshold or self.config.VOLATILITY_THRESHOLD
        if len(df) < 2:
            return False
        
        # Calculate price change from first to last bar
        price_change = abs(df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
        return price_change >= threshold
    
    def capture_snapshot(self, df: pd.DataFrame, event_id: str) -> Dict[str, Any]:
        """Capture K-line chart image and data before volatility"""
        # Use all bars except the last one (the volatility bar itself)
        pre_volatility_df = df.iloc[:-1].copy()
        
        # Create chart
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(pre_volatility_df['timestamp'], pre_volatility_df['close'], linewidth=2, color='blue')
        ax.fill_between(pre_volatility_df['timestamp'], 
                       pre_volatility_df['high'], 
                       pre_volatility_df['low'], 
                       alpha=0.3, color='gray')
        
        ax.set_title(f"K-Line Pattern Before Volatility Event", fontsize=14)
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save image
        img_path = os.path.join(self.candidate_dir, f"{event_id}_chart.png")
        fig.savefig(img_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        # Save raw data
        data_path = os.path.join(self.candidate_dir, f"{event_id}_data.csv")
        pre_volatility_df.to_csv(data_path, index=False)
        
        # Create metadata
        metadata = {
            "event_id": event_id,
            "timestamp": datetime.now().isoformat(),
            "symbol": self.config.SYMBOL,
            "timeframe": self.config.TIMEFRAME,
            "bars_count": len(pre_volatility_df),
            "price_start": float(pre_volatility_df['close'].iloc[0]),
            "price_end": float(pre_volatility_df['close'].iloc[-1]),
            "volatility_detected": True,
            "chart_path": img_path,
            "data_path": data_path
        }
        
        meta_path = os.path.join(self.candidate_dir, f"{event_id}_meta.json")
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return {
            "image_path": img_path,
            "data_path": data_path,
            "metadata": metadata
        }
    
    def get_candidates(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all captured candidate snapshots"""
        candidates = []
        for filename in os.listdir(self.candidate_dir):
            if filename.endswith("_meta.json"):
                meta_path = os.path.join(self.candidate_dir, filename)
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                
                # Load image to verify it exists
                img_path = metadata.get("chart_path")
                if img_path and os.path.exists(img_path):
                    candidates.append(metadata)
        
        # Sort by timestamp descending
        candidates.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return candidates[:limit]
    
    def monitor_and_capture(self, callback=None):
        """Continuously monitor for volatility and capture snapshots"""
        print(f"Starting volatility monitoring for {self.config.SYMBOL}...")
        event_count = 0
        
        while True:
            try:
                df = self.fetch_ohlcv()
                
                if self.detect_volatility(df):
                    event_count += 1
                    event_id = f"event_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{event_count}"
                    
                    print(f"\n🎯 Volatility detected! Capturing snapshot: {event_id}")
                    snapshot = self.capture_snapshot(df, event_id)
                    print(f"✅ Saved: {snapshot['image_path']}")
                    
                    if callback:
                        callback(snapshot)
                
                # Wait for next candle (simplified - in production use proper scheduling)
                import time
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"Error during monitoring: {e}")
                import time
                time.sleep(60)
