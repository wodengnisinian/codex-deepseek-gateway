import unittest

from adapters.chat_to_responses import tool_call_to_function_item
from adapters.responses_to_chat import responses_input_to_messages
from adapters.tools_adapter import codex_tools_to_deepseek_tools, needs_codex_tool_protocol_hint


class ResponsesToChatTests(unittest.TestCase):
    def test_string_input_becomes_user_message(self):
        messages = responses_input_to_messages({"instructions": "Be brief.", "input": "Hello"})
        self.assertEqual(messages[0], {"role": "system", "content": "Be brief."})
        self.assertEqual(messages[1], {"role": "user", "content": "Hello"})

    def test_function_call_and_output_round_trip_to_chat_messages(self):
        body = {
            "input": [
                {"role": "user", "content": "What time is it?"},
                {
                    "type": "function_call",
                    "id": "fc_1",
                    "call_id": "call_1",
                    "name": "get_current_time",
                    "arguments": '{"timezone":"Asia/Shanghai"}',
                },
                {
                    "type": "function_call_output",
                    "call_id": "call_1",
                    "output": '{"time":"23:59"}',
                },
            ]
        }
        messages = responses_input_to_messages(body)
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["tool_calls"][0]["id"], "call_1")
        self.assertEqual(messages[1]["tool_calls"][0]["function"]["name"], "get_current_time")
        self.assertEqual(messages[2]["role"], "tool")
        self.assertEqual(messages[2]["tool_call_id"], "call_1")

    def test_namespaced_function_call_round_trips_to_chat_tool_name(self):
        body = {
            "input": [
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "namespace": "github",
                    "name": "fetch_pr",
                    "arguments": '{"pr_number":1}',
                }
            ]
        }
        messages = responses_input_to_messages(body)
        self.assertEqual(messages[0]["tool_calls"][0]["function"]["name"], "ns__github__fetch_pr")

    def test_tool_search_output_becomes_tool_message(self):
        body = {
            "input": [
                {
                    "type": "tool_search_call",
                    "call_id": "call_search",
                    "arguments": {"query": "github"},
                },
                {
                    "type": "tool_search_output",
                    "call_id": "call_search",
                    "output": [{"name": "github_fetch_pr"}],
                },
            ]
        }
        messages = responses_input_to_messages(body)
        self.assertEqual(messages[0]["tool_calls"][0]["function"]["name"], "tool_search")
        self.assertEqual(messages[1]["role"], "tool")
        self.assertEqual(messages[1]["tool_call_id"], "call_search")

    def test_custom_tool_call_becomes_wrapped_chat_tool_call(self):
        body = {
            "input": [
                {
                    "type": "custom_tool_call",
                    "call_id": "call_custom",
                    "name": "apply_patch",
                    "input": "*** Begin Patch\n*** End Patch\n",
                }
            ]
        }
        messages = responses_input_to_messages(body)
        function = messages[0]["tool_calls"][0]["function"]
        self.assertEqual(function["name"], "custom__apply_patch")
        self.assertIn("input", function["arguments"])


class ToolsAdapterTests(unittest.TestCase):
    def test_responses_function_tool_becomes_chat_tool(self):
        tools = codex_tools_to_deepseek_tools(
            [
                {
                    "type": "function",
                    "name": "get_current_time",
                    "description": "Get the time.",
                    "parameters": {"type": "object", "properties": {}},
                    "strict": True,
                },
                {"type": "web_search_preview"},
            ]
        )
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["type"], "function")
        self.assertEqual(tools[0]["function"]["name"], "get_current_time")
        self.assertTrue(tools[0]["function"]["strict"])

    def test_namespace_tool_is_flattened_for_chat_completions(self):
        tools = codex_tools_to_deepseek_tools(
            [
                {
                    "type": "namespace",
                    "name": "github",
                    "tools": [
                        {
                            "type": "function",
                            "name": "fetch_pr",
                            "description": "Fetch a pull request.",
                            "parameters": {"type": "object", "properties": {}},
                        }
                    ],
                }
            ]
        )
        self.assertEqual(len(tools), 1)
        self.assertRegex(tools[0]["function"]["name"], r"^cx_github_fetch_pr_[0-9a-f]{8}$")

    def test_tool_search_is_exposed_as_function_tool(self):
        tools = codex_tools_to_deepseek_tools(
            [
                {
                    "type": "tool_search",
                    "execution": "client",
                    "description": "Search tools.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
                }
            ]
        )
        self.assertEqual(tools[0]["function"]["name"], "tool_search")

    def test_custom_tool_is_exposed_as_wrapped_function_tool(self):
        tools = codex_tools_to_deepseek_tools(
            [
                {
                    "type": "custom",
                    "name": "apply_patch",
                    "description": "Apply a patch.",
                }
            ]
        )
        self.assertRegex(tools[0]["function"]["name"], r"^cx_apply_patch_[0-9a-f]{8}$")
        self.assertIn("input", tools[0]["function"]["parameters"]["properties"])

    def test_protocol_hint_needed_for_deferred_plugin_shapes(self):
        self.assertTrue(needs_codex_tool_protocol_hint([{"type": "tool_search"}]))
        self.assertTrue(needs_codex_tool_protocol_hint([{"type": "namespace"}]))
        self.assertFalse(needs_codex_tool_protocol_hint([{"type": "function", "name": "read_file"}]))


class ChatToResponsesTests(unittest.TestCase):
    def test_tool_call_becomes_function_call_item(self):
        item = tool_call_to_function_item(
            {
                "id": "call_abc",
                "type": "function",
                "function": {"name": "get_current_time", "arguments": '{"timezone":"UTC"}'},
            }
        )
        self.assertEqual(item["type"], "function_call")
        self.assertEqual(item["call_id"], "call_abc")
        self.assertEqual(item["name"], "get_current_time")
        self.assertEqual(item["arguments"], '{"timezone":"UTC"}')

    def test_namespaced_tool_call_decodes_to_responses_namespace(self):
        item = tool_call_to_function_item(
            {
                "id": "call_abc",
                "type": "function",
                "function": {"name": "ns__github__fetch_pr", "arguments": '{"pr_number":1}'},
            }
        )
        self.assertEqual(item["type"], "function_call")
        self.assertEqual(item["namespace"], "github")
        self.assertEqual(item["name"], "fetch_pr")

    def test_tool_search_call_becomes_tool_search_item(self):
        item = tool_call_to_function_item(
            {
                "id": "call_search",
                "type": "function",
                "function": {"name": "tool_search", "arguments": '{"query":"github"}'},
            }
        )
        self.assertEqual(item["type"], "tool_search_call")
        self.assertEqual(item["execution"], "client")
        self.assertEqual(item["arguments"], {"query": "github"})

    def test_custom_tool_call_decodes_to_responses_custom_tool_call(self):
        item = tool_call_to_function_item(
            {
                "id": "call_custom",
                "type": "function",
                "function": {"name": "custom__apply_patch", "arguments": '{"input":"patch text"}'},
            }
        )
        self.assertEqual(item["type"], "custom_tool_call")
        self.assertEqual(item["name"], "apply_patch")
        self.assertEqual(item["input"], "patch text")


if __name__ == "__main__":
    unittest.main()
