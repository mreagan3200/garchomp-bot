import nextcord
from nextcord.ext import commands
from util.RolesUtil import *
from util.BanUtil import *
from util.DataUtil import *

import sqlite3
import json

type_roles = ['Normal', 'Fire', 'Water', 'Grass', 'Electric', 'Ice', 'Fighting', 'Poison', 'Ground',
             'Flying', 'Psychic', 'Bug', 'Rock', 'Ghost', 'Dark', 'Dragon', 'Steel', 'Fairy']
react_roles_dict = {'knook':'Chess', 'vicowboy':'League', 'pokeball':'Pokemon'}

class ReactionRoles(commands.Cog):
    def __init__(self, client : nextcord.Client):
        self.client = client
        self.datautil = DataUtil('data/data.json')
        self.data = self.datautil.load()
    
    async def select_role(self, member : nextcord.Member, role : nextcord.Role, message):
        for r in member.roles:
            if r.name in type_roles:
                if r.name == role.name:
                    return
                await add_role(member, role)
                await remove_role(member, r)
                guild = self.client.get_guild(self.data.get('emote_server_id'))
                emoji = nextcord.utils.get(guild.emojis, name=r.name.lower())
                await message.remove_reaction(emoji, member)
                return
        await add_role(member, role)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload : nextcord.RawReactionActionEvent):
        if payload.message_id not in self.data.get('react_message_ids'):
            return
        if payload.member.bot:
            return
        message = await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        guild = self.client.get_guild(payload.guild_id)
        if payload.message_id == self.data.get('react_message_ids')[0]:
            role_name = payload.emoji.name.capitalize()
            if role_name in type_roles:
                role = nextcord.utils.get(guild.roles, name=role_name)
                await self.select_role(payload.member, role, message)
                return
        elif payload.message_id == self.data.get('react_message_ids')[1]:
            role_name = react_roles_dict.get(payload.emoji.name)
            if role_name is not None:
                role = nextcord.utils.get(guild.roles, name=role_name)
                await add_role(payload.member, role)
                return
        elif payload.message_id == self.data.get('react_message_ids')[2]:
            await message.remove_reaction(payload.emoji, payload.member)
            await ban(payload.member)
            await unban(payload.member)
            return
        await message.remove_reaction(payload.emoji, payload.member)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload : nextcord.RawReactionActionEvent):
        if payload.message_id not in self.data.get('react_message_ids'):
            return
        guild = self.client.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member is None or member.bot:
            return
        if payload.message_id == self.data.get('react_message_ids')[0]:
            role_name = payload.emoji.name.capitalize()
            role = nextcord.utils.get(guild.roles, name=role_name)
            await remove_role(member, role)
        elif payload.message_id == self.data.get('react_message_ids')[1]:
            role_name = react_roles_dict.get(payload.emoji.name)
            if role_name is not None:
                role = nextcord.utils.get(guild.roles, name=role_name)
                await remove_role(member, role)

    @nextcord.slash_command(guild_ids=[1093195040320389200], name='resetreactionroles', description='Reset the reaction role messages. Must be an administrator to use')
    async def resetreactionroles(self, interaction : nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You are not authorized to run this command', ephemeral=True)
            return
        roles_channel = interaction.guild.get_channel(1093916970644156419)
        guild = interaction.guild
        emote_guild = self.client.get_guild(self.data.get('emote_server_id'))
        color = guild.get_member(self.client.user.id).color

        messages = []
        async for message in roles_channel.history():
            messages += [message]
        await roles_channel.delete_messages(messages)

        description = 'React with a emote below to change\nyour color to that type\'s color!\n\n'
        b = False
        for role_name in type_roles:
            role = nextcord.utils.get(guild.roles, name=role_name)
            emoji = nextcord.utils.get(emote_guild.emojis, name=role_name.lower())
            description += f'{role.mention}: {emoji}'
            description += '\n' if b else ' '
            b = not b
        embed = nextcord.Embed(title='Choose Your Tera Type!', 
                                description=description,
                                color=color)
        type_message = await roles_channel.send(embed=embed)

        description = ''
        for key, value in react_roles_dict.items():
            role = nextcord.utils.get(guild.roles, name=value)
            emoji = nextcord.utils.get(emote_guild.emojis, name=key)
            description += f'React with {emoji} to get the {role.mention} role\n'

        embed = nextcord.Embed(title='Add Additional Channels!',
                                description=description,
                                color=color)
        channel_message = await roles_channel.send(embed=embed)

        embed = nextcord.Embed(title='React to this message to get banned',
                                description='Yes you really get banned',
                                color=color)
        ban_message = await roles_channel.send(embed=embed)

        for role in type_roles:
            emoji = nextcord.utils.get(emote_guild.emojis, name=role.lower())
            await type_message.add_reaction(emoji)
        for key, value in react_roles_dict.items():
            emoji = nextcord.utils.get(emote_guild.emojis, name=key)
            await channel_message.add_reaction(emoji)
        for emote_name in ['blunder', 'brilliant']:
            emoji = nextcord.utils.get(emote_guild.emojis, name=emote_name)
            await ban_message.add_reaction(emoji)
        
        self.data = self.datautil.updateData({'react_message_ids':[type_message.id, channel_message.id, ban_message.id]})

        await interaction.followup.send('done', ephemeral=True)

def setup(client : nextcord.Client):
    client.add_cog(ReactionRoles(client))