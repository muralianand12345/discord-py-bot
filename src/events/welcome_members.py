import discord
import logging
from discord.ext import commands
from bot import bot, logger
from config import BOT


@bot.event
async def on_member_join(member):
    