import asyncio
import re
from datetime import datetime, timedelta
import random

import discord
from discord.ext import commands
import pandas as pd
from transformers import pipeline
import better_profanity as bp

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

classifier = pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english')

def is_profanity(text):
    return bp.profanity.contains_profanity(text)

async def delete_and_warn(message, warning):
    try:
        await message.delete()
    except discord.errors.HTTPException as e:
        if e.code == 429:
            retry_after = e.retry_after
            for i in range(5):
                await asyncio.sleep(retry_after * (2 ** i))
                try:
                    await message.delete()
                    break
                except:
                    continue
        else:
            raise e

    warning_message = await message.channel.send(f"{message.author.mention}, {warning}")
    await asyncio.sleep(10)
    await warning_message.delete()

async def delete_duplicates(message):
    async for msg in message.channel.history(limit=10):
        if (
            msg.author == message.author
            and msg.content == message.content
            and (message.created_at - msg.created_at) < timedelta(seconds=2)
            and msg.id != message.id
        ):
            await delete_and_warn(
                message,
                "please refrain from sending duplicate messages in a short period of time."
            )
            break

    timestamps = []
    async for msg in message.channel.history(limit=10):
        if msg.author == message.author and msg.id != message.id:
            timestamps.append(msg.created_at)

    if timestamps:
        time_difference = message.created_at - max(timestamps)
        if time_difference < timedelta(seconds=2):
            await delete_and_warn(
                message,
                "please refrain from sending messages too quickly."
            )

    words = re.findall(r'\b\w+\b', message.content)
    if len(set(words)) < len(words):
        await delete_and_warn(message, "please refrain from using duplicate phrases.")
        return

    for word in words:
        if len(word) > 1 and sum(c.isupper() for c in word) / len(word) > 0.5:
            await delete_and_warn(
                message,
                "please refrain from using messages with too many capital letters."
            )
            break

# List of messages for the bot profile
bot_profile_messages = [
    "I'm here to help you with all your needs!",
    "I'm a friendly bot who loves to chat.",
    "Need some assistance? Just ask me!",
    "I'm always ready to lend a helping hand.",
    "I'm a bot, but I'm also a good listener!",
]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    # Start an infinite loop to change the bot's activity every 10 seconds
    while True:
        message = random.choice(bot_profile_messages)
        await bot.change_presence(activity=discord.Game(name=message))
        await asyncio.sleep(10)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if is_profanity(message.content):
        await delete_and_warn(message, "please refrain from using inappropriate language.")
        return

    async with message.channel.typing():
        words = re.findall(r'\b\w+\b', message.content)
        if len(set(words)) > 30:
            await delete_and_warn(message, "please refrain from using spammy sentences.")
            return

        if message.content.islower():
            result = classifier(message.content)
            sentiment = result[0]['label']
            score = result[0]['score']
            if sentiment == 'NEGATIVE' and score < 0.1:
                await delete_and_warn(message, "please refrain from using random sentences.")
                return

        await delete_duplicates(message)
        await bot.process_commands(message)

bot.run('your-token-here')
