import nextcord
from nextcord.ext import commands

from util.RolesUtil import *

import json

react_roles_dict = {'normal':'Normal', 'fire':'Fire', 'water':'Water', 'grass':'Grass', 
                    'electric':'Electric', 'ice':'Ice', 'fighting':'Fighting', 'poison':'Poison',
                    'ground':'Ground', 'flying':'Flying', 'psychic':'Psychic', 'bug':'Bug',
                    'rock':'Rock', 'ghost':'Ghost', 'dark':'Dark', 'dragon':'Dragon', 
                    'steel':'Steel', 'fairy':'Fairy', 'pokeball':'Pokemon', 'knook':'Chess',
                    'vicowboy':'League'}
type_roles = ['Normal', 'Fire', 'Water', 'Grass', 'Electric', 'Ice', 'Fighting', 'Poison', 'Ground',
               'Flying', 'Psychic', 'Bug', 'Rock', 'Ghost', 'Dark', 'Dragon', 'Steel', 'Fairy']
channel_react_emotes = ['knook', 'vicowboy', 'pokeball']

class ReactionRoles(commands.Cog):
    def __init__(self, client : commands.Bot):
        self.client = client
        with open('data/data.json', 'r') as data_file:
            self.data = json.load(data_file)

    @commands.command(pass_context = True)
    @commands.has_permissions(manage_roles = True)
    async def selectNewRole(self, user : nextcord.Member, emojiName, message : nextcord.Message, guild : nextcord.Guild):
        for role in user.roles:
            if role.name in type_roles and role.name != react_roles_dict.get(emojiName):
                emoji = nextcord.utils.get(guild.emojis, name=role.name.lower())
                await removeRole(user, role)
                await message.remove_reaction(emoji, user)
                return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload : nextcord.RawReactionActionEvent):
        if payload.member.bot:
            return
        if payload.message_id not in self.data['react_message_ids']:
            return
        guild = self.client.get_guild(payload.guild_id)
        emote_guild = self.client.get_guild(self.data['emote_server_id'])
        role_name = react_roles_dict.get(payload.emoji.name)
        message = await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if role_name is None:
            await message.remove_reaction(payload.emoji, payload.member)
            return
        role = nextcord.utils.get(guild.roles, name=role_name)
        await addRole(payload.member, role)
        if payload.message_id == self.data['react_message_ids'][0]:
            await self.selectNewRole(payload.member, payload.emoji.name, message, emote_guild)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload : nextcord.RawReactionActionEvent):
        if payload.message_id not in self.data['react_message_ids']:
            return
        guild = self.client.get_guild(payload.guild_id)
        user = await self.client.fetch_user(payload.user_id)
        member = guild.get_member(user.id)
        name = react_roles_dict.get(payload.emoji.name)
        if name:
            role = nextcord.utils.get(guild.roles, name=name)
            await removeRole(member, role)

    @nextcord.slash_command(guild_ids=[1093195040320389200], name='resetreactmessages', description='Resets react messages. Must be an administrator to use.')
    async def resetReactMessages(self, interaction : nextcord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You are not authorized to run this command', ephemeral=True)
            return
        await interaction.response.defer()
        channel = self.client.get_channel(1093916970644156419)
        guild = self.client.get_guild(1093195040320389200)
        emote_guild = self.client.get_guild(self.data['emote_server_id'])
        messages = await channel.history().flatten()
        await channel.delete_messages(messages)
        description = 'React with a emote below to change\nyour color to that type\'s color!\n\n'
        i = 0
        for t in type_roles:
            role = nextcord.utils.get(guild.roles, name=t)
            emoji = nextcord.utils.get(emote_guild.emojis, name=t.lower())
            line = role.mention + ': ' + str(emoji)
            if i%2 == 1:
                line += '\n'
            else:
                line += ' '
            i += 1
            description += line
        embed = nextcord.Embed(
            title='Choose Your Tera Type!',
            description=description
        )
        type_message = await channel.send(embed=embed)

        message = await channel.fetch_message(type_message.id)
        for t in type_roles:
            emoji = nextcord.utils.get(emote_guild.emojis, name=t.lower())
            await message.add_reaction(emoji)
        
        description = ''
        channel_emotes = [nextcord.utils.get(emote_guild.emojis, name=n) for n in channel_react_emotes]
        channel_roles = [nextcord.utils.get(guild.roles, name=react_roles_dict.get(n)) for n in channel_react_emotes]
        for i in range(len(channel_react_emotes)):
            description += f'React with {channel_emotes[i]} to get the {channel_roles[i].mention} role\n'
        embed = nextcord.Embed(
            title='Add Additional Channels!',
            description=description
        )
        channel_message = await channel.send(embed=embed)

        message = await channel.fetch_message(channel_message.id)
        for e in channel_react_emotes:
            emoji = nextcord.utils.get(emote_guild.emojis, name=e)
            await message.add_reaction(emoji)

        self.data['react_message_ids'] = [type_message.id, channel_message.id]
        with open('data/data.json', 'w') as data_file:
            data_file.write(json.dumps(self.data, indent=4))

        await interaction.followup.send('done')
        
def setup(client : nextcord.Client):
    client.add_cog(ReactionRoles(client))