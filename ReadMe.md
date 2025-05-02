# Discord PY Bot

A multi-purpose Discord bot that translates member names to Arabic, provides welcome/goodbye messages, and includes a chatbot feature - all powered by LLM API integration.

## Features

- **Name Translation**: Automatically translates new member names to Arabic using LLM
- **Custom Welcome Messages**: Sends personalized welcome messages when members join
- **Custom Goodbye Messages**: Sends personalized farewell messages when members leave
- **Chatbot Integration**: Dedicated channel for members to interact with LLM-powered chatbot
- **Role Assignment**: Automatically assigns roles to new members

## Requirements

- Python 3.12 or higher
- Discord Bot Token
- LLM API Keys (Groq, Perplexity, or others)
- Discord Server (Guild) with appropriate permissions

## Installation

### Using uv

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver.

1. Clone the repository

```bash
git clone git@github.com:muralianand12345/discord-py-bot.git
cd discord-name-changer
```

2. Install dependencies with uv

```bash
# Install uv if you don't have it
pip install uv

# Install dependencies from pyproject.toml
uv pip install --system
```

## Configuration

1. Copy the example environment file

```bash
cp .env.example .env
```

2. Edit the `.env` file with your configuration:

```
BOT_TOKEN=your_discord_bot_token
BOT_PREFIX=!
GUILD_ID=your_guild_id

LLM_API_KEY_1=your_welcome_llm_api_key
LLM_API_KEY_2=your_goodbye_llm_api_key
LLM_API_KEY_3=your_translator_llm_api_key
LLM_API_KEY_4=your_chatbot_llm_api_key
```

3. Configure channel IDs in `src/config.py`:
   - Update welcome channel ID, goodbye channel ID, and chatbot channel ID to match your server
   - Configure roles IDs for automatic role assignment
   - Adjust LLM model settings if needed

## Running the Bot

```bash
# Navigate to the src directory
cd src

# Run the bot
python main.py
```

## Project Structure

```md
discord-name-changer/
├── logs/                  # Log files
├── data/                  # Chatbot history and database
├── src/
│   ├── events/            # Event handlers
│   │   ├── __init__.py
│   │   ├── welcome_members.py
│   │   ├── goodbye_members.py
│   │   └── chatbot.py
│   ├── utils/             # Utility modules
│   │   ├── llm.py
│   │   └── logging_manager.py
│   ├── bot.py             # Bot configuration
│   ├── config.py          # Configuration settings
│   └── main.py            # Entry point
├── .env                   # Environment variables (create from .env.example)
├── .env.example           # Example environment file
├── pyproject.toml         # Python project dependencies
└── README.md              # This file
```

## Customization

### Changing Translation Language

To change the translation language, update the `LANGUAGE` setting in `src/config.py`:

```python
class TRANSLATOR:
    LANGUAGE = "Arabic"  # Change to your desired language
```

### Modifying Bot Behavior

- Edit welcome and goodbye message templates in their respective event handlers
- Customize bot status messages in `src/bot.py`
- Adjust chatbot settings in the `LLM.CHATBOT` section of `config.py`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Powered by Groq LLM API for AI-generated messages and translations
