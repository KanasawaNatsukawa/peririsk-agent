# PeriRisk 理解债偿还计划

## 目标

不追求背下每一行代码，而是对项目每个模块都能回答六个问题：

1. 它接收什么输入？
2. 它产生什么输出？
3. 谁调用它，它又调用谁？
4. 为什么需要它，而不是把这件事交给大模型？
5. 出错或边界情况会发生什么？
6. 用什么命令或测试可以验证它？

能做到这六点，才算真正理解；只会说“AI 写的，能跑”不算。

## 项目主链路

```text
evaluate.py / app.py / 命令行
        ↓
peririsk_agent.run_agent(task, on_event)
        ↓
llm.chat_with_tools(messages, TOOLS)
        ↓
DeepSeek 返回 tool_calls
        ↓
TOOL_FUNCTIONS[name](**args)
        ↓
get_patient_record / analyze_waveform / assess_asa_grade
        ↓
结果以 role=tool 回填
        ↓
再问 DeepSeek，直到返回最终报告
```

## 模块顺序

| 顺序 | 模块 | 必须理解的内容 |
|---|---|---|
| 1 | `peririsk_agent.py` | `run_agent` 循环、工具注册、JSON Schema、`on_event` |
| 2 | `asa_risk.py` | 基础规则、血压地板、只升不降、回归测试 |
| 3 | `patient.py` | 患者字段、`PATIENTS`、`build_summary`、评估时替换患者 |
| 4 | `llm.py` | 请求格式、system prompt、tool calls、错误处理 |
| 5 | `evaluate.py` | `Trace`、调用顺序判断、ASA 一致性、心率误差、CSV |
| 6 | `app.py` | Streamlit 事件渲染、思考过程、报告展示 |
| 7 | `data/` | 波形采样率、60 秒参考心率、为什么 5.7 不是 5 人平均 |
| 8 | 历史版本 | v1b / final / real 各自解决了什么问题，为什么主推 Agent 版 |

## 学习方式

每个模块都按同一套动作：

1. 先画输入和输出；
2. 只读这个模块的主路径；
3. 用最小命令跑一次；
4. 故意问一个边界问题；
5. 合上代码，用自己的话复述；
6. 把结论写进决策记录。

不在一个模块没讲清时跳到下一个模块。

## 今日任务

先追一条最短的完整链路：

`evaluate.py` 选中一个患者 → `run_agent` 第一轮 → DeepSeek 返回工具调用 → 本地执行 → 结果回填 → 最终报告。

今天只要求讲清楚这条链路，不扩展到所有历史文件。

## 完成标准

- 能不看代码画出主链路；
- 能解释 `tool_call_id` 为什么必须回填；
- 能解释 `on_event` 为什么让 CLI 和 Web 共用一套循环；
- 能说出三个工具各自的输入、输出和失败方式；
- 能解释 `evaluate.py` 的“ASA 一致”到底在验证什么。
