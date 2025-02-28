import discord
from discord import Embed

def error_embed(text: str):
    return Embed(color = discord.Colour.red(), description=text)

def warning_embed(text: str):
    return Embed(color = discord.Colour.orange(), description=text)

def success_embed(text: str):
    return Embed(color = discord.Colour.green(), description=text)