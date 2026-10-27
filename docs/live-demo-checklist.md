# 现场代码与运行演示清单

## 演示结构

不要试图在讲台电脑上完整跑 DeepSeek Agent。现场演示分三层：

1. **本地确定性代码**：现场运行 ASA 规则脚本，不依赖 API。
2. **代码讲解**：打开 `peririsk_agent.py`，只讲 `run_agent` 的 `messages → tool_calls → 本地执行 → tool_call_id 回填`。
3. **完整 Agent 轨迹**：用真实运行截图或 60–90 秒录屏展示完整流程。

## 现场最稳的 3 分钟流程

### 0:00–0:40 讲问题和架构

一句话：大模型负责调度，ASA 和心率由本地代码计算。

### 0:40–1:40 现场跑 ASA

```powershell
cd demo_package\code
python demo_asa_cases.py
```

展示四个输出：

- 50 岁、SBP 146 → II
- 55 岁糖尿病、SBP 185 → III
- 82 岁不稳定 → V
- 冠心病 + 肾衰 → IV

### 1:40–2:20 讲代码

打开 `peririsk_agent.py`，只指出四处：

- `messages = [system, user]`
- `chat_with_tools(messages, TOOLS)`
- `TOOL_FUNCTIONS[name](**args)`
- `messages.append({"role": "tool", "tool_call_id": ...})`

### 2:20–3:00 展示完整 Agent

打开 `ui_thinking.png` 和 `ui_report.png`，或播放 60–90 秒真实录屏。

说明：完整 Agent 需要 DeepSeek API 和网络，现场用真实轨迹展示；ASA 和心率计算已经现场跑过。

## 需要带的东西

- U 盘：`demo_package/`、`data_aligned/`、最终 PPTX 和 PDF
- 两张截图：`ui_thinking.png`、`ui_report.png`
- 一段 60–90 秒完整 Agent 录屏（可选但强烈建议）
- USB-C/HDMI 转接头、充电线
- 手机热点备用

不要带 `config.py`，不要在讲台电脑上输入 API Key。

## 到场检查

1. 打开 PowerShell，运行 `python --version`。
2. 如果能显示版本，再运行 `python demo_asa_cases.py`。
3. 如果提示找不到 Python，直接切到 PDF + 截图 + 录屏。
4. 检查投影分辨率，PDF 优先于 PPT 编辑界面。

## 如果老师要求“完整跑一遍”

先说明现场约束：

> 完整 Agent 需要 DeepSeek API Key 和网络，公共电脑不适合保存密钥；ASA、心率工具已经现场运行。完整轨迹这里用真实运行录屏展示。

然后播放录屏。不要在台上现场安装依赖或输入 Key。
