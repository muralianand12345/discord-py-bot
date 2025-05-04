# Discord PY Bot

A multi-purpose Discord bot with Arabic name translation, welcome/goodbye messages, and LLM-powered chatbot functionality.

## 🌟 Features

- **Name Translation**: Automatically translates new member names to Arabic (or other languages)
- **Custom Welcome Messages**: Sends personalized LLM-generated welcome messages when members join
- **Custom Goodbye Messages**: Sends personalized LLM-generated farewell messages when members leave
- **Chatbot Integration**: Dedicated channel for members to interact with an LLM-powered chatbot
- **Role Assignment**: Automatically assigns roles to new members

## 📋 Requirements

- Python 3.12 or higher
- Discord Bot Token
- LLM API Keys (Groq, Perplexity, etc.)
- Discord Server (Guild) with appropriate permissions

## 🔧 Installation

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver that offers significant performance improvements over pip.

```bash
# Clone the repository
git clone https://github.com/muralianand12345/discord-py-bot.git
cd discord-py-bot

# Install uv if you don't have it
pip install uv

# Create and activate a virtual environment (optional but recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies from pyproject.toml
uv pip install --requirement pyproject.toml
```

### Alternative Installation Methods

```bash
# Using pip directly
pip install -r requirements.txt  # Generate requirements.txt first with: uv pip freeze > requirements.txt

# Using pipx for isolated installation
pipx install .
```

## ⚙️ Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit the `.env` file with your configuration:

```ini
BOT_TOKEN=your_discord_bot_token
BOT_PREFIX=!
GUILD_ID=your_guild_id

LLM_API_KEY_1=your_welcome_llm_api_key
LLM_API_KEY_2=your_goodbye_llm_api_key
LLM_API_KEY_3=your_translator_llm_api_key
LLM_API_KEY_4=your_chatbot_llm_api_key
```

3. Configure channel IDs in `src/config.py`:
   - Update welcome channel ID, goodbye channel ID, and chatbot channel ID
   - Configure role IDs for automatic role assignment
   - Adjust LLM model settings if needed

## 🚀 Running the Bot

```bash
# Navigate to the src directory
cd src

# Run the bot
python main.py
```

## 🏗️ Project Structure

```bash
discord-py-bot/
├── logs/                  # Log files
├── data/                  # Chatbot history and database
├── src/
│   ├── commands/          # Bot commands
│   │   ├── __init__.py
│   │   └── nickname.py    # Nickname translation commands
│   │
│   ├── events/            # Event handlers
│   │   ├── __init__.py
│   │   ├── welcome_members.py
│   │   ├── goodbye_members.py
│   │   └── chatbot.py
│   │
│   ├── utils/             # Utility modules
│   │   ├── llm.py         # LLM client implementation
│   │   ├── translator.py  # Translation utilities
│   │   ├── command_utils.py
│   │   └── logging_manager.py
│   │
│   ├── bot.py             # Bot configuration
│   ├── config.py          # Configuration settings
│   └── main.py            # Entry point
│
├── .env                   # Environment variables (create from .env.example)
├── .env.example           # Example environment file
├── pyproject.toml         # Python project dependencies
└── README.md              # This file
```

## 🛠️ Customization

### Changing Translation Language

To change the translation language, update the `LANGUAGE` setting in `src/config.py`:

```python
class TRANSLATOR:
    LANGUAGE = "Arabic"  # Change to your desired language
```

### Bot Command Examples

The bot provides various commands for nickname management:

```bash
!nickname user @user1 @user2 language=Spanish  # Translate specific users' names
!nickname role "New Members" language=Japanese  # Translate names for a role
!nickname all language=Arabic                   # Translate all member names
!nickname reset @user1 @user2                   # Reset specific users' nicknames
```

### Modifying Bot Behavior

- Edit welcome and goodbye message templates in their respective event handlers
- Customize bot status messages in `src/bot.py`
- Adjust chatbot settings in the `LLM.CHATBOT` section of `config.py`
- Configure LLM parameters for translation and message generation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Powered by Groq and Perplexity for AI-generated messages and translations
- Uses uv for efficient dependency management
