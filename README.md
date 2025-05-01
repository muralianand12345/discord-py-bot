# Discord Multi-Purpose Bot

A friendly Discord bot with multiple features including conversational AI, nickname translation, moderation tools, utility commands, and fun activities - perfect for building an engaging community server.

![Bot Banner](https://img.shields.io/badge/Discord-Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12+-blue?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

## ✨ Features

- **🤖 Conversational AI**
  - Friendly, engaging chatbot powered by Groq LLM
  - Customizable personality (friendly, funny, professional, helpful)
  - Context-aware with conversation memory
  - Natural interactions in designated channels

- **🔤 Nickname Management**
  - Automatic translation of usernames to Japanese when users join
  - Manual translation of usernames to different languages
  - Batch translation of all server members
  - Random Japanese name generator

- **🛡️ Moderation Tools**
  - Message purging and cleaning
  - User management (kick, ban, timeout)
  - Channel management (lock, unlock, slowmode)
  - Customizable word, invite, and caps filters

- **🛠️ Utility Commands**
  - Server and user information
  - Ping and uptime tracking
  - Avatar display
  - Poll creation
  - Reminder system

- **🎮 Fun Commands**
  - Magic 8-ball
  - Dice rolling
  - Rock, paper, scissors game
  - Random facts and jokes
  - Text manipulation (reverse, emojify)

- **👋 Welcome System**
  - Personalized welcome and goodbye messages
  - Automatic role assignment for new members
  - AI-generated greetings using LLM

## 📋 Requirements

- Python 3.12+
- Discord Bot Token
- Groq API Key (for LLM features)

## 🚀 Installation

1. Clone this repository:

   ```bash
   git clone git@github.com:muralianand12345/discord-bot.git
   cd discord-bot
   ```

2. Set up a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -e .
   ```

4. Create a `.env` file based on the provided `.env.example`:

   ```bash
   cp .env.example .env
   ```

5. Edit the `.env` file with your Discord Bot Token and Groq API Key.

## ⚙️ Configuration

The bot can be configured through environment variables in the `.env` file:

### Bot Configuration

- `BOT_TOKEN`: Your Discord Bot Token
- `BOT_PREFIX`: Command prefix (default: `!`)
- `BOT_DESCRIPTION`: Brief description of your bot
- `BOT_VERSION`: Current version of the bot
- `GUILD_ID`: ID of your Discord server (for single-guild mode)
- `EXTENSIONS_ENABLED`: Comma-separated list of cog modules to load

### Chatbot Settings

- `CHATBOT_ENABLED`: Enable/disable the chatbot feature
- `CHATBOT_CHANNELS`: Comma-separated list of channel IDs where the chatbot should respond
- `CHATBOT_NAME`: Name for your chatbot
- `CHATBOT_PERSONALITY`: Description of bot personality (e.g., "friendly, helpful and witty")
- `CHATBOT_MAX_HISTORY`: Number of messages to remember in conversations
- `CHATBOT_MAX_TOKENS`: Maximum length of generated responses

### LLM Settings

- `GROQ_API_KEY`: Your Groq API Key
- `GROQ_MODEL`: LLM model to use (e.g., "llama-3.3-70b-versatile")
- `LLM_REQUEST_TIMEOUT`: Timeout for LLM API requests
- `MAX_REQUESTS_PER_MINUTE`: API rate limiting

### Feature Flags

- `FEATURE_AUTO_TRANSLATION`: Enable/disable automatic name translation
- `FEATURE_MODERATION`: Enable/disable moderation features
- `FEATURE_FUN_COMMANDS`: Enable/disable fun commands

### Welcome/Goodbye Settings

- `WELCOME_CHANNEL_ID`: Channel ID for welcome messages
- `GOODBYE_CHANNEL_ID`: Channel ID for goodbye messages
- `DEFAULT_ROLE_ID`: Role ID to automatically assign to new members

## 📁 Project Structure

```md
discord-bot/
├── .env                  # Environment variables (create from .env.example)
├── LICENSE               # MIT License
├── pyproject.toml        # Project dependencies
├── README.md             # Project documentation
├── src/                  # Source code
│   ├── bot.py            # Enhanced bot setup with friendly personality
│   ├── main.py           # Application entry point
│   ├── cogs/             # Command modules
│   │   ├── admin.py      # Admin commands
│   │   ├── chatbot.py    # Enhanced conversational AI
│   │   ├── fun.py        # Fun commands
│   │   ├── help.py       # Custom help command
│   │   ├── moderation.py # Moderation commands
│   │   ├── nickname.py   # Nickname commands
│   │   ├── utility.py    # Utility commands
│   │   └── welcome.py    # Welcome/goodbye system
│   └── utils/            # Utility modules
│       ├── db_manager.py # Database management
│       ├── llm.py        # Enhanced LLM interaction
│       ├── logging_manager.py # Logging setup
│       ├── settings.py   # Configuration with personality settings
│       └── translate.py  # Translation utilities
└── logs/                 # Log files
```

## 📚 Usage

### Starting the Bot

```bash
python src/main.py
```

### Basic Commands

Here are some example commands:

- `!help` - Display available commands
- `!chatbot enable` - Enable the chatbot in the current channel
- `!chatbot personality friendly` - Set the chatbot's personality to friendly
- `!translate_name @user` - Translate a user's name to Japanese
- `!reset_name @user` - Reset a user's nickname to their original username
- `!userinfo @user` - Display information about a user
- `!serverinfo` - Display information about the server
- `!ping` - Check the bot's latency
- `!8ball question` - Ask the magic 8-ball a question
- `!roll 2d6` - Roll dice using DnD notation
- `!purge 10` - Delete the last 10 messages in a channel
- `!remind 1h Check the oven` - Set a reminder for 1 hour from now

### Chatbot Commands

The chatbot feature allows natural conversation in designated channels:

- `!chatbot enable` - Enable the chatbot
- `!chatbot disable` - Disable the chatbot
- `!chatbot status` - Show chatbot status
- `!chatbot clear` - Clear conversation history in the current channel
- `!chatbot addchannel` - Add the current channel to chatbot channels
- `!chatbot removechannel` - Remove the current channel from chatbot channels
- `!chatbot personality [friendly|funny|helpful|professional]` - Change the chatbot's personality

### Nickname Translation

- `!translate_name @user` - Translate a user's name to Japanese
- `!translate_name @user fr` - Translate a user's name to French
- `!reset_name @user` - Reset a user's name to their original username
- `!random_name @user` - Give a user a random Japanese name
- `!translate_all` - Translate all member names in the server to Japanese

### Moderation Commands

- `!purge 10` - Delete the last 10 messages in a channel
- `!kick @user reason` - Kick a user from the server
- `!ban @user reason` - Ban a user from the server
- `!mute @user 1h reason` - Timeout (mute) a user for 1 hour
- `!unmute @user` - Remove timeout from a user
- `!lock` - Lock the current channel to prevent messages
- `!unlock` - Unlock a previously locked channel
- `!slowmode 5` - Set slowmode delay in the current channel

## 🔧 Bot Permissions

The bot requires the following permissions:

- **General Permissions**
  - View Channels
  - Send Messages
  - Manage Messages
  - Embed Links
  - Attach Files
  - Read Message History
  - Use External Emojis
  - Add Reactions

- **Member Permissions**
  - Kick Members
  - Ban Members
  - Manage Nicknames
  - Moderate Members (Timeout)

- **Channel Permissions**
  - Manage Channels

## 🔍 Troubleshooting

### Common Issues

- **Bot not responding**: Ensure your bot token is correct and the bot has appropriate permissions.
- **LLM features not working**: Check your Groq API key and connection settings.
- **Permission errors**: Ensure the bot has the necessary permissions in your Discord server.

### Logs

Check the `logs/` directory for detailed logs which can help diagnose issues.

## 🔄 Extending the Bot

### Adding New Commands

To add new commands, create a new cog in the `src/cogs` directory:

```python
from discord.ext import commands

class MyCog(commands.Cog, name="My Category"):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="mycommand")
    async def my_command(self, ctx, arg1, arg2):
        """This is a description of my command."""
        await ctx.send(f"You provided: {arg1} and {arg2}")

async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

Then add your cog name to the `EXTENSIONS_ENABLED` setting in your `.env` file.

## 📊 Performance Considerations

- The LLM features require API calls which may have rate limits and latency.
- For larger servers, consider using more conservative settings for `CHATBOT_MAX_HISTORY` and `TRANSLATION_CACHE_SIZE`.
- The bot is optimized for single-guild operation by setting the `GUILD_ID` parameter.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Created by Murali Anand - [GitHub](https://github.com/muralianand12345)
