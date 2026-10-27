# PeriRisk 项目目录说明

## 根目录只保留运行入口和公共模块

| 文件 | 用途 |
|---|---|
| `peririsk_agent.py` | 主 Agent 版本，三工具 Function Calling |
| `app.py` | Streamlit Web 界面 |
| `evaluate.py` | 5 例批量评估 |
| `asa_risk.py` | ASA 规则引擎 |
| `patient.py` | 患者档案与摘要 |
| `llm.py` | DeepSeek 调用入口 |
| `runtime_state.py` | 当前评估患者的运行时状态 |
| `tools/` | 三工具实现、Schema 和注册表 |
| `config.py` | 本地 API Key，不提交 |

## 子目录

| 目录 | 内容 |
|---|---|
| `data_cases/` | 当前主用的 5 个不同 VitalDB 病例 |
| `images/` | README 使用的界面截图 |
| `tests/` | 自动测试，例如 ASA 规则回归测试 |
| `docs/` | 开发日志、术语表、讲解、决策记录、组会计划 |
| `tools/` | `patient_record.py`、`waveform.py`、`asa_grade.py` |
| `demo_package/` | 线下组会演示包 |
| `deck_output/` | 当前最终 PPTX/PDF、5 篇参考文献全文与核验记录 |
| `competition/` | openJiuwen 比赛 PPT、补充材料、调研和草稿 |

## 常用命令

```bash
python peririsk_agent.py
python -m streamlit run app.py
python evaluate.py
python -m unittest discover -s tests -v
```

## 整理原则

- `config.py` 和 `evaluation_results.csv` 不动，因为它们分别被代码直接导入和写入。
- 主程序和公共模块不移动，保证当前 Agent 路径可运行。
- 比赛材料保留，历史脚本和旧单例数据不再维护。
