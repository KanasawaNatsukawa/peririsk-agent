# AGENTS.md — PeriRisk Agent 项目交接说明

> 本文件供 AI 编码助手（Codex 等）快速接手项目使用。先读本文件，再读 README.md，最后按需深入具体模块。

## 项目一句话

围术期麻醉风险评估 Agent：输入患者基本信息 + 生命体征，Agent 通过 Function Calling 自主调度三个工具（查病历 / PPG 波形算心率 / ASA 规则分级），最后调 DeepSeek 大模型生成三段式术前风险评估报告。

**定位：教学/演示项目，不是医疗器械，不构成医疗建议。ASA 分级逻辑是简化版。**

## 技术栈

- Python 3.11+（本项目在 3.14 下开发运行）
- DeepSeek API（Function Calling 模式，走 requests 直连，**不用 openai 库**）
- scipy（信号处理，找 PPG 峰值算心率）
- Streamlit（Web 界面）
- 数据：VitalDB 公开生理数据集（waveform_120s.csv 脉搏波 500Hz；numeric_60s.csv 监护仪参考心率）

## 核心架构（最重要）

**大模型负责决策调度，本地代码负责确定性计算。** 大模型不直接算心率、不直接判级，只负责"决定调用哪个工具、传什么参数"。

Agent 主循环（peririsk_agent.py 的 run_agent）：
1. messages = [系统提示词, 用户任务]
2. 调 DeepSeek，把三个工具的 JSON Schema 一并传入
3. 返回含 tool_calls → 执行对应本地函数；只有 content → 信息够了直接出报告
4. 工具结果以 role=tool 回填（凭 tool_call_id 对账），循环最多 8 轮（MAX_ROUNDS=8 安全阀）

三个工具：
| 工具 | 参数 | 返回 |
|---|---|---|
| get_patient_record | 无 | 年龄/冠心病/糖尿病/肾功能不全/病情不稳定/收缩压 |
| analyze_waveform | segment_seconds | 分析秒数/检测心跳次数/算法心率/监护仪对照心率 |
| assess_asa_grade | 6 个必填参数 | ASA 分级 |

## 文件地图

**公共模块（改一处全项目生效）**
- `asa_risk.py` — ASA 规则引擎（纯逻辑不调 AI）：基础规则 + 血压地板（取 max，只升不降）
- `patient.py` — 患者档案 PATIENTS 花名册 + build_summary 摘要拼接
- `llm.py` — DeepSeek 调用唯一入口（模型名、API 地址、系统提示词都在这一处）

**主程序**
- `peririsk_agent.py` — **Agent 版（主推）**：run_agent 主循环 + 三工具实现 + on_event 回调钩子（CLI/Web 共用）
- `app.py` — Streamlit Web 界面（选患者 → 逐行看思考过程 → markdown 报告）
- `evaluate.py` — 离线批量评估（5 例，导出 evaluation_results.csv，utf-8-sig）
- `peririsk_agent_v1b.py` / `peririsk_agent_final.py` / `peririsk_real.py` — 历史流水线版（v1b 最小流水线 / final 整合模拟波形 / real 接真实数据）
- `peririsk_agent_v1.py` — 已弃用（openai 库发中文卡住，被 v1b 取代）

**数据与教学**
- `data/` — waveform_120s.csv、numeric_60s.csv
- `heartbeat_demo.py` — 心率检测教学
- `_*.py` — 波形峰检测调试草稿（可忽略）
- `test_deepseek.py` — 测 DeepSeek 连接

**比赛材料（不是代码，改动要谨慎）**
- `ojw_ppt_edit/` `submission_materials/` `ojw_checklist/` `draft_93c7dc6b_folder/` — openJiuwen 大赛 PPT/补充材料，与运行逻辑无关

## 运行命令

```bash
pip install requests scipy numpy matplotlib streamlit
# config.py 填 DeepSeek API Key（被 .gitignore 排除，本地才有）
python peririsk_agent.py              # 命令行 Agent（可带提示词参数）
python -m streamlit run app.py        # Web 界面
python evaluate.py                    # 5 例批量评估，导出 CSV
python test_deepseek.py               # 测 API 连接
```

## 关键约定（改代码必须遵守）

1. **config.py 绝不提交**，也不在任何代码里写死 API Key。config.py 被 .gitignore 排除，接手方本地需要自己填 Key。
2. **防幻觉三机制**：字段白名单（系统提示词限定只能引用工具返回字段，性别/舒张压/造影结果等禁止写）；结论附"（依据：…）"；8 轮强制收敛。**不要削弱这三条。**
3. **心率口径**：误差 5.7 次/分 = 基于 VitalDB 示范波形的算法心率 88.0 vs 监护仪参考 82.3 的单例对照值，**不是 5 位患者平均误差**（5 例共用同一份波形）。
4. **心率检测必须本地 scipy 算**（find_peaks，distance=fs*0.4=200 点，prominence=0.5），不要交给大模型猜。
5. ASA 规则"只升不降"：取 max(基础级别, 血压地板)，内部用数字 1-5 最后映射文案。
6. 命令行参数、工具参数、报告格式与已有输出保持向后兼容；旧调用方（v1b/final）一行不改也能运行。
7. 新函数改动尽量复用 on_event 回调设计，CLI 和 Web 共用一份主循环逻辑。
8. 输出 CSV 用 utf-8-sig 编码（Excel 打开不乱码）。

## 当前待办/优化方向（按优先级）

1. 扩充评估样本到 20+ 例，从 VitalDB 下载多份不同患者波形（当前 5 例共用一份波形）
2. 心率检测参数网格搜索（prominence 0.1-1.0 × distance 0.3-0.6）降低误差
3. ASA 规则扩展字段（BMI≥30 至少 II、急诊手术升一级、恶性肿瘤至少 III）
4. 接入 FHIR 标准（get_patient_record 改为从 FHIR Bundle 解析）
5. 界面加"医生修正"反馈闭环
6. Streamlit 部署到 Community Cloud（免费公网 Demo）
7. 加单元测试（目前无测试覆盖）

## 参赛背景（了解优先级用）

openJiuwen 智能体创意大赛：创意评审已提交（2026-10-31 截止创意），DEMO 开发阶段 11/15–12/27，决赛 2027 年 1 月底。获奖需签 CLA + Apache-2.0 开源（已开源在 GitHub: KanasawaNatsukawa/peririsk-agent）。
