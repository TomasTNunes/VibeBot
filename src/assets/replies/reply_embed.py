import discord
from discord import Embed

def error_embed(text: str):
    """Returns an red embed with received message."""
    return Embed(color = discord.Colour.red(), description=text)

def warning_embed(text: str):
    """Returns an orange embed with received message."""
    return Embed(color = discord.Colour.orange(), description=text)

def success_embed(text: str):
    """Returns an green embed with received message."""
    return Embed(color = discord.Colour.green(), description=text)