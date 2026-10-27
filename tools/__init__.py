"""PeriRisk 工具注册表。

每个工具模块同时提供：
- 一个本地 Python 函数；
- 一份 JSON Schema。
Agent 只从这里拿到工具菜单和函数表。
"""

from .asa_grade import SCHEMA as ASA_GRADE_SCHEMA
from .asa_grade import assess_asa_grade
from .patient_record import SCHEMA as PATIENT_RECORD_SCHEMA
from .patient_record import get_patient_record
from .waveform import SCHEMA as WAVEFORM_SCHEMA
from .waveform import analyze_waveform


TOOLS = [
    PATIENT_RECORD_SCHEMA,
    WAVEFORM_SCHEMA,
    ASA_GRADE_SCHEMA,
]

TOOL_FUNCTIONS = {
    "get_patient_record": get_patient_record,
    "analyze_waveform": analyze_waveform,
    "assess_asa_grade": assess_asa_grade,
}
