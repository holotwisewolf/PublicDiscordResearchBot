# 🤖 Multi-AI Research Bot

A Discord bot that coordinates multiple AI models (Claude, GPT-4, Gemini) for rigorous research workflows. Route questions to the right AI based on cost and capability.

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

## ✨ Features

- **Multi-AI Routing** - Use the right model for each task
- **Research Mode** - Deep analysis with Claude ($$$)
- **Hard Mode** - Aggressive skepticism to stress-test ideas
- **Free Coding** - Simple scripts with Gemini (FREE!)
- **Consensus** - Query all 3 AIs and compare responses
- **Task Tracking** - Manage research tasks in Discord
- **Context-Aware** - Loads your project context from local files

## 🧠 AI Model Strategy

| Role | Model | Cost | Best For |
|------|-------|------|----------|
| **General** | GPT-4 | 💲 | Quick answers, definitions |
| **Reasoner** | Claude 3.5 Sonnet | 💲💲💲 | Deep analysis, critique |
| **Coder** | Gemini Pro | FREE | Simple scripts, quick fixes |
| **Builder** | Claude 3.5 Sonnet | 💲💲💲 | Complex implementation |

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/ResearchBot.git
cd ResearchBot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Setup Wizard
```bash
python setup.py
```

The wizard will guide you through:
- Discord bot token
- API keys (Anthropic, OpenAI, Gemini)
- Discord channel IDs

### 4. Customize Your Prompts
Copy and edit the template files in `prompts/templates/`:
```bash
cp prompts/templates/canon_template.md prompts/canon.md
cp prompts/templates/discipline_template.md prompts/discipline.md
cp prompts/templates/structure_template.md prompts/structure.md
```

### 5. Run the Bot
```bash
python main.py
```

---

## 🔧 Getting API Keys

| Service | URL | Notes |
|---------|-----|-------|
| **Discord** | [Discord Developer Portal](https://discord.com/developers/applications) | Create a bot, get token |
| **Anthropic** | [Anthropic Console](https://console.anthropic.com/) | Claude API |
| **OpenAI** | [OpenAI Platform](https://platform.openai.com/) | GPT-4 API |
| **Gemini** | [Google AI Studio](https://aistudio.google.com/app/apikey) | **FREE!** |

### Discord Bot Setup
1. Create application at Discord Developer Portal
2. Go to "Bot" tab → Create bot
3. Copy the token
4. Enable "Message Content Intent"
5. Invite bot to your server with appropriate permissions

---

## 📚 Command Reference

### 💬 General & Quick
| Command | Usage | Description |
|---------|-------|-------------|
| `!ask` | `!ask [question]` | Ask **GPT-4**. Best for general questions. |
| `!gemini` | `!gemini [question]` | Ask **Gemini** directly. **FREE**. |

### 🧠 Deep Research & Reasoning
| Command | Usage | Description |
|---------|-------|-------------|
| `!deep` | `!deep [topic]` | Deep research with full context. |
| `!research`| `!research [topic]` | *Alias for `!deep`.* |
| `!hardmode`| `!hardmode [idea]` | **Aggressive skepticism.** Try to destroy the idea. |

### 🛠️ Coding & Building
| Command | Usage | Description |
|---------|-------|-------------|
| `!code` | `!code [request]` | **Gemini** (Free). Simple scripts. |
| `!build` | `!build [request]` | **Claude**. Complex implementation with assumption checking. |

### 📋 Task Management
| Command | Usage | Description |
|---------|-------|-------------|
| `!task` | `!task [description]` | Create a new active task. |
| `!complete`| `!complete [id] [result]`| Mark a task as done. |

### ⚖️ Consensus & Verification
| Command | Usage | Description |
|---------|-------|-------------|
| `!crosscheck`| `!crosscheck [query]` | **Claude** and **GPT-4** side-by-side. |
| `!consensus` | `!consensus [query]` | All 3 AIs. Logs results to #findings. |

### 🔧 Utilities
| Command | Usage | Description |
|---------|-------|-------------|
| `!log_finding`| `!log_finding [text]` | Save insight to #findings. |
| `!context` | `!context [channel] [n]` | View last n messages from a channel. |
| `!channels` | `!channels` | List all configured channels. |
| `!help_bot` | `!help_bot` | Show command summary. |

---

## 📁 Project Structure

```
ResearchBot/
├── main.py              # Main bot code
├── setup.py             # Interactive setup wizard
├── config.json          # Your channel IDs (created by setup)
├── config.example.json  # Template configuration
├── .env                 # Your API keys (created by setup)
├── .env.example         # Template environment file
├── requirements.txt     # Python dependencies
├── LICENSE              # CC BY-NC 4.0
└── prompts/
    ├── canon.md         # Your project's source of truth
    ├── structure.md     # Project structure description
    ├── discipline.md    # Research discipline rules
    ├── research_core.md # Research agent prompt
    ├── research_hardmode.md # Hard mode prompt
    └── templates/       # Template files for new users
```

---

## 💼 Support & Services

This project is **free for non-commercial use** under CC BY-NC 4.0.

**Need help?**
- **Custom Setup** - I'll configure the bot for your Discord server
- **Prompt Engineering** - Tailored prompts for your research domain
- **Commercial License** - Contact for commercial use

📧 **Contact:** yjchoongwork@gmail.com

---

## 📜 License

This work is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).

- ✅ Free for personal and educational use
- ✅ Modify and share with attribution
- ❌ Commercial use requires separate license

For commercial licensing, contact: yjchoongwork@gmail.com
