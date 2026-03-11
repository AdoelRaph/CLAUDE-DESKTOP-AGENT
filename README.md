# Claude Desktop Agent

An AI agent that lets Claude see your screen and control your computer to complete tasks automatically.

## What It Solves
AI models are trapped in chat windows - they can think but can't do. This agent bridges that gap by letting Claude:
- 👁️ **See** your screen via screenshots
- 🖱️ **Control** your mouse and keyboard
- 🚀 **Open** applications and browse websites
- ✅ **Execute** tasks while you supervise

## How It Works

The agent operates on a **screenshot → reason → act** loop:

```
┌─────────────────────────────────────────────────┐
│                  YOU: "Book a flight             │
│                  to NYC on Google Flights"        │
│                                                   │
│   ┌───────────┐    ┌──────────┐    ┌──────────┐  │
│   │ Screenshot │───▶│  Claude   │───▶│ Execute  │  │
│   │  (vision)  │    │ (reason)  │    │ Actions  │  │
│   └───────────┘    └──────────┘    └──────────┘  │
│         ▲                               │         │
│         └───────────────────────────────┘         │
│                    (repeat)                        │
└─────────────────────────────────────────────────┘
```

## Quick Start

### Installation
```bash
# Install dependencies
pip install anthropic pyautogui pillow mss pynput

# Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Run the agent
python agent.py
```

### First Task
```bash
🎯 What should I do? > Open Notepad and write "Hello World"
```

The agent will:
1. Take a screenshot of your screen
2. Claude identifies where Notepad is
3. Agent moves mouse and clicks to open it
4. Types the text
5. You approve each step

## Example Tasks

Try these out:

| Category | Example |
|----------|---------|
| **Email** | `Open Chrome and go to gmail.com, compose an email to john@example.com saying hello` |
| **Calculations** | `Open the calculator app and compute 1547 × 382` |
| **Coding** | `Open VS Code, create a new file called hello.py, and write a hello world program` |
| **Social Media** | `Go to twitter.com and post a tweet saying Good Morning` |
| **File Management** | `Open File Explorer and create a new folder called Projects on the Desktop` |
| **System Tasks** | `Take a screenshot of my desktop and save it to Downloads` |

## Safety Features

The agent includes multiple safety mechanisms:

| Feature | Description |
|---------|-------------|
| **🔒 Confirmation Mode** | ON by default - every action requires your approval before execution |
| **🛑 Failsafe** | Move mouse to any screen corner to instantly abort the script |
| **⏱️ Max Loop Limit** | 50 iterations maximum to prevent infinite loops |
| **💾 Token Management** | Conversation history capped at 20 turns to control API costs |
| **👀 Transparency** | You see every action before it executes |

### Disable Confirmations (Not Recommended)
```bash
# At the prompt, type:
noconfirm
```

## Customization Tips

| Setting | Description | Default |
|---------|-------------|---------|
| `MODEL` | Claude model to use | `claude-3-sonnet-20240229` |
| `SCREENSHOT_SCALE` | Reduce for lower token costs | `0.5` (50% scaling) |
| `REQUIRE_CONFIRMATION` | Auto-execute without asking | `True` |
| `DELAY_BETWEEN_ACTIONS` | Seconds between actions | `0.5` |
| `MAX_LOOPS` | Safety limit per task | `50` |

### Add Custom Applications
Edit the `_open_application` method in `agent.py`:
```python
common = {
    "myapp": "C:\\Path\\To\\MyApp.exe",
    "custom": "/Applications/Custom.app",
    # Add your apps here
}
```

## Important Considerations

⚠️ **This agent has real control over your computer**

- **Start with confirmation mode ON** - Review every action
- **Watch the first few runs** - Ensure it behaves as expected
- **API costs** - Each loop sends an image (~1000+ tokens). A 10-step task might cost $0.10-0.30
- **Be specific** - Clear tasks get better results
- **Supervise sensitive operations** - Especially around login pages or delete buttons

## Requirements

- Python 3.8+
- Anthropic API key with access to Claude vision models
- Operating System: Windows, macOS, or Linux

## Dependencies
```
anthropic>=0.18.0
pyautogui>=0.9.54
pillow>=10.0.0
mss>=9.0.0  # optional, faster screenshots
pynput>=1.7.6
```

## Troubleshooting

**Issue:** "No module named X"
```bash
pip install [module-name]
```

**Issue:** Agent clicks wrong locations
- Ensure `SCREENSHOT_SCALE` matches between screenshot and coordinate calculation
- Check if your display scaling (125%, 150%) affects coordinates

**Issue:** Application won't open
- Add full path in the `_open_application` method
- On macOS, use `open -a "Application Name"`

## Contributing

Ideas for improvements:
- Voice control integration
- Multi-monitor support
- Task scheduling
- Error recovery strategies
- Recording/replaying tasks
- Different LLM backends

## License

MIT - Feel free to use, modify, and distribute

---

**Remember:** You're in control. The agent follows your commands, and you approve each action. Use responsibly!
