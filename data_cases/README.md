# VitalDB 多病例对齐数据

由 `scripts/build_vitaldb_cases.py` 生成。每个病例都截取同一 60 秒窗口：

- `waveform_60s.csv`：PLETH 波形，500Hz
- `numeric_60s.csv`：`Solar8000/HR` 与 `Solar8000/PLETH_HR`

窗口选择规则：PLETH 有效率 ≥90%，两条心率轨道各至少 10 个有效读数。没有按误差大小挑选窗口。

`manifest.csv` 记录来源、窗口起点、算法心率和两个参考值。
