# ============================================================
# PeriRisk Demo · 公共模块：调 DeepSeek 生成报告
# 全项目只有这一处知道"怎么跟大模型说话"：
#   以后想换模型 / 改提示词 / 改接口地址，只改这个文件。
# ============================================================

import json

import requests

from config import API_KEY   # key 统一从 config.py 读取（已被 .gitignore 保护，不进仓库）

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"      # deepseek-chat = 对话模型，便宜够用

# 角色设定 + 输出格式要求（想让报告换个风格，只改这里）
SYSTEM_PROMPT = (
    "你是一名资深麻醉科医生。请根据患者信息输出一份术前风险评估报告，"
    "格式必须包含三部分：【风险评估】【麻醉关注点】【建议】。"
    "必须引用给出的数值，不要编造患者没有的病史。"
)


def generate_report(summary):
    """把患者摘要发给 DeepSeek，返回生成的报告文本。

    请求失败（网络问题 / key 错误 / 额度用完）时抛出 RuntimeError，
    并把 DeepSeek 返回的原始原因带出来，方便当场排查。
    """
    resp = requests.post(
        API_URL,
        headers={
            "Authorization": "Bearer " + API_KEY,   # 门禁卡
            "Content-Type": "application/json",      # 声明发的是 JSON 格式
        },
        data=json.dumps({                            # 把消息打包成 JSON 数据包
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "患者信息如下，请出报告：" + summary},
            ],
        }),
        timeout=30,   # 最多等 30 秒
    )
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek 请求失败（状态码 {resp.status_code}）：{resp.text}")
    return resp.json()["choices"][0]["message"]["content"]


def chat_with_tools(messages, tools, timeout=60, temperature=0.2):
    """带"工具菜单"的对话：把 tools（JSON Schema 列表）一并发给大脑。

    返回响应里的那条 assistant 消息（dict），调用方要看它点了什么菜：
      - 含 tool_calls → 大脑点名了工具，调用方本地执行后把结果回填进对话
      - 只有 content  → 大脑认为信息够了，直接给出最终回答
    """
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": tools,
        "temperature": temperature,
    }
    resp = requests.post(
        API_URL,
        headers={
            "Authorization": "Bearer " + API_KEY,
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek 请求失败（状态码 {resp.status_code}）：{resp.text}")
    return resp.json()["choices"][0]["message"]
