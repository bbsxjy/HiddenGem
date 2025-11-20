# LLM Task Checklist

## 1. RL 策略与执行闭环
- **VecNormalize**：在 `trading/rl_strategy.py` 初始化时加载 `*_vecnormalize.pkl`，并在 QF-Lib 适配器/回测脚本中复用相同归一化统计。
- **动作落地**：`_action_to_signal` 含义（BUY_25/SELL_ALL）需要传递给 `MultiStrategyManager.execute_signals()`，按 `target_ratio` 或 `position_delta` 下单，避免动作信息丢失。
- **账户状态输入**：`generate_signals` 中的 `portfolio_state` 应包含真实 `total_equity`、持仓成本、T+1 可卖量等，从 `SimulatedBroker` 读取并传给 RL/LLM。
- **回测适配器**：`qflib_integration/rl_strategy_adapter.py` 同步 5 动作空间映射，并加载 VecNormalize，以保证与线上一致。

## 2. LLM/Memory 管线
- **Embedding 健康检测**：`tradingagents/agents/utils/memory.py` 在提供零向量或降级时要返回清晰错误，让调用者跳过记忆检索，并记录状态。
- **长文本处理**：实现新闻/lesson 的 chunk+overlap，总结后再送入 embedding，避免“长度超限直接跳过”。
- **Memory 内容脱敏**：写入 `TradingEpisode.lesson` 时拆分“当日信息”和“未来结果”，避免后续推理读取未来数据。
- **小模型路由**：为 Multi-Agent 每个角色配置 lightweight 模型（7B/13B），并在 orchestrator 中根据任务复杂度决定是否升级到 80B。

## 3. DataFlow & 缓存
- **统一缓存层**：`tradingagents/dataflows/interface.py` 引入 TTL 缓存（例如 `functools.lru_cache` + 失效时间），Time Travel/回测优先读取缓存或磁盘文件。
- **AKShare 超时**：改用 `ThreadPoolExecutor` + `future.result(timeout)` 或 requests timeout，移除 per-call 线程。
- **日志初始化**：避免 `setup_dataflow_logging()` 在 import 时多次执行；改为懒加载，统一 logger 配置。

## 4. Auto Trading 服务
- **线程监管**：为 `_run_trading_loop` 添加 supervisor/健康检查，异常时自动重启或清晰告警，`self.running` 状态与实际一致。
- **行情失败处理**：不要生成随机 K 线；若实时数据缺失，则跳过该标的或使用最近一次真实数据，并标记低置信度。
- **Metrics/状态接口**：新增 API 或 Prometheus 指标，暴露策略收益、持仓、线程状态，方便监控。

## 5. Time Travel & 训练流程
- **数据生成 vs 训练**：将 `enhanced_time_travel_training` 输出结构化 JSONL（行情特征、LLM 决策、收益），供后续 SFT/蒸馏使用，避免把“生成”误当训练。
- **无未来约束**：Memory/lesson 只包含当前日期信息；未来收益单独存储在 outcome，不参与 LLM prompt。
- **断点与并行**：Time Travel 支持断点恢复、multi-symbol 并行、批量写入 Memory，缩短运行时间。
- **SFT/蒸馏脚本**：基于 Time Travel 产出的样本，编写面向 7B/13B 模型的 SFT/LoRA 训练脚本，实现真正的“小模型训练”。

## 6. 基础设施与文档
- **配置集中化**：新增 `config/settings.py`，在启动时验证必需环境变量/API key，避免各脚本重复读取 .env。
- **任务监控**：长任务（RL训练、Time Travel、AutoTrading）写入 `results/checkpoint.json`，记录进度与最近状态。
- **测试覆盖**：为 RLStrategy、MultiStrategyManager、Time Travel 核心逻辑增加单元/集成测试，防止回归。
- **脚本去重**：整合 `train_rl_*` 多个脚本为统一 Trainer，减少维护成本。
