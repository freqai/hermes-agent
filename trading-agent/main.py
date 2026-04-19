"""
Main Trading Agent Orchestrator
Coordinates all components: Hunter, Multi-Agent System, Strategy Manager
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from config import Config
from agents.hunter_agent import DataHunter
from agents.multi_agent_system import MultiAgentSystem
from core.strategy_manager import StrategyManager

class TradingAgent:
    """Main orchestrator for the self-evolving trading agent"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config.from_env()
        self.hunter = DataHunter(self.config)
        self.multi_agent = MultiAgentSystem(self.config)
        self.strategy_manager = StrategyManager(self.config)
        
        # Initialize exchange
        self.exchange = getattr(ccxt, self.config.EXCHANGE_ID)({
            'enableRateLimit': True,
        })
        
        # Current chart cache
        self.current_chart_path = None
    
    def fetch_current_chart(self) -> str:
        """Fetch current market data and generate chart"""
        df = self.hunter.fetch_ohlcv()
        
        # Create chart
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df['timestamp'], df['close'], linewidth=2, color='green')
        ax.fill_between(df['timestamp'], 
                       df['high'], 
                       df['low'], 
                       alpha=0.3, color='lightgreen')
        
        ax.set_title(f"Current Market: {self.config.SYMBOL}", fontsize=14, fontweight='bold')
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.grid(True, alpha=0.3)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save to temp location
        os.makedirs(self.config.DATA_DIR, exist_ok=True)
        chart_path = os.path.join(self.config.DATA_DIR, "current_market.png")
        fig.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        self.current_chart_path = chart_path
        return chart_path
    
    def initialize_strategy_from_candidate(self, candidate_id: str, params: Dict = None) -> Dict:
        """Create initial strategy from a captured candidate pattern"""
        candidates_dir = os.path.join(self.config.DATA_DIR, "candidates")
        
        # Find candidate files
        meta_path = os.path.join(candidates_dir, f"{candidate_id}_meta.json")
        chart_path = os.path.join(candidates_dir, f"{candidate_id}_chart.png")
        
        if not os.path.exists(meta_path) or not os.path.exists(chart_path):
            raise ValueError(f"Candidate {candidate_id} not found")
        
        # Load metadata
        with open(meta_path, 'r') as f:
            metadata = json.load(f)
        
        # Default params
        default_params = {
            "entry_condition": "Visual pattern match with base chart",
            "position_size": 0.1,  # 10% of portfolio
            "stop_loss": 0.05,     # 5% stop loss
            "take_profit": 0.20,   # 20% take profit
        }
        
        if params:
            default_params.update(params)
        
        # Create strategy
        strategy = self.strategy_manager.create_strategy(
            strategy_id=candidate_id,
            base_chart_path=chart_path,
            params=default_params,
            metadata=metadata
        )
        
        return strategy
    
    def scan_and_execute(self) -> Dict[str, Any]:
        """Scan all strategies against current market and execute trades"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "market_price": None,
            "strategies_evaluated": 0,
            "trades_executed": 0,
            "details": []
        }
        
        # Fetch current market data
        current_chart = self.fetch_current_chart()
        df = self.hunter.fetch_ohlcv()
        results["market_price"] = float(df['close'].iloc[-1])
        
        # Get all active strategies
        strategies = self.strategy_manager.list_strategies()
        
        for strategy in strategies:
            strategy_id = strategy["strategy_id"]
            detail = {
                "strategy_id": strategy_id,
                "action": "none",
                "reason": "",
                "similarity_score": 0.0
            }
            
            # Use MLLM to evaluate pattern match
            evaluation = self.multi_agent.evaluate_trade_opportunity(
                current_chart=current_chart,
                strategy=strategy
            )
            
            detail["similarity_score"] = evaluation.get("similarity_score", 0.0)
            detail["confidence"] = evaluation.get("confidence", "unknown")
            detail["reasoning"] = evaluation.get("reasoning", "")
            
            if evaluation.get("should_execute", False):
                # Execute trade (or record signal)
                detail["action"] = "EXECUTE_TRADE"
                detail["params"] = strategy["params"]
                results["trades_executed"] += 1
                
                # Update performance as success opportunity
                self.strategy_manager.update_performance(
                    strategy_id=strategy_id,
                    success=True,
                    details={"price": results["market_price"]}
                )
                
                print(f"🎯 TRADE SIGNAL: {strategy_id} - Match score: {detail['similarity_score']:.2f}")
            else:
                # Check if we missed an opportunity (volatility happened but we didn't trade)
                # This is simplified - in production you'd check if volatility occurred after signal
                detail["action"] = "HOLD"
                
                # For demo: randomly mark some as missed to test evolution
                # In production, this would be determined by actual market movement
                import random
                if random.random() < 0.3:  # 30% chance to simulate missed opportunity
                    self.strategy_manager.update_performance(
                        strategy_id=strategy_id,
                        success=False,
                        details={"price": results["market_price"], "reason": "Pattern appeared but no follow-through"}
                    )
                    detail["action"] = "MISSED_OPPORTUNITY"
            
            results["details"].append(detail)
            results["strategies_evaluated"] += 1
        
        return results
    
    def evolve_strategies(self) -> Dict[str, Any]:
        """Check all strategies and evolve those that need it"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "strategies_checked": 0,
            "strategies_evolved": 0,
            "evolutions": []
        }
        
        strategies = self.strategy_manager.list_strategies()
        candidates = self.strategy_manager.get_all_candidates()
        
        for strategy in strategies:
            strategy_id = strategy["strategy_id"]
            results["strategies_checked"] += 1
            
            # Check if evolution is needed
            if self.strategy_manager.should_evolve(strategy_id):
                print(f"🔄 Strategy {strategy_id} triggered evolution...")
                
                # Get failed cases from performance log
                perf = strategy["performance"]
                failed_cases = [r for r in perf["last_10_results"] if r["result"] == "missed"]
                
                # Use EvolutionArchitect to select new pattern
                evolution_decision = self.multi_agent.trigger_evolution(
                    strategy=strategy,
                    failed_cases=failed_cases,
                    candidates=candidates
                )
                
                selected_candidate_id = evolution_decision.get("selected_candidate_id")
                
                if selected_candidate_id:
                    # Find the candidate chart
                    candidates_dir = os.path.join(self.config.DATA_DIR, "candidates")
                    new_chart_path = os.path.join(candidates_dir, f"{selected_candidate_id}_chart.png")
                    
                    if os.path.exists(new_chart_path):
                        # Evolve the strategy
                        evolved_strategy = self.strategy_manager.evolve_strategy(
                            strategy_id=strategy_id,
                            new_base_chart_path=new_chart_path,
                            evolution_reason=evolution_decision.get("reason_for_change", "Performance degradation"),
                            selected_candidate_id=selected_candidate_id
                        )
                        
                        results["strategies_evolved"] += 1
                        results["evolutions"].append({
                            "strategy_id": strategy_id,
                            "new_pattern_source": selected_candidate_id,
                            "reason": evolution_decision.get("reason_for_change", ""),
                            "advantages": evolution_decision.get("advantages_of_new", "")
                        })
                        
                        print(f"✅ Evolved {strategy_id} -> New pattern from {selected_candidate_id}")
                    else:
                        print(f"⚠️ Candidate chart not found: {new_chart_path}")
                else:
                    print(f"⚠️ No suitable candidate found for evolution")
        
        return results
    
    def run_monitoring_loop(self, interval_seconds: int = 60):
        """Run continuous monitoring loop"""
        print(f"🚀 Starting Trading Agent for {self.config.SYMBOL}")
        print(f"Volatility threshold: {self.config.VOLATILITY_THRESHOLD * 100}%")
        print(f"Evolution window: {self.config.EVOLUTION_WINDOW} trades")
        print(f"Failure threshold: {self.config.FAILURE_THRESHOLD} failures\n")
        
        import time
        
        while True:
            try:
                print(f"\n{'='*60}")
                print(f"⏰ Cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                
                # Step 1: Scan market and execute trades
                print("\n📊 Scanning market opportunities...")
                scan_results = self.scan_and_execute()
                print(f"Evaluated {scan_results['strategies_evaluated']} strategies")
                print(f"Trade signals: {scan_results['trades_executed']}")
                
                # Step 2: Check for evolution
                print("\n🧬 Checking strategy evolution...")
                evolution_results = self.evolve_strategies()
                print(f"Strategies evolved: {evolution_results['strategies_evolved']}")
                
                # Wait for next cycle
                print(f"\n💤 Waiting {interval_seconds} seconds...")
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                import traceback
                traceback.print_exc()
                import time
                time.sleep(interval_seconds)


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Self-Evolving Trading Agent")
    parser.add_argument("--mode", choices=["monitor", "scan", "evolve", "init"], 
                       default="monitor", help="Operation mode")
    parser.add_argument("--candidate", type=str, help="Candidate ID to initialize strategy from")
    parser.add_argument("--symbol", type=str, help="Trading pair (e.g., BTC/USDT)")
    parser.add_argument("--threshold", type=float, help="Volatility threshold (e.g., 0.20 for 20 percent)")
    
    args = parser.parse_args()
    
    # Create config
    config = Config.from_env()
    if args.symbol:
        config.SYMBOL = args.symbol
    if args.threshold:
        config.VOLATILITY_THRESHOLD = args.threshold
    
    # Create agent
    agent = TradingAgent(config)
    
    if args.mode == "init":
        if not args.candidate:
            print("❌ --candidate required for init mode")
            return
        
        # List available candidates
        candidates = agent.hunter.get_candidates()
        if not candidates:
            print("❌ No candidates found. Run hunter first to capture volatility events.")
            return
        
        print("Available candidates:")
        for i, c in enumerate(candidates[:10]):
            print(f"  {i+1}. {c['event_id']} - {c['price_start']} -> {c['price_end']}")
        
        # Initialize strategy
        strategy = agent.initialize_strategy_from_candidate(args.candidate)
        print(f"\n✅ Strategy created: {strategy['strategy_id']}")
        
    elif args.mode == "scan":
        results = agent.scan_and_execute()
        print(json.dumps(results, indent=2))
        
    elif args.mode == "evolve":
        results = agent.evolve_strategies()
        print(json.dumps(results, indent=2))
        
    elif args.mode == "monitor":
        agent.run_monitoring_loop()


if __name__ == "__main__":
    main()
