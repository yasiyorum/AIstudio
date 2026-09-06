"""
AI Model Stüdyosu — Çekirdek Birim Testleri
ConfigManager, SimpleMemory, ModelManager ve ChatEngine temel işlevlerini test eder.
"""
import os
import unittest
import tempfile
import shutil
import json

from backend.config_manager import ConfigManager
from backend.chat_engine import SimpleMemory, ChatEngine
from backend.model_manager import ModelManager


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager()

    def test_default_values_exist(self):
        self.assertIn("provider", self.config.get_all())
        self.assertIn("rag_base_model", self.config.get_all())
        self.assertIn("temperature", self.config.get_all())

    def test_set_and_get(self):
        self.config.set("test_key", "test_value", auto_save=False)
        self.assertEqual(self.config.get("test_key"), "test_value")

    def test_default_fallback(self):
        self.assertEqual(self.config.get("non_existent_key", "default_val"), "default_val")


class TestSimpleMemory(unittest.TestCase):
    def setUp(self):
        self.test_model = "test_unit_model"
        self.memory = SimpleMemory(model_name=self.test_model)

    def tearDown(self):
        self.memory.clear()

    def test_save_and_load_context(self):
        self.memory.save_context({"input": "Merhaba"}, {"output": "Nasıl yardımcı olabilirim?"})
        self.assertEqual(len(self.memory.chat_memory), 2)
        self.assertEqual(self.memory.chat_memory[0]["role"], "human")
        self.assertEqual(self.memory.chat_memory[0]["content"], "Merhaba")
        self.assertEqual(self.memory.chat_memory[1]["role"], "ai")

    def test_persistence_format(self):
        self.memory.save_context({"input": "Test Soru"}, {"output": "Test Cevap"})
        self.assertTrue(os.path.exists(self.memory.file_path))
        with open(self.memory.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("model_name", data)
            self.assertIn("session_id", data)
            self.assertIn("messages", data)
            self.assertEqual(data["model_name"], self.test_model)
            self.assertEqual(data["message_count"], 2)


class TestModelManager(unittest.TestCase):
    def setUp(self):
        self.manager = ModelManager()

    def test_size_formatting(self):
        self.assertEqual(self.manager._format_size(500), "500 B")
        self.assertEqual(self.manager._format_size(2048), "2.0 KB")
        self.assertEqual(self.manager._format_size(5 * 1024 * 1024), "5.0 MB")
        self.assertEqual(self.manager._format_size(2 * 1024 * 1024 * 1024), "2.0 GB")

    def test_db_directory_is_absolute(self):
        self.assertTrue(os.path.isabs(self.manager.db_dir))
        self.assertTrue(os.path.exists(self.manager.db_dir))


class TestChatEngine(unittest.TestCase):
    def setUp(self):
        self.manager = ModelManager()
        self.engine = ChatEngine(self.manager)

    def test_initial_state(self):
        self.assertFalse(self.engine.is_loading)
        self.assertFalse(self.engine._cancel_stream)

    def test_stop_stream(self):
        self.engine.stop_stream()
        self.assertTrue(self.engine._cancel_stream)

    def test_new_session(self):
        session_id = self.engine.new_session("test_model")
        self.assertIsNotNone(session_id)
        self.assertEqual(self.engine.memory.model_name, "test_model")
        self.engine.memory.clear()


if __name__ == "__main__":
    unittest.main()
