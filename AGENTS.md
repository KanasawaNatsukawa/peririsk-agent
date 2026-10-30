# AGENTS.md — PeriRisk Agent 项目交接说明

> 本文件供 AI 编码助手（Codex 等）快速接手项目使用。先读本文件，再读 README.md，最后按需深入具体模块。

## 项目一句话

围术期麻醉风险评估 Agent：输入患者基本信息 + 生命体征，Agent 通过 Function Calling 自主调度五个工具（查病历 / 数据质量 / PPG 波形算心率 / 窗口稳定性 / ASA 规则分级），最后调 DeepSeek 大模型生成三段式术前风险评估报告，并执行程序化报告校验。

**定位：教学/演示项目，不是医疗器械，不构成医疗建议。ASA 分级逻辑是简化版。**

## 技术栈

- Python 3.11+（本项目在 3.14 下开发运行）
- DeepSeek API（Function Calling 模式，走 requests 直连，**不用 openai 库**）
- scipy（信号处理，找 PPG 峰值算心率）
- Streamlit（Web 界面；推演舱使用原生 `st.echarts_chart` 绘制 PPG）
- 数据：VitalDB 公开生理数据集（20 个病例，每个 120 秒 PLETH 脉搏波，500Hz；工具在运行时选择 60 秒分析窗口，同窗口 PLETH_HR/HR 作为监护仪参考）

## 核心架构（最重要）

**大模型负责决策调度，本地代码负责确定性计算。** 大模型不直接算心率、不直接判级，只负责"决定调用哪个工具、传什么参数"。

Agent 主循环（peririsk_agent.py 的 run_agent）：
1. messages = [系统提示词, 用户任务]
2. 调 DeepSeek，把五个工具的 JSON Schema 一并传入
3. 返回含 tool_calls → 执行对应本地函数；只有 content → 信息够了直接出报告
4. 工具结果以 role=tool 回填（凭 tool_call_id 对账），循环最多 10 轮（MAX_ROUNDS=10 安全阀）

五个工具：
| 工具 | 参数 | 返回 |
|---|---|---|
| get_patient_record | 无 | 姓名/年龄/病史/BMI/收缩压/急诊/困难气道/波形ID |
| validate_case_data | waveform_id（可选）/ segment_seconds | 病历完整性/采样点/有效比例/波形质量 |
| analyze_waveform | waveform_id（可选）/ segment_seconds | 波形ID/分析秒数/检测心跳次数/算法心率/PLETH_HR/HR |
| compare_hr_windows | waveform_id（可选）/ windows_seconds / max_difference | 各窗口心率/最大差值/是否稳定 |
| assess_asa_grade | 10 个必填参数（含 BMI、活动性肿瘤、急诊、困难气道） | ASA 分级、E 标识、气道关注 |

## 文件地图

**公共模块（改一处全项目生效）**
- `asa_risk.py` — ASA 规则引擎（纯逻辑不调 AI）：基础规则 + 血压地板（取 max，只升不降）
- `patient.py` — 患者档案 PATIENTS 花名册 + build_summary 摘要拼接
- `llm.py` — DeepSeek 调用唯一入口（模型名、API 地址、系统提示词都在这一处）
- `runtime_state.py` — 当前评估患者的状态，`set_patient` / `get_patient`
- `report_guard.py` — 生成后的章节、禁止字段和依据格式校验
- `twin_lab.py` — 数字孪生推演舱的纯本地计算，不调用大模型
- `tools/` — 五个工具的实现和统一注册表

**主程序**
- `peririsk_agent.py` — **Agent 版（主推）**：只保留 run_agent 主循环和 on_event 回调钩子；工具从 `tools/` 导入
- `app.py` — Streamlit Web 界面（临床评估 + 数字孪生推演两个标签页）
- `evaluate.py` — 离线批量评估（20 例，导出 evaluation_results.csv，utf-8-sig）
**数据与教学**
- `data_cases/` — 20 个不同 VitalDB 病例的配对 120 秒波形与 PLETH_HR/HR，当前唯一主数据

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
python evaluate.py                    # 20 例批量评估，导出 CSV
python evaluate.py --windows-only      # 260 个候选窗口确定性评估，不调用大模型
python evaluate.py --tune-heart-rate    # 40 组 prominence × distance 搜索，不调用大模型
python -m unittest discover -s tests -v  # 42 项规则、病例、波形、路径、报告和页面测试
```

## 关键约定（改代码必须遵守）

1. **config.py 绝不提交**，也不在任何代码里写死 API Key。config.py 被 .gitignore 排除，接手方本地需要自己填 Key。
2. **防幻觉三机制**：字段白名单（系统提示词限定只能引用工具返回字段，性别/舒张压/造影结果等禁止写）；结论附"（依据：…）"；10 轮强制收敛。**不要削弱这三条。**
3. **心率口径**：当前 `tools/waveform.py` 按患者绑定读取 `data_cases/` 中 20 段不同 120 秒波形；默认从 13 个候选 60 秒窗口中按数据质量和前后半段稳定性选窗，不使用参考心率挑窗。当前算法心率范围 54–101，同源 PLETH_HR 平均差 1.3，综合 HR 平均差 1.8。这是 20 个病例的工程验证，不是临床准确率。
4. **心率检测必须本地 scipy 算**（find_peaks，distance=fs*0.4=200 点，prominence=0.5），不要交给大模型猜。
5. ASA 规则"只升不降"：取 max(基础级别, 血压地板)，内部用数字 1-5 最后映射文案。
6. 当前只保留主 Agent 路径；患者病例和波形都从 `data_cases/` 读取。
7. 新函数改动尽量复用 on_event 回调设计，CLI 和 Web 共用一份主循环逻辑。
8. 输出 CSV 用 utf-8-sig 编码（Excel 打开不乱码）。
9. 数字孪生推演只做确定性模拟，不调用大模型、不写回病例；PPG 图继续使用 `st.echarts_chart`，避免内联 Altair 分层数据在部分版本中显示为空。
10. 波形显示异常与峰值检测异常分开处理：图中断开幅度哨兵和起始基线未稳定片段；峰值检测只对幅度哨兵局部插值，不能随意剔除正常脉搏波，否则会改变已核验的 60 秒心率。
11. 120 秒原始数据是唯一主数据；60 秒分析窗口必须由 `select_best_window` 按质量与稳定性选择，禁止用参考心率差异反向挑选窗口。
12. ASA 新增规则均为教学简化：BMI 30–39.9 至少 II、BMI ≥40 至少 III、活动性肿瘤至少 III；急诊只加 E 标识，困难气道不改变等级。

## 当前待办/优化方向（按优先级）

1. 继续扩充到 50+ 例，并按患者划分调参集和验证集
2. 与临床人员复核新增 ASA 简化规则
3. 接入 FHIR 标准（get_patient_record 改为从 FHIR Bundle 解析）
4. 界面加"医生修正"反馈闭环
5. Streamlit 部署到 Community Cloud（免费公网 Demo）
6. 增加 Agent 端到端测试（当前已有 42 项规则、病例、工具、路径、报告和页面测试）

## 参赛背景（了解优先级用）

openJiuwen 智能体创意大赛：创意评审已提交（2026-10-31 截止创意），DEMO 开发阶段 11/15–12/27，决赛 2027 年 1 月底。获奖需签 CLA + Apache-2.0 开源（已开源在 GitHub: KanasawaNatsukawa/peririsk-agent）。
