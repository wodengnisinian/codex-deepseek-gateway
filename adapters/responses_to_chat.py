from __future__ import annotations

from typing import Any

from adapters.tools_adapter import (
    TOOL_SEARCH_NAME,
    ReverseToolNameMap,
    encode_custom_tool_name,
    encode_tool_name,
    reverse_key,
)


CHAT_ROLES = {"system", "user", "assistant", "tool"}


def extract_text_from_content(content: Any) -> str:
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue

            if isinstance(item, dict):
                value = (
                    item.get("text")
                    or item.get("input_text")
                    or item.get("output_text")
                    or item.get("content")
                    or item.get("output")
                    or ""
                )
                if isinstance(value, (dict, list)):
                    parts.append(extract_text_from_content(value))
                else:
                    parts.append(str(value))
                continue

            parts.append(str(item))

        return "\n".join(part for part in parts if part)

    if isinstance(content, dict):
        value = (
            content.get("text")
            or content.get("input_text")
            or content.get("output_text")
            or content.get("content")
            or content.get("output")
            or ""
        )
        if isinstance(value, (dict, list)):
            return extract_text_from_content(value)
        return str(value)

    return str(content)


def normalize_chat_role(role: Any) -> str:
    if not isinstance(role, str):
        return "user"

    if role == "developer":
        return "system"

    if role in CHAT_ROLES:
        return role

    return "user"


def _function_call_to_tool_call(
    item: dict[str, Any],
    reverse_tool_name_map: ReverseToolNameMap | None = None,
) -> dict[str, Any]:
    call_id = item.get("call_id") or item.get("id") or ""
    name = str(item.get("name") or "")
    namespace = item.get("namespace")
    if not isinstance(namespace, str):
        namespace = None
    encoded_name = None
    if reverse_tool_name_map is not None:
        encoded_name = reverse_tool_name_map.get(reverse_key("function", name, namespace))

    return {
        "id": str(call_id),
        "type": "function",
        "function": {
            "name": encoded_name or encode_tool_name(name, namespace),
            "arguments": item.get("arguments") or "{}",
        },
    }


def _tool_search_call_to_tool_call(item: dict[str, Any]) -> dict[str, Any]:
    call_id = item.get("call_id") or item.get("id") or ""
    arguments = item.get("arguments") or {}
    return {
        "id": str(call_id),
        "type": "function",
        "function": {
            "name": TOOL_SEARCH_NAME,
            "arguments": arguments if isinstance(arguments, str) else __import__("json").dumps(arguments),
        },
    }


def _custom_tool_call_to_tool_call(
    item: dict[str, Any],
    reverse_tool_name_map: ReverseToolNameMap | None = None,
) -> dict[str, Any]:
    call_id = item.get("call_id") or item.get("id") or ""
    name = str(item.get("name") or "")
    input_text = item.get("input") or ""
    encoded_name = None
    if reverse_tool_name_map is not None:
        encoded_name = reverse_tool_name_map.get(reverse_key("custom", name))

    return {
        "id": str(call_id),
        "type": "function",
        "function": {
            "name": encoded_name or encode_custom_tool_name(name),
            "arguments": __import__("json").dumps({"input": str(input_text)}),
        },
    }


def _function_output_to_tool_message(item: dict[str, Any]) -> dict[str, Any]:
    output = item.get("output", "")
    return {
        "role": "tool",
        "tool_call_id": str(item.get("call_id") or ""),
        "content": extract_text_from_content(output),
    }


def _message_to_chat_message(item: dict[str, Any]) -> dict[str, Any]:
    role = normalize_chat_role(item.get("role", "user"))
    return {
        "role": role,
        "content": extract_text_from_content(item.get("content", "")),
    }


def responses_input_to_messages(
    body: dict[str, Any],
    reverse_tool_name_map: ReverseToolNameMap | None = None,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    instructions = body.get("instructions")
    if instructions:
        messages.append({"role": "system", "content": extract_text_from_content(instructions)})

    input_data = body.get("input", "")
    if isinstance(input_data, str):
        messages.append({"role": "user", "content": input_data})
        return messages

    if not isinstance(input_data, list):
        messages.append({"role": "user", "content": extract_text_from_content(input_data)})
        return messages

    pending_tool_calls: list[dict[str, Any]] = []

    def flush_pending_tool_calls() -> None:
        nonlocal pending_tool_calls
        if not pending_tool_calls:
            return
        messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": pending_tool_calls,
            }
        )
        pending_tool_calls = []

    for raw_item in input_data:
        if not isinstance(raw_item, dict):
            flush_pending_tool_calls()
            messages.append({"role": "user", "content": str(raw_item)})
            continue

        item_type = raw_item.get("type")

        if item_type == "function_call":
            pending_tool_calls.append(_function_call_to_tool_call(raw_item, reverse_tool_name_map))
            continue

        if item_type == "tool_search_call":
            pending_tool_calls.append(_tool_search_call_to_tool_call(raw_item))
            continue

        if item_type == "custom_tool_call":
            pending_tool_calls.append(_custom_tool_call_to_tool_call(raw_item, reverse_tool_name_map))
            continue

        if item_type == "function_call_output":
            flush_pending_tool_calls()
            messages.append(_function_output_to_tool_message(raw_item))
            continue

        if item_type in {"tool_search_output", "custom_tool_call_output"}:
            flush_pending_tool_calls()
            messages.append(_function_output_to_tool_message(raw_item))
            continue

        flush_pending_tool_calls()
        messages.append(_message_to_chat_message(raw_item))

    flush_pending_tool_calls()

    return messages or [{"role": "user", "content": ""}]
