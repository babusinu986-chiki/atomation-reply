# ----------------------
# This the traiel or the example before trying this live so this is not a real or the working code.
# So do not copy this file and the code the real one is 04_AI_bot.py written by me with the help of AI.
# ----------------------
import pyautogui
import pyperclip
import time
from google import genai
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
client = genai.Client(

  api_key=os.environ["GEMINI_API_KEY"]
  )

# Safety: move mouse to the top-left corner to stop the script
pyautogui.FAILSAFE = True

# Give yourself time to switch to the correct window
print("Starting in 3 seconds...")
time.sleep(3)

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

# --------------------------------------------------
# 2. Click the person/chat at (315, 346)
# --------------------------------------------------

pyautogui.click(315,346)

print("Chat/person clicked.")

# Wait for the chat to load
time.sleep(2)

# --------------------------------------------------
# 3. Select all text from (538, 140) to (1221, 935)
# --------------------------------------------------

print("Selecting text...")

# Move to the starting point
pyautogui.moveTo(670, 195, duration=0.5)

# Press and hold the left mouse button
pyautogui.mouseDown()

# Drag to the ending point
pyautogui.moveTo(1472, 938, duration=1.5)

# Release the mouse button
pyautogui.mouseUp()

print("Text selected.")

# --------------------------------------------------
# 4. Copy the selected text
# --------------------------------------------------

time.sleep(0.5)

pyautogui.hotkey("ctrl", "c")
pyautogui.click(873, 658)
print("Copy command executed.")

# --------------------------------------------------
# 5. Read the clipboard into a variable
# --------------------------------------------------

time.sleep(0.5)

copied_text = pyperclip.paste()

# --------------------------------------------------
# 6. Print the copied text
# --------------------------------------------------

print("\n========== COPIED TEXT ==========\n")
print(copied_text)
print("\n=================================")


response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=copied_text
)


reply = response.text

print("\n========= AI RESPONSE ==========")
print(reply)
print("\n================================")

print(response.text)
# --------------------------------------------------
# 7. Paste AI response into the chat box
# --------------------------------------------------

print("Opening message box...")

pyautogui.click(878, 984)

time.sleep(0.5)

# Put the value of 'reply' into clipboard
pyperclip.copy(reply)

# Paste the value of 'reply'
pyautogui.hotkey("ctrl", "v")

time.sleep(1)

print("AI response pasted into chat box.")

# Send the message
pyautogui.press("enter")

print("AI reply sent successfully.")