# atomation-reply

A Python learning project that reads visible WhatsApp Web chat text, asks Google Gemini for a short reply, and pastes and sends that reply through mouse and keyboard automation. Built with AI assistance while learning Python, API integration, and desktop automation.

## How it works

1. Open the intended WhatsApp Web conversation.
2. The bot selects and copies the visible chat using configured screen coordinates.
3. Gemini generates a reply using up to the latest 6,000 characters.
4. The bot pastes the reply, checks the pasted text, and presses Enter.
5. It checks for changes, with a best-effort check to avoid replying to its own last response.

## Setup (Windows / PowerShell)

Tested with Python 3.13 and google-genai 2.23.0.

```powershell
git clone https://github.com/babusinu986-chiki/atomation-reply.git
cd atomation-reply
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` locally and set `GEMINI_API_KEY` to your own key. Never commit it. Existing PowerShell environment variables take priority over `.env`.

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
```

Check setup and test the API separately:

```powershell
.\.venv\Scripts\python.exe .\04_AI_bot.py --check
.\.venv\Scripts\python.exe .\04_AI_bot.py --test-api
```

The API test uses a sample greeting and sends no WhatsApp message. It makes a real Gemini request.

## Calibrate and test copying

Keep WhatsApp Web at the same zoom, window size, and screen position. The default coordinates were recorded on the developer's machine.

```powershell
.\.venv\Scripts\python.exe .\04_AI_bot.py --calibrate
.\.venv\Scripts\python.exe .\04_AI_bot.py --test-copy
```

During calibration, point directly at the start and end of message text, then inside the typing box. Calibration is saved locally in `bot_coordinates.json`. The copy test shows selected text in the terminal without calling Gemini or sending messages.

To generate one reply without pasting or sending it:

```powershell
.\.venv\Scripts\python.exe .\04_AI_bot.py --preview
```

## Run

```powershell
.\.venv\Scripts\python.exe .\04_AI_bot.py
```

Normal startup clicks the configured taskbar position in `open_app()`, then shows a five-second countdown. That taskbar coordinate is also machine-specific: adjust `open_app()` if it opens or minimizes the wrong window. Switch to the intended chat during the countdown and leave the mouse and keyboard alone while the bot runs. The normal mode sends messages automatically.

Stop with **Ctrl+C** in the terminal or move the mouse to the top-left corner.

## Files

- `04_AI_bot.py`: main bot, calibration, diagnostics, and connection recovery.
- `01_get_cursour.py`: helper that prints mouse coordinates; stop it with Ctrl+C.
- `03_tutorial_example.py`: earlier tutorial experiment, not the main entry point. Running it performs mouse actions and can send a message.
- `test_bot.py`: offline tests with simulated clipboard, mouse, and API actions.
- `requirements.txt`: dependencies.
- `run_bot.ps1`: shortcut for the project virtual environment.
- `.env.example`: blank API-key configuration template.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest test_bot.py
```

Tests do not operate WhatsApp or make Gemini requests.

## Current limitations

This is a training prototype, not a WhatsApp API integration. Copying and pasting depend on screen coordinates, focus, page layout, and timing. Changing windows, scrolling, or moving the mouse can interrupt it. Sender detection is a text heuristic and may skip or duplicate replies. A successful Enter keypress does not confirm message delivery. Gemini latency and network/DNS outages can delay replies.

Copied conversation text is sent to Gemini. Use chats you are comfortable processing this way, and supervise the prototype. Browser-element-based message selection is a possible future improvement.
