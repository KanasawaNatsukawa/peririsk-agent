"""当前运行中的患者状态。

工具从 Patient 花名册读取数据，但“这一次评估的是谁”属于运行时状态，
不放在 Agent 主循环里，避免工具反向依赖 Agent 模块。
"""

from patient import PATIENT


_current_patient = dict(PATIENT)


def set_patient(patient):
    """切换当前评估患者。"""
    global _current_patient
    _current_patient = dict(patient)


def get_patient():
    """返回当前患者的副本，避免工具意外修改原始档案。"""
    return dict(_current_patient)
