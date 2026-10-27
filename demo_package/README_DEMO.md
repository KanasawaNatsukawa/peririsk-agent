# PeriRisk 线下组会演示包

## 现场先做什么

1. 先打开 `slides/PeriRisk_组会汇报_5病例.pdf`，不要先打开 PowerPoint。
2. 讲完架构后，如果要现场演示代码，进入 `code/`，运行：

```powershell
python demo_asa_cases.py
```

这个脚本只依赖标准 Python，不调用 API，不需要安装 `scipy` 或 `requests`。

3. 如果要展示完整 Agent 流程，优先用 PPT 里的两张界面截图；`video/` 里的录屏是可选项，不是必需项。

## 文件说明

| 路径 | 用途 |
|---|---|
| `slides/PeriRisk_组会汇报_5病例.pptx` | 可编辑源文件 |
| `slides/PeriRisk_组会汇报_5病例.pdf` | 现场优先打开，排版不会变 |
| `演讲备注_5病例.md` | 与 PPTX 备注同步的逐页演讲参考 |
| `references/` | 5 篇核心文献的阅读版 PDF、XML 原文与核验说明 |
| `code/demo_asa_cases.py` | 现场 ASA 规则演示，推荐 |
| `code/asa_risk.py` | 规则引擎源码，可打开讲解 |
| `data/evaluation_results.csv` | 5 例评估结果 |
| `assets/ui_thinking.png` | Agent 思考与工具调用截图 |
| `assets/ui_report.png` | 三段式报告截图 |
| `video/` | 可选的完整 Agent 录屏，不录也不影响主方案 |
| `record_cues.md` | 可选录屏时的逐页提示卡，现场播放 PPT 不需要 |

## 讲台电脑检查

- 打开 PowerShell，输入 `python --version`。
- 如果显示 Python 版本，现场可以运行 `demo_asa_cases.py`。
- 如果提示找不到 `python`，再试 `py --version`。
- 两者都没有，直接切到 PDF + 截图，不在台上安装环境。

## 安全边界

- U 盘里没有 `config.py`，也没有 API Key。
- 不要在现场运行完整 `peririsk_agent.py`；它需要 DeepSeek API Key，公共电脑不留密钥。
- 完整 Agent 用录屏展示，现场只跑确定性规则。

## 演示顺序

1. PDF 讲问题和架构。
2. `demo_asa_cases.py` 展示四个输入和输出。
3. 打开 `asa_risk.py`，只指出 `if / elif` 顺序和 `max(level, bp_floor)`。
4. 用 PPT 里的两张界面截图讲完整 Agent 流程。
5. 用 CSV 说明 5.7 是单份波形的对照，不是 5 位患者的平均。
