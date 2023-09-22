import nextcord
from nextcord.ext import commands
import shared

async def add_role(member : nextcord.Member, role : nextcord.Role):
    if role not in member.roles:
        await member.add_roles(role)

async def remove_role(member : nextcord.Member, role : nextcord.Role):
    if role in member.roles:
        await member.remove_roles(role)

async def administrator_command_executed(interaction : nextcord.Interaction):
    command_name = interaction.data.get('name')
    command = f'/{command_name}'
    for o in interaction.data.get('options'):
        if o.get('type') == 6:
            command += ' ' + str(o.get('name')) + ': ' + str(shared.client.get_user(int(o.get('value'))).mention)
        else:
            command += ' ' + str(o.get('name')) + ': ' + str(o.get('value'))
    channel = shared.client.get_channel(1093921362961252372)
    embed = nextcord.Embed(title='command executed', description=command, color=interaction.user.color)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    await channel.send(embed=embed)