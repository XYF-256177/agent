"""内置工具集合与默认注册表构建。"""
from agent.tool_registry import ToolRegistry
from agent.tools.calculator import calculate, CALCULATOR_SCHEMA
from agent.tools.search import search, SEARCH_SCHEMA
from agent.tools.todo import todo, TODO_SCHEMA

__all__ = [
    "calculate",
    "search",
    "todo",
    "CALCULATOR_SCHEMA",
    "SEARCH_SCHEMA",
    "TODO_SCHEMA",
    "build_default_registry",
]


def build_default_registry() -> ToolRegistry:
    """构建包含三个默认工具的注册表。"""
    registry = ToolRegistry()
    registry.register(
        "calculator",
        "计算数学表达式，支持四则运算、幂、取模及 abs/round/min/max 函数",
        CALCULATOR_SCHEMA,
        calculate,
    )
    registry.register(
        "search",
        "检索内置知识库（当前为 mock 实现），例如查询天气、政策等信息",
        SEARCH_SCHEMA,
        search,
    )
    registry.register(
        "todo",
        "管理当前会话的待办事项，支持 add/list/clear 操作",
        TODO_SCHEMA,
        todo,
    )
    return registry
