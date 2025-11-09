"""
LLM Service for intelligent trading signal analysis.
Uses SiliconFlow API (OpenAI-compatible) for LLM inference.
"""

import json
from typing import Dict, Any, List, Optional
from decimal import Decimal

import httpx
from loguru import logger

from config.settings import settings


class LLMService:
    """
    Service for calling LLM API to analyze trading signals.

    Uses SiliconFlow API which is OpenAI-compatible.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """
        Initialize LLM service.

        Args:
            api_key: API key for SiliconFlow
            base_url: Base URL for API
            model: Model name to use
            timeout: Request timeout in seconds (defaults to settings.llm_timeout)
        """
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model
        self.timeout = timeout if timeout is not None else settings.llm_timeout

        if not self.api_key:
            raise ValueError("LLM_API_KEY not configured")

        logger.info(
            f"Initialized LLM service: {self.base_url}, "
            f"model={self.model}, timeout={self.timeout}s"
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if LLM service is healthy and accessible.

        Returns:
            Dict with health status information
        """
        try:
            # Simple test request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": "测试连接，请回复'OK'"
                    }
                ],
                "max_tokens": 10,
                "temperature": 0
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                return {
                    "status": "healthy",
                    "base_url": self.base_url,
                    "model": self.model,
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                    "api_accessible": True,
                    "test_response": result.get("choices", [{}])[0].get("message", {}).get("content", "")
                }

        except httpx.TimeoutException:
            return {
                "status": "unhealthy",
                "base_url": self.base_url,
                "model": self.model,
                "api_accessible": False,
                "error": "连接超时"
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "unhealthy",
                "base_url": self.base_url,
                "model": self.model,
                "api_accessible": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "base_url": self.base_url,
                "model": self.model,
                "api_accessible": False,
                "error": str(e)
            }

    async def analyze_trading_signal(
        self,
        symbol: str,
        agent_results: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze trading signals from multiple agents.

        Args:
            symbol: Stock symbol
            agent_results: Results from all agents
            market_context: Additional market context

        Returns:
            LLM analysis result with:
            - recommended_direction: LONG/SHORT/HOLD/CLOSE
            - confidence: 0.0 to 1.0
            - reasoning: Human-readable explanation
            - risk_assessment: Risk analysis
            - key_factors: Key decision factors
        """
        try:
            # Prepare data for LLM
            analysis_data = self._prepare_analysis_data(
                symbol,
                agent_results,
                market_context
            )

            # Ensure we have current price (critical for price_targets)
            if not analysis_data.get("current_price"):
                logger.warning(f"Current price not found in agent results for {symbol}, fetching from data source")
                current_price = await self._fetch_current_price(symbol)
                if current_price:
                    analysis_data["current_price"] = current_price
                    logger.info(f"Fetched current price for {symbol}: {current_price:.2f}")
                else:
                    logger.error(f"Failed to fetch current price for {symbol}, LLM may return inaccurate price targets")

            # Create prompt
            prompt = self._create_analysis_prompt(analysis_data)

            # Call LLM
            response = await self._call_llm(prompt)

            # Parse response
            result = self._parse_analysis_response(response)

            logger.info(
                f"LLM analysis for {symbol}: "
                f"direction={result.get('recommended_direction')}, "
                f"confidence={result.get('confidence'):.2f}"
            )

            return result

        except Exception as e:
            logger.error(f"Error in LLM analysis for {symbol}: {e}")
            raise

    async def _fetch_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current price from data source when not available in agent results.

        Args:
            symbol: Stock symbol

        Returns:
            Current price or None if failed
        """
        try:
            from core.data.sources import data_source
            from datetime import datetime, timedelta

            # Try 1: Get real-time quote first (fastest)
            try:
                quote = data_source.get_realtime_quote(symbol)
                if quote and 'price' in quote and quote['price']:
                    price = float(quote['price'])
                    if price > 0:
                        logger.info(f"Got real-time price for {symbol}: {price}")
                        return price
            except Exception as e:
                logger.warning(f"Failed to get real-time quote for {symbol}: {e}")

            # Try 2: Get latest daily bar (fallback)
            try:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

                bars = data_source.get_daily_bars(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )

                if bars is not None and len(bars) > 0:
                    latest = bars.iloc[-1]
                    price = float(latest['close'])
                    logger.info(f"Got latest close price for {symbol}: {price}")
                    return price
            except Exception as e:
                logger.warning(f"Failed to get daily bars for {symbol}: {e}")

            return None

        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None

    def _prepare_analysis_data(
        self,
        symbol: str,
        agent_results: Dict[str, Any],
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Prepare agent data for LLM analysis.

        Args:
            symbol: Stock symbol
            agent_results: Results from agents
            market_context: Market context

        Returns:
            Structured data for LLM
        """
        data = {
            "symbol": symbol,
            "agents": {},
            "current_price": None
        }

        # Extract current price from agent results
        # Try to get from technical agent first, then market agent
        for agent_name, result in agent_results.items():
            if not result.is_error and result.analysis:
                # Check technical agent for close price
                if 'technical' in agent_name.lower():
                    if 'close' in result.analysis:
                        data["current_price"] = float(result.analysis['close'])
                        break
                    elif 'price' in result.analysis:
                        data["current_price"] = float(result.analysis['price'])
                        break
                # Check market agent
                elif 'market' in agent_name.lower():
                    if 'close' in result.analysis:
                        data["current_price"] = float(result.analysis['close'])
                        break
                    elif 'price' in result.analysis:
                        data["current_price"] = float(result.analysis['price'])
                        break

        # Extract key information from each agent
        for agent_name, result in agent_results.items():
            if result.is_error:
                data["agents"][agent_name] = {
                    "status": "error",
                    "error": result.error_message
                }
                continue

            data["agents"][agent_name] = {
                "direction": result.direction.value if result.direction else None,
                "confidence": float(result.confidence) if result.confidence else 0.0,
                "score": float(result.score) if result.score else 0.0,
                "reasoning": result.reasoning,
                "analysis": self._simplify_analysis(result.analysis)
            }

        # Add market context if available
        if market_context:
            data["market_context"] = market_context

        return data

    def _simplify_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simplify analysis data to reduce token usage.

        Args:
            analysis: Full analysis data

        Returns:
            Simplified analysis
        """
        simplified = {}

        # Keep only essential fields
        essential_keys = [
            'overall_score', 'valuation', 'sentiment_score',
            'impact_score', 'description', 'trend', 'volatility',
            'rsi', 'macd', 'moving_averages', 'pe_ratio', 'pb_ratio',
            'roe', 'debt_to_equity', 'northbound_flow', 'margin_balance',
            'close', 'price'  # Add price fields
        ]

        for key in essential_keys:
            if key in analysis:
                value = analysis[key]
                # Convert Decimal to float
                if isinstance(value, Decimal):
                    simplified[key] = float(value)
                elif isinstance(value, dict):
                    simplified[key] = {
                        k: float(v) if isinstance(v, Decimal) else v
                        for k, v in value.items()
                        if k in ['value', 'score', 'signal', 'adx', 'atr_percentage']
                    }
                else:
                    simplified[key] = value

        return simplified

    def _create_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """
        Create prompt for LLM analysis.

        Args:
            data: Analysis data

        Returns:
            Prompt string
        """
        symbol = data.get("symbol", "未知")
        current_price = data.get("current_price")
        agents = data.get("agents", {})

        prompt = f"""你是一个专业的A股量化交易分析师。请分析以下多个AI agents对股票{symbol}的分析结果，并给出综合交易建议。

"""

        # Add current price prominently if available
        if current_price:
            prompt += f"""# 当前价格
**{symbol}的最新价格: {current_price:.2f}元**

"""

        prompt += f"""# Agent分析结果

"""

        # Add agent results
        for agent_name, agent_data in agents.items():
            if agent_data.get("status") == "error":
                prompt += f"\n## {agent_name}\n状态: 错误 - {agent_data.get('error')}\n"
                continue

            prompt += f"\n## {agent_name}\n"
            prompt += f"- 方向: {agent_data.get('direction', 'N/A')}\n"
            prompt += f"- 置信度: {agent_data.get('confidence', 0):.2f}\n"
            prompt += f"- 推理: {agent_data.get('reasoning', 'N/A')}\n"

            # Add key analysis points
            analysis = agent_data.get('analysis', {})
            if analysis:
                prompt += f"- 关键指标: {json.dumps(analysis, ensure_ascii=False, indent=2)}\n"

        # Add market context if available
        if "market_context" in data:
            prompt += f"\n# 市场环境\n{json.dumps(data['market_context'], ensure_ascii=False, indent=2)}\n"

        prompt += """

# 任务要求

请综合分析以上信息，输出JSON格式的交易建议。

**重要：请直接输出JSON，不要包含任何其他文本、解释或markdown代码块标记。**

JSON格式要求：

{
  "recommended_direction": "LONG|SHORT|HOLD|CLOSE",
  "confidence": 0.0到1.0之间的数值,
  "reasoning": "详细的决策理由（纯文本字符串），包括：\\n1. 各agent信号的综合评估\\n2. 信号之间的冲突或一致性\\n3. 关键决策因素\\n4. 建议的操作逻辑",
  "risk_assessment": "风险评估（纯文本字符串），包括：主要风险点、风险级别(低/中/高)、风险应对建议",
  "key_factors": [
    "关键因素1",
    "关键因素2",
    "关键因素3"
  ]
}

注意事项：
1. 充分考虑A股市场特点（涨跌停、T+1、情绪驱动等）
2. 权衡技术面、基本面、情绪面、政策面的信号
3. 如果各agent信号严重冲突，应倾向于HOLD
4. 置信度应反映信号的一致性和强度
5. reasoning和risk_assessment必须是纯文本字符串，不要使用嵌套对象
6. 必须返回有效的JSON格式
7. 不要输出思考过程，直接输出JSON结果
8. **专注于分析，不要给出具体的价格建议（入场价、止损价、止盈价等）**
9. **推理应基于分析数据和市场信息，而非价格预测**
"""

        return prompt

    async def _call_llm(self, prompt: str) -> str:
        """
        Call LLM API.

        Args:
            prompt: Prompt text

        Returns:
            LLM response text
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的A股量化交易分析师，擅长综合分析多维度信息并给出精准的交易建议。请直接输出JSON格式的分析结果，不要输出思考过程或其他额外文本。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Lower temperature for more consistent analysis
            "max_tokens": 2000
        }

        # Log LLM request
        logger.info("="*80)
        logger.info("LLM REQUEST")
        logger.info("="*80)
        logger.info(f"Model: {self.model}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Temperature: {payload['temperature']}")
        logger.info(f"Max Tokens: {payload['max_tokens']}")
        logger.info("-"*80)
        logger.info("System Message:")
        logger.info(payload['messages'][0]['content'])
        logger.info("-"*80)
        logger.info("User Prompt:")
        logger.info(payload['messages'][1]['content'])
        logger.info("="*80)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # Log LLM response
                logger.info("="*80)
                logger.info("LLM RESPONSE")
                logger.info("="*80)
                logger.info(f"Response Length: {len(content)} chars")
                logger.info(f"Status Code: {response.status_code}")
                logger.info(f"Response Time: {response.elapsed.total_seconds():.2f}s")
                logger.info("-"*80)
                logger.info("Response Content:")
                logger.info(content)
                logger.info("="*80)

                return content

            except httpx.TimeoutException as e:
                logger.error(f"LLM API timeout after {self.timeout}s: {e}")
                raise Exception(f"LLM API请求超时({self.timeout}秒)")
            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_json = e.response.json()
                    error_detail = error_json.get("error", {}).get("message", e.response.text)
                except:
                    error_detail = e.response.text

                logger.error(
                    f"LLM API HTTP error: {e.response.status_code}\n"
                    f"URL: {e.request.url}\n"
                    f"Error detail: {error_detail}"
                )
                raise Exception(f"LLM API错误 ({e.response.status_code}): {error_detail}")
            except httpx.ConnectError as e:
                logger.error(f"LLM API connection failed: {e}")
                raise Exception(f"无法连接到LLM服务 ({self.base_url})")
            except httpx.RequestError as e:
                logger.error(f"LLM API request error: {type(e).__name__} - {e}")
                raise Exception(f"LLM请求失败: {str(e)}")
            except KeyError as e:
                logger.error(f"LLM API response format error - missing key: {e}")
                raise Exception(f"LLM响应格式错误: 缺少字段 {e}")
            except Exception as e:
                logger.error(f"LLM API call failed: {type(e).__name__} - {e}")
                raise

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured format.
        Handles DeepSeek-R1's <think> tags and various formats.

        Args:
            response: LLM response text

        Returns:
            Parsed analysis result
        """
        try:
            # Remove <think>...</think> tags (DeepSeek-R1 specific)
            import re
            response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)

            # Strip whitespace
            response = response.strip()

            # Find JSON content (between { and })
            # Look for the first { and last }
            json_start = response.find('{')
            json_end = response.rfind('}')

            if json_start != -1 and json_end != -1 and json_end > json_start:
                response = response[json_start:json_end+1]
            else:
                # Try to remove markdown code blocks
                if response.startswith("```"):
                    # Remove ```json or ``` at start
                    lines = response.split("\n")
                    response = "\n".join(lines[1:])
                if response.endswith("```"):
                    response = response.rsplit("\n```", 1)[0]
                response = response.strip()

            # Parse JSON
            result = json.loads(response)

            # Validate and normalize
            if "recommended_direction" not in result:
                raise ValueError("Missing 'recommended_direction' in LLM response")

            if "confidence" not in result:
                result["confidence"] = 0.5

            # Ensure confidence is in [0, 1]
            result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))

            # Normalize direction
            direction = result["recommended_direction"].upper()
            if direction not in ["LONG", "SHORT", "HOLD", "CLOSE"]:
                logger.warning(f"Invalid direction from LLM: {direction}, defaulting to HOLD")
                result["recommended_direction"] = "HOLD"
            else:
                result["recommended_direction"] = direction

            # Normalize risk_assessment to string if it's a dict
            if isinstance(result.get("risk_assessment"), dict):
                risk_dict = result["risk_assessment"]
                risk_parts = []
                if "主要风险点" in risk_dict:
                    risk_parts.append(f"主要风险: {risk_dict['主要风险点']}")
                if "风险级别" in risk_dict:
                    risk_parts.append(f"风险级别: {risk_dict['风险级别']}")
                if "风险应对建议" in risk_dict:
                    risk_parts.append(f"应对建议: {risk_dict['风险应对建议']}")
                result["risk_assessment"] = "；".join(risk_parts) if risk_parts else "风险评估数据格式异常"

            # Ensure key_factors is a list
            if not isinstance(result.get("key_factors"), list):
                result["key_factors"] = []

            # Price targets are no longer required from LLM
            # Always set to empty dict (will be calculated elsewhere if needed)
            result["price_targets"] = {}

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response text (first 500 chars): {response[:500]}")
            # Return default safe result
            return {
                "recommended_direction": "HOLD",
                "confidence": 0.0,
                "reasoning": f"LLM响应解析失败: {str(e)}",
                "risk_assessment": "无法评估",
                "key_factors": ["LLM响应格式错误"],
                "price_targets": {}
            }
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {
                "recommended_direction": "HOLD",
                "confidence": 0.0,
                "reasoning": f"分析过程出错: {str(e)}",
                "risk_assessment": "无法评估",
                "key_factors": ["分析异常"],
                "price_targets": {}
            }


# Global LLM service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get or create global LLM service instance.

    Returns:
        LLM service instance
    """
    global _llm_service

    if _llm_service is None:
        _llm_service = LLMService()

    return _llm_service
