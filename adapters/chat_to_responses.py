from __future__ import annotations

import time
import uuid
from typing import Any

from adapters.tools_adapter import TOOL_SEARCH_NAME, ToolNameMap, decode_custom_tool_name, decode_tool_name


def new_response_id() -> str:
    return "resp_" + uuid.uuid4().hex


def new_message_id() -> str:
    return "msg_" + uuid.uuid4().hex


def new_function_call_id() -> str:
    return "fc_" + uuid.uuid4().hex


def output_text_item(text: str, item_id: str | None = None, status: str = "completed") -> dict[str, Any]:
    return {
        "id": item_id or new_message_id(),
        "type": "message",
        "status": status,
        "role": "assistant",
        "content": [
            {
                "type": "output_text",
                "text": text,
                "annotations": [],
            }
        ],
    }


def function_call_item(
    *,
    name: str,
    arguments: str,
    call_id: str,
    item_id: str | None = None,
    status: str = "completed",
    namespace: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": item_id or new_function_call_id(),
        "type": "function_call",
        "status": status,
        "call_id": call_id,
        "name": name,
        "arguments": arguments or "{}",
    }
    if namespace:
        item["namespace"] = namespace
    return item


def tool_search_call_item(
    *,
    arguments: str,
    call_id: str,
    item_id: str | None = None,
    status: str = "completed",
) -> dict[str, Any]:
    try:
        parsed_arguments: Any = json_loads_or_empty(arguments)
    except Exception:
        parsed_arguments = {"query": arguments}

    return {
        "id": item_id or new_function_call_id(),
        "type": "tool_search_call",
        "status": status,
        "call_id": call_id,
        "execution": "client",
        "arguments": parsed_arguments,
    }


def custom_tool_call_item(
    *,
    name: str,
    input_text: str,
    call_id: str,
    item_id: str | None = None,
    status: str = "completed",
) -> dict[str, Any]:
    return {
        "id": item_id or new_function_call_id(),
        "type": "custom_tool_call",
        "status": status,
        "call_id": call_id,
        "name": name,
        "input": input_text,
    }


def json_loads_or_empty(value: str) -> Any:
    if not value:
        return {}
    return __import__("json").loads(value)


def tool_call_to_function_item(
    tool_call: dict[str, Any],
    tool_name_map: ToolNameMap | None = None,
) -> dict[str, Any]:
    function = tool_call.get("function") or {}
    raw_name = str(function.get("name") or "")
    arguments = function.get("arguments") or "{}"
    call_id = str(tool_call.get("id") or "")

    mapped = (tool_name_map or {}).get(raw_name)

    if mapped and mapped.get("kind") == "tool_search":
        return tool_search_call_item(
            item_id=new_function_call_id(),
            call_id=call_id,
            arguments=arguments,
        )

    if raw_name == TOOL_SEARCH_NAME:
        return tool_search_call_item(
            item_id=new_function_call_id(),
            call_id=call_id,
            arguments=arguments,
        )

    custom_name = str(mapped.get("name")) if mapped and mapped.get("kind") == "custom" else None
    custom_name = custom_name or decode_custom_tool_name(raw_name)
    if custom_name:
        try:
            parsed = json_loads_or_empty(arguments)
            input_text = parsed.get("input", arguments) if isinstance(parsed, dict) else str(parsed)
        except Exception:
            input_text = arguments
        return custom_tool_call_item(
            item_id=new_function_call_id(),
            call_id=call_id,
            name=custom_name,
            input_text=input_text,
        )

    if mapped and mapped.get("kind") == "function":
        namespace = mapped.get("namespace")
        name = str(mapped.get("name") or raw_name)
    else:
        namespace, name = decode_tool_name(raw_name)
    return function_call_item(
        item_id=new_function_call_id(),
        call_id=call_id,
        namespace=namespace,
        name=name,
        arguments=arguments,
    )


def response_object(
    *,
    model: str,
    output: list[dict[str, Any]],
    response_id: str | None = None,
    usage: dict[str, Any] | None = None,
    status: str = "completed",
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "id": response_id or new_response_id(),
        "object": "response",
        "created_at": int(time.time()),
        "status": status,
        "model": model,
        "output": output,
    }
    if usage is not None:
        response["usage"] = usage
    if error:
        response["error"] = error
    return response


def text_response_object(model: str, text: str, usage: dict[str, Any] | None = None) -> dict[str, Any]:
    return response_object(model=model, output=[output_text_item(text)], usage=usage)


def tool_calls_response_object(
    model: str,
    tool_calls: list[dict[str, Any]],
    tool_name_map: ToolNameMap | None = None,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return response_object(
        model=model,
        output=[tool_call_to_function_item(tool_call, tool_name_map) for tool_call in tool_calls],
        usage=usage,
    )
