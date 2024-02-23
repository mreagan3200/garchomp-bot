import nextcord
from nextcord.ext import commands

import sqlite3
from datetime import datetime

from util.DataUtil import *
from shared import *

class Starboard(commands.Cog):
    def __init__(self, client : nextcord.Client):
        self.client = client
        self.datautil = DataUtil('data/data.json')
        self.data = self.datautil.load()
        self.db = sqlite3.connect('data/bot_data.db')
        self.cursor = self.db.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS starboard (message INTEGER, original_message INTEGER, channel_id INTEGER, stars SMALLINT)')
    
    async def update_stars(self, message, stars):
        starboard_message = await self.client.get_channel(starboard_channel_id).fetch_message(message)
        embed = starboard_message.embeds[0]
        name = embed.author.name
        name = name[:name.rfind('⭐')+1] + str(stars)
        embed.set_author(name=name, icon_url=embed.author.icon_url)
        await starboard_message.edit(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload : nextcord.RawReactionActionEvent):
        if str(payload.emoji) != self.data.get('starboard_emoji'):
            return
        channel = self.client.get_channel(payload.channel_id)
        if channel.category is not None:
            message = await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
            emoji = str(payload.emoji) if str(payload.emoji).find('<') == -1 else payload.emoji
            stars = nextcord.utils.get(message.reactions, emoji=emoji)
            if stars.count >= self.data['starboard_min_reactions']:
                self.cursor.execute('SELECT message FROM starboard WHERE original_message = ?', (message.id,))
                starboard_entry = self.cursor.fetchone()
                if starboard_entry:
                    await self.update_stars(starboard_entry[0], stars.count)
                    self.cursor.execute('UPDATE starboard SET stars = ? WHERE message = ?', (stars.count, starboard_entry[0]))
                else:
                    embed = nextcord.Embed(description=f'{message.content}\n\n[**Source**]({message.jump_url})',
                                            color=message.author.color)
                    for attachment in message.attachments:
                        if attachment.content_type.startswith('image'):
                            embed.set_image(attachment.url)
                            break
                    embed.set_author(name=f'{message.author.display_name}  ⭐{stars.count}', icon_url=message.author.display_avatar.url)
                    time = message.created_at.astimezone(tz=datetime.now().astimezone().tzinfo)
                    embed.set_footer(text=time.strftime("%m/%d/%Y %I:%M %p"))
                    starboard_channel = self.client.get_channel(starboard_channel_id)
                    starboard_message = await starboard_channel.send(embed=embed)
                    self.cursor.execute('INSERT INTO starboard (message, original_message, channel_id, stars) VALUES (?, ?, ?, ?)', (starboard_message.id, message.id, payload.channel_id, stars.count))
                self.db.commit()
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload : nextcord.RawReactionActionEvent):
        if str(payload.emoji) != self.data.get('starboard_emoji'):
            return
        channel = self.client.get_channel(payload.channel_id)
        if channel.category is not None:
            message = await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
            emoji = str(payload.emoji) if str(payload.emoji).find('<') == -1 else payload.emoji
            stars = nextcord.utils.get(message.reactions, emoji=emoji)
            self.cursor.execute('SELECT message FROM starboard WHERE original_message = ?', (message.id,))
            starboard_entry = self.cursor.fetchone()
            if starboard_entry:
                stars = stars.count if stars else 0
                if stars == 0:
                    starboard_message = await self.client.get_channel(starboard_channel_id).fetch_message(starboard_entry[0])
                    self.cursor.execute('DELETE FROM starboard WHERE original_message = ?', (message.id,))
                    await starboard_message.delete()
                else:
                    await self.update_stars(starboard_entry[0], stars)
                    self.cursor.execute('UPDATE starboard SET stars = ? WHERE message = ?', (stars, starboard_entry[0]))
                self.db.commit()
    
    async def changeminstars(self, stars : int):
        self.datautil.updateData({'starboard_min_reactions':stars})
        self.data = self.datautil.load()
        return f'Minimum stars set to {stars} stars'

    @nextcord.slash_command(guild_ids=[server_id], description='Generate top starboard messages.')
    async def starboard(self, interaction : nextcord.Interaction):
        await interaction.response.defer()
        self.cursor.execute('SELECT * FROM starboard ORDER BY stars DESC LIMIT 10')
        result = self.cursor.fetchall()
        if len(result) == 0:
            await interaction.followup.send('There are no messages on the starboard')
        else:
            description = ''
            i = 1
            max_length = 22
            for sb_message, original, channel, stars in result:
                message = await self.client.get_channel(int(channel)).fetch_message(int(original))
                content = message.content.replace('\n', ' ')
                if len(content) > max_length:
                    content = content[:max_length]+'...'
                elif len(content) == 0:
                    content = 'Source'
                description += f'{i}. [{content}]({message.jump_url}) - {message.author.mention} ⭐{stars}\n'
                i += 1
            embed = nextcord.Embed(description=description, color=nextcord.Colour(0xd4af37))
            await interaction.followup.send(embed=embed)

    def __del__(self):
        self.cursor.close()
        self.db.close()

def setup(client : nextcord.Client):
    client.add_cog(Starboard(client))