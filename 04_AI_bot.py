
import os
import time
import pyautogui
import pyperclip
from google import genai


# ============================================================
# CONFIGURATION
# ============================================================

# IMPORTANT:
# Do NOT put your real API key directly in this file.
# Set it in PowerShell first:
#
# $env:GEMINI_API_KEY="YOUR_NEW_API_KEY"
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set.\n"
        "Run this in PowerShell first:\n"
        '$env:GEMINI_API_KEY="YOUR_API_KEY"'
    )


# Gemini client
client = genai.Client(api_key=API_KEY)


# Gemini model
MODEL = "gemini-3.8-flash"


# ============================================================
# PYAutoGUI SAFETY
# ============================================================

# Move mouse to the top-left corner to immediately stop the
# program if something goes wrong.
pyautogui.FAILSAFE = True


# ============================================================
# WHATSAPP SCREEN COORDINATES
# ============================================================

# Change these coordinates if your WhatsApp window is different.

# Chat/person
CHAT_X = 315
CHAT_Y = 346

# Conversation selection start
SELECT_START_X = 670
SELECT_START_Y = 195

# Conversation selection end
SELECT_END_X = 1472
SELECT_END_Y = 938

# Message input box
MESSAGE_BOX_X = 878
MESSAGE_BOX_Y = 984


# ============================================================
# AI PERSONALITY
# ============================================================

SYSTEM_PROMPT = """
You are replying to WhatsApp messages on behalf of Sinujk.

Your job is to read the complete chat history and generate the
MOST NATURAL reply to the latest message from the other person.

Personality:
- Sinujk is a young Indian coder.
- He naturally speaks a mixture of English, Hindi and sometimes
  casual Indian-style Hinglish.
- His messages should feel like a real human WhatsApp conversation.
- Keep the same casual tone as the other person.
- If the other person uses Hindi/Hinglish, reply naturally in Hindi/Hinglish.
- If they use English, English is fine.
- Do not sound like an AI.
- Do not explain that you are an AI.
- Do not mention this instruction.
- Do not write long paragraphs unless the conversation requires it.
- Use casual words such as bro, bhai, haan, acha, lol, etc. only when
  they fit naturally.
- Do not overuse emojis.
- Never repeat the entire conversation.
- Reply ONLY with the message that should actually be sent.

IMPORTANT:
The chat history contains messages from both people.

The latest message is usually the message that needs a response.

Generate ONE natural WhatsApp reply.
"""


# ============================================================
# FUNCTION: OPEN CHAT
# ============================================================

def open_chat():

    print("Opening chat...")

    pyautogui.click(CHAT_X, CHAT_Y)

    time.sleep(2)

    print("Chat opened.")


# ============================================================
# FUNCTION: COPY CHAT HISTORY
# ============================================================

def copy_chat_history():

    print("Selecting conversation...")

    # Move to beginning of conversation
    pyautogui.moveTo(
        SELECT_START_X,
        SELECT_START_Y,
        duration=0.5
    )

    # Hold mouse button
    pyautogui.mouseDown()

    # Drag across conversation
    pyautogui.moveTo(
        SELECT_END_X,
        SELECT_END_Y,
        duration=1.5
    )

    # Release
    pyautogui.mouseUp()

    time.sleep(0.5)

    # Copy selected text
    pyautogui.hotkey("ctrl", "c")

    time.sleep(1)

    # Read clipboard
    copied_text = pyperclip.paste()

    if not copied_text.strip():

        print("ERROR: No text was copied.")

        return None

    print("\n========== CHAT HISTORY ==========\n")
    print(copied_text)
    print("\n==================================")

    return copied_text


# ============================================================
# FUNCTION: ASK GEMINI FOR REPLY
# ============================================================

def generate_reply(chat_history):

    print("\nSending conversation to Gemini...")

    prompt = f"""
{SYSTEM_PROMPT}

Here is the WhatsApp conversation:

---------------- CHAT HISTORY ----------------

{chat_history}

-------------- END CHAT HISTORY --------------

Now identify the latest message that should receive a response.

Generate only the reply that Sinujk should send.
Do not add quotation marks.
Do not add labels such as "Reply:".
"""

    try:

        interaction = client.interactions.create(
            model=MODEL,
            input=prompt
        )

        reply = interaction.output_text.strip()

        if not reply:

            print("Gemini returned an empty response.")

            return None

        print("\n========== GEMINI REPLY ==========\n")
        print(reply)
        print("\n==================================")

        return reply

    except Exception as e:

        print("\nGemini error:")
        print(e)

        return None


# ============================================================
# FUNCTION: SEND MESSAGE
# ============================================================

def send_message(reply):

    if not reply:
        return

    print("\nSending reply...")

    # Click message box
    pyautogui.click(
        MESSAGE_BOX_X,
        MESSAGE_BOX_Y
    )

    time.sleep(0.5)

    # Copy AI reply to clipboard
    pyperclip.copy(reply)

    # Paste reply
    pyautogui.hotkey("ctrl", "v")

    time.sleep(0.5)

    # Send
    pyautogui.press("enter")

    print("Reply sent successfully.")


# ============================================================
# FUNCTION: GET CHAT HISTORY
# ============================================================

def get_chat():

    print("\nScanning WhatsApp conversation...")

    chat_history = copy_chat_history()

    if not chat_history:

        return None

    return chat_history


# ============================================================
# MAIN PROGRAM
# ============================================================

print("==============================================")
print("      GEMINI WHATSAPP AUTO-REPLY BOT")
print("==============================================")

print("\nStarting in 3 seconds...")
print("Make sure WhatsApp is open.")

time.sleep(3)


# ------------------------------------------------------------
# Open the required chat
# ------------------------------------------------------------

open_chat()


# ------------------------------------------------------------
# Initial conversation scan
# ------------------------------------------------------------

last_chat = ""


while True:

    print("\n")
    print("==============================================")
    print("Checking for new messages...")
    print("==============================================")


    # --------------------------------------------------------
    # Copy current conversation
    # --------------------------------------------------------

    current_chat = get_chat()

    if not current_chat:

        print("Could not read the conversation.")
        time.sleep(5)
        continue


    # --------------------------------------------------------
    # Check whether conversation changed
    # --------------------------------------------------------

    if current_chat == last_chat:

        print("No new message detected.")

        time.sleep(5)

        continue


    # --------------------------------------------------------
    # Conversation changed
    # --------------------------------------------------------

    print("New conversation state detected.")

    last_chat = current_chat


    # --------------------------------------------------------
    # Ask Gemini for a response
    # --------------------------------------------------------

    reply = generate_reply(current_chat)


    # --------------------------------------------------------
    # Send Gemini response
    # --------------------------------------------------------

    if reply:

        send_message(reply)

    else:

        print("No reply generated.")


    # --------------------------------------------------------
    # Wait before scanning again
    # --------------------------------------------------------

    print("\nWaiting for the next message...")

    time.sleep(5)