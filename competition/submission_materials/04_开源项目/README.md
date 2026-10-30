# PeriRisk Agent

围术期风险评估演示项目。输入患者的基本信息和生命体征，程序先自己算出 ASA 麻醉分级和心率，再调用 DeepSeek 大模型生成一份术前风险评估报告。

> 教学/演示用，不是医疗器械，不构成医疗建议。ASA 分级逻辑是简化版，跟临床完整标准有差异。

## 界面预览

选择患者后，Agent 按任务调用「查病历 → 数据质量检查 → 波形心率检测 → 稳定性复核 → ASA 规则分级」，思考过程与每次工具返回逐条可见：

![Agent 思考过程与工具调用轨迹](images/ui_thinking.png)

信息集齐后生成三段式报告（风险评估 / 麻醉关注点 / 建议），每条结论句末标注引用的工具返回依据：

![三段式术前风险评估报告](images/ui_report.png)

网页第二个标签页是「数字孪生推演」，用于现场演示患者状态变化，不调用大模型：

![数字孪生推演舱](images/twin_case_004_60s_selected.png)

推演舱可以切换患者、查看 5/10/30/60 秒 PPG 与检测峰、拖动虚拟收缩压观察 ASA 变化，并注入「缺少收缩压 / 波形平直 / 心率冲突」三类故障，查看 Agent 工具路径如何随之变化。每个病例保存 120 秒原始数据，本地工具按异常点、缺失率和前后半段心率稳定性自动选择 60 秒分析窗口，不读取参考心率来挑答案。所有推演都在内存中完成，不修改病例文件。

推演舱还支持实时调整 BMI、活动性恶性肿瘤、急诊手术和困难气道；急诊使用 `E` 标识，困难气道作为额外关注，不会伪造 ASA 数字等级。

![扩展 ASA 参数](images/twin_extended_asa.png)

![候选窗口质量热力图](images/twin_window_heatmap.png)

热力图按时间顺序展示全部 13 个候选窗口，黄色边框标记工具选择；“同源差”只用于评估，不参与选窗。

推演页还会对比固定首窗、仅信号质量、当前“质量 + 稳定性”和参考最优上界四种策略；其中参考最优只用于评估，不能用于实际选窗。

![选窗策略对比](images/twin_window_policy.png)

## 怎么用

1. 装依赖：`pip install requests scipy numpy streamlit`
2. 去 DeepSeek 开放平台创建 API Key，填进 `config.py`
3. 两种入口：
   - **命令行 Agent**：`python peririsk_agent.py`（可带提示词参数）
   - **Web 界面**：`python -m streamlit run app.py`（浏览器里选患者、看思考过程和报告）
4. 离线批量评估：`python evaluate.py`（对 5 个测试病例跑 Agent，打印汇总表并导出 `evaluation_results.csv`）
5. 全候选窗口评估（不调用大模型）：`python evaluate.py --windows-only`
6. 心率参数网格搜索（不调用大模型）：`python evaluate.py --tune-heart-rate`

`config.py` 已经被 .gitignore 排除，不要提交它，也不要在任何代码里写死 key。

## 结构

公共模块（改一处，全项目生效）：
- `asa_risk.py` — ASA 分级规则引擎（纯逻辑，不调 AI；已纳入收缩压，见下方规则）
- `patient.py` — 患者档案 + 摘要拼接；内置 20 个病例花名册 `PATIENTS`，网页与评估共用
- `llm.py` — DeepSeek 调用（提示词、模型名、接口地址都在这一处）
- `runtime_state.py` — 当前运行患者的切换状态
- `tools/` — 五个工具的本地实现、JSON Schema 和注册表
- `report_guard.py` — 对最终报告执行程序化字段、章节和依据校验
- `twin_lab.py` — 数字孪生推演舱的确定性计算：血压分级、波形视图、故障注入和工具路径
- `deck_output/PeriRisk_核心参考文献_原文/references/` — 5 篇核心文献，全部附可阅读全文 PDF（XML 原文件同时保留）

主程序：
- `peririsk_agent.py` — **Agent 版（主推）**：DeepSeek 通过 function calling 自主调度工具（Agent 循环），带彩色思考过程和 loading 动画
- `app.py` — Streamlit Web 界面：临床评估 + 数字孪生推演；PPG 使用原生 ECharts 绘制
- `evaluate.py` — 离线批量评估：工具调用顺序、ASA 分级一致性、心率误差，导出 CSV
- `window_evaluation_results.csv` — 20 个病例 × 13 个候选窗口的全部逐窗指标
- `window_evaluation_summary.csv` — 选中窗口与全部候选窗口的汇总对比
- `window_policy_comparison.csv` — 四种选窗策略的逐病例误差与最终窗口
- `heart_rate_parameter_search.csv` — 40 组 prominence × distance 参数搜索结果

数据：
- `data_cases/` — 20 个不同 VitalDB 病例的配对 120 秒波形，患者与波形 ID 一一绑定

完整目录、测试、文档和比赛材料的位置见 `PROJECT_LAYOUT.md`。

## 流程

患者信息 → Agent 自主查病历、检查数据质量、分析波形心率并按需比较窗口、调用 ASA 规则引擎 → DeepSeek 写三段式报告。

五个工具：

- `get_patient_record` — 查病历（年龄、既往史、BMI、收缩压、急诊和气道信息）
- `validate_case_data` — 检查病历字段、波形缺失值和信号质量
- `analyze_waveform` — 从 120 秒脉搏波中选择质量最好且最稳定的 60 秒，返回分析窗口、算法心率、PLETH_HR 与综合 HR
- `compare_hr_windows` — 比较多个时间窗口，判断心率结果是否稳定
- `assess_asa_grade` — 规则引擎综合既往史、BMI、活动性肿瘤、收缩压、急诊标识和困难气道

报告里**每一条结论句末都附"（依据：…）"**，标注它引用了哪个工具的哪个返回值；模型只能引用工具真实返回的字段。生成后还会由 `report_guard.py` 检查必需章节、禁止字段和依据格式。

## ASA 分级规则（简化演示版）

基础规则：病情不稳定 → IV/V 级；肾衰+冠心病叠加 → IV；有冠心病、糖尿病或活动性恶性肿瘤 → III；BMI 30–39.9 至少 II；BMI ≥40 至少 III；≥65 岁健康 → II；否则 I。

血压地板（与基础级别取高，只升不降）：收缩压 ≥180 → 至少 III；140–179 → 至少 II；<140 或未提供 → 不影响。

急诊手术使用 ASA 的 `E` 标识，不自动抬高数字等级；困难气道作为额外的围术期关注，不改变 ASA 数字等级。

心率参数搜索基于全部 260 个候选窗口。20 例复核后，`prominence=0.5 / distance=0.4` 仍是稳健评分最优的平台之一，因此默认值不需要调整。

## 后面想做的

- ASA 分级补全更多并发症维度（舒张压、靶器官损害等）
- 继续扩充到 50+ 个不同患者病例
- 加无袖带血压预测（PINN 方向）
- 用 JiuwenSwarm 做多 Agent 协作版
