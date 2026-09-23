import os
import re
import sys
import json
import time
import threading
import socket
from pathlib import Path
from uuid import uuid4

import pyautogui
import pyperclip
from dotenv import load_dotenv
from google import genai


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_FOLDER = Path(__file__).resolve().parent
load_dotenv(PROJECT_FOLDER / ".env", encoding="utf-8-sig")
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Flash-Lite was tested with your key for faster short chat replies.
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
client = None  # Created once in main(), reused for every message.

POLL_INTERVAL = 1.0
COPY_TIMEOUT = 2.0
MAX_HISTORY_CHARS = 6000


# ============================================================
# PYAutoGUI SAFETY
# ============================================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

def open_app():
    # --------------------------------------------------
    # 1. Check the icon at (1295, 1050) and click it
    # --------------------------------------------------

    # Move to the icon
    pyautogui.moveTo(1260, 1052, duration=0.3)

    # Click the icon
    pyautogui.click()

    print("Icon clicked.")

    # Wait for the next screen/window to appear
    time.sleep(9)


# ============================================================
# WHATSAPP SCREEN COORDINATES
# ============================================================

CHAT_X = 315
CHAT_Y = 346
SELECT_START_X = 670
SELECT_START_Y = 195
SELECT_END_X = 1472
SELECT_END_Y = 938
MESSAGE_BOX_X = 878
MESSAGE_BOX_Y = 984

# Open the correct chat yourself during the startup countdown.
# Clicking a taskbar icon can MINIMIZE an already-open WhatsApp window.
# Set this to True only if you want the original fixed chat click.
CLICK_CHAT_ON_START = False
COORDINATES_FILE = PROJECT_FOLDER / "bot_coordinates.json"


def load_coordinates():
    global SELECT_START_X, SELECT_START_Y, SELECT_END_X, SELECT_END_Y
    global MESSAGE_BOX_X, MESSAGE_BOX_Y
    if COORDINATES_FILE.exists():
        saved = json.loads(COORDINATES_FILE.read_text(encoding="utf-8"))
        SELECT_START_X, SELECT_START_Y = saved["selection_start"]
        SELECT_END_X, SELECT_END_Y = saved["selection_end"]
        MESSAGE_BOX_X, MESSAGE_BOX_Y = saved["message_box"]


def calibrate_coordinates():
    print("Open WhatsApp and the target chat. Keep the window at its normal size.", flush=True)
    input("Press Enter here when ready. You will have 5 seconds for each position...")
    saved = {}
    for name, instruction in [
        ("selection_start", "Hover directly on the FIRST LETTER of a visible message (not blank background)"),
        ("selection_end", "Hover just after the LAST LETTER of the latest visible message (not below it)"),
        ("message_box", "Move the mouse INSIDE the message typing box"),
    ]:
        print(instruction + " (recording in 5 seconds).", flush=True)
        time.sleep(5)
        saved[name] = list(pyautogui.position())
        print("Recorded:", saved[name], flush=True)
    COORDINATES_FILE.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    print("Coordinates saved. Run --test-copy to verify text selection first.", flush=True)


# ============================================================
# AI PERSONALITY
# ============================================================

SYSTEM_PROMPT = """
You are writing a WhatsApp reply on behalf of Sinujk.
Reply naturally to the latest message in the conversation.
Match the language and tone: English, Hindi, Hinglish, or Odia.
Keep the reply short, usually one or two sentences.
Return ONLY the reply, without quotation marks or a Reply label.
"""


# ============================================================
# FUNCTION: OPEN CHAT
# ============================================================

def open_chat():
    print("Switch to WhatsApp and open the target chat NOW.", flush=True)
    for seconds in range(5, 0, -1):
        print(f"Starting in {seconds}...", flush=True)
        time.sleep(1)
    if CLICK_CHAT_ON_START:
        pyautogui.click(CHAT_X, CHAT_Y)
        time.sleep(1)
    print("Reading the currently open chat.", flush=True)


# ============================================================
# FUNCTION: COPY CHAT HISTORY
# ============================================================

def wait_for_copy(marker):
    deadline = time.perf_counter() + COPY_TIMEOUT
    while time.perf_counter() <deadline:
        copied = pyperclip.paste()
        if copied != marker:
            return copied
        time.sleep(0.05)
    return None


def copy_chat_history():
    start = (SELECT_START_X, SELECT_START_Y)
    end = (SELECT_END_X, SELECT_END_Y)
    if start == end or not all(pyautogui.onScreen(*point) for point in (start, end)):
        raise RuntimeError("Selection coordinates are invalid for this screen. Run --calibrate.")

    print("Selecting text automatically. Please do not hold or move the mouse.", flush=True)
    marker = "bot-copy-" + uuid4().hex
    pyperclip.copy(marker)

    # Original selection sequence: no extra click before pressing and holding.
    pyautogui.moveTo(SELECT_START_X, SELECT_START_Y, duration=0.5)
    pyautogui.mouseDown(button="left")
    try:
        pyautogui.moveTo(SELECT_END_X, SELECT_END_Y, duration=1.5)
    finally:
        pyautogui.mouseUp(button="left")

    # Let WhatsApp finish selecting before copying. Do not click elsewhere yet.
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "c")
    copied_text = wait_for_copy(marker)
    if not copied_text or not copied_text.strip():
        print("COPY FAILED: the selected area did not produce text.", flush=True)
        return None

    print(f"Copied {len(copied_text)} characters.", flush=True)
    return copied_text.strip()


def test_copy():
    # No client, DNS lookup, taskbar click, paste, or send in this diagnostic.
    print("COPY-ONLY TEST: open WhatsApp Web and the target conversation.", flush=True)
    open_chat()
    copied_text = copy_chat_history()
    if not copied_text:
        raise RuntimeError("Copy test failed. Run --calibrate, then --test-copy again.")
    print("\n========== COPIED TEXT PREVIEW ==========", flush=True)
    print(copied_text[-1500:], flush=True)
    print("=======================================", flush=True)
    print("Check that this is your intended chat. No Gemini request or message was sent.", flush=True)


# ============================================================
# CONNECTION RECOVERY
# ============================================================


class GeminiDNSError(RuntimeError):
    pass


def is_dns_error(error):
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, socket.gaierror) or "getaddrinfo failed" in str(error).lower():
            return True
        error = error.__cause__ or error.__context__
    return False


def wait_for_dns(attempts=6):
    # Diagnose name lookup without making paid requests or changing Windows DNS.
    host = "generativelanguage.googleapis.com"
    for attempt in range(attempts):
        try:
            socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            if attempt:
                print("Gemini DNS lookup recovered. Continuing...", flush=True)
            return
        except socket.gaierror:
            if attempt == attempts - 1:
                raise GeminiDNSError(
                    "Windows still cannot resolve Gemini's server address. "
                    "Reconnect Wi-Fi or try a mobile hotspot, then run "
                    "python 04_AI_bot.py --test-api before restarting the bot."
                ) from None
            print("DNS lookup failed. Waiting 5 seconds for the connection...", flush=True)
            time.sleep(5)


# ============================================================
# FUNCTION: ASK GEMINI FOR REPLY
# ============================================================


def generate_reply(chat_history):
    print("Sending conversation to Gemini...", flush=True)
    started = time.perf_counter()
    finished = threading.Event()

    def show_waiting():
        while not finished.wait(3):
            elapsed = time.perf_counter() - started
            print(f"Waiting for Gemini response... {elapsed:.0f}s", flush=True)

    threading.Thread(target=show_waiting, daemon=True).start()
    thinking = "minimal" if "flash-lite" in MODEL else "low"
    try:
        interaction = client.interactions.create(
            model=MODEL,
            system_instruction=SYSTEM_PROMPT,
            input="WhatsApp conversation:\n" + chat_history[-MAX_HISTORY_CHARS:],
            generation_config={"thinking_level": thinking, "max_output_tokens": 1024},
            timeout=30.0,
        )
        reply = (interaction.output_text or "").strip()
        print(f"Gemini finished in {time.perf_counter() - started:.2f} seconds.", flush=True)
        if not reply:
            print("Gemini returned an empty response. Nothing will be sent.", flush=True)
            return None
        print("\n========== AI RESPONSE ==========", flush=True)
        print(reply, flush=True)
        print("=================================\n", flush=True)
        return reply
    except Exception as error:
        if is_dns_error(error):
            raise GeminiDNSError(
                "Windows could not resolve the Gemini server address (DNS error 11001)."
            ) from error
        message = str(error)
        if API_KEY:
            message = message.replace(API_KEY, "[REDACTED]")
        message = re.sub(r"AIza[\w-]+", "[REDACTED]", message)
        print(f"Gemini error ({type(error).__name__}): {message[:500]}", flush=True)
        return None
    finally:
        finished.set()


# ============================================================
# FUNCTION: SEND MESSAGE
# ============================================================


def normalize(text):
    return " ".join(text.split())


def send_message(reply):
    if not reply:
        return False
    print("Opening message box...", flush=True)
    pyautogui.click(MESSAGE_BOX_X, MESSAGE_BOX_Y)
    time.sleep(0.5)
    pyperclip.copy(reply)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.6)

    # Verify that the reply really reached the typing box before pressing Enter.
    # A wrong coordinate must not be reported as a successful send.
    pyautogui.hotkey("ctrl", "a")
    marker = "bot-verify-" + uuid4().hex
    pyperclip.copy(marker)
    pyautogui.hotkey("ctrl", "c")
    pasted_text = wait_for_copy(marker)
    pyautogui.press("right")
    if pasted_text is None or normalize(pasted_text) != normalize(reply):
        print("PASTE CHECK FAILED. Enter was NOT pressed.", flush=True)
        print("Check the typing-box position; run with --calibrate if needed.", flush=True)
        return False

    print("Reply verified in message box. Pressing Enter...", flush=True)
    pyautogui.press("enter")
    time.sleep(0.4)
    print("Enter pressed. Check WhatsApp for delivery status.", flush=True)
    return True


# ============================================================
# FUNCTION: GET CHAT HISTORY
# ============================================================


def get_chat():
    return copy_chat_history()


def is_own_reply_echo(history, last_reply):
    # Best effort only: selected screen text does not include reliable sender IDs.
    return bool(last_reply) and normalize(history).endswith(normalize(last_reply))


# ============================================================
# MAIN PROGRAM
# ============================================================


def run_bot(preview=False):
    print("==============================================", flush=True)
    print("      GEMINI WHATSAPP AUTO-REPLY BOT", flush=True)
    print("==============================================", flush=True)
    print(f"Model: {MODEL}", flush=True)
    print("Ctrl+C or mouse to the top-left corner stops the bot.", flush=True)
    wait_for_dns()
    open_app()
    open_chat()

    last_chat = ""
    last_reply = ""
    failures = 0
    copy_failures = 0

    while True:
        current_chat = get_chat()
        if not current_chat:
            copy_failures += 1
            if copy_failures >= 3:
                raise RuntimeError("Chat copy failed 3 times. Run --calibrate to correct the coordinates.")
            time.sleep(POLL_INTERVAL)
            continue
        copy_failures = 0

        if current_chat == last_chat or is_own_reply_echo(current_chat, last_reply):
            last_chat = current_chat
            print("No new message detected.", flush=True)
            time.sleep(POLL_INTERVAL)
            continue

        try:
            reply = generate_reply(current_chat)
        except GeminiDNSError as error:
            print(f"Connection interrupted: {error}", flush=True)
            print("Pausing before checking the connection again...", flush=True)
            failures += 1
            if failures >= 3:
                raise GeminiDNSError(
                    "Gemini connection keeps failing even though direct DNS lookup works. "
                    "Check proxy/VPN settings in the terminal you use to launch the bot, "
                    "or try another network, then run --test-api."
                ) from None
            time.sleep(5)
            wait_for_dns()
            # Read the latest chat after reconnection instead of sending a stale reply.
            continue
        if not reply:
            failures += 1
            if failures >= 3:
                raise RuntimeError("Gemini failed 3 times. Read the Gemini error printed above.")
            time.sleep(2 * failures)
            continue
        failures = 0

        if preview:
            print("Preview complete. No message was pasted or sent.", flush=True)
            return
        if not send_message(reply):
            raise RuntimeError("Stopped after a failed paste check. Inspect the message box before restarting.")

        # Only mark the conversation handled after a verified paste and Enter.
        last_chat = current_chat
        last_reply = reply
        time.sleep(POLL_INTERVAL)


def main():
    global client
    if "--calibrate" in sys.argv:
        calibrate_coordinates()
        return
    load_coordinates()
    if "--test-copy" in sys.argv:
        try:
            test_copy()
        except (KeyboardInterrupt, pyautogui.FailSafeException):
            print("Copy test stopped.", flush=True)
        except RuntimeError as error:
            print(str(error), flush=True)
            raise SystemExit(1) from None
        return
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing from the .env file beside this script.")
    client = genai.Client(api_key=API_KEY)
    try:
        if "--check" in sys.argv:
            print(f"Setup OK. API key loaded. Model: {MODEL}. No mouse actions or messages.")
        elif "--test-api" in sys.argv:
            wait_for_dns()
            if not generate_reply("Friend: Hi! How are you?"):
                raise SystemExit(1)
            print("API test passed. No WhatsApp message was sent.")
        else:
            run_bot(preview="--preview" in sys.argv)
    except RuntimeError as error:
        print(f"\nBot stopped: {error}", flush=True)
        raise SystemExit(1) from None
    except (KeyboardInterrupt, pyautogui.FailSafeException):
        print("\nBot stopped.", flush=True)
    finally:
        client.close()


if __name__ == "__main__":
    main()
