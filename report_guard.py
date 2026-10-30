"""最终报告的程序化安全检查。

系统提示词要求模型只引用工具字段并附依据，但提示词属于软约束。
本模块在报告返回后进行确定性检查，发现明显违规时触发一次模型纠正。
"""

import re


REQUIRED_SECTIONS = ("风险评估", "麻醉关注点", "建议")
FORBIDDEN_TERMS = (
    "男性",
    "女性",
    "舒张压",
    "高血压诊断",
    "冠脉造影",
    "冠状动脉造影",
)


def validate_report(report):
    """返回报告检查结果；不判断临床内容是否正确。"""
    text = report or ""
    issues = []

    def has_section(section):
        bracketed = f"【{section}】" in text
        numbered_heading = re.search(
            rf"^\s*(?:#{{1,6}}\s*)?(?:\*\*)?"
            rf"(?:[一二三四五六七八九十0-9]+[、.．]?\s*)?"
            rf"{re.escape(section)}(?:\*\*)?\s*$",
            text,
            flags=re.MULTILINE,
        )
        return bracketed or numbered_heading is not None

    missing_sections = [
        section for section in REQUIRED_SECTIONS
        if not has_section(section)
    ]
    if missing_sections:
        issues.append("缺少必需章节：" + "、".join(missing_sections))

    forbidden_hits = [
        term for term in FORBIDDEN_TERMS
        if term in text
    ]
    if forbidden_hits:
        issues.append("出现禁止字段：" + "、".join(forbidden_hits))

    if re.search(r"\btrue\b|\bfalse\b", text, flags=re.IGNORECASE):
        issues.append("出现未转换的 true/false")

    conclusion_lines = [
        line.strip()
        for line in text.splitlines()
        if line.lstrip().startswith(("- ", "* ", "• "))
    ]
    unsupported_lines = [
        line for line in conclusion_lines
        if "依据：" not in line
    ]
    if unsupported_lines:
        issues.append(f"{len(unsupported_lines)} 条结论缺少“依据：”标注")

    return {
        "通过": not issues,
        "问题": issues,
        "检查结论条数": len(conclusion_lines),
        "缺少证据条数": len(unsupported_lines),
    }


def build_correction_message(validation):
    problems = "；".join(validation["问题"])
    return (
        "程序校验未通过："
        f"{problems}。请重写最终报告，保持三段式结构；"
        "每一条结论必须附“（依据：工具实际返回值）”，"
        "不得出现工具未返回的字段，不得猜测临床信息。"
    )
