# CAREER.md — 使用者职业规划上下文

> 本文件供 AI 编码助手（Codex 等）了解项目使用者是谁、想去哪、当前在哪，以便后续协作时给出的建议和代码改动都对齐他的职业目标。先读 AGENTS.md（技术交接），再读本文件（人的交接）。

## 使用者画像

- **身份**：19 岁男性，深圳技术大学（SZTU）生物医学工程（BME）2 班大三在读，2024 级（预计 2028 届毕业）
- **当前学期（2026 秋）在修课程**：生物医学数字信号处理、免疫检验原理与技术、生物医学传感与检测、数字电子技术 B
- **技术栈水平**：Python（主力）、DeepSeek API（Function Calling）、scipy（信号处理）、Streamlit（Web 界面）；不熟悉 Java、大模型部署（Ollama / vLLM）、大模型微调
- **职业方向**：医疗 AI / Agent 开发方向（想做医疗大模型应用工程师、临床数据工程师类岗位）

## 为什么做 PeriRisk

- 这是他第一个完整的 AI Agent 项目，也是简历核心项目
- 参加 openJiuwen 智能体创意大赛（2026-10-31 截止创意提交，DEMO 阶段 11/15–12/27，决赛 2027 年 1 月底）
- 导师反馈：第一次组会汇报"不够具体不够详细，讲的都是 AI 精炼总结的东西"——后续所有产出（代码注释、文档、PPT）都要**具体到函数名、参数、数值**，不要抽象概括
- 队友郭羿妤在做数字孪生 wPINN（加权物理信息神经网络）+ ECG/PPG 血压研究，两人方向可交叉

## 职业目标（按优先级）

1. **短期（2026 秋-2027 春）**：把 PeriRisk 做到能写进简历的程度——有量化评估、有公网 Demo、有 README
2. **中期（2027 夏-秋招）**：投医疗 AI / Agent 开发实习或秋招岗位；目标公司方向：医院信息科、医疗 AI 公司（联影/鹰瞳/数坤等）、互联网医疗团队
3. **长期（毕业后 3 年）**：医疗 AI 应用工程师，能独立做"传统医疗业务 + AI 模块"的落地项目

## 简历能力差距（对照 B 站 UP 主「黑马尼古拉斯阿玮」视频《Agent开发上岸，简历要具备哪些能力？》BV1NE9DBSE5s）

视频核心观点（已验证过）：
- 孤立的 AI 项目会被视为"玩具"，必须绑定传统业务背景写完整链路（技术→成果→问题→解决）
- Agent 架构不能只堆技术名词（LangChain/LangGraph），要说明为什么选这个架构（ReAct / Planning / 组合）、解决了什么问题、比传统方案好在哪
- 加分项：传统业务经验、Agent 架构设计、大模型部署（Ollama / vLLM）、大模型微调

**PeriRisk 当前对应情况**：

| 视频要求 | PeriRisk 现状 | 差距 |
|---|---|---|
| 绑定传统业务背景 | 围术期麻醉评估是传统医疗业务，已绑定 | 基本满足 |
| 说明架构选型逻辑 | 用了 ReAct 式 Function Calling，但 README 没写"为什么选 ReAct 不选 Planning" | 需补 |
| 传统业务经验 | BME 在读，懂医疗数据，但没做过传统信息系统开发 | 中长期补 |
| Agent 架构设计 | 三工具主循环 + 8 轮安全阀 + on_event 回调，有一定设计 | 基本满足，需文档化 |
| 大模型部署 | 直接调 DeepSeek API，没做过本地部署 | 缺 |
| 大模型微调 | 没做过 | 缺 |

## 给 Codex 的任务清单（按优先级）

### P0 — 比赛前必须完成（2026-10-31 前）
- [ ] 把 README 里的"为什么选 ReAct 式 Function Calling"补成一段（对比 Planning 架构为什么不适合本项目）
- [ ] README 加一节"简历项目描述"——按视频标准写 200 字，可直接复制到简历
- [ ] 跑通 `python evaluate.py` 并确认 evaluation_results.csv 是最新的

### P1 — 比赛后 1 个月内（2026-11 月）
- [ ] 扩充评估样本到 20+ 例（从 VitalDB 下载多份不同患者波形）
- [ ] 心率检测参数网格搜索（prominence 0.1-1.0 × distance 0.3-0.6），把误差从 5.7 次/分降下来
- [ ] ASA 规则扩展字段（BMI≥30 至少 II、急诊手术升一级、恶性肿瘤至少 III）
- [ ] 部署到 Streamlit Community Cloud（免费公网 Demo）

### P2 — 寒假（2027 年 1-2 月）
- [ ] 学习 Ollama 本地部署一个小模型（Qwen2.5-7B），能跑通本地推理——补"大模型部署"差距
- [ ] 做 FHIR（快速医疗互操作资源）接入：把 get_patient_record 改成从 FHIR Bundle 解析患者数据
- [ ] 帮队友郭羿妤做 ECG+PPG 血压预测的数据预处理（和 PeriRisk 的波形处理模块复用）

### P3 — 大三下（2027 春）
- [ ] 基于 PeriRisk 写一篇课程论文或大作业（DSP 课、传感课都可以挂靠）
- [ ] 整理一份"PeriRisk 技术博客"（GitHub Pages 或知乎），讲开发过程和踩坑
- [ ] 开始投暑期实习（医疗 AI 方向）

## 学习路径建议（给 Codex 参考，不要一次全推）

1. **不要先补 Java**——PeriRisk 是 Python 项目，简历主打 Python Agent 开发够用，Java 是中期进传统医疗信息系统才需要
2. **优先补大模型部署**——Ollama 部署 Qwen2.5 是入门门槛最低的，1 周能跑通，简历上能写"本地部署开源大模型"
3. **不要先学微调**——微调需要大量标注数据和 GPU，本科阶段先把"用 API 做 Agent 应用"做深，微调是研究生或实习后再碰的方向
4. **wPINN（加权物理信息神经网络）方向**——和队友交叉，他做 ECG/PPG 血压预测，PeriRisk 未来可以加一个"无袖带血压预测"工具（从 PPG 波形直接算收缩压），既是项目增量也是简历亮点

## 已有的外部参考资料（不要重复搜索，直接读）

- B 站视频《Agent开发上岸，简历要具备哪些能力？》UP 主「黑马尼古拉斯阿玮」，BV1NE9DBSE5s：https://www.bilibili.com/video/BV1NE9DBSE5s/
- 论文《Toward Noninvasive Calibration-Free Blood Pressure Estimation: A Physics-Informed Neural Network With Hemodynamic Priors》（IEEE, 2026）：https://www.computer.org/csdl/journal/tm/2026/04/11223230/2bgx0NC09tm —— ECG+PPG 做无袖带血压，VitalDB 评估，MAE 13.10 mmHg
- 论文《PITN: Physics-Informed Temporal Networks for Cuffless Blood Pressure Estimation》（arXiv 2408.08488）：https://arxiv.org/html/2408.08488
- 综述《Cardiovascular Digital Twins from Physics Based to Data Driven Approaches》（arXiv 2608.02135）：https://arxiv.org/html/2608.02135v1

## 沟通风格约定

- 回复要**具体到函数名、参数值、命令**，不要"建议优化一下性能"这种空话
- 英文缩写第一次出现附中文解释（如 PPG=光电容积脉搏波）
- 不要替他做医疗临床判断——项目里所有"医疗建议"都要带"教学演示用，不构成医疗建议"声明
- 他是 BME 学生不是 CS 科班，遇到新概念先讲原理再给代码
