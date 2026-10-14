# PeriRisk Agent

围术期风险评估演示项目。输入患者的基本信息和生命体征，程序先自己算出 ASA 麻醉分级和心率，再调用 DeepSeek 大模型生成一份术前风险评估报告。

> 教学/演示用，不是医疗器械，不构成医疗建议。ASA 分级逻辑是简化版，跟临床完整标准有差异。

## 怎么用

1. 装依赖：`pip install requests scipy numpy matplotlib`
2. 去 DeepSeek 开放平台创建 API Key，填进 `config.py`
3. 运行 `python peririsk_agent_v1b.py`

`config.py` 已经被 .gitignore 排除，不要提交它，也不要在任何代码里写死 key。

## 结构

- `peririsk_agent_v1b.py` — 主程序，编排流程，调 DeepSeek 生成报告
- `asa_risk.py` — ASA 分级规则（纯逻辑，不调 AI）
- `heartbeat_demo.py` — 心率检测，脉搏波信号处理
- `peririsk_real.py` — 真实数据版，接 VitalDB 生理数据（进行中）
- `test_deepseek.py` — 测 DeepSeek 连接是否正常

## 流程

患者信息 → ASA 规则引擎算出分级 → 心率检测算出心率 → 拼成摘要 → DeepSeek 生成三段式报告（风险评估 / 麻醉关注点 / 建议）

## 后面想做的

- 接 VitalDB 真实数据跑通端到端
- ASA 分级补全更多并发症维度
- 加无袖带血压预测（PINN 方向）
- 用 JiuwenSwarm 做多 Agent 协作版
