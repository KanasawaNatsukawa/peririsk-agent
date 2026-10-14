# PeriRisk Agent · 围术期风险评估助手

一个基于 **大模型 Agent + 临床规则引擎** 的围术期风险评估演示项目：根据患者的基本信息与生命体征，自动计算 **ASA 麻醉分级**（美国麻醉医师协会身体状况分级）、检测脉搏 **心率**，并调用 **DeepSeek 大模型** 生成结构化的术前风险评估报告。

> ⚠️ 本项目为**教学 / 演示用途**，不构成任何临床诊断或医疗建议。ASA 分级逻辑为教学简化版，与临床完整标准存在差异。

---

## ✨ 功能特性

| 功能 | 说明 | 实现方式 |
|---|---|---|
| ASA 麻醉分级 | 基于年龄与既往病史自动分级（I–V 级） | 规则引擎（`asa_risk.py`） |
| 心率检测 | 从脉搏波信号自动提取心率（次/分钟） | 信号处理 + 波峰检测（`heartbeat_demo.py`） |
| AI 风险评估报告 | 生成【风险评估】【麻醉关注点】【建议】三段式报告 | DeepSeek 大模型 API（`peririsk_agent_v1b.py`） |
| 真实数据接入（进行中） | 支持真实生理数据（VitalDB）输入 | `peririsk_real.py` |

## 🏗️ 系统架构

```
患者信息（年龄 / 病史 / 生命体征）
        │
        ▼
┌─────────────────┐
│  ASA 分级规则引擎 │──► ASA I–V 级
│   (asa_risk.py)  │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  脉搏波心率检测   │──► 心率 (bpm)
│ (heartbeat_demo) │
└─────────────────┘
        │
        ▼
┌──────────────────────────┐
│  DeepSeek 大模型 API 调用  │──► 术前风险评估报告
│  (peririsk_agent_v1b.py)  │    【风险评估】【麻醉关注点】【建议】
└──────────────────────────┘
```

**数据流**：`患者信息 → 规则引擎计算 ASA + 信号处理计算心率 → 拼接患者摘要 → 大模型生成结构化报告`

## 📁 项目结构

```
peririsk-demo/
├── peririsk_agent_v1b.py   # 主程序：Agent 编排，调用 DeepSeek 生成报告
├── asa_risk.py             # ASA 分级规则引擎（临床规则，纯逻辑，无 AI）
├── heartbeat_demo.py       # 心率检测（脉搏波信号处理）
├── peririsk_real.py        # 真实数据版（接入 VitalDB 生理数据）
├── test_deepseek.py        # DeepSeek API 连通性测试
├── config.py               # ⚠️ API Key 配置文件（已被 .gitignore 排除，勿提交）
└── .gitignore              # 忽略敏感文件（config.py 等）
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- 依赖库：`requests`（主程序）、`scipy` / `numpy` / `matplotlib`（心率检测）

```bash
pip install requests scipy numpy matplotlib
```

### 2. 配置 API Key

1. 在 [DeepSeek 开放平台](https://platform.deepseek.com) 创建 API Key
2. 打开 `config.py`，将 `API_KEY` 替换为你的 key：

```python
API_KEY = "sk-你的key"
```

> 🔒 **安全提醒**：`config.py` 已被 `.gitignore` 排除，**切勿**将其提交到仓库；请勿在任何代码中硬编码 API Key。

### 3. 运行

```bash
# 生成围术期风险评估报告（主程序）
python peririsk_agent_v1b.py

# 单独测试 ASA 分级
python asa_risk.py

# 心率检测（会绘制脉搏波图）
python heartbeat_demo.py

# 测试 DeepSeek 连接
python test_deepseek.py
```

## 🛠️ 技术栈

- **语言**：Python
- **大模型**：DeepSeek（`deepseek-chat`）
- **API 调用**：HTTP `requests` 直连（避免 openai 库的中文消息兼容问题）
- **信号处理**：SciPy `find_peaks` 波峰检测
- **临床规则**：ASA 身体状况分级（教学简化版）

## 📌 Roadmap

- [ ] 接入 VitalDB 真实生理信号数据，验证端到端流程
- [ ] 补充完整版 ASA 分级（含更多并发症维度）
- [ ] 增加血压（无袖带）预测模块（PINN 方向）
- [ ] 多 Agent 协作版（JiuwenSwarm 编排）

---

*项目用于教学演示与 Agent 应用开发学习。*
