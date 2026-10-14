# PeriRisk Agent

围术期风险评估演示项目。输入患者的基本信息和生命体征，程序先自己算出 ASA 麻醉分级和心率，再调用 DeepSeek 大模型生成一份术前风险评估报告。

> 教学/演示用，不是医疗器械，不构成医疗建议。ASA 分级逻辑是简化版，跟临床完整标准有差异。

## 怎么用

1. 装依赖：`pip install requests scipy numpy matplotlib`
2. 去 DeepSeek 开放平台创建 API Key，填进 `config.py`
3. 运行 `python peririsk_agent_v1b.py`（或 `peririsk_agent_final.py` / `peririsk_real.py`）

`config.py` 已经被 .gitignore 排除，不要提交它，也不要在任何代码里写死 key。

## 结构

公共模块（改一处，全项目生效）：
- `asa_risk.py` — ASA 分级规则引擎（纯逻辑，不调 AI）
- `patient.py` — 患者档案 + 摘要拼接
- `llm.py` — DeepSeek 调用（提示词、模型名、接口地址都在这一处）

主程序（三选一，逐步进阶）：
- `peririsk_agent_v1b.py` — 最小可跑版：评分 → 摘要 → DeepSeek
- `peririsk_agent_final.py` — 整合版：模拟波形算心率，带步骤日志
- `peririsk_real.py` — 真实数据版，接 VitalDB 生理数据
- `peririsk_agent.py` — Agent 版：DeepSeek 通过 function calling 自主调度工具（Agent 循环）

数据：
- `data/waveform_120s.csv` — VitalDB 真实脉搏波（120 秒，500Hz）
- `data/numeric_60s.csv` — 监护仪记录的数值心率（用于对照验证）

教学与调试：
- `test_deepseek.py` — 测 DeepSeek 连接是否正常
- `heartbeat_demo.py` — 心率检测教学，脉搏波信号处理
- `peririsk_agent_v1.py` — 已弃用（openai 库发中文卡住，被 v1b 取代）
- `_*.py` — 波形峰检测的调试草稿

## 流程

患者信息 → ASA 规则引擎算出分级 → 心率检测算出心率 → `patient.build_summary` 拼成摘要 → `llm.generate_report` 调 DeepSeek → 三段式报告（风险评估 / 麻醉关注点 / 建议）

Agent 版（`peririsk_agent.py`）：不写死顺序，大脑在循环中自主决定调用哪个工具，信息收集齐后输出同样格式的报告。

## 后面想做的

- ASA 分级补全更多并发症维度
- 加无袖带血压预测（PINN 方向）
- 用 JiuwenSwarm 做多 Agent 协作版
