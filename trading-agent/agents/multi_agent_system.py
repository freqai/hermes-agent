"""
Multi-Agent System for Strategy Evolution using MLLM
"""
import os
import json
import base64
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config import Config

class MLLMAgent:
    """Base class for MLLM-powered agents"""
    
    def __init__(self, config: Config, role: str, system_prompt: str):
        self.config = config
        self.role = role
        self.system_prompt = system_prompt
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def query(self, user_prompt: str, images: List[str] = None) -> str:
        """Query MLLM with text and optional images"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": []}
        ]
        
        # Add images if provided
        content = []
        if images:
            for img_path in images:
                base64_image = self.encode_image(img_path)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                })
        
        # Add text prompt
        content.append({"type": "text", "text": user_prompt})
        messages[0]["content"] = content
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.3
        )
        
        return response.choices[0].message.content


class VisualJudge(MLLMAgent):
    """Agent that compares current K-line with strategy patterns and decides execution"""
    
    def __init__(self, config: Config):
        super().__init__(
            config,
            role="Visual Judge",
            system_prompt="""You are an expert trading pattern recognition specialist. 
Your task is to compare the current K-line chart with a historical strategy pattern.
Analyze visual similarities in:
- Price structure (higher highs/lows, lower highs/lows)
- Consolidation patterns
- Breakout setups
- Candle formations

Respond ONLY with a JSON object:
{
    "similarity_score": 0.0-1.0,
    "should_execute": true/false,
    "confidence": "low/medium/high",
    "reasoning": "brief explanation"
}"""
        )
    
    def evaluate(self, current_chart: str, strategy_chart: str, strategy_params: Dict) -> Dict:
        """Evaluate if current chart matches strategy pattern"""
        prompt = f"""
Compare these two K-line charts:

CHART 1 (Current Market): This is the live market situation
CHART 2 (Strategy Pattern): This is the historical pattern we want to match

Strategy Parameters to consider if match is found:
- Entry condition: {strategy_params.get('entry_condition', 'N/A')}
- Position size: {strategy_params.get('position_size', 'N/A')}
- Stop loss: {strategy_params.get('stop_loss', 'N/A')}
- Take profit: {strategy_params.get('take_profit', 'N/A')}

Is the current chart visually similar enough to the strategy pattern to execute a trade?
"""
        
        response = self.query(prompt, images=[current_chart, strategy_chart])
        
        # Parse JSON response
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(response[start:end])
                return result
        except Exception as e:
            print(f"Error parsing judge response: {e}")
        
        return {
            "similarity_score": 0.0,
            "should_execute": False,
            "confidence": "low",
            "reasoning": f"Failed to parse response: {e}"
        }


class EvolutionArchitect(MLLMAgent):
    """Agent that analyzes failed trades and selects new base patterns"""
    
    def __init__(self, config: Config):
        super().__init__(
            config,
            role="Evolution Architect",
            system_prompt="""You are a strategy evolution specialist.
Your task is to analyze failed trades and select the best replacement pattern from candidates.

When a strategy fails to capture volatility (missed opportunities), you must:
1. Analyze what went wrong with the current base pattern
2. Compare candidate patterns from recent volatility events
3. Select the candidate that best captures the missing characteristics
4. Ensure the new pattern maintains core successful elements while adapting

Respond ONLY with a JSON object:
{
    "selected_candidate_id": "event_id of chosen pattern",
    "reason_for_change": "why current pattern failed",
    "advantages_of_new": "why new pattern is better",
    "key_differences": ["list", "of", "differences"]
}"""
        )
    
    def evolve_strategy(self, 
                       current_pattern: str,
                       failed_cases: List[Dict],
                       candidates: List[Dict]) -> Dict:
        """Analyze failures and select new base pattern"""
        
        # Build prompt with context
        prompt = f"""
CURRENT STRATEGY PATTERN: (see attached image)

FAILED TRADES ANALYSIS:
The current pattern failed to capture {len(failed_cases)} recent volatility events.
This means the pattern appeared but the expected move didn't happen, or we missed valid signals.

CANDIDATE PATTERNS TO CONSIDER:
"""
        
        for i, candidate in enumerate(candidates[:5]):  # Limit to top 5
            prompt += f"\n{i+1}. {candidate['event_id']}: Price {candidate['price_start']} -> {candidate['price_end']}"
        
        prompt += "\n\nWhich candidate pattern should replace the current base pattern to improve future performance?"
        
        # Prepare candidate images
        candidate_images = [c['chart_path'] for c in candidates[:5] if os.path.exists(c['chart_path'])]
        
        response = self.query(prompt, images=[current_pattern] + candidate_images)
        
        # Parse JSON response
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(response[start:end])
                return result
        except Exception as e:
            print(f"Error parsing architect response: {e}")
        
        return {
            "selected_candidate_id": candidates[0]['event_id'] if candidates else None,
            "reason_for_change": "Automatic fallback selection",
            "advantages_of_new": "Most recent volatility pattern",
            "key_differences": []
        }


class MultiAgentSystem:
    """Coordinates multiple MLLM agents for strategy evolution"""
    
    def __init__(self, config: Config):
        self.config = config
        self.judge = VisualJudge(config)
        self.architect = EvolutionArchitect(config)
    
    def evaluate_trade_opportunity(self, 
                                   current_chart: str, 
                                   strategy: Dict) -> Dict:
        """Use VisualJudge to evaluate if we should trade"""
        strategy_chart = strategy.get('base_chart_path')
        if not strategy_chart or not os.path.exists(strategy_chart):
            return {"should_execute": False, "reason": "Strategy chart not found"}
        
        return self.judge.evaluate(current_chart, strategy_chart, strategy.get('params', {}))
    
    def trigger_evolution(self, 
                         strategy: Dict, 
                         failed_cases: List[Dict],
                         candidates: List[Dict]) -> Dict:
        """Use EvolutionArchitect to evolve strategy after failures"""
        current_chart = strategy.get('base_chart_path')
        if not current_chart or not os.path.exists(current_chart):
            return {"error": "No current pattern to evolve from"}
        
        return self.architect.evolve_strategy(current_chart, failed_cases, candidates)
