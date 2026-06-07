from __future__ import annotations

import json
import os
import time
from typing import Any, AsyncIterator

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from adapters.chat_to_responses import (
    function_call_item,
    new_function_call_id,
    new_message_id,
    new_response_id,
    output_text_item,
    response_object,
    text_response_object,
    tool_calls_response_object,
)
from adapters.responses_to_chat import responses_input_to_messages
from adapters.tools_adapter import codex_tools_to_deepseek_tools
from adapters.tools_adapter import codex_tools_to_deepseek_tool_set
from adapters.tools_adapter import needs_codex_tool_protocol_hint
from adapters.tools_adapter import ToolNameMap
from adapters.tools_adapter import ReverseToolNameMap


load_dotenv()

app = FastAPI(title="Codex DeepSeek Gateway", version="0.1.0")

DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek-v4-flash")
DEFAULT_THINKING = os.getenv("DEEPSEEK_THINKING", "enabled").strip().lower()
DEFAULT_REASONING_EFFORT = os.getenv("DEEPSEEK_REASONING_EFFORT", "high").strip().lower()
GATEWAY_AUTH_TOKEN = os.getenv("GATEWAY_AUTH_TOKEN", "").strip()
GATEWAY_MODEL_PROVIDER = os.getenv("GATEWAY_MODEL_PROVIDER", "").strip()


def request_bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return ""


def authorize_gateway_request(request: Request) -> bool:
    if not GATEWAY_AUTH_TOKEN:
        return True
    return request_bearer_token(request) == GATEWAY_AUTH_TOKEN


def get_deepseek_api_key(request: Request) -> str:
    env_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if env_key:
        return env_key

    if GATEWAY_AUTH_TOKEN:
        return ""

    return request_bearer_token(request)


def codex_tool_protocol_hint() -> dict[str, str]:
    return {
        "role": "system",
        "content": (
            "Codex exposes local plugins and MCP capabilities through function tools. "
            "If a user asks to use a plugin, connector, app, or an @-mentioned tool and the exact tool is not listed, "
            "call the tool_search function with a concise query instead of answering from memory. "
            "Functions whose names start with ns__ encode Codex namespace tools; call them normally when relevant. "
            "Functions whose names start with custom__ encode freeform Codex tools; pass their raw text in the input field. "
            "Never claim you used a Codex plugin unless you actually called the corresponding tool."
        ),
    }


def build_deepseek_payload(
    body: dict[str, Any],
) -> tuple[dict[str, Any], ToolNameMap, ReverseToolNameMap]:
    model = body.get("model") or DEFAULT_MODEL
    stream = bool(body.get("stream", False))
    tools, tool_name_map, reverse_tool_name_map = codex_tools_to_deepseek_tool_set(body.get("tools"))

    messages = responses_input_to_messages(body, reverse_tool_name_map)
    # When Codex tools are present, merge the tool protocol hint into the first
    # system message rather than inserting it as a separate message.  A single
    # merged system message avoids splitting the DeepSeek prompt-cache prefix
    # across two misaligned 128-token blocks, reducing cache-miss fragmentation.
    if needs_codex_tool_protocol_hint(body.get("tools")):
        hint_text = codex_tool_protocol_hint()["content"]
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] = hint_text + "\n\n" + messages[0]["content"]
        else:
            messages.insert(0, codex_tool_protocol_hint())

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }

    if DEFAULT_THINKING in {"enabled", "disabled"}:
        payload["thinking"] = {"type": DEFAULT_THINKING}

    if DEFAULT_REASONING_EFFORT in {"high", "max"}:
        payload["reasoning_effort"] = DEFAULT_REASONING_EFFORT

    if body.get("max_output_tokens") is not None:
        payload["max_tokens"] = body["max_output_tokens"]

    if body.get("temperature") is not None and DEFAULT_THINKING == "disabled":
        payload["temperature"] = body["temperature"]

    if tools:
        payload["tools"] = tools
        if body.get("tool_choice") is not None:
            payload["tool_choice"] = body["tool_choice"]

    return payload, tool_name_map, reverse_tool_name_map


def normalize_usage(usage: dict[str, Any] | None) -> dict[str, Any] | None:
    if not usage:
        return None

    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
    total_tokens = usage.get("total_tokens")

    if input_tokens is None or output_tokens is None:
        return None

    if total_tokens is None:
        try:
            total_tokens = int(input_tokens) + int(output_tokens)
        except Exception:
            return None

    normalized: dict[str, Any] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }
    if "input_tokens_details" in usage:
        normalized["input_tokens_details"] = usage["input_tokens_details"]
    if "output_tokens_details" in usage:
        normalized["output_tokens_details"] = usage["output_tokens_details"]
    return normalized


def upstream_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def openai_error(status_code: int, message: str, error_type: str = "gateway_error") -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message, "type": error_type}},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "codex-deepseek-gateway"}


MODEL_CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codex", "model_catalog.json")

def _load_model_catalog() -> list[dict[str, Any]]:
    try:
        with open(MODEL_CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("models", data.get("catalog", []))
    except Exception:
        return []


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    now = int(time.time())
    catalog = _load_model_catalog()
    # GATEWAY_MODEL_PROVIDER overrides owned_by so /v1/models matches
    # model_provider in the Codex config (especially in plugin-compatible mode).
    owned_by = GATEWAY_MODEL_PROVIDER or None
    if catalog:
        data = []
        for m in catalog:
            data.append({
                "id": m["id"],
                "object": "model",
                "created": now,
                "owned_by": owned_by or m.get("provider", "deepseek"),
            })
    else:
        data = [
            {"id": "deepseek-v4-flash", "object": "model", "created": now, "owned_by": owned_by or "deepseek"},
            {"id": "deepseek-v4-pro", "object": "model", "created": now, "owned_by": owned_by or "deepseek"},
        ]
    return {"object": "list", "data": data}


@app.post("/v1/responses", response_model=None)
async def create_response(request: Request) -> JSONResponse | StreamingResponse | dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return openai_error(400, "Request body must be valid JSON", "invalid_request_error")

    if not authorize_gateway_request(request):
        return openai_error(401, "Invalid gateway bearer token", "authentication_error")

    api_key = get_deepseek_api_key(request)
    if not api_key:
        return openai_error(401, "Missing DEEPSEEK_API_KEY", "authentication_error")

    payload, tool_name_map, _ = build_deepseek_payload(body)
    model = str(payload["model"])

    if payload["stream"]:
        return StreamingResponse(
            stream_response(payload=payload, model=model, api_key=api_key, tool_name_map=tool_name_map),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return await non_stream_response(payload=payload, model=model, api_key=api_key, tool_name_map=tool_name_map)


async def non_stream_response(
    payload: dict[str, Any],
    model: str,
    api_key: str,
    tool_name_map: ToolNameMap | None = None,
) -> JSONResponse | dict[str, Any]:
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            upstream = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers=upstream_headers(api_key),
                json=payload,
            )
        except httpx.HTTPError as exc:
            return openai_error(502, f"DeepSeek upstream request failed: {exc}")

    if upstream.status_code >= 400:
        try:
            error_body = upstream.json()
        except Exception:
            error_body = {"error": {"message": upstream.text, "type": "upstream_error"}}
        return JSONResponse(status_code=upstream.status_code, content=error_body)

    data = upstream.json()
    message = (data.get("choices") or [{}])[0].get("message") or {}
    tool_calls = message.get("tool_calls") or []
    usage = normalize_usage(data.get("usage"))

    if tool_calls:
        return tool_calls_response_object(
            model=model,
            tool_calls=tool_calls,
            tool_name_map=tool_name_map,
            usage=usage,
        )

    text = message.get("content") or ""
    return text_response_object(model=model, text=text, usage=usage)


def sse(event_type: str, data: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class StreamState:
    def __init__(self, model: str, tool_name_map: ToolNameMap | None = None) -> None:
        self.model = model
        self.tool_name_map = tool_name_map or {}
        self.response_id = new_response_id()
        self.message_item_id: str | None = None
        self.text = ""
        self.text_started = False
        self.sequence_number = 0
        self.tool_states: dict[int, dict[str, Any]] = {}

    def next_sequence(self) -> int:
        self.sequence_number += 1
        return self.sequence_number

    def created_event(self) -> str:
        response = response_object(
            response_id=self.response_id,
            model=self.model,
            output=[],
            status="in_progress",
        )
        return sse(
            "response.created",
            {
                "type": "response.created",
                "sequence_number": self.next_sequence(),
                "response": response,
            },
        )

    def start_text_events(self) -> list[str]:
        if self.text_started:
            return []
        self.text_started = True
        self.message_item_id = new_message_id()
        item = output_text_item("", item_id=self.message_item_id, status="in_progress")
        return [
            sse(
                "response.output_item.added",
                {
                    "type": "response.output_item.added",
                    "sequence_number": self.next_sequence(),
                    "response_id": self.response_id,
                    "output_index": 0,
                    "item": item,
                },
            ),
            sse(
                "response.content_part.added",
                {
                    "type": "response.content_part.added",
                    "sequence_number": self.next_sequence(),
                    "response_id": self.response_id,
                    "item_id": self.message_item_id,
                    "output_index": 0,
                    "content_index": 0,
                    "part": {"type": "output_text", "text": "", "annotations": []},
                },
            ),
        ]

    def text_delta_events(self, delta: str) -> list[str]:
        if not delta:
            return []
        self.text += delta
        events = self.start_text_events()
        events.append(
            sse(
                "response.output_text.delta",
                {
                    "type": "response.output_text.delta",
                    "sequence_number": self.next_sequence(),
                    "response_id": self.response_id,
                    "item_id": self.message_item_id,
                    "output_index": 0,
                    "content_index": 0,
                    "delta": delta,
                },
            )
        )
        return events

    def tool_delta_events(self, tool_delta: dict[str, Any]) -> list[str]:
        index = int(tool_delta.get("index", 0))
        state = self.tool_states.get(index)
        events: list[str] = []

        if state is None:
            function = tool_delta.get("function") or {}
            state = {
                "id": new_function_call_id(),
                "call_id": str(tool_delta.get("id") or ""),
                "name": str(function.get("name") or ""),
                "arguments": "",
                "started": False,
            }
            self.tool_states[index] = state

        if tool_delta.get("id"):
            state["call_id"] = str(tool_delta["id"])

        function = tool_delta.get("function") or {}
        if function.get("name"):
            state["name"] = str(function["name"])

        arguments_delta = function.get("arguments") or ""

        if not state["started"]:
            state["started"] = True
            output_index = self.output_index_for_tool(index)
            item = self.tool_state_to_response_item(state, status="in_progress")
            events.append(
                sse(
                    "response.output_item.added",
                    {
                        "type": "response.output_item.added",
                        "sequence_number": self.next_sequence(),
                        "response_id": self.response_id,
                        "output_index": output_index,
                        "item": item,
                    },
                )
            )

        if arguments_delta:
            state["arguments"] += arguments_delta
            events.append(
                sse(
                    "response.function_call_arguments.delta",
                    {
                        "type": "response.function_call_arguments.delta",
                        "sequence_number": self.next_sequence(),
                        "response_id": self.response_id,
                        "item_id": state["id"],
                        "output_index": self.output_index_for_tool(index),
                        "delta": arguments_delta,
                    },
                )
            )

        return events

    def output_index_for_tool(self, tool_index: int) -> int:
        return (1 if self.text_started else 0) + tool_index

    def done_events(self) -> list[str]:
        events: list[str] = []
        output: list[dict[str, Any]] = []

        if self.text_started:
            assert self.message_item_id is not None
            events.extend(
                [
                    sse(
                        "response.output_text.done",
                        {
                            "type": "response.output_text.done",
                            "sequence_number": self.next_sequence(),
                            "response_id": self.response_id,
                            "item_id": self.message_item_id,
                            "output_index": 0,
                            "content_index": 0,
                            "text": self.text,
                        },
                    ),
                    sse(
                        "response.content_part.done",
                        {
                            "type": "response.content_part.done",
                            "sequence_number": self.next_sequence(),
                            "response_id": self.response_id,
                            "item_id": self.message_item_id,
                            "output_index": 0,
                            "content_index": 0,
                            "part": {"type": "output_text", "text": self.text, "annotations": []},
                        },
                    ),
                ]
            )
            message_item = output_text_item(self.text, item_id=self.message_item_id)
            output.append(message_item)
            events.append(
                sse(
                    "response.output_item.done",
                    {
                        "type": "response.output_item.done",
                        "sequence_number": self.next_sequence(),
                        "response_id": self.response_id,
                        "output_index": 0,
                        "item": message_item,
                    },
                )
            )

        for tool_index in sorted(self.tool_states):
            state = self.tool_states[tool_index]
            item = function_call_item(
                item_id=state["id"],
                call_id=state["call_id"],
                name=state["name"],
                arguments=state["arguments"],
            )
            item = self.tool_state_to_response_item(state)
            output.append(item)
            output_index = self.output_index_for_tool(tool_index)
            events.extend(
                [
                    sse(
                        "response.function_call_arguments.done",
                        {
                            "type": "response.function_call_arguments.done",
                            "sequence_number": self.next_sequence(),
                            "response_id": self.response_id,
                            "item_id": state["id"],
                            "output_index": output_index,
                            "name": state["name"],
                            "arguments": state["arguments"],
                        },
                    ),
                    sse(
                        "response.output_item.done",
                        {
                            "type": "response.output_item.done",
                            "sequence_number": self.next_sequence(),
                            "response_id": self.response_id,
                            "output_index": output_index,
                            "item": item,
                        },
                    ),
                ]
            )

        completed = response_object(response_id=self.response_id, model=self.model, output=output)
        events.append(
            sse(
                "response.completed",
                {
                    "type": "response.completed",
                    "sequence_number": self.next_sequence(),
                    "response": completed,
                },
            )
        )
        return events

    def tool_state_to_response_item(
        self,
        state: dict[str, Any],
        status: str = "completed",
    ) -> dict[str, Any]:
        tool_call = {
            "id": state["call_id"],
            "type": "function",
            "function": {
                "name": state["name"],
                "arguments": state["arguments"],
            },
        }
        from adapters.chat_to_responses import tool_call_to_function_item

        item = tool_call_to_function_item(tool_call, self.tool_name_map)
        item["id"] = state["id"]
        item["status"] = status
        if status == "in_progress":
            if item["type"] == "function_call":
                item["arguments"] = ""
            elif item["type"] == "custom_tool_call":
                item["input"] = ""
        return item

    def failed_event(self, message: str) -> str:
        failed = response_object(
            response_id=self.response_id,
            model=self.model,
            output=[],
            status="failed",
            error={"message": message, "type": "upstream_error"},
        )
        return sse(
            "response.failed",
            {
                "type": "response.failed",
                "sequence_number": self.next_sequence(),
                "response": failed,
            },
        )


async def stream_response(
    payload: dict[str, Any],
    model: str,
    api_key: str,
    tool_name_map: ToolNameMap | None = None,
) -> AsyncIterator[str]:
    state = StreamState(model=model, tool_name_map=tool_name_map)
    yield state.created_event()

    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream(
                "POST",
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers=upstream_headers(api_key),
                json=payload,
            ) as upstream:
                if upstream.status_code >= 400:
                    body = (await upstream.aread()).decode("utf-8", errors="ignore")
                    yield state.failed_event(body)
                    return

                async for line in upstream.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break

                    try:
                        chunk = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices") or []
                    if not choices:
                        continue

                    delta = choices[0].get("delta") or {}
                    text_delta = delta.get("content") or ""
                    for event in state.text_delta_events(text_delta):
                        yield event

                    for tool_delta in delta.get("tool_calls") or []:
                        for event in state.tool_delta_events(tool_delta):
                            yield event
        except httpx.HTTPError as exc:
            yield state.failed_event(f"DeepSeek upstream request failed: {exc}")
            return

    for event in state.done_events():
        yield event
