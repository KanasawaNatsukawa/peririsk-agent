"""工具 1：查询当前患者病历。"""

from patient import DEFAULT_WAVEFORM_ID, PATIENT_WAVEFORMS
from runtime_state import get_patient


SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_patient_record",
        "description": (
            "查询患者病历，返回年龄、既往史（冠心病/糖尿病/肾功能不全/"
            "病情是否稳定）、收缩压和波形ID。"
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}


def get_patient_record():
    patient = get_patient()
    record = dict(patient)
    record["波形ID"] = PATIENT_WAVEFORMS.get(
        patient["姓名"],
        DEFAULT_WAVEFORM_ID,
    )
    return record
