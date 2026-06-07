from __future__ import annotations

import hashlib
import re
from typing import Any


ENCODED_NAMESPACE_PREFIX = "ns__"
ENCODED_CUSTOM_PREFIX = "custom__"
TOOL_SEARCH_NAME = "tool_search"
MAX_CHAT_TOOL_NAME_LENGTH = 64


ToolNameMap = dict[str, dict[str, str | None]]
ReverseToolNameMap = dict[str, str]


def _safe_tool_name_part(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", value)
    return safe or "tool"


def _compact_tool_alias(kind: str, name: str, namespace: str | None = None) -> str:
    readable_parts = [part for part in [namespace, name] if part]
    readable = _safe_tool_name_part("_".join(readable_parts))
    readable = re.sub(r"_+", "_", readable).strip("_") or "tool"
    digest_source = f"{kind}\0{namespace or ''}\0{name}"
    digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:8]
    prefix = "cx"
    suffix = f"_{digest}"
    budget = MAX_CHAT_TOOL_NAME_LENGTH - len(prefix) - 1 - len(suffix)
    return f"{prefix}_{readable[:budget]}{suffix}"


def reverse_key(kind: str, name: str, namespace: str | None = None) -> str:
    return f"{kind}\0{namespace or ''}\0{name}"


def encode_tool_name(name: str, namespace: str | None = None) -> str:
    if namespace:
        return f"{ENCODED_NAMESPACE_PREFIX}{_safe_tool_name_part(namespace)}__{_safe_tool_name_part(name)}"
    return _safe_tool_name_part(name)


def encode_custom_tool_name(name: str) -> str:
    return f"{ENCODED_CUSTOM_PREFIX}{_safe_tool_name_part(name)}"


def decode_tool_name(name: str) -> tuple[str | None, str]:
    if not name.startswith(ENCODED_NAMESPACE_PREFIX):
        return None, name

    rest = name[len(ENCODED_NAMESPACE_PREFIX) :]
    namespace, separator, tool_name = rest.rpartition("__")
    if not separator or not namespace or not tool_name:
        return None, name
    return namespace, tool_name


def decode_custom_tool_name(name: str) -> str | None:
    if not name.startswith(ENCODED_CUSTOM_PREFIX):
        return None
    value = name[len(ENCODED_CUSTOM_PREFIX) :]
    return value or None


def _chat_function_tool(
    *,
    name: str,
    description: str = "",
    parameters: dict[str, Any] | None = None,
    strict: bool | None = None,
) -> dict[str, Any]:
    function: dict[str, Any] = {
        "name": name,
        "description": description or "",
        "parameters": parameters or {"type": "object", "properties": {}},
    }
    if strict is not None:
        function["strict"] = strict
    return {"type": "function", "function": function}


def _responses_function_tool_to_chat(
    tool: dict[str, Any],
    namespace: str | None = None,
    alias: str | None = None,
) -> dict[str, Any] | None:
    if isinstance(tool.get("function"), dict):
        source = dict(tool["function"])
    else:
        source = dict(tool)

    name = source.get("name")
    if not isinstance(name, str) or not name:
        return None

    strict = source.get("strict")
    if strict is not None and not isinstance(strict, bool):
        strict = None

    parameters = source.get("parameters")
    if not isinstance(parameters, dict):
        parameters = {"type": "object", "properties": {}}

    return _chat_function_tool(
        name=alias or encode_tool_name(name, namespace),
        description=str(source.get("description") or ""),
        parameters=parameters,
        strict=strict,
    )


def codex_tools_to_deepseek_tool_set(
    tools: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], ToolNameMap, ReverseToolNameMap]:
    converted: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    tool_name_map: ToolNameMap = {}
    reverse_tool_name_map: ReverseToolNameMap = {}

    def append_once(
        tool: dict[str, Any] | None,
        *,
        kind: str,
        name: str,
        namespace: str | None = None,
    ) -> None:
        if not tool:
            return
        encoded_name = tool.get("function", {}).get("name")
        if not isinstance(encoded_name, str) or encoded_name in seen_names:
            return
        seen_names.add(encoded_name)
        tool_name_map[encoded_name] = {"kind": kind, "namespace": namespace, "name": name}
        reverse_tool_name_map[reverse_key(kind, name, namespace)] = encoded_name
        converted.append(tool)

    for tool in tools or []:
        if not isinstance(tool, dict):
            continue

        tool_type = tool.get("type")

        if tool_type == "function":
            name = tool.get("name") or tool.get("function", {}).get("name")
            if not isinstance(name, str) or not name:
                continue
            alias = encode_tool_name(name)
            append_once(
                _responses_function_tool_to_chat(tool, alias=alias),
                kind="function",
                name=name,
            )
            continue

        if tool_type == "namespace":
            namespace = tool.get("name")
            if not isinstance(namespace, str) or not namespace:
                continue
            for namespace_tool in tool.get("tools") or []:
                if isinstance(namespace_tool, dict) and namespace_tool.get("type") == "function":
                    name = namespace_tool.get("name") or namespace_tool.get("function", {}).get("name")
                    if not isinstance(name, str) or not name:
                        continue
                    alias = _compact_tool_alias("function", name, namespace)
                    append_once(
                        _responses_function_tool_to_chat(
                            namespace_tool,
                            namespace=namespace,
                            alias=alias,
                        ),
                        kind="function",
                        namespace=namespace,
                        name=name,
                    )
            continue

        if tool_type == "tool_search":
            parameters = tool.get("parameters")
            if not isinstance(parameters, dict):
                parameters = {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for available tools.",
                        }
                    },
                    "required": ["query"],
                }
            append_once(
                _chat_function_tool(
                    name=TOOL_SEARCH_NAME,
                    description=str(tool.get("description") or "Search available tools."),
                    parameters=parameters,
                ),
                kind="tool_search",
                name=TOOL_SEARCH_NAME,
            )
            continue

        if tool_type == "custom":
            name = tool.get("name")
            if not isinstance(name, str) or not name:
                continue
            alias = _compact_tool_alias("custom", name)
            append_once(
                _chat_function_tool(
                    name=alias,
                    description=str(tool.get("description") or ""),
                    parameters={
                        "type": "object",
                        "properties": {"input": {"type": "string"}},
                        "required": ["input"],
                    },
                ),
                kind="custom",
                name=name,
            )

    return converted, tool_name_map, reverse_tool_name_map


def codex_tools_to_deepseek_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    converted, _, _ = codex_tools_to_deepseek_tool_set(tools)
    return converted


def needs_codex_tool_protocol_hint(tools: list[dict[str, Any]] | None) -> bool:
    for tool in tools or []:
        if not isinstance(tool, dict):
            continue
        if tool.get("type") in {"namespace", "tool_search", "custom"}:
            return True
    return False
