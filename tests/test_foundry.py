import ast
import asyncio
from contextlib import redirect_stdout
from functools import partial
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CONFIG = {
    "AZURE_OPENAI_API_KEY": "offline-test-key",
    "AZURE_OPENAI_ENDPOINT": "https://manadry.cognitiveservices.azure.com/",
    "OPENAI_API_VERSION": "2024-12-01-preview",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-6.1-sol",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "embedding-test",
    "AZURE_OPENAI_AUDIO_DEPLOYMENT": "audio-test",
    "TAVILY_API_KEY": "offline-tavily-key",
}


def sources():
    for path in sorted((ROOT / "notebooks").rglob("*.ipynb")):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code":
                yield f"{path.name}:cell-{index}", "".join(cell["source"])
    for path in (ROOT / "notebooks").rglob("*.py"):
        yield path.name, path.read_text(encoding="utf-8")


def model_calls():
    for name, source in sources():
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("AzureChatOpenAI", "AzureOpenAIEmbeddings"):
                    yield name, node


def construct(node, **kwargs):
    from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

    namespace = {
        "os": os,
        "AzureChatOpenAI": partial(AzureChatOpenAI, **kwargs),
        "AzureOpenAIEmbeddings": partial(AzureOpenAIEmbeddings, **kwargs),
    }
    return eval(compile(ast.Expression(node), "<model-configuration>", "eval"), namespace)


class FoundryConfigurationTests(unittest.TestCase):
    def test_environment_templates(self):
        from dotenv import dotenv_values

        for template in ("example.env", ".env.example"):
            with self.subTest(template=template):
                values = dotenv_values(ROOT / template)
                for key in ("AZURE_OPENAI_ENDPOINT", "OPENAI_API_VERSION", "AZURE_OPENAI_DEPLOYMENT"):
                    self.assertEqual(values[key], CONFIG[key])
                self.assertEqual(values["AZURE_OPENAI_API_KEY"], "your_azure_openai_api_key_here")
                self.assertNotIn("OPENAI_API_KEY", values)

    def test_notebook_and_script_syntax(self):
        for name, source in sources():
            with self.subTest(source=name):
                compile(source, name, "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)

    def test_no_public_openai_model_initializers(self):
        for name, source in sources():
            with self.subTest(source=name):
                for node in ast.walk(ast.parse(source)):
                    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                        continue
                    self.assertNotIn(node.func.id, ("ChatOpenAI", "OpenAIEmbeddings", "OpenAI"))
                    if node.func.id in ("create_agent", "init_chat_model", "SummarizationMiddleware"):
                        models = node.args[:1] + [kw.value for kw in node.keywords if kw.arg == "model"]
                        for model in models:
                            if isinstance(model, ast.Constant) and isinstance(model.value, str):
                                self.assertFalse(model.value.startswith(("gpt-", "openai:")))

    def test_every_azure_initializer_uses_deployment_environment(self):
        calls = list(model_calls())
        self.assertTrue(calls)
        seen = set()
        for name, node in calls:
            with self.subTest(source=name, line=node.lineno):
                deployment = next(kw.value for kw in node.keywords if kw.arg == "azure_deployment")
                self.assertIsInstance(deployment, ast.Subscript)
                self.assertEqual(ast.unparse(deployment.value), "os.environ")
                self.assertIn(deployment.slice.value, CONFIG)
                seen.add(deployment.slice.value)
        self.assertEqual(seen, {
            "AZURE_OPENAI_DEPLOYMENT",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
            "AZURE_OPENAI_AUDIO_DEPLOYMENT",
        })

    def test_all_azure_constructors(self):
        import httpx

        with patch.dict(os.environ, CONFIG, clear=True):
            with httpx.Client() as client:
                for name, node in model_calls():
                    with self.subTest(source=name, line=node.lineno):
                        model = construct(node, http_client=client)
                        self.assertEqual(model.openai_api_version, CONFIG["OPENAI_API_VERSION"])
                        self.assertEqual(model.azure_endpoint, CONFIG["AZURE_OPENAI_ENDPOINT"])

    def test_chat_and_audio_request_routing(self):
        import httpx

        calls = {}
        for _, node in model_calls():
            if node.func.id == "AzureChatOpenAI":
                key = next(kw.value.slice.value for kw in node.keywords if kw.arg == "azure_deployment")
                calls.setdefault(key, node)

        def respond(request):
            body = json.loads(request.content)
            deployment = request.url.path.split("/")[-3]
            self.assertEqual(request.url.host, "manadry.cognitiveservices.azure.com")
            self.assertEqual(request.headers["api-key"], CONFIG["AZURE_OPENAI_API_KEY"])
            self.assertEqual(request.url.params["api-version"], CONFIG["OPENAI_API_VERSION"])
            self.assertIn(deployment, (CONFIG["AZURE_OPENAI_DEPLOYMENT"], CONFIG["AZURE_OPENAI_AUDIO_DEPLOYMENT"]))
            self.assertEqual(request.url.path, f"/openai/deployments/{deployment}/chat/completions")
            self.assertEqual(body["messages"], [{"role": "user", "content": "Hello"}])
            return httpx.Response(200, json={
                "id": "offline-chat",
                "object": "chat.completion",
                "created": 0,
                "model": deployment,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            })

        with patch.dict(os.environ, CONFIG, clear=True):
            with httpx.Client(transport=httpx.MockTransport(respond)) as client:
                for key, node in calls.items():
                    with self.subTest(deployment=key):
                        model = construct(node, http_client=client)
                        self.assertEqual(model.invoke("Hello").content, "OK")

            async def check_async():
                async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                    model = construct(calls["AZURE_OPENAI_DEPLOYMENT"], http_async_client=client)
                    self.assertEqual((await model.ainvoke("Hello")).content, "OK")

            asyncio.run(check_async())

    def test_web_search_agent_disables_reasoning_for_function_tools(self):
        import httpx
        from langchain.agents import create_agent

        source = next(
            source for name, source in sources()
            if name.startswith("1.2_web_search.ipynb:") and "tools=[web_search]" in source
        )
        node = next(
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "AzureChatOpenAI"
        )
        requests = []
        queries = []
        question = "Who is the current mayor of San Francisco?"

        def web_search(query: str) -> str:
            """Search the web for current information."""
            queries.append(query)
            return "Offline search result."

        def respond(request):
            body = json.loads(request.content)
            self.assertTrue(request.url.path.endswith("/chat/completions"))
            self.assertEqual(body.get("reasoning_effort"), "none")
            self.assertEqual(body["tools"][0]["function"]["name"], "web_search")
            requests.append(body)
            if len(requests) == 1:
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "search-call",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": json.dumps({"query": question}),
                        },
                    }],
                }
                finish_reason = "tool_calls"
            else:
                self.assertEqual(body["messages"][-1]["role"], "tool")
                self.assertEqual(body["messages"][-1]["tool_call_id"], "search-call")
                self.assertEqual(body["messages"][-1]["content"], "Offline search result.")
                message = {"role": "assistant", "content": "Offline answer."}
                finish_reason = "stop"
            return httpx.Response(200, json={
                "id": "offline-search",
                "object": "chat.completion",
                "created": 0,
                "model": CONFIG["AZURE_OPENAI_DEPLOYMENT"],
                "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            })

        with patch.dict(os.environ, CONFIG, clear=True):
            with httpx.Client(transport=httpx.MockTransport(respond)) as client:
                agent = create_agent(model=construct(node, http_client=client), tools=[web_search])
                response = agent.invoke({"messages": [{"role": "user", "content": question}]})
        self.assertEqual(response["messages"][-1].content, "Offline answer.")
        self.assertEqual(queries, [question])
        self.assertEqual(len(requests), 2)

    def test_embedding_request_routing(self):
        import httpx

        node = next(node for _, node in model_calls() if node.func.id == "AzureOpenAIEmbeddings")

        def respond(request):
            self.assertEqual(request.url.host, "manadry.cognitiveservices.azure.com")
            self.assertEqual(request.url.path, "/openai/deployments/embedding-test/embeddings")
            self.assertEqual(request.url.params["api-version"], CONFIG["OPENAI_API_VERSION"])
            self.assertEqual(request.headers["api-key"], CONFIG["AZURE_OPENAI_API_KEY"])
            self.assertEqual(json.loads(request.content)["model"], "text-embedding-3-large")
            return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0, 0.0, 0.0]}]})

        with patch.dict(os.environ, CONFIG, clear=True):
            with httpx.Client(transport=httpx.MockTransport(respond)) as client:
                model = construct(node, http_client=client, check_embedding_ctx_length=False)
                self.assertEqual(model.embed_query("Hello"), [1.0, 0.0, 0.0])

    def test_environment_defaults_and_required_values(self):
        from dotenv import dotenv_values
        from env_utils import doublecheck_env

        for template in ("example.env", ".env.example"):
            for value in ("offline-test-key", "your_azure_openai_api_key_here", "", None):
                config = dict(CONFIG)
                config.pop("AZURE_OPENAI_API_KEY")
                if value is not None:
                    config["AZURE_OPENAI_API_KEY"] = value
                with self.subTest(template=template, value=value):
                    output = io.StringIO()
                    with (
                        patch.dict(os.environ, config, clear=True),
                        patch("env_utils.dotenv_values", side_effect=lambda path: {} if str(path) == ".env" else dotenv_values(path)),
                        redirect_stdout(output),
                    ):
                        doublecheck_env(str(ROOT / template))
                    text = output.getvalue()
                    self.assertEqual("Issues found:" in text, value != "offline-test-key")
                    self.assertNotIn("offline-test-key", text)


if __name__ == "__main__":
    unittest.main()
