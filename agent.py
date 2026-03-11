"""
AI Desktop Agent — powered by Claude
=====================================
Takes a task in natural language, captures your screen,
sends it to Claude for reasoning, and executes the returned actions
on your desktop (mouse, keyboard, opening apps, browser, etc.).

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python agent.py
"""

import anthropic
import pyautogui
import subprocess
import platform
import base64
import json
import time
import sys
import os
import io
import re
import webbrowser
from datetime import datetime

# Optional: mss is faster for screenshots
try:
    import mss
    USE_MSS = True
except ImportError:
    USE_MSS = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "YOUR_API_KEY_HERE")
MODEL = "claude-sonnet-4-20250514"  # or claude-3-5-sonnet, claude-3-opus, etc.
MAX_LOOPS = 50                     # safety: max action loops per task
DELAY_BETWEEN_ACTIONS = 0.5        # seconds between actions
SCREENSHOT_SCALE = 0.5             # downscale factor for screenshots (save tokens)
REQUIRE_CONFIRMATION = True        # ask user before each action?
SYSTEM_OS = platform.system()      # "Windows", "Darwin", "Linux"

pyautogui.FAILSAFE = True          # move mouse to corner to abort
pyautogui.PAUSE = 0.3

# ---------------------------------------------------------------------------
# Screenshot Utility
# ---------------------------------------------------------------------------

def take_screenshot_base64(scale=SCREENSHOT_SCALE):
    """Capture the screen and return a base64-encoded JPEG string."""
    if USE_MSS:
        with mss.mss() as sct:
            monitor = sct.monitors[0]  # full virtual screen
            img = sct.grab(monitor)
            from PIL import Image
            pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
    else:
        pil_img = pyautogui.screenshot()

    # Downscale to save tokens
    if scale != 1.0:
        from PIL import Image
        new_size = (int(pil_img.width * scale), int(pil_img.height * scale))
        pil_img = pil_img.resize(new_size, Image.LANCZOS)

    buffer = io.BytesIO()
    pil_img.save(buffer, format="JPEG", quality=75)
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8"), pil_img.size


def get_screen_size():
    """Return the real (unscaled) screen size."""
    return pyautogui.size()

# ---------------------------------------------------------------------------
# Action Executor
# ---------------------------------------------------------------------------

class ActionExecutor:
    """Executes structured actions returned by Claude."""

    def __init__(self):
        self.screen_w, self.screen_h = get_screen_size()

    def execute(self, action: dict) -> str:
        """
        Execute one action dict and return a status string.
        Supported action types:
            - click          {type, x, y, button?, clicks?}
            - double_click   {type, x, y}
            - right_click    {type, x, y}
            - move_mouse     {type, x, y}
            - type_text      {type, text}
            - hotkey          {type, keys}  e.g. keys: ["ctrl", "c"]
            - press_key      {type, key}   e.g. key: "enter"
            - scroll         {type, x, y, direction, amount}
            - open_app       {type, app_name}
            - open_url       {type, url}
            - shell_command  {type, command}
            - wait           {type, seconds}
            - screenshot     {type}  (no-op, next loop takes one)
            - done           {type, summary}
        """
        atype = action.get("type", "").lower()
        try:
            if atype == "click":
                x, y = self._coords(action)
                btn = action.get("button", "left")
                clicks = action.get("clicks", 1)
                pyautogui.click(x, y, clicks=clicks, button=btn)
                return f"Clicked ({x},{y}) button={btn} clicks={clicks}"

            elif atype == "double_click":
                x, y = self._coords(action)
                pyautogui.doubleClick(x, y)
                return f"Double-clicked ({x},{y})"

            elif atype == "right_click":
                x, y = self._coords(action)
                pyautogui.rightClick(x, y)
                return f"Right-clicked ({x},{y})"

            elif atype == "move_mouse":
                x, y = self._coords(action)
                pyautogui.moveTo(x, y)
                return f"Moved mouse to ({x},{y})"

            elif atype == "type_text":
                text = action.get("text", "")
                pyautogui.typewrite(text, interval=0.03) if text.isascii() else pyautogui.write(text)
                return f"Typed: {text[:60]}..."

            elif atype == "hotkey":
                keys = action.get("keys", [])
                pyautogui.hotkey(*keys)
                return f"Hotkey: {'+'.join(keys)}"

            elif atype == "press_key":
                key = action.get("key", "enter")
                pyautogui.press(key)
                return f"Pressed key: {key}"

            elif atype == "scroll":
                x, y = self._coords(action)
                direction = action.get("direction", "down")
                amount = action.get("amount", 3)
                scroll_val = -amount if direction == "down" else amount
                pyautogui.scroll(scroll_val, x, y)
                return f"Scrolled {direction} by {amount} at ({x},{y})"

            elif atype == "open_app":
                app = action.get("app_name", "")
                self._open_application(app)
                return f"Opened application: {app}"

            elif atype == "open_url":
                url = action.get("url", "")
                webbrowser.open(url)
                return f"Opened URL: {url}"

            elif atype == "shell_command":
                cmd = action.get("command", "")
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=15
                )
                output = (result.stdout + result.stderr).strip()[:500]
                return f"Shell: {cmd}\nOutput: {output}"

            elif atype == "wait":
                secs = action.get("seconds", 2)
                time.sleep(secs)
                return f"Waited {secs}s"

            elif atype == "screenshot":
                return "Will take a fresh screenshot next loop."

            elif atype == "done":
                return "DONE: " + action.get("summary", "Task complete.")

            else:
                return f"Unknown action type: {atype}"

        except Exception as e:
            return f"Error executing {atype}: {e}"

    # ---- helpers ----

    def _coords(self, action):
        """Extract and scale x,y coordinates back to real screen size."""
        x = int(action.get("x", 0))
        y = int(action.get("y", 0))
        # If Claude sent coordinates based on the scaled screenshot,
        # we scale them back up.
        if SCREENSHOT_SCALE != 1.0:
            x = int(x / SCREENSHOT_SCALE)
            y = int(y / SCREENSHOT_SCALE)
        x = max(0, min(x, self.screen_w - 1))
        y = max(0, min(y, self.screen_h - 1))
        return x, y

    def _open_application(self, app_name: str):
        app = app_name.lower().strip()
        if SYSTEM_OS == "Windows":
            # Try Start Menu search via subprocess
            common = {
                "notepad": "notepad.exe",
                "calculator": "calc.exe",
                "paint": "mspaint.exe",
                "file explorer": "explorer.exe",
                "explorer": "explorer.exe",
                "cmd": "cmd.exe",
                "command prompt": "cmd.exe",
                "terminal": "wt.exe",
                "powershell": "powershell.exe",
                "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                "google chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
                "edge": "msedge.exe",
                "word": "winword.exe",
                "excel": "excel.exe",
                "outlook": "outlook.exe",
            }
            exe = common.get(app, app_name)
            subprocess.Popen(exe, shell=True)

        elif SYSTEM_OS == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", app_name])

        else:  # Linux
            subprocess.Popen(app_name, shell=True)

# ---------------------------------------------------------------------------
# Claude Agent Brain
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You are an AI agent controlling a {SYSTEM_OS} computer.
You see a screenshot of the user's screen each turn. Your job is to complete
the user's task by issuing actions.

## Screen info
- OS: {SYSTEM_OS}
- Real screen size: {get_screen_size()}
- Screenshot scale factor: {SCREENSHOT_SCALE}
  (coordinates you return should be relative to the SCALED screenshot image)

## Available actions (return as JSON array)
Return a JSON array of action objects. Each loop you may return 1-3 actions max.
The system will execute them in order, then take a new screenshot.

Action types:
1. click          — {{type:"click", x:INT, y:INT, button:"left"|"right", clicks:1}}
2. double_click   — {{type:"double_click", x:INT, y:INT}}
3. right_click    — {{type:"right_click", x:INT, y:INT}}
4. move_mouse     — {{type:"move_mouse", x:INT, y:INT}}
5. type_text      — {{type:"type_text", text:"string to type"}}
6. hotkey         — {{type:"hotkey", keys:["ctrl","a"]}}
7. press_key      — {{type:"press_key", key:"enter"}}
8. scroll         — {{type:"scroll", x:INT, y:INT, direction:"up"|"down", amount:3}}
9. open_app       — {{type:"open_app", app_name:"Chrome"}}
10. open_url      — {{type:"open_url", url:"https://..."}}
11. shell_command — {{type:"shell_command", command:"echo hello"}}
12. wait          — {{type:"wait", seconds:2}}
13. screenshot    — {{type:"screenshot"}}  (request a fresh screenshot without acting)
14. done          — {{type:"done", summary:"what was accomplished"}}

## Rules
- Return ONLY a JSON array. No other text outside the JSON.
- Coordinates are pixel positions in the SCALED screenshot image.
- When a task is fully complete, return [{{"type":"done","summary":"..."}}].
- Be careful with sensitive actions. Double-check before clicking dangerous buttons.
- If you need to wait for something to load, use the wait action.
- If you're stuck or can't proceed, return done with a summary explaining why.
- For typing into a field, first click on the field, then type_text.
- If the user asks to log into an account, they will need to have already provided
  credentials or be logged in. You can navigate to login pages and fill in fields.
"""


class ClaudeAgent:
    """The main agent loop: screenshot → Claude → actions → repeat."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.executor = ActionExecutor()
        self.conversation_history = []

    def run(self, task: str):
        """Run the agent on a task until done or max loops reached."""
        print(f"\n{'='*60}")
        print(f"  TASK: {task}")
        print(f"{'='*60}\n")

        # Add initial user message with the task
        self.conversation_history = []

        for loop_num in range(1, MAX_LOOPS + 1):
            print(f"\n--- Loop {loop_num}/{MAX_LOOPS} ---")

            # 1. Take screenshot
            print("  📸 Taking screenshot...")
            screenshot_b64, img_size = take_screenshot_base64()
            print(f"  Screenshot size: {img_size}")

            # 2. Build the message for this turn
            user_content = []
            if loop_num == 1:
                user_content.append({
                    "type": "text",
                    "text": f"TASK: {task}\n\nHere is the current screenshot of my screen. "
                            f"Analyze it and decide what actions to take to accomplish the task. "
                            f"Return a JSON array of actions."
                })
            else:
                user_content.append({
                    "type": "text",
                    "text": "Here is the updated screenshot after the previous actions. "
                            "Continue working on the task. Return a JSON array of actions."
                })

            user_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": screenshot_b64,
                }
            })

            self.conversation_history.append({
                "role": "user",
                "content": user_content,
            })

            # 3. Call Claude
            print("  🧠 Asking Claude for actions...")
            try:
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=2048,
                    system=SYSTEM_PROMPT,
                    messages=self.conversation_history,
                )
                assistant_text = response.content[0].text.strip()
            except Exception as e:
                print(f"  ❌ Claude API error: {e}")
                time.sleep(5)
                # Remove the last user message so we can retry
                self.conversation_history.pop()
                continue

            # Save assistant response in history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_text,
            })

            # Keep conversation history manageable (last 20 turns)
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            # 4. Parse actions from Claude's response
            actions = self._parse_actions(assistant_text)
            if not actions:
                print(f"  ⚠️  Could not parse actions from response:")
                print(f"      {assistant_text[:200]}")
                continue

            # 5. Execute each action
            for i, action in enumerate(actions):
                atype = action.get("type", "unknown")
                print(f"\n  🎯 Action {i+1}: {json.dumps(action, indent=2)}")

                # Confirmation gate
                if REQUIRE_CONFIRMATION and atype not in ("screenshot", "wait", "done"):
                    confirm = input("     Execute? [Y/n/skip/quit]: ").strip().lower()
                    if confirm == "n" or confirm == "skip":
                        print("     Skipped.")
                        continue
                    if confirm == "quit" or confirm == "q":
                        print("     Quitting agent.")
                        return

                result = self.executor.execute(action)
                print(f"     ✅ {result}")

                if atype == "done":
                    print(f"\n{'='*60}")
                    print(f"  ✅ TASK COMPLETE")
                    print(f"  Summary: {action.get('summary', 'N/A')}")
                    print(f"{'='*60}\n")
                    return

                time.sleep(DELAY_BETWEEN_ACTIONS)

        print(f"\n⚠️  Reached max loops ({MAX_LOOPS}). Stopping.")

    def _parse_actions(self, text: str) -> list:
        """Extract a JSON array of actions from Claude's response."""
        # Try to find JSON array in the response
        # First try: direct parse
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
        except json.JSONDecodeError:
            pass

        # Second try: find JSON array with regex
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Third try: find JSON object
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, dict):
                    return [parsed]
            except json.JSONDecodeError:
                pass

        return []

# ---------------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------------

def print_banner():
    banner = """
    ╔═══════════════════════════════════════════════════╗
    ║         🤖  Claude Desktop Agent  🖥️              ║
    ║                                                   ║
    ║  I can see your screen, control mouse/keyboard,   ║
    ║  open apps, browse the web, and automate tasks.   ║
    ║                                                   ║
    ║  Safety: Move mouse to screen corner to abort.    ║
    ║          Each action requires confirmation.        ║
    ╚═══════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    print_banner()

    # Check API key
    if ANTHROPIC_API_KEY == "YOUR_API_KEY_HERE" or not ANTHROPIC_API_KEY:
        print("❌ Please set your ANTHROPIC_API_KEY environment variable:")
        print("   export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    agent = ClaudeAgent()

    print("Type a task and press Enter. Type 'quit' to exit.\n")

    while True:
        try:
            task = input("🎯 What should I do? > ").strip()
            if not task:
                continue
            if task.lower() in ("quit", "exit", "q"):
                print("Goodbye! 👋")
                break

            # Settings commands
            if task.lower() == "noconfirm":
                global REQUIRE_CONFIRMATION
                REQUIRE_CONFIRMATION = False
                print("⚠️  Confirmation disabled. Actions will execute automatically.")
                continue
            if task.lower() == "confirm":
                REQUIRE_CONFIRMATION = True
                print("✅ Confirmation re-enabled.")
                continue

            agent.run(task)

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye! 👋")
            break


if __name__ == "__main__":
    main()
