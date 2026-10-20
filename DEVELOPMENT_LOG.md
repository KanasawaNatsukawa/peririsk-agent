# PeriRisk 开发日志

> 本文档是给 AI 编程助手（Codex / Cursor / Copilot）和新贡献者看的"项目传记"。
> 记录开发时间线、关键决策、已知坑和优化方向。每次重大改动后请更新本文档。

---

## 一、项目定位

**PeriRisk** = 围术期麻醉风险评估智能体（Perioperative Risk Assessment Agent）。

- **核心功能**：输入患者基本信息 + 生命体征波形，自动输出 ASA 分级 + 三段式麻醉风险评估报告
- **技术架构**：三工具 Function Calling（LLM 只做调度和报告生成，关键计算走确定性代码）
- **参赛**：openJiuwen 智能体创意大赛（初赛提交截止 2026-10-31，初赛交创意 PPT + 补充材料）
- **GitHub**：git@github.com:KanasawaNatsukawa/peririsk-agent.git
- **演示界面**：Streamlit（`app.py`）

---

## 二、技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| Agent 主循环 | 自研 `peririsk_agent.py` | 三工具 Function Calling + 8轮强制收敛安全阀 |
| LLM | DeepSeek API（`llm.py`） | 负责工具调用决策和三段式报告生成 |
| 工具1 | `get_patient_record` | 读取患者档案（当前硬编码，未来接 FHIR） |
| 工具2 | `analyze_waveform` | PPG 峰值法算心率（scipy.signal.find_peaks） |
| 工具3 | `assess_asa_grade` | 规则引擎判 ASA 分级（确定性，非 LLM） |
| 防幻觉 | 字段白名单 + 结论附依据 | 系统提示词限制 LLM 只能写工具返回的字段 |
| 前端 | Streamlit（`app.py`） | 展示思考过程 + 工具调用 + 最终报告 |
| 评估 | `evaluate.py` | 批量跑病例，输出 CSV |

---

## 三、开发时间线

### 第1周（9.28 - 10.5）：MVP 搭建

**完成内容**：
- 从零搭建 `peririsk_agent.py` 主循环，实现三工具 Function Calling
- `analyze_waveform.py`：scipy.signal.find_peaks 峰值法，prominence=0.5（经验值，未调优），distance=0.5
- `asa_risk.py`：规则引擎，6 个字段（年龄、冠心病、糖尿病、肾衰、血压、不稳定状态）
  - 基础规则：不稳定→IV/V、肾衰+冠心病→IV、冠心病或糖尿病→III、≥65岁→II、否则I
  - 血压地板：SBP≥180→至少III、140-179→至少II、取max
- `llm.py`：DeepSeek 调用，三段式报告模板（术前评估/术中风险/术后建议），每段带"（依据：…）"
- 防幻觉机制：字段白名单系统提示词（工具未返回的信息如性别/舒张压/造影结果禁止写入）
- 8轮安全阀：超过8轮未收敛则强制输出
- 5 个手工构造病例（张三68冠心病→III、李四45健康→I、王秀兰72→II、陈伟50高血压→II、赵芳82不稳定→V）

**评估结果**：
- ASA 一致率 5/5 = 100%（但样本太小，无统计说服力）
- 工具调用顺序正确率 5/5 = 100%
- 心率算法误差：基于 VitalDB waveform_120s.csv，算法 88.0 bpm vs 监护仪参考 82.3 bpm，误差 5.7 次/分（相对 6.9%）

**关键决策**：
- ASA 分级用规则引擎而不是纯 LLM → 可解释、可复现、防幻觉
- 心率用 PPG 峰值法而不是深度学习 → 轻量、可解释、demo 够用
- 防幻觉用字段白名单而不是让 LLM 自己判断 → 实测 LLM 会编造性别、舒张压等字段

---

### 第2周（10.6 - 10.12）：评估体系 + 界面 + 竞品调研

**完成内容**：
- `evaluate.py`：批量评估脚本，输出 `evaluation_results.csv`（5例 + 统计行，utf-8-sig）
- `app.py`：Streamlit 界面，两屏展示
  - 屏1：Agent 多轮思考与工具调用过程（ui_thinking.png）
  - 屏2：三段式评估报告输出（ui_report.png）
- `heartbeat_demo.py`：心率算法教学演示脚本
- GitHub 同类医疗 Agent 调研（5个项目）：
  - ClearPath（jbrodev，MIT）：https://github.com/jbrodev/clearpath
  - RiskAgent（AI-in-Health）：https://github.com/AI-in-Health/RiskAgent + arXiv:2503.03802
  - MedAgent-Pro（NUS+牛津 jinlabimvr）：https://github.com/jinlabimvr/MedAgent-Pro + arXiv:2503.18968
  - MedAgentBench（斯坦福 ML）：https://github.com/stanfordmlgroup/MedAgentBench + arXiv:2501.14654
  - Microsoft HAO：https://github.com/Azure-Samples/healthcare-agent-orchestrator
- 参赛 PPT 初版（7页模板）

**发现的问题**：
- 心率误差 5.7 bpm 偏大，prominence=0.5 是经验值未调优
- 5 例共用同一份波形，无多样性
- ASA 规则只有 6 字段，未纳入 BMI、吸烟史、手术类型等真实分级因素

---

### 第3周（10.13 - 10.19）：组会汇报 + 优化规划

**完成内容**：
- 组会汇报 PPT（19页，含完整参考文献14条，具体到期刊卷期页码）
  - 老师反馈：第一次汇报"不够具体，都是AI精炼总结" → 本次极度详细化
  - P15 列出5点不足及优化方案
- 参赛 PPT 扩页（7→11页），官方确认可加页
- 补充材料打包（PeriRisk_补充材料.zip，含6份说明文档）
- 确定两周优化计划（前三点不足）：
  1. 样本量 5→20例，波形 1→15-20份
  2. 心率 MAE 5.7→≤3.0 bpm（网格搜索 + 带通滤波）
  3. ASA 规则 6字段→12+字段（BMI/吸烟/急诊/肿瘤等）

---

### 第4周（10.20 - 10.26）：优化执行中

**当前状态**：优化计划执行中，待更新。

---

## 四、关键决策记录（ADR）

### ADR-001：ASA 分级用规则引擎而非纯 LLM
- **日期**：2026-09-30
- **决策**：ASA 分级由 `assess_asa_grade.py` 规则引擎计算，LLM 只负责生成报告文本
- **原因**：LLM 对 ASA 分级的一致性差（不同 prompt 给不同结果），规则引擎可解释、可复现、可单元测试
- **代价**：规则覆盖不全时会漏判，需持续扩展字段

### ADR-002：心率用 PPG 峰值法而非深度学习
- **日期**：2026-10-01
- **决策**：用 scipy.signal.find_peaks 检测 PPG 波峰算心率
- **原因**：轻量（无需模型文件）、可解释（每个峰值可见）、比赛 demo 够用
- **代价**：低质量波形上误差大（当前 5.7 bpm），需加滤波和参数调优
- **未来**：可换 NeuroKit2 库或 1D-CNN，但当前阶段不做

### ADR-003：防幻觉用字段白名单
- **日期**：2026-10-02
- **决策**：系统提示词明确列出"允许写入报告的字段清单"，工具未返回的字段禁止出现
- **原因**：实测 DeepSeek 会编造患者性别、舒张压、造影结果等工具未返回的信息
- **效果**：5例评估中无幻觉字段
- **补充**：报告中每个结论必须附"（依据：工具返回的XXX字段）"

### ADR-004：患者数据硬编码而非接数据库
- **日期**：2026-09-29
- **决策**：当前患者数据硬编码在 `patient.py`，评估时从 JSON 读取
- **原因**：比赛 demo 阶段不需要真实 HIS 对接，硬编码最简单
- **未来**：DEMO 阶段（11/15-12/27）计划实现 FHIR Patient/Observation 资源解析器

---

## 五、已知坑（别再踩）

1. **prominence=0.5 在低质量波形上会漏检** → 需加 0.5-8Hz 带通滤波预处理
2. **5例 100% ASA 一致率是过拟合** → 扩充到20例后准确率会下降但更真实，这是正常的
3. **心率误差 5.7 bpm 的正确口径**：是基于 VitalDB 示范波形 waveform_120s.csv 的算法值(88.0)与监护仪参考值(82.3)的对照，**不是**5位患者平均误差
4. **config.py 里的 DeepSeek API key 已在 .gitignore** → 不要提交，不要在代码里硬编码 key
5. **`<border width>` 只接受正整数** → 写 1.5 会被服务端 4000153 拦截（这是飞书 PPT 的坑，不是代码）
6. **PowerShell 5.1 重定向文件默认 UTF-16 + BOM** → 读写 CSV 用 Python，不要用 `>` / `Out-File`

---

## 六、当前评估数据（基线）

| 指标 | 值 | 口径 |
|---|---|---|
| 病例数 | 5 | 手工构造 |
| ASA 一致率 | 5/5 = 100% | 与人工标注对比 |
| 工具调用顺序正确率 | 5/5 = 100% | get_patient→analyze_waveform→assess_asa |
| 心率 MAE | 5.7 bpm | 单份 VitalDB 波形对照 |
| 心率相对误差 | 6.9% | 5.7 / 82.3 |
| ASA 规则字段数 | 6 | 年龄/冠心病/糖尿病/肾衰/血压/不稳定 |
| 波形份数 | 1 | waveform_120s.csv |

---

## 七、优化目标（两周计划，截止 11.03 组会）

| 指标 | 当前 | 目标 | 做法 |
|---|---|---|---|
| 病例数 | 5 | 20 | 覆盖 I-V 各级 + 2-3 例边界病例 |
| 波形份数 | 1 | 15-20 | VitalDB 下载不同患者 PLETH 通道 |
| 心率 MAE | 5.7 bpm | ≤3.0 bpm | 网格搜索 prominence×distance + 0.5-8Hz 带通滤波 |
| ASA 规则字段 | 6 | 12+ | BMI≥30→II、吸烟≥10年→II、急诊升一级、恶性肿瘤→III |
| 评估输出 | 单一准确率 | 混淆矩阵 + 各级 F1 | evaluate.py 输出 5×5 混淆矩阵 |

---

## 八、文件结构

```
peririsk-demo/
├── peririsk_agent.py      # Agent 主循环（三工具调度 + 8轮安全阀）
├── asa_risk.py            # ASA 分级规则引擎（确定性）
├── llm.py                 # DeepSeek API 封装 + 三段式报告模板
├── patient.py             # 患者档案（当前硬编码）
├── evaluate.py            # 批量评估脚本
├── app.py                 # Streamlit 界面
├── heartbeat_demo.py      # 心率算法教学演示
├── config.py              # API key（.gitignore，不提交）
├── data/
│   ├── waveform_120s.csv  # VitalDB 示范 PPG 波形（120秒，100Hz）
│   └── numeric_60s.csv    # 生命体征数值
├── images/
│   ├── ui_thinking.png    # 界面截图：思考过程
│   └── ui_report.png      # 界面截图：报告输出
├── evaluation_results.csv # 批量评估结果
├── README.md              # 项目说明（面向人）
├── DEVELOPMENT_LOG.md     # 本文档（面向 AI + 贡献者）
└── submission_materials/  # 参赛补充材料
```

---

## 九、参考文献（组会 PPT P19 完整引用）

1. Hawes RH, et al. Anaesthesia. 2016;71(3):273-279. doi:10.1111/anae.13340
2. Compère V, et al. Anesth Analg. 2022;134(3):496-504. doi:10.1213/ANE.0000000000005889
3. Sankar A, et al. Br J Anaesth. 2014;113(3):424-432. doi:10.1093/bja/aeu100
4. 国家卫健委等七部门. 国卫医发〔2018〕21号. 2018年8月
5. 国家卫健委. 2025年医疗资源配置白皮书
6. Horvath B, et al. Anesthesiology. 2021;135(5):904-919. doi:10.1097/ALN.0000000000003967
7. Karim HMR. Turk J Anaesthesiol Reanim. 2021;49(2):186-189. PMC8098727
8. ANSI/AAMI EC57:2019 & ISO 80601-2-61:2017
9. JMIR. 2022;24(12):e42359. doi:10.2196/42359. PMC9840097
10. Omar M, et al. Commun Med. 2025;5:330. doi:10.1038/s43856-025-01021-3
11. Chang CT, et al. NPJ Digit Med. 2025;8:149. doi:10.1038/s41746-025-01542-0
12. Roustan D, Bastardot F. Interact J Med Res. 2025;14:e59823. doi:10.2196/59823
13. HL7 International. 2025 State of FHIR Survey Report
14. HL7 International. FHIR 10周年报告；美国CMS HTI-2最终规则

---

*最后更新：2026-10-20*
