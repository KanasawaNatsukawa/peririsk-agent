# ============================================================
# PeriRisk Demo · 第 4 步（备用版）：用 requests 直连 DeepSeek
# 为什么有这个文件：openai 库在你这台电脑上发中文时被"卡在门口"，
# 这个版本不经过它，直接把请求发给 DeepSeek，更简单也更好懂。
# 用法：python peririsk_agent_v1b.py
# ============================================================

import json
import requests
from asa_risk import assess_asa   # 复用第 3 步的评分函数

# ---- 0) 在这里粘贴你的 key ----
# ⚠️ 注意：引号里只能有 sk- 开头那串字符，不要带空格、不要带中文、不要带注释
API_KEY = "sk-93e394b84b954cae96d55e8d26157c35"

# ---- 1) 患者信息 ----
patient = {
    "姓名": "张三",
    "年龄": 68,
    "冠心病": True,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "心率": 92,
    "收缩压": 158,
}

# ---- 2) 程序算出 ASA 等级，整理成摘要 ----
grade = assess_asa(
    patient["年龄"],
    patient["冠心病"],
    patient["糖尿病"],
    patient["肾功能不全"],
    patient["病情不稳定"],
)
summary = (
    f"患者{patient['姓名']}，{patient['年龄']}岁，"
    f"ASA分级（程序计算）：{grade}，"
    f"心率 {patient['心率']} 次/分钟，收缩压 {patient['收缩压']} mmHg，"
    f"既往史：冠心病{'是' if patient['冠心病'] else '否'}、"
    f"糖尿病{'是' if patient['糖尿病'] else '否'}。"
)

# ---- 3) 把请求发给 DeepSeek（走"数据包"，中文不会卡门口）----
resp = requests.post(
    "https://api.deepseek.com/chat/completions",
    headers={
        "Authorization": "Bearer " + API_KEY,   # 门禁卡
        "Content-Type": "application/json",      # 声明发的是 JSON 格式
    },
    data=json.dumps({                            # 把消息打包成 JSON 数据包
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一名资深麻醉科医生。请根据患者信息输出一份术前风险评估报告，"
                    "格式必须包含三部分：【风险评估】【麻醉关注点】【建议】。"
                    "必须引用给出的数值，不要编造患者没有的病史。"
                ),
            },
            {"role": "user", "content": "患者信息如下，请出报告：" + summary},
        ],
    }),
    timeout=30,   # 最多等 30 秒
)

# ---- 4) 检查是否成功，然后打印报告 ----
if resp.status_code == 200:
    data = resp.json()
    print(data["choices"][0]["message"]["content"])
else:
    # 失败时把 DeepSeek 返回的原因打出来（比如额度用完、key 错误）
    print("请求失败，状态码：", resp.status_code)
    print("返回内容：", resp.text)
