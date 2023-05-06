import nextcord
from nextcord.ext import commands

async def add_role(member : nextcord.Member, role : nextcord.Role):
    if role not in member.roles:
        await member.add_roles(role)

async def remove_role(member : nextcord.Member, role : nextcord.Role):
    if role in member.roles:
        await member.remove_roles(role)