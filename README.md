How It Works
The agent operates on a screenshot → reason → act loop. Here's the flow:

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

Example tasks you can give it:

"Open Chrome and go to gmail.com and compose an email to john@example.com saying hello"
"Open the calculator app and compute 1547 × 382"
"Open VS Code, create a new file called hello.py, and write a hello world program"
"Go to twitter.com and post a tweet saying Good Morning"
"Open File Explorer and create a new folder called Projects on the Desktop"
"Take a screenshot of my desktop and save it to Downloads"
Safety Features
The code includes several safety mechanisms:

Confirmation mode is on by default — every action is shown to you and requires approval before execution. Type noconfirm at the prompt to disable this (at your own risk). PyAutoGUI failsafe is enabled — moving your mouse to any corner of the screen instantly aborts the script. There's a max loop limit of 50 iterations to prevent infinite loops. The conversation history is capped at 20 turns to avoid unbounded token usage.

Customization Tips
You can change MODEL to any Claude model you have access to (e.g. claude-3-5-sonnet-20241022). Lower SCREENSHOT_SCALE to reduce API costs (smaller images = fewer tokens). Set REQUIRE_CONFIRMATION = False in the code if you want fully autonomous operation. Adjust DELAY_BETWEEN_ACTIONS if your machine needs more time between steps. Add more application paths in the _open_application method for your specific installed software.

Important: This agent has real control over your computer. Always start with confirmation mode on, and review each action before approving it. Your Anthropic API key is used for every screenshot+reasoning call, so be mindful of token costs — each loop sends an image (~1000+ tokens).
