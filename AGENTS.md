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
- 数据：VitalDB 公开生理数据集（5 个病例，每个 60 秒 PLETH 脉搏波，500Hz；同窗口 PLETH_HR/HR 作为监护仪参考）

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
| get_patient_record | 无 | 姓名/年龄/病史/收缩压/波形ID |
| analyze_waveform | waveform_id（可选）/ segment_seconds | 波形ID/分析秒数/检测心跳次数/算法心率/PLETH_HR/HR |
| assess_asa_grade | 6 个必填参数 | ASA 分级 |

## 文件地图

**公共模块（改一处全项目生效）**
- `asa_risk.py` — ASA 规则引擎（纯逻辑不调 AI）：基础规则 + 血压地板（取 max，只升不降）
- `patient.py` — 患者档案 PATIENTS 花名册 + build_summary 摘要拼接
- `llm.py` — DeepSeek 调用唯一入口（模型名、API 地址、系统提示词都在这一处）
- `runtime_state.py` — 当前评估患者的状态，`set_patient` / `get_patient`
- `tools/` — `patient_record.py`、`waveform.py`、`asa_grade.py` 和统一注册表

**主程序**
- `peririsk_agent.py` — **Agent 版（主推）**：只保留 run_agent 主循环和 on_event 回调钩子；工具从 `tools/` 导入
- `app.py` — Streamlit Web 界面（选患者 → 逐行看思考过程 → markdown 报告）
- `evaluate.py` — 离线批量评估（5 例，导出 evaluation_results.csv，utf-8-sig）
**数据与教学**
- `data_cases/` — 5 个不同 VitalDB 病例的配对 60 秒波形与 PLETH_HR/HR，当前唯一主数据

**比赛材料（不是代码，改动要谨慎）**
- `competition/ppt/` `competition/submission_materials/` `competition/checklist/` `competition/drafts/` `competition/research/` — openJiuwen 大赛材料，与运行逻辑无关

**文档与交付**
- `docs/` — 开发日志、术语表、理解计划、代码讲解、决策记录
- `demo_package/` — 线下组会演示包
- `deck_output/` — 组会 PPT、参考全文和核验记录
- `PROJECT_LAYOUT.md` — 当前目录结构说明

## 运行命令

```bash
pip install requests scipy numpy streamlit
# config.py 填 DeepSeek API Key（被 .gitignore 排除，本地才有）
python peririsk_agent.py              # 命令行 Agent（可带提示词参数）
python -m streamlit run app.py        # Web 界面
python evaluate.py                    # 5 例批量评估，导出 CSV
python -m unittest discover -s tests -v  # 15 项规则、病例和波形测试
```

## 关键约定（改代码必须遵守）

1. **config.py 绝不提交**，也不在任何代码里写死 API Key。config.py 被 .gitignore 排除，接手方本地需要自己填 Key。
2. **防幻觉三机制**：字段白名单（系统提示词限定只能引用工具返回字段，性别/舒张压/造影结果等禁止写）；结论附"（依据：…）"；8 轮强制收敛。**不要削弱这三条。**
3. **心率口径**：当前 `tools/waveform.py` 按患者绑定读取 `data_cases/case_001`–`case_005` 的 5 段不同 60 秒波形；算法心率范围 71–98，同源 PLETH_HR 平均差 1.5，综合 HR 平均差 1.9。这是 5 个病例的小样本，不是临床准确率。
4. **心率检测必须本地 scipy 算**（find_peaks，distance=fs*0.4=200 点，prominence=0.5），不要交给大模型猜。
5. ASA 规则"只升不降"：取 max(基础级别, 血压地板)，内部用数字 1-5 最后映射文案。
6. 当前只保留主 Agent 路径；患者病例和波形都从 `data_cases/` 读取。
7. 新函数改动尽量复用 on_event 回调设计，CLI 和 Web 共用一份主循环逻辑。
8. 输出 CSV 用 utf-8-sig 编码（Excel 打开不乱码）。

## 当前待办/优化方向（按优先级）

1. 扩充评估样本到 20+ 例，从 VitalDB 下载更多不同患者波形（当前为 5 个病例）
2. 心率检测参数网格搜索（prominence 0.1-1.0 × distance 0.3-0.6）降低误差
3. ASA 规则扩展字段（BMI≥30 至少 II、急诊手术升一级、恶性肿瘤至少 III）
4. 接入 FHIR 标准（get_patient_record 改为从 FHIR Bundle 解析）
5. 界面加"医生修正"反馈闭环
6. Streamlit 部署到 Community Cloud（免费公网 Demo）
7. 增加 Agent 端到端测试（当前已有 15 项规则、病例和工具单元测试）

## 参赛背景（了解优先级用）

openJiuwen 智能体创意大赛：创意评审已提交（2026-10-31 截止创意），DEMO 开发阶段 11/15–12/27，决赛 2027 年 1 月底。获奖需签 CLA + Apache-2.0 开源（已开源在 GitHub: KanasawaNatsukawa/peririsk-agent）。
