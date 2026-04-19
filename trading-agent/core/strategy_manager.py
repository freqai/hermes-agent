"""
Strategy Manager - Handles strategy storage, evolution logic, and lifecycle
"""
import os
import json
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import Config

class StrategyManager:
    """Manages strategy lifecycle: creation, storage, evolution, and deletion"""
    
    def __init__(self, config: Config):
        self.config = config
        self.strategies_dir = config.STRATEGIES_DIR
        os.makedirs(self.strategies_dir, exist_ok=True)
    
    def create_strategy(self, 
                       strategy_id: str,
                       base_chart_path: str,
                       params: Dict[str, Any],
                       metadata: Dict[str, Any] = None) -> Dict:
        """Create a new strategy from a captured pattern"""
        
        strategy_dir = os.path.join(self.strategies_dir, strategy_id)
        os.makedirs(strategy_dir, exist_ok=True)
        
        # Copy base chart to strategy directory
        chart_filename = "base_pattern.png"
        dest_chart_path = os.path.join(strategy_dir, chart_filename)
        shutil.copy2(base_chart_path, dest_chart_path)
        
        # Create strategy manifest
        manifest = {
            "strategy_id": strategy_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "base_chart_path": dest_chart_path,
            "params": {
                "entry_condition": params.get("entry_condition", "Pattern match > 0.85"),
                "position_size": params.get("position_size", 0.1),  # 10% of portfolio
                "stop_loss": params.get("stop_loss", 0.05),  # 5% stop loss
                "take_profit": params.get("take_profit", 0.20),  # 20% take profit
            },
            "performance": {
                "total_trades": 0,
                "successful_captures": 0,
                "missed_opportunities": 0,
                "last_10_results": []  # Track last 10 outcomes for evolution logic
            },
            "evolution_history": [],
            "metadata": metadata or {}
        }
        
        # Save manifest
        manifest_path = os.path.join(strategy_dir, "manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"✅ Created strategy: {strategy_id}")
        return manifest
    
    def load_strategy(self, strategy_id: str) -> Optional[Dict]:
        """Load a strategy by ID"""
        strategy_dir = os.path.join(self.strategies_dir, strategy_id)
        manifest_path = os.path.join(strategy_dir, "manifest.json")
        
        if not os.path.exists(manifest_path):
            return None
        
        with open(manifest_path, 'r') as f:
            return json.load(f)
    
    def update_performance(self, 
                          strategy_id: str, 
                          success: bool,
                          details: Dict = None) -> Dict:
        """Update strategy performance after a trade opportunity"""
        
        strategy = self.load_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        perf = strategy["performance"]
        perf["total_trades"] += 1
        
        if success:
            perf["successful_captures"] += 1
            result = "success"
        else:
            perf["missed_opportunities"] += 1
            result = "missed"
        
        # Add to last 10 results (sliding window)
        perf["last_10_results"].append({
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "details": details or {}
        })
        
        # Keep only last 10
        if len(perf["last_10_results"]) > 10:
            perf["last_10_results"] = perf["last_10_results"][-10:]
        
        # Update timestamp
        strategy["updated_at"] = datetime.now().isoformat()
        
        # Save updated manifest
        self._save_strategy(strategy)
        
        return strategy
    
    def should_evolve(self, strategy_id: str) -> bool:
        """Check if strategy should evolve based on performance"""
        
        strategy = self.load_strategy(strategy_id)
        if not strategy:
            return False
        
        perf = strategy["performance"]
        last_10 = perf["last_10_results"]
        
        # Need at least some data points
        if len(last_10) < self.config.EVOLUTION_WINDOW:
            return False
        
        # Count failures in last N trades
        recent_failures = sum(1 for r in last_10[-self.config.EVOLUTION_WINDOW:] 
                             if r["result"] == "missed")
        
        # Trigger evolution if failures exceed threshold
        return recent_failures >= self.config.FAILURE_THRESHOLD
    
    def evolve_strategy(self, 
                       strategy_id: str, 
                       new_base_chart_path: str,
                       evolution_reason: str,
                       selected_candidate_id: str) -> Dict:
        """Evolve strategy by replacing base pattern"""
        
        strategy = self.load_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        # Record evolution history
        evolution_record = {
            "evolved_at": datetime.now().isoformat(),
            "reason": evolution_reason,
            "previous_pattern": strategy["base_chart_path"],
            "new_pattern_source": selected_candidate_id,
            "performance_before": {
                "successes": strategy["performance"]["successful_captures"],
                "misses": strategy["performance"]["missed_opportunities"]
            }
        }
        strategy["evolution_history"].append(evolution_record)
        
        # Replace base chart
        chart_filename = "base_pattern.png"
        dest_chart_path = os.path.join(self.strategies_dir, strategy_id, chart_filename)
        shutil.copy2(new_base_chart_path, dest_chart_path)
        strategy["base_chart_path"] = dest_chart_path
        
        # Reset performance tracking (optional - could also keep historical)
        strategy["performance"]["last_10_results"] = []
        strategy["updated_at"] = datetime.now().isoformat()
        
        # Save updated strategy
        self._save_strategy(strategy)
        
        print(f"🔄 Evolved strategy {strategy_id}: {evolution_reason}")
        return strategy
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """Delete a strategy"""
        strategy_dir = os.path.join(self.strategies_dir, strategy_id)
        
        if os.path.exists(strategy_dir):
            shutil.rmtree(strategy_dir)
            print(f"🗑️ Deleted strategy: {strategy_id}")
            return True
        return False
    
    def list_strategies(self) -> List[Dict]:
        """List all active strategies"""
        strategies = []
        
        for strategy_id in os.listdir(self.strategies_dir):
            strategy_dir = os.path.join(self.strategies_dir, strategy_id)
            if os.path.isdir(strategy_dir):
                manifest_path = os.path.join(strategy_dir, "manifest.json")
                if os.path.exists(manifest_path):
                    with open(manifest_path, 'r') as f:
                        strategies.append(json.load(f))
        
        return strategies
    
    def _save_strategy(self, strategy: Dict):
        """Save strategy manifest"""
        strategy_id = strategy["strategy_id"]
        manifest_path = os.path.join(self.strategies_dir, strategy_id, "manifest.json")
        
        with open(manifest_path, 'w') as f:
            json.dump(strategy, f, indent=2)
    
    def get_all_candidates(self) -> List[Dict]:
        """Get all candidate patterns from data directory"""
        candidates_dir = os.path.join(self.config.DATA_DIR, "candidates")
        candidates = []
        
        if not os.path.exists(candidates_dir):
            return candidates
        
        for filename in os.listdir(candidates_dir):
            if filename.endswith("_meta.json"):
                meta_path = os.path.join(candidates_dir, filename)
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                
                # Verify chart exists
                if os.path.exists(metadata.get("chart_path", "")):
                    candidates.append(metadata)
        
        # Sort by timestamp descending (most recent first)
        candidates.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return candidates
