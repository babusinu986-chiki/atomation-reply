"""Offline regression checks; no mouse movements, clipboard changes, or API calls."""
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location("bot", Path(__file__).with_name("04_AI_bot.py"))
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)


class BotTests(unittest.TestCase):
    def test_delayed_copy_returns_new_text(self):
        clipboard = Mock()
        clipboard.paste.side_effect = ["bot-copy-test", "fresh message"]
        with patch.object(bot, "pyautogui"), patch.object(bot, "pyperclip", clipboard), patch.object(bot, "uuid4", return_value=SimpleNamespace(hex="test")), patch.object(bot.time, "sleep"):
            self.assertEqual(bot.copy_chat_history(), "fresh message")

    def test_failed_copy_does_not_return_stale_text(self):
        clipboard = Mock()
        clipboard.paste.return_value = "bot-copy-test"
        with patch.object(bot, "pyautogui"), patch.object(bot, "pyperclip", clipboard), patch.object(bot, "uuid4", return_value=SimpleNamespace(hex="test")), patch.object(bot.time, "perf_counter", side_effect=[0, 0.1, 3, 4, 4.1, 7]), patch.object(bot.time, "sleep"):
            self.assertIsNone(bot.copy_chat_history())

    def test_gemini_receives_latest_bounded_context(self):
        client = Mock()
        bot.client = client
        client.interactions.create.return_value = SimpleNamespace(output_text=" Hello! ")
        history = "old context " * 1000 + "LATEST MESSAGE"
        self.assertEqual(bot.generate_reply(history), "Hello!")
        sent = client.interactions.create.call_args.kwargs
        self.assertEqual(sent["input"], "WhatsApp conversation:\n" + history[-bot.MAX_HISTORY_CHARS:])
        self.assertEqual(sent["generation_config"]["thinking_level"], "minimal" if "flash-lite" in bot.MODEL else "low")

    def test_api_failure_returns_no_reply(self):
        client = Mock()
        bot.client = client
        client.interactions.create.side_effect = RuntimeError("offline")
        self.assertIsNone(bot.generate_reply("hello"))

    def test_own_echo_but_not_followup_is_skipped(self):
        self.assertTrue(bot.is_own_reply_echo("Friend: hi\nMe: Hello there!", "Hello there!"))
        self.assertFalse(bot.is_own_reply_echo("Me: Hello there!\nFriend: How are you?", "Hello there!"))

    def test_failed_generation_retries_same_chat(self):
        client = Mock()
        bot.client = client
        with patch.object(bot, "wait_for_dns"), patch.object(bot, "open_app"), patch.object(bot, "pyautogui"), patch.object(bot.time, "sleep"), patch.object(bot, "copy_chat_history", side_effect=["hello", "hello", KeyboardInterrupt]), patch.object(bot, "generate_reply", side_effect=[None, "hi"]) as generate, patch.object(bot, "send_message", return_value=True) as send:
            with self.assertRaises(KeyboardInterrupt):
                bot.run_bot()
            self.assertEqual(generate.call_count, 2)
            send.assert_called_once_with("hi")

    def test_wrong_message_box_never_presses_enter(self):
        with patch.object(bot, "pyautogui") as gui, patch.object(bot, "pyperclip"), patch.object(bot.time, "sleep"), patch.object(bot, "wait_for_copy", return_value="wrong page text"):
            self.assertFalse(bot.send_message("Hello!"))
            self.assertNotIn(unittest.mock.call("enter"), gui.press.call_args_list)

    def test_verified_paste_presses_enter(self):
        with patch.object(bot, "pyautogui") as gui, patch.object(bot, "pyperclip"), patch.object(bot.time, "sleep"), patch.object(bot, "wait_for_copy", return_value="Hello!"):
            self.assertTrue(bot.send_message("Hello!"))
            self.assertIn(unittest.mock.call("enter"), gui.press.call_args_list)

    def test_empty_generation_is_not_sent(self):
        client = Mock()
        bot.client = client
        client.interactions.create.return_value = SimpleNamespace(output_text=None)
        self.assertIsNone(bot.generate_reply("hello"))

    def test_open_chat_does_not_toggle_taskbar(self):
        with patch.object(bot, "pyautogui") as gui, patch.object(bot.time, "sleep"), patch.object(bot, "CLICK_CHAT_ON_START", False):
            bot.open_chat()
            gui.click.assert_not_called()

    def test_wrapped_dns_failure_is_recognized(self):
        error = RuntimeError("API connection failed")
        error.__cause__ = bot.socket.gaierror(11001, "getaddrinfo failed")
        self.assertTrue(bot.is_dns_error(error))
        self.assertFalse(bot.is_dns_error(RuntimeError("Invalid key")))

    def test_dns_recovers_after_temporary_failure(self):
        with patch.object(bot.socket, "getaddrinfo", side_effect=[bot.socket.gaierror(11001, "getaddrinfo failed"), []]) as lookup, patch.object(bot.time, "sleep"):
            bot.wait_for_dns()
            self.assertEqual(lookup.call_count, 2)

    def test_persistent_dns_failure_has_actionable_error(self):
        with patch.object(bot.socket, "getaddrinfo", side_effect=bot.socket.gaierror(11001, "getaddrinfo failed")), patch.object(bot.time, "sleep"):
            with self.assertRaisesRegex(bot.GeminiDNSError, "Reconnect Wi-Fi"):
                bot.wait_for_dns(attempts=2)

    def test_bot_resumes_after_dns_failure(self):
        with patch.object(bot, "wait_for_dns") as wait, patch.object(bot, "open_app"), patch.object(bot, "open_chat"), patch.object(bot.time, "sleep"), patch.object(bot, "get_chat", side_effect=["old chat", "latest chat", KeyboardInterrupt]), patch.object(bot, "generate_reply", side_effect=[bot.GeminiDNSError("offline"), "hello"]) as generate, patch.object(bot, "send_message", return_value=True) as send:
            with self.assertRaises(KeyboardInterrupt):
                bot.run_bot()
            self.assertEqual(wait.call_count, 2)
            generate.assert_called_with("latest chat")
            send.assert_called_once_with("hello")


if __name__ == "__main__":
    unittest.main()
