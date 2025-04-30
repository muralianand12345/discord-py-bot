"""
Fun commands for the Discord bot.
"""

import random
import aiohttp
import discord
import logging
from typing import Optional
from discord.ext import commands

from utils.settings import COOLDOWNS


class FunCog(commands.Cog, name="Fun"):
    """Fun commands for entertainment."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("fun_cog")
        self._8ball_responses = [
            # Positive responses
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes, definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            # Neutral responses
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            # Negative responses
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful.",
        ]

    @commands.command(name="8ball")
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def eightball(self, ctx: commands.Context, *, question: str):
        """
        Ask the magic 8-ball a question.

        Args:
            question: The question to ask

        Example:
            !8ball Will I win the lottery?
        """
        if not question.endswith("?"):
            question += "?"

        response = random.choice(self._8ball_responses)

        embed = discord.Embed(title="🎱 Magic 8-Ball", color=discord.Color.blue())

        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=response, inline=False)
        embed.set_footer(text=f"Asked by {ctx.author}")

        await ctx.send(embed=embed)

    @commands.command(name="coinflip", aliases=["flip", "coin"])
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def coinflip(self, ctx: commands.Context):
        """Flip a coin and get heads or tails."""
        result = random.choice(["Heads", "Tails"])

        # Create an embed with the result
        embed = discord.Embed(
            title="Coin Flip",
            description=f"The coin landed on: **{result}**",
            color=discord.Color.gold(),
        )

        # Add an appropriate emoji
        if result == "Heads":
            embed.set_thumbnail(
                url="https://cdn-icons-png.flaticon.com/512/272/272525.png"
            )
        else:
            embed.set_thumbnail(
                url="https://cdn-icons-png.flaticon.com/512/272/272527.png"
            )

        embed.set_footer(text=f"Flipped by {ctx.author}")

        await ctx.send(embed=embed)

    @commands.command(name="choose", aliases=["pick"])
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def choose(self, ctx: commands.Context, *options: str):
        """
        Choose randomly from multiple options.

        Args:
            options: Options to choose from (separated by spaces)

        Example:
            !choose pizza pasta salad
            !choose "go to the park" "stay home" "visit a friend"
        """
        if len(options) < 2:
            await ctx.send("Please provide at least two options to choose from.")
            return

        choice = random.choice(options)

        await ctx.send(f"I choose: **{choice}**")

    @commands.command(name="reverse")
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def reverse(self, ctx: commands.Context, *, text: str):
        """
        Reverse the provided text.

        Args:
            text: The text to reverse

        Example:
            !reverse Hello world!
        """
        reversed_text = text[::-1]
        await ctx.send(f"{reversed_text}")

    @commands.command(name="rps", aliases=["rockpaperscissors"])
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def rps(self, ctx: commands.Context, choice: str = None):
        """
        Play Rock, Paper, Scissors with the bot.

        Args:
            choice: 'rock', 'paper', or 'scissors'

        Example:
            !rps rock
        """
        choices = ["rock", "paper", "scissors"]

        if not choice or choice.lower() not in choices:
            await ctx.send("Please choose `rock`, `paper`, or `scissors`.")
            return

        user_choice = choice.lower()
        bot_choice = random.choice(choices)

        # Determine the winner
        if user_choice == bot_choice:
            result = "It's a tie!"
            color = discord.Color.gold()
        elif (
            (user_choice == "rock" and bot_choice == "scissors")
            or (user_choice == "paper" and bot_choice == "rock")
            or (user_choice == "scissors" and bot_choice == "paper")
        ):
            result = "You win!"
            color = discord.Color.green()
        else:
            result = "I win!"
            color = discord.Color.red()

        # Create an embed with the result
        embed = discord.Embed(
            title="Rock, Paper, Scissors", description=result, color=color
        )

        # Add choice emojis
        choice_emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

        embed.add_field(
            name="Your choice",
            value=f"{choice_emojis[user_choice]} {user_choice.title()}",
            inline=True,
        )
        embed.add_field(
            name="My choice",
            value=f"{choice_emojis[bot_choice]} {bot_choice.title()}",
            inline=True,
        )

        embed.set_footer(text=f"Played by {ctx.author}")

        await ctx.send(embed=embed)

    @commands.command(name="emojify")
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def emojify(self, ctx: commands.Context, *, text: str):
        """
        Convert text to regional indicator emojis.

        Args:
            text: Text to convert to emojis

        Example:
            !emojify hello
        """
        # Define mapping for letters to regional indicator emojis
        regional_indicators = {
            "a": "🇦",
            "b": "🇧",
            "c": "🇨",
            "d": "🇩",
            "e": "🇪",
            "f": "🇫",
            "g": "🇬",
            "h": "🇭",
            "i": "🇮",
            "j": "🇯",
            "k": "🇰",
            "l": "🇱",
            "m": "🇲",
            "n": "🇳",
            "o": "🇴",
            "p": "🇵",
            "q": "🇶",
            "r": "🇷",
            "s": "🇸",
            "t": "🇹",
            "u": "🇺",
            "v": "🇻",
            "w": "🇼",
            "x": "🇽",
            "y": "🇾",
            "z": "🇿",
            "0": "0️⃣",
            "1": "1️⃣",
            "2": "2️⃣",
            "3": "3️⃣",
            "4": "4️⃣",
            "5": "5️⃣",
            "6": "6️⃣",
            "7": "7️⃣",
            "8": "8️⃣",
            "9": "9️⃣",
            " ": "  ",
            "!": "❗",
            "?": "❓",
        }

        # Convert the text to emojis
        emojified_text = ""
        for char in text.lower():
            if char in regional_indicators:
                emojified_text += f"{regional_indicators[char]} "
            else:
                emojified_text += char + " "

        # Split message if it's too long
        if len(emojified_text) > 2000:
            await ctx.send("The resulting message is too long to display.")
            return

        await ctx.send(emojified_text)

    @commands.command(name="joke")
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.channel)
    async def joke(self, ctx: commands.Context):
        """Get a random joke."""
        joke_api_url = "https://official-joke-api.appspot.com/random_joke"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(joke_api_url) as response:
                    if response.status == 200:
                        joke_data = await response.json()

                        embed = discord.Embed(
                            title="Random Joke", color=discord.Color.random()
                        )

                        embed.add_field(
                            name="Setup", value=joke_data.get("setup"), inline=False
                        )
                        embed.add_field(
                            name="Punchline",
                            value=joke_data.get("punchline"),
                            inline=False,
                        )

                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("Failed to fetch a joke. Try again later.")
            except Exception as e:
                await ctx.send("Failed to fetch a joke. Try again later.")
                self.logger.error(f"Error fetching joke: {str(e)}")

    @commands.command(name="fact")
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.channel)
    async def fact(self, ctx: commands.Context):
        """Get a random fact."""
        fact_api_url = "https://uselessfacts.jsph.pl/random.json?language=en"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(fact_api_url) as response:
                    if response.status == 200:
                        fact_data = await response.json()

                        embed = discord.Embed(
                            title="Random Fact",
                            description=fact_data.get("text"),
                            color=discord.Color.blue(),
                        )

                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("Failed to fetch a fact. Try again later.")
            except Exception as e:
                await ctx.send("Failed to fetch a fact. Try again later.")
                self.logger.error(f"Error fetching fact: {str(e)}")

    @commands.command(name="numberfact")
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def numberfact(self, ctx: commands.Context, number: Optional[int] = None):
        """
        Get a random fact about a number.

        Args:
            number: The number to get a fact about (optional)

        Example:
            !numberfact 42
        """
        # If no number is provided, get a random number fact
        if number is None:
            api_url = "http://numbersapi.com/random/trivia"
        else:
            api_url = f"http://numbersapi.com/{number}/trivia"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        fact = await response.text()

                        embed = discord.Embed(
                            title=f"Number Fact {'(Random)' if number is None else f'for {number}'}",
                            description=fact,
                            color=discord.Color.blue(),
                        )

                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(
                            "Failed to fetch a number fact. Try again later."
                        )
            except Exception as e:
                await ctx.send("Failed to fetch a number fact. Try again later.")
                self.logger.error(f"Error fetching number fact: {str(e)}")

    @commands.command(name="say")
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def say(self, ctx: commands.Context, *, message: str):
        """
        Make the bot say something.

        Args:
            message: What the bot should say

        Example:
            !say Hello everyone!
        """
        # Check for potential abuse
        if "@everyone" in message or "@here" in message:
            await ctx.send("I won't ping everyone/here, sorry!")
            return

        # Delete the command message if possible
        try:
            await ctx.message.delete()
        except:
            pass

        await ctx.send(message)


async def setup(bot: commands.Bot):
    """Add this cog to the bot."""
    await bot.add_cog(FunCog(bot))
