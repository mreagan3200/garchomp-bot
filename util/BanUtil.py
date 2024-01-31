import nextcord

async def kick(member : nextcord.Member, reason=None):
    await member.kick(reason=reason)

async def ban(member : nextcord.Member, reason=None):
    await member.ban(reason=reason)

async def unban(member : nextcord.Member, reason=None):
    await member.unban(reason=reason)