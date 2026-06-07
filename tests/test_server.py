import json
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

import server


class FakePostResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_models(self):
        response = self.client.get("/v1/models")
        self.assertEqual(response.status_code, 200)
        model_ids = {item["id"] for item in response.json()["data"]}
        self.assertIn("deepseek-v4-flash", model_ids)
        self.assertIn("deepseek-v4-pro", model_ids)

    @patch("server.httpx.AsyncClient")
    def test_non_stream_text_response(self, async_client_cls):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = FakePostResponse(
            {
                "choices": [{"message": {"content": "Hello from DeepSeek."}}],
                "usage": {"input_tokens": 1, "output_tokens": 2},
            }
        )
        async_client_cls.return_value = client

        response = self.client.post(
            "/v1/responses",
            headers={"Authorization": "Bearer test-key"},
            json={"model": "deepseek-v4-flash", "input": "Hello", "stream": False},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["output"][0]["type"], "message")
        self.assertEqual(body["output"][0]["content"][0]["text"], "Hello from DeepSeek.")

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "env-deepseek-key"}, clear=False)
    @patch("server.httpx.AsyncClient")
    def test_gateway_prefers_env_deepseek_key_over_authorization_header(self, async_client_cls):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = FakePostResponse({"choices": [{"message": {"content": "ok"}}]})
        async_client_cls.return_value = client

        response = self.client.post(
            "/v1/responses",
            headers={"Authorization": "Bearer local-gateway-token"},
            json={"model": "deepseek-v4-flash", "input": "Hello", "stream": False},
        )
        self.assertEqual(response.status_code, 200)
        _, kwargs = client.post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer env-deepseek-key")

    @patch("server.httpx.AsyncClient")
    def test_non_stream_tool_call_response(self, async_client_cls):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = FakePostResponse(
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {
                                        "name": "get_current_time",
                                        "arguments": '{"timezone":"UTC"}',
                                    },
                                }
                            ]
                        }
                    }
                ]
            }
        )
        async_client_cls.return_value = client

        response = self.client.post(
            "/v1/responses",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "deepseek-v4-pro",
                "input": "Use the tool",
                "stream": False,
                "tools": [{"type": "function", "name": "get_current_time"}],
            },
        )
        self.assertEqual(response.status_code, 200)
        item = response.json()["output"][0]
        self.assertEqual(item["type"], "function_call")
        self.assertEqual(item["call_id"], "call_123")
        self.assertEqual(item["name"], "get_current_time")
        self.assertEqual(item["arguments"], '{"timezone":"UTC"}')

    def test_tool_protocol_hint_is_inserted_for_tool_search(self):
        payload, _, _ = server.build_deepseek_payload(
            {
                "model": "deepseek-v4-flash",
                "input": "Use GitHub",
                "stream": False,
                "tools": [{"type": "tool_search", "description": "Search tools."}],
            }
        )
        self.assertIn("tool_search", payload["messages"][0]["content"])
        self.assertEqual(payload["tools"][0]["function"]["name"], "tool_search")

    @patch("server.httpx.AsyncClient")
    def test_namespaced_plugin_tool_call_decodes_with_generated_map(self, async_client_cls):
        client = AsyncMock()
        client.__aenter__.return_value = client

        captured_payload = {}

        async def fake_post(*args, **kwargs):
            captured_payload.update(kwargs["json"])
            encoded_name = captured_payload["tools"][0]["function"]["name"]
            return FakePostResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "id": "call_node",
                                        "type": "function",
                                        "function": {
                                            "name": encoded_name,
                                            "arguments": '{"code":"1+1"}',
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                }
            )

        client.post.side_effect = fake_post
        async_client_cls.return_value = client

        response = self.client.post(
            "/v1/responses",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "deepseek-v4-pro",
                "input": "Run JS",
                "stream": False,
                "tools": [
                    {
                        "type": "namespace",
                        "name": "mcp__node_repl",
                        "tools": [
                            {
                                "type": "function",
                                "name": "js",
                                "description": "Run JavaScript.",
                                "parameters": {"type": "object", "properties": {}},
                            }
                        ],
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        item = response.json()["output"][0]
        self.assertEqual(item["type"], "function_call")
        self.assertEqual(item["namespace"], "mcp__node_repl")
        self.assertEqual(item["name"], "js")


class StreamStateTests(unittest.TestCase):
    def test_stream_tool_delta_events_complete_function_call(self):
        state = server.StreamState(model="deepseek-v4-pro")
        events = state.tool_delta_events(
            {
                "index": 0,
                "id": "call_123",
                "type": "function",
                "function": {"name": "get_current_time", "arguments": '{"timezone"'},
            }
        )
        events += state.tool_delta_events(
            {
                "index": 0,
                "function": {"arguments": ':"UTC"}'},
            }
        )
        events += state.done_events()
        joined = "".join(events)
        self.assertIn("response.function_call_arguments.delta", joined)
        self.assertIn("response.function_call_arguments.done", joined)
        self.assertIn('"arguments": "{\\"timezone\\":\\"UTC\\"}"', joined)

    def test_completed_stream_event_omits_empty_usage(self):
        state = server.StreamState(model="deepseek-v4-flash")
        state.text_delta_events("hello")
        joined = "".join(state.done_events())
        completed_payloads = [
            line.removeprefix("data: ")
            for line in joined.splitlines()
            if line.startswith("data: ") and '"type": "response.completed"' in line
        ]
        self.assertEqual(len(completed_payloads), 1)
        completed = json.loads(completed_payloads[0])
        self.assertNotIn("usage", completed["response"])


if __name__ == "__main__":
    unittest.main()
