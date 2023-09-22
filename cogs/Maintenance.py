import nextcord
from nextcord.ext import commands

import os
import io
import datetime

class Mainenance(commands.Cog):
    def __init__(self, client : nextcord.Client):
        self.client = client
    
    @commands.Cog.listener()
    async def on_member_join(self, member : nextcord.Member):
        guild = self.client.get_guild(1093195040320389200)
        color = guild.get_member(self.client.user.id).color
        embed = nextcord.Embed(title=f'{member.name} has joined the server', color=color)
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
        await self.client.get_channel(1093921362961252372).send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member : nextcord.Member):
        guild = self.client.get_guild(1093195040320389200)
        color = guild.get_member(self.client.user.id).color
        timestamp = datetime.datetime.now() - datetime.timedelta(seconds=5)
        title = None
        description = None
        async for entry in guild.audit_logs(limit=1, action=nextcord.AuditLogAction.kick, after=timestamp):
            if entry is not None and entry.target == member and entry.user != member:
                title='was kicked from the server'
                description=f'by {entry.user.name}'
        async for entry in guild.audit_logs(limit=1, action=nextcord.AuditLogAction.ban, after=timestamp):
            if entry is not None and entry.target == member and entry.user != member:
                title='was banned from the server'
                description=f'by {entry.user.name}'
        if title is None:
            title='has left the server'
        embed = nextcord.Embed(title=f'{member.name} {title}', description=description, color=color)
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
        await self.client.get_channel(1093921362961252372).send(embed=embed)
    
    @commands.Cog.listener()
    async def on_thread_create(self, thread : nextcord.Thread):
        await thread.join()

    @commands.Cog.listener()
    async def on_message_delete(self, message : nextcord.Message):
        if message.channel.category is not None:
            guild = self.client.get_guild(1093195040320389200)
            color = guild.get_member(self.client.user.id).color
            embed = nextcord.Embed(title='deleted message', description=message.content, color=color)
            embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
            await self.client.get_channel(1093921362961252372).send(embed=embed)
            
            files = None
            if message.attachments:
                files = []
                for attachment in message.attachments:
                    image_bytes = await attachment.read()
                    image_io = io.BytesIO(image_bytes)
                    files.append(nextcord.File(image_io, attachment.filename))
                await self.client.get_channel(1093921362961252372).send('Attachments:', files=files)

    @commands.Cog.listener()
    async def on_message_edit(self, before : nextcord.Message, after : nextcord.Message):
        if before.author.bot:
            return
        if before.channel.category is not None:
            guild = self.client.get_guild(1093195040320389200)
            color = guild.get_member(self.client.user.id).color
            description = f'**original**\n{before.content}\n**edited**\n{after.content}\n\n[**Source**]({after.jump_url})'
            embed = nextcord.Embed(title='edited message', description=description, color=color)
            embed.set_author(name=before.author.name, icon_url=before.author.display_avatar.url)
            await self.client.get_channel(1093921362961252372).send(embed=embed)

    async def dump_log_files(self):
        logs = os.listdir('./logs')
        mod_logs = self.client.get_guild(1093195040320389200).get_channel(1093921362961252372)
        for fileName in logs:
            message = fileName + '\n```'
            with open(f'logs/{fileName}', 'r') as log_file:
                message += log_file.read()
            message += '```'
            await mod_logs.send(message)
            os.remove(f'logs/{fileName}')
        if len(logs) == 0:
            await mod_logs.send('No errors or warnings to report for this week')

def setup(client : nextcord.Client):
    client.add_cog(Mainenance(client))