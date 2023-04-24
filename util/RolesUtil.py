import nextcord
from nextcord.ext import commands

@commands.command(pass_context = True)
@commands.has_permissions(manage_roles = True)
async def addRole(user : nextcord.Member, role : nextcord.Role):
    if role in user.roles:
        pass
    else:
        await user.add_roles(role)
@commands.command(pass_context = True)
@commands.has_permissions(manage_roles = True)
async def removeRole(user : nextcord.Member, role : nextcord.Role):
    if role in user.roles:
        await user.remove_roles(role)
    else:
        pass