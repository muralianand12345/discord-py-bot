# Discord Name Changer Bot

A specialized Discord bot that automatically translates usernames to Japanese when users join, alongside AI-powered welcome messages and chatbot functionality.

![Python](https://img.shields.io/badge/Python-3.12+-blue?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Discord](https://img.shields.io/badge/Discord-Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white)

## ✨ Features

### 🌏 Nickname Translation

- **Auto Translation**: Automatically translates usernames to Japanese when new users join
- **Fallback System**: Uses katakana romanization if translation service is unavailable

### 👋 Welcome System

- **AI-Generated Greetings**: Personalized welcome messages using LLM
- **Customized Embeds**: Rich embeds showing user details and translated names
- **Auto-Role Assignment**: Automatically assigns roles to new members
- **Goodbye Messages**: Custom farewell messages when members leave

### 🤖 AI Chatbot

- **Contextual Conversations**: Remembers conversation history
- **Discord-Optimized Responses**: Formatted for Discord's markdown
- **Per-Channel Configuration**: Can be enabled in specific channels

## 🔧 Requirements

- Python 3.12+
- Discord Bot Token
- Groq API Key for LLM features

## 🚀 Installation

1. **Clone the repository**

   ```bash
   git clone git@github.com:muralianand12345/discord-py-bot.git
   cd discord-name-changer
   ```

2. **Set up a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -e .
   ```

4. **Configure your bot**

   ```bash
   cp .env.example .env
   # Edit the .env file with your Discord Bot Token and Groq API Keys
   ```

## ⚙️ Configuration

The bot is configured via environment variables in the `.env` file:

### Bot Configuration

- `BOT_TOKEN`: Your Discord Bot Token
- `BOT_PREFIX`: Command prefix (default: `!`)
- `GUILD_ID`: Your server ID (bot is designed for single guild usage)

### Welcome System

- `WELCOME_CHANNEL_ID`: Channel ID for welcome messages
- `GOODBYE_CHANNEL_ID`: Channel ID for goodbye messages
- `DEFAULT_ROLE_ID`: Role ID to assign to new members

### LLM Configuration

- Four separate LLM keys can be configured for different features:
  - Welcome messages
  - Goodbye messages
  - Name translation
  - Chatbot functionality

### Chatbot Settings

- `CHATBOT_ENABLED`: Enable/disable chatbot
- `CHATBOT_CHANNELS`: Channel IDs where chatbot responds
- `CHATBOT_MAX_HISTORY`: Number of messages to remember
- `CHATBOT_NAME`: Name for your bot's personality

## 🏗️ Project Structure

```md
discord-name-changer/
├── .env                  # Environment variables
├── pyproject.toml       # Project dependencies
├── README.md            # Project documentation
├── src/                 # Source code
│   ├── bot.py           # Bot initialization
│   ├── main.py          # Application entry point
│   ├── config.py        # Configuration loader
│   ├── events/          # Event handlers
│   │   ├── __init__.py
│   │   ├── welcome_members.py
│   │   ├── goodbye_members.py
│   │   └── chatbot.py
│   └── utils/           # Utility modules
│       ├── llm.py       # LLM interaction client
│       └── logging_manager.py
└── logs/                # Log files
```

## 🧠 How It Works

1. **Name Translation**: When users join, their names are translated to Japanese using LLM. A fallback system uses phonetic katakana if the LLM service is unavailable.

2. **Welcome System**: The bot automatically creates a rich embed welcome message and sends it to the configured channel. It assigns the default role and uses LLM to generate a personalized greeting.

3. **Chatbot**: In designated channels, the bot maintains conversation history and responds to user messages using LLM. It formats responses for Discord and handles user context.

## 📝 Logging

The bot uses a comprehensive logging system that outputs to both console and file. Logs are stored in the `logs/` directory with timestamps.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Created with ❤️ by Murali Anand
