# Discord Multi-Purpose Bot

A modular Discord bot with multiple features including name translation, moderation tools, utility commands, and more.

## Features

- **Nickname Management**
  - Automatic translation of usernames to Japanese when users join
  - Manual translation of usernames to different languages
  - Batch translation of all server members
  - Random Japanese name generator

- **Moderation Tools**
  - Message purging and cleaning
  - User management (kick, ban, timeout)
  - Channel management (lock, unlock, slowmode)
  - Customizable word, invite, and caps filters

- **Utility Commands**
  - Server and user information
  - Ping and uptime tracking
  - Avatar display
  - Poll creation
  - Reminder system

- **Fun Commands**
  - Magic 8-ball
  - Dice rolling
  - Rock, paper, scissors game
  - Random facts and jokes
  - Text manipulation (reverse, emojify)

- **Admin Commands**
  - Server management
  - User moderation
  - Server information

## Requirements

- Python 3.12+
- Discord Bot Token
- Groq API Key (optional, for translation features)

## Installation

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

## Configuration

The bot can be configured through environment variables in the `.env` file. Here are the key configuration options:

### Bot Configuration

- `BOT_TOKEN`: Your Discord Bot Token
- `BOT_PREFIX`: Command prefix for the bot (default: `!`)
- `BOT_DESCRIPTION`: Brief description of your bot
- `EXTENSIONS_ENABLED`: Comma-separated list of cog modules to load

### Feature Configuration

- `FEATURE_AUTO_TRANSLATION`: Enable/disable automatic name translation
- `FEATURE_MODERATION`: Enable/disable moderation features
- `FEATURE_FUN_COMMANDS`: Enable/disable fun commands

### Translation Settings

- `GROQ_API_KEY`: Your Groq API Key
- `GROQ_MODEL`: Groq LLM model to use
- `TRANSLATION_CACHE_SIZE`: Number of translations to cache
- `MAX_REQUESTS_PER_MINUTE`: Maximum API requests per minute
- `USE_ROMANIZATION_FALLBACK`: Whether to use romanization fallback

### Cooldown Settings

- `COOLDOWN_DEFAULT`: Default command cooldown in seconds
- `COOLDOWN_TRANSLATION`: Cooldown for translation commands
- `COOLDOWN_BATCH_OPERATIONS`: Cooldown for batch operations

### Database and Logging

- `DB_TYPE`: Database type (`sqlite` or `json`)
- `DB_PATH`: Path to the database file
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `LOG_TO_FILE`: Whether to log to a file
- `LOG_FILE_PATH`: Path to the log file

## Project Structure

```md
discord-bot/
├── .env                  # Environment variables (you must create this)
├── .env.example          # Example environment variables
├── LICENSE               # MIT License
├── pyproject.toml        # Project dependencies
├── README.md             # Project documentation
├── src/                  # Source code
│   ├── bot.py            # Main bot setup
│   ├── main.py           # Entry point
│   ├── cogs/             # Command modules
│   │   ├── admin.py      # Admin commands
│   │   ├── fun.py        # Fun commands
│   │   ├── help.py       # Custom help command
│   │   ├── moderation.py # Moderation commands
│   │   ├── nickname.py   # Nickname commands
│   │   └── utility.py    # Utility commands
│   └── utils/            # Utility modules
│       ├── db_manager.py # Database management
│       ├── logging_manager.py # Logging setup
│       ├── settings.py   # Configuration
│       └── translate.py  # Translation utilities
└── logs/                 # Log files
```

## Usage

### Starting the Bot

```bash
python src/main.py
```

### Basic Commands

Here are some example commands:

- `!help` - Display available commands
- `!translate_name @user` - Translate a user's name to Japanese
- `!reset_name @user` - Reset a user's nickname to their original username
- `!userinfo @user` - Display information about a user
- `!serverinfo` - Display information about the server
- `!ping` - Check the bot's latency
- `!8ball question` - Ask the magic 8-ball a question
- `!roll 2d6` - Roll dice using DnD notation
- `!purge 10` - Delete the last 10 messages in a channel

## Bot Permissions

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

## Extending the Bot

### Adding New Commands

To add new commands, create a new cog in the `src/cogs` directory or extend existing ones. Here's a template:

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
