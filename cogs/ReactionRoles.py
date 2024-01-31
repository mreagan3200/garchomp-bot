import nextcord
from nextcord.ext import commands
from util.RolesUtil import *
from util.BanUtil import *
from util.DataUtil import *

import random

type_roles = ['Normal', 'Fire', 'Water', 'Grass', 'Electric', 'Ice', 'Fighting', 'Poison', 'Ground',
             'Flying', 'Psychic', 'Bug', 'Rock', 'Ghost', 'Dark', 'Dragon', 'Steel', 'Fairy', 'Stellar']
role_colors = [11052922, 15630640, 6525168, 8046412, 16240684, 9886166, 12725800, 10698401, 14860133, 
               11112435, 16340359, 10926362, 11968822, 7559063, 7362374, 7288316, 12040142, 14058925]
react_roles_dict = {'knook':'Chess', 'vicowboy':'League', 'pokeball':'Pokemon'}
emote_server_id = 1097591742766776463

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
                guild = self.client.get_guild(emote_server_id)
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
            await kick(payload.member)
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

    async def resetreactionroles(self):
        roles_channel = self.client.get_channel(1093916970644156419)
        guild = self.client.get_guild(1093195040320389200)
        emote_guild = self.client.get_guild(1097591742766776463)
        color = guild.get_member(self.client.user.id).color

        async for message in roles_channel.history():
            await message.delete()

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

    async def change_stellar_tera(self):
        guild = self.client.get_guild(1093195040320389200)
        role = guild.get_role(1190034205535645796)
        colors = role_colors.copy()
        colors.remove(role.color.value)
        await change_role_color(role, random.choice(colors))

def setup(client : nextcord.Client):
    client.add_cog(ReactionRoles(client))