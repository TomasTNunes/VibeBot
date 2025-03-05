import discord
from discord import Embed

def error_embed(text: str):
    """Returns a red embed with received message."""
    return Embed(color = discord.Colour.red(), description=text)

def warning_embed(text: str):
    """Returns an orange embed with received message."""
    return Embed(color = discord.Colour.orange(), description=text)

def success_embed(text: str):
    """Returns a green embed with received message."""
    return Embed(color = discord.Colour.green(), description=text)

def info_embed(text: str):
    """Returns a purple embed with received message."""
    return Embed(color = discord.Colour.from_rgb(137, 76, 193), description=text)