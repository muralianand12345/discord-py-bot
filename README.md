# Discord Name Changer Bot

A Discord bot that automatically translates usernames to Japanese using the Groq LLM API. The bot can translate names when users join the server or on-demand through commands.

## Features

- **Automatic Translation**: Automatically translates usernames to Japanese when users join the server
- **On-Demand Translation**: Command to translate a user's name on demand
- **Batch Translation**: Command to translate all users' names in the server
- **Rate Limiting**: Built-in rate limiting to prevent API overload
- **Caching**: LRU cache for translations to reduce API calls
- **Fallback Mechanism**: Falls back to romanization if translation fails or API is not available
- **Comprehensive Logging**: Detailed logging for monitoring and debugging

## Requirements

- Python 3.12+
- Discord Bot Token
- Groq API Key (optional, will fallback to romanization if not provided)

## Installation

1. Clone this repository:
   ```bash
   git clone git@github.com:muralianand12345/discord-name-changer.git
   cd discord-name-changer
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

The bot can be configured through environment variables in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| BOT_TOKEN | Your Discord Bot Token | (required) |
| BOT_PREFIX | Command prefix for the bot | ! |
| GROQ_API_KEY | Your Groq API Key | (optional) |
| GROQ_MODEL | Groq LLM model to use | llama3-70b-8192 |
| TRANSLATION_CACHE_SIZE | Number of translations to cache | 100 |
| TRANSLATION_COOLDOWN_SECONDS | Cooldown between translation requests | 1.0 |
| MAX_TRANSLATION_LENGTH | Maximum length of text to translate | 100 |
| MAX_REQUESTS_PER_MINUTE | Maximum API requests per minute | 50 |
| USE_ROMANIZATION_FALLBACK | Whether to use romanization fallback | true |
| LOG_LEVEL | Logging level (INFO, DEBUG, etc.) | INFO |
| LOG_TO_FILE | Whether to log to a file | true |
| LOG_FILE_PATH | Path to the log file | logs/bot.log |

## Usage

### Starting the Bot

```bash
python src/main.py
```

### Bot Commands

- `!translate_name [member] [language]`: Translate a member's name (defaults to the command author if no member is specified, and Japanese if no language is specified)
- `!translate_all [batch_size] [delay]`: Translate all members' names in the server (requires administrator permissions)
- `!reset_name [member]`: Reset a member's nickname to their original username (defaults to the command author if no member is specified)

## Bot Permissions

The bot requires the following permissions:
- Manage Nicknames (to change users' nicknames)
- Read Messages (to read commands)
- Send Messages (to respond to commands)

## Error Handling

The bot includes comprehensive error handling for:
- API rate limits
- Network issues
- Permission errors
- Invalid inputs

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.