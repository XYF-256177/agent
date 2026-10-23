# 从零实现的最小可用 Agent Runtime

一个不依赖任何现有 Agent 框架（LangGraph / OpenHands / OpenClaw 等）的、从零手写的 Agent 运行时，核心循环、工具注册、输出解析、Session 与 Context 管理全部自研。

## 功能特性

- **自主循环**：接收输入 → LLM 决策（直接回复 or 调工具）→ 执行工具 → 根据结果继续 loop 或返回答案
- **工具注册机制**：每个工具含名称、描述、参数 Schema（JSON Schema），LLM 基于 Schema 自主决策调用
- **三个内置工具**：`calculator`（安全计算）、`search`（mock 检索）、`todo`（会话级待办）
- **Session 隔离**：多窗口独立会话，随时续聊、互不影响
- **Context 有效管理**：轮次限制、纯对话/带工具追问、超长上下文基础压缩
- **长期 Memory**：跨会话记忆 + 关键词召回
- **健壮性**：基本异常处理、工具调用 trace/执行日志

## 目录结构

```
agent-runtime/
├── agent/
│   ├── __init__.py          # 包入口，统一导出
│   ├── runtime.py           # 核心：Agent 主循环 + context 组装/压缩
│   ├── llm_client.py        # OpenAI 兼容 LLM 客户端（真实 API）
│   ├── parser.py            # LLM 输出解析（思考/工具调用/最终答案）
│   ├── tool_registry.py     # 工具注册机制
│   ├── memory.py            # 长期记忆 + token 估算
│   ├── session.py           # 多窗口 session 隔离
│   └── tools/
│       ├── calculator.py    # calculator 工具
│       ├── search.py        # search 工具（mock）
│       └── todo.py          # todo 工具（按 session 隔离）
├── examples/
│   └── demo.py              # 交互式演示
├── tests/                   # pytest 测试用例
├── AI_PROMPT.md             # AI Prompt 与问题解决记录
├── requirements.txt
└── .env.example
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 LLM API

```bash
cp .env.example .env
```

编辑 `.env`，填入真实 API Key（支持 DeepSeek / 通义千问 / OpenAI 等任意 OpenAI 兼容接口）：

```bash
LLM_API_KEY=sk-xxxxxxxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### 3. 运行交互式演示

```bash
python examples/demo.py
```

示例对话：

```
[window-1] 你: 帮我算一下 (128 + 256) * 2 等于多少
[window-1] Agent: 结果是 768

[window-1] 你: 帮我记个待办：下午查北京天气
[window-1] Agent: 已记录待办「下午查北京天气」

[window-1] 你: new window-2          # 切换到窗口2
[window-2] 你: 帮我记个待办：写周报
[window-2] Agent: 已记录待办「写周报」

[window-2] 你: new window-1          # 切回窗口1
[window-1] 你: 看看我的待办
[window-1] Agent: 你的待办只有「下午查北京天气」  # 看不到窗口2的内容
```

### 4. 运行测试

一键验证（先单元测试，再真实 API 冒烟测试）：

```bash
python verify_all.py
```

也可以单独跑：

```bash
pytest -v                      # 单元测试（离线，29 个用例）
python examples/verify.py      # 真实 API 冒烟测试
```

## 系统设计

### 主循环

```
用户输入
   │
   ▼
组装 context ──► 调用 LLM（携带工具 Schema）
   ▲                │
   │                ▼
   │          解析 LLM 输出
   │                │
   │        ┌───────┴────────┐
   │        │                │
   │     需要工具         直接回复
   │        │                │
   │        ▼                ▼
   └── 执行工具           返回最终答案
        （结果回填）
```

核心逻辑位于 `agent/runtime.py` 的 `AgentRuntime.run()`，一次调用完成一个完整轮次，循环步数受 `max_turns` 限制，避免死循环。

### 模块职责与关键设计

**1. LLM 客户端（`llm_client.py`）**
只负责"发请求、拿原始响应"，不做任何解析，保证职责单一。任意 OpenAI 兼容接口都可通过 `.env` 切换。

**2. 工具注册机制（`tool_registry.py`）**
每个工具由三要素构成：`name` + `description` + `parameters`（JSON Schema）。`ToolRegistry.to_openai_schema()` 把这些元信息转成 OpenAI 的 `tools` 参数，LLM 据此自主决策是否调用、如何传参。

隐藏参数注入：`todo` 工具需要按会话隔离，但 `session_id` 不该暴露给 LLM。因此 `registry.call()` 支持通过 `context` 注入"隐藏参数"——用 `inspect` 检查函数签名，只注入函数真正需要的键。这样工具函数既保持无状态、可测试，又能拿到运行时会话信息。

**3. 输出解析（`parser.py`）**
两层解析：
- **主路径**：解析 OpenAI 原生 `tool_calls` 字段；
- **兜底路径**：当模型不支持 function calling 或未返回 `tool_calls` 时，从 `content` 中正则提取 JSON（`{"thought":..., "tool":..., "answer":...}`）。

思考过程优先取 `reasoning_content`（DeepSeek reasoner 等模型提供），兜底从 JSON 的 `thought` 字段提取。

**4. Session 隔离（`session.py`）**
`SessionManager` 以 `session_id` 为 key 维护独立 `Session`，每个 Session 拥有自己的消息历史。用户 A 的窗口 1、窗口 2 各自独立，可随时 `get_or_create` 续聊。

**5. Context 管理（`runtime.py`）**
每次组装 context 的组成（从上到下）：

```
[system] 角色说明 + 工具列表 + 长期记忆摘要
[system] （可选）对话历史压缩摘要
[user / assistant / tool] 历史消息（含工具调用与结果）
[user] 当前输入
```

- **轮次限制**：`max_turns` 限制单次任务的 loop 步数，超限返回兜底提示。
- **追问支持**：历史消息完整保留在 Session 中，纯对话追问（"那再帮我加一条"）与带工具追问（"刚才算的结果再查一下天气"）都能基于完整上下文成立。
- **基础压缩**：历史消息超过 `max_history_messages` 时，把最老部分用 LLM 摘要成一条 system 消息，保留最近消息。压缩失败自动退回原文，不阻塞主流程。

### Memory 设计（召回时机与放置方式）

题目要求重点说明，这里展开。

**数据模型**：`{user_id: [{"key", "value", "ts"}, ...]}`，跨 session 共享，按用户隔离。

**召回时机**：**每次组装 context 之前**。在 `_build_messages()` 里，先调用 `memory.summarize()` 取回该用户的长期记忆摘要，再拼装 system prompt。也就是说，召回是"对话开始前的即时动作"，而非定时任务或懒加载。

**放置方式**：召回结果放在 **system prompt 顶部**（"已记住的长期信息"区块），位置高于历史对话。这样做的理由：
1. system 消息对模型指令遵从度最高，记忆作为"先验事实"应稳定地影响每一轮回答；
2. 与历史对话分离，避免被后续压缩逻辑误伤；
3. 优先级明确：长期记忆 > 近期对话 > 当前输入。

**召回策略**：`recall(user_id, query, top_k)` 做关键词匹配（query 分词 → 匹配 key/value），无命中时退回"最近 top_k 条"，保证追问不丢上下文。当前为简化实现，复杂语义召回（向量化）不在本题范围内。

**写入时机**：`_auto_remember()` 用简单规则识别自我介绍/偏好表达（"我叫 / 我是 / 我喜欢 / 记住"），写入长期记忆。

## 测试说明

`tests/` 用 pytest + 可编程假 LLM（`FakeLLM`）覆盖，不依赖真实 API：

| 测试文件 | 覆盖点 |
|---|---|
| `test_tool_registry.py` | 注册/Schema、重复注册、未知工具、异常兜底、隐藏参数注入 |
| `test_parser.py` | 原生 tool_calls、最终答案、JSON 兜底、非法输入 |
| `test_session.py` | 多窗口隔离、重置 |
| `test_memory.py` | 记忆写入/覆盖/召回/token 估算 |
| `test_runtime.py` | 直接回复、工具 loop 收敛、带工具追问、多会话独立、max_turns、异常兜底、上下文压缩 |

## 设计取舍与可扩展点

- **不引入框架**：主循环、注册表、解析器均为手写，满足"核心 Agent Runtime 自研"要求。
- **安全计算**：`calculator` 用 `ast` 白名单解析而非 `eval`，避免任意代码执行。
- **可扩展**：新增工具只需在 `tools/` 写一个函数 + 定义 Schema，再注册进 `ToolRegistry`，主流程零改动。
- **后续方向**：工具并发调用、流式输出、持久化会话、向量化 memory 召回、token 级精确裁剪等，均可在此骨架上增量演进。
