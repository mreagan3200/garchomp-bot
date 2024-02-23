import nextcord
import subprocess
from nextcord.ext import commands
from shared import *

import os
import io
import datetime
import shutil

class Maintenance(commands.Cog):
    def __init__(self, client : nextcord.Client):
        self.client = client
    
    @commands.Cog.listener()
    async def on_member_join(self, member : nextcord.Member):
        guild = self.client.get_guild(server_id)
        color = guild.get_member(self.client.user.id).color
        embed = nextcord.Embed(title=f'{member.name} has joined the server', color=color)
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
        await self.client.get_channel(mod_logs_id).send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member : nextcord.Member):
        guild = self.client.get_guild(server_id)
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
        await self.client.get_channel(mod_logs_id).send(embed=embed)
    
    @commands.Cog.listener()
    async def on_thread_create(self, thread : nextcord.Thread):
        await thread.join()

    @commands.Cog.listener()
    async def on_message_delete(self, message : nextcord.Message):
        if message.channel.category is not None:
            guild = self.client.get_guild(server_id)
            color = guild.get_member(self.client.user.id).color
            embed = nextcord.Embed(title='deleted message', description=message.content, color=color)
            embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
            await self.client.get_channel(mod_logs_id).send(embed=embed)
            
            files = None
            if message.attachments:
                files = []
                for attachment in message.attachments:
                    image_bytes = await attachment.read()
                    image_io = io.BytesIO(image_bytes)
                    files.append(nextcord.File(image_io, attachment.filename))
                await self.client.get_channel(mod_logs_id).send('Attachments:', files=files)

    @commands.Cog.listener()
    async def on_message_edit(self, before : nextcord.Message, after : nextcord.Message):
        if before.author.bot:
            return
        if before.channel.category is not None:
            guild = self.client.get_guild(server_id)
            color = guild.get_member(self.client.user.id).color
            description = f'**original**\n{before.content}\n**edited**\n{after.content}\n\n[**Source**]({after.jump_url})'
            embed = nextcord.Embed(title='edited message', description=description, color=color)
            embed.set_author(name=before.author.name, icon_url=before.author.display_avatar.url)
            await self.client.get_channel(mod_logs_id).send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message : nextcord.Message):
        if message.author.id == 1149200790779592704:
            try:
                subprocess.Popen('python Update.py', shell=True)
            except subprocess.CalledProcessError as e:
                if e.returncode != 15:
                    print(f"Error restarting the bot: {e}")

    async def dump_log_files(self):
        logs = os.listdir('./logs')
        mod_logs = self.client.get_guild(server_id).get_channel(mod_logs_id)
        for fileName in logs:
            message = fileName + '\n```'
            with open(f'logs/{fileName}', 'r') as log_file:
                message += log_file.read()
            message += '```'
            await mod_logs.send(message)
            os.remove(f'logs/{fileName}')
        if len(logs) == 0:
            await mod_logs.send('No errors or warnings to report for this week')
    
    async def create_backup(self):
        shutil.copy('data/bot_data.db', 'data/backup_data.db')
    
    async def restore_backup(self):
        if os.path.isfile('data/backup_data.db'):
            shutil.copy('data/backup_data.db', 'data/bot_data.db')
            return 'Backup restored'
        else:
            return 'No backup'

def setup(client : nextcord.Client):
    client.add_cog(Maintenance(client))