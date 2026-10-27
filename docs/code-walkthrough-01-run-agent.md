# 代码讲解 01：`run_agent` 主循环

对应文件：`peririsk_agent.py`，第 220–276 行。

这一节只讲一件事：一次评估是怎样从“用户任务”走到“最终报告”的。

## 1. 准备聊天记录

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": task},
]
```

逐词解释：

- `messages`（消息列表）：整段对话记录。
- `role`（角色）：这条消息是谁说的。
- `system`（系统）：给模型的固定规则。
- `content`（内容）：消息正文。
- `SYSTEM_PROMPT`（系统提示词）：项目预先写好的工作规则。
- `task`（任务）：用户这次要求，例如“请为下一位患者完成术前风险评估”。

现在聊天记录里只有两条：规则和任务。

## 2. 问模型下一步

```python
msg = chat_with_tools(messages, TOOLS)
calls = msg.get("tool_calls")
```

- `chat_with_tools`（带工具的对话函数）：把消息和工具清单发给 DeepSeek。
- `TOOLS`（工具清单）：三个工具的说明书。
- `msg`（消息）：模型这一次的回复。
- `tool_calls`（工具调用请求）：模型要求执行哪些工具。

如果模型没有请求工具，说明它认为信息够了：

```python
if not calls:
    return msg["content"], round_no
```

- `content`（内容）：最终报告正文。
- `round_no`（轮数）：这次是第几轮思考。
- `return`（返回）：结束函数，把报告和轮数交给调用方。

## 3. 把模型的请求放回聊天记录

```python
messages.append(msg)
```

- `append`（追加）：把一条消息加到列表末尾。

为什么必须放回去？因为模型刚才发出的工具请求也是对话的一部分。没有这条请求，后面的工具结果就无法和它对应。

## 4. 本地执行工具

```python
name = call["function"]["name"]
args = json.loads(call["function"]["arguments"] or "{}")
result = TOOL_FUNCTIONS[name](**args)
```

- `call`（一次工具调用）：模型发出的单个请求。
- `function`（函数）：请求里的函数信息。
- `name`（函数名）：例如 `analyze_waveform`。
- `arguments`（参数）：模型准备传给函数的参数。
- `json.loads`（解析 JSON 文本）：把文本形式的参数变成 Python 字典。
- `TOOL_FUNCTIONS`（工具函数表）：函数名到真实函数的映射。
- `result`（结果）：本地函数真正执行后的返回值。

这里最重要：**模型只负责点菜，真正做菜的是本地 Python。**

## 5. 把结果回填给模型

```python
messages.append({
    "role": "tool",
    "tool_call_id": call["id"],
    "content": json.dumps(result, ensure_ascii=False),
})
```

- `role: tool`（角色是工具）：告诉模型“这是一条工具执行结果”。
- `tool_call_id`（工具调用编号）：把结果和刚才那次请求配对。
- `json.dumps`（转成 JSON 文本）：把 Python 字典转成模型能读的文本。
- `ensure_ascii=False`（保留中文）：不要把中文转成编码。

`tool_call_id` 可以理解成取餐号：模型点了“查病历”，本地做完后拿着同一个号码把结果交回去。号码对不上，模型就不知道这份结果属于哪次请求。

## 6. 循环继续

整个循环最多执行 `MAX_ROUNDS = 8`（最大轮数 8）次。

正常情况下：

1. 第一轮：查病历；
2. 第二轮：分析波形；
3. 第三轮：算 ASA；
4. 最后一轮：模型不再调用工具，返回三段式报告。

如果 8 轮还没结束，函数返回“达到最大思考轮数，强制停止”，防止无限循环和持续消耗 API。

## 现在必须记住的五句话

1. `messages` 是聊天记录，不是患者数据。
2. 大模型只提出工具调用请求，不亲自执行。
3. 本地 `TOOL_FUNCTIONS` 才真正执行函数。
4. 工具结果必须带同一个 `tool_call_id` 回到聊天记录。
5. 模型不再请求工具时，循环结束，返回报告。
