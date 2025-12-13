import importlib.util
import pathlib
import sys
import types
import unittest


RUNNER_PATH = pathlib.Path(__file__).resolve().parents[1] / "apex" / "plugins" / "MemoryPlus" / "runner.py"
graphiti_core = types.ModuleType("graphiti_core")
graphiti_core.Graphiti = type("Graphiti", (), {})

nodes = types.ModuleType("graphiti_core.nodes")
nodes.EpisodeType = type("EpisodeType", (), {})
sys.modules["graphiti_core.nodes"] = nodes
graphiti_core.nodes = nodes

llm_client = types.ModuleType("graphiti_core.llm_client")
llm_client.LLMConfig = type("LLMConfig", (), {})
sys.modules["graphiti_core.llm_client"] = llm_client
graphiti_core.llm_client = llm_client

openai_generic = types.ModuleType("graphiti_core.llm_client.openai_generic_client")
openai_generic.OpenAIGenericClient = type("OpenAIGenericClient", (), {})
sys.modules["graphiti_core.llm_client.openai_generic_client"] = openai_generic

embedder_openai = types.ModuleType("graphiti_core.embedder.openai")
embedder_openai.OpenAIEmbedder = type("OpenAIEmbedder", (), {})
embedder_openai.OpenAIEmbedderConfig = type("OpenAIEmbedderConfig", (), {})
sys.modules["graphiti_core.embedder.openai"] = embedder_openai

embedder_gemini = types.ModuleType("graphiti_core.embedder.gemini")
embedder_gemini.GeminiEmbedder = type("GeminiEmbedder", (), {})
embedder_gemini.GeminiEmbedderConfig = type("GeminiEmbedderConfig", (), {})
sys.modules["graphiti_core.embedder.gemini"] = embedder_gemini

kuzu_driver = types.ModuleType("graphiti_core.driver.kuzu_driver")
kuzu_driver.KuzuDriver = type("KuzuDriver", (), {})
sys.modules["graphiti_core.driver.kuzu_driver"] = kuzu_driver

sys.modules["graphiti_core"] = graphiti_core
sys.modules["openai"] = types.ModuleType("openai")
sys.modules["neo4j"] = types.SimpleNamespace(GraphDatabase=type("GraphDatabase", (), {"driver": staticmethod(lambda *args, **kwargs: None)}))
sys.modules["kuzu"] = types.ModuleType("kuzu")

spec = importlib.util.spec_from_file_location("memoryplus_runner", RUNNER_PATH)
runner_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner_module)

sanitize_memory = runner_module.sanitize_memory


class SanitizeMemoryTests(unittest.TestCase):
    def test_removes_untagged_code_blocks(self):
        raw = "before\n```\nsecret\n```\nafter"
        config = {"sanitization": {"sanitize_code_blocks": True, "preserve_tagged_code": True}}

        result = sanitize_memory(raw, config)

        self.assertEqual(result, "before\n\nafter")

    def test_preserves_keep_code_blocks(self):
        raw = "[KEEP_CODE]\n```\nkeep me\n```\ntext"
        config = {"sanitization": {"sanitize_code_blocks": True, "preserve_tagged_code": True}}

        result = sanitize_memory(raw, config)

        self.assertEqual(result, "```\nkeep me\n```\ntext")

    def test_can_strip_keep_code_when_disabled(self):
        raw = "[KEEP_CODE]\n```\nkeep me\n```\ntext"
        config = {"sanitization": {"sanitize_code_blocks": True, "preserve_tagged_code": False}}

        result = sanitize_memory(raw, config)

        self.assertEqual(result, "text")

    def test_removes_tool_calls_and_normalizes_whitespace(self):
        raw = "before\n\n\n<tool_call>do not store</tool_call>\n\n\nafter"
        config = {
            "sanitization": {
                "sanitize_tool_calls": True,
                "sanitize_code_blocks": False,
                "normalize_whitespace": True,
            }
        }

        result = sanitize_memory(raw, config)

        self.assertEqual(result, "before\n\nafter")

    def test_does_not_normalize_whitespace_by_default(self):
        raw = "first\n\n\nsecond"
        config = {"sanitization": {"sanitize_tool_calls": False, "sanitize_code_blocks": False}}

        result = sanitize_memory(raw, config)

        self.assertEqual(result, "first\n\n\nsecond")


if __name__ == "__main__":
    unittest.main()
