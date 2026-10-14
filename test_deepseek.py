# ============================================================
# PeriRisk Demo · 第 1 步：让 DeepSeek 转起来
# 这个文件只做一件简单的事：问 DeepSeek 一个问题，并打印它的回答。
# 用法：在下面填好 API_KEY 后，命令行运行  python test_deepseek.py
# ============================================================

# 1) 导入 openai 库（刚才装好的"电话线"）
from openai import OpenAI

# 2) 【唯一需要你动手的地方】粘贴你的 DeepSeek API Key
#    去 platform.deepseek.com → API keys → 创建，复制 sk- 开头那串
API_KEY = "sk-93e394b84b954cae96d55e8d26157c35"

# 3) 建立连接 DeepSeek 的客户端（DeepSeek 接口与 OpenAI 兼容，只需改地址）
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# 4) 发一条消息给 DeepSeek，等它回复
reply = client.chat.completions.create(
    model="deepseek-chat",      # deepseek-chat = 对话模型，便宜够用
    messages=[
        {"role": "system", "content": "你是一个麻醉科医生助手。"},
        {"role": "user", "content": "你好，用一句话介绍什么是 ASA 分级。"},
    ],
)

# 5) 把它的回答打印出来
print(reply.choices[0].message.content)
