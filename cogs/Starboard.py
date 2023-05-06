import nextcord
from nextcord.ext import commands

import json
import sqlite3
from datetime import timezone, datetime

from util.DataUtil import *

class Starboard(commands.Cog):
    def __init__(self, client : nextcord.Client):
        self.client = client
        self.datautil = DataUtil('data/data.json')
        self.data = self.datautil.load()
        self.db = sqlite3.connect('data/bot_data.db')
        cursor = self.db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS starboard (message INTEGER, original_message INTEGER, stars SMALLINT)')
        cursor.close()
    
    async def update_stars(self, message, stars):
        starboard_message = await self.client.get_channel(1102065147046015099).fetch_message(message)
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
                cursor = self.db.cursor()
                cursor.execute('SELECT message FROM starboard WHERE original_message = ?', (message.id,))
                starboard_entry = cursor.fetchone()
                if starboard_entry:
                    await self.update_stars(starboard_entry[0], stars.count)
                    cursor.execute('UPDATE starboard SET stars = ? WHERE message = ?', (stars.count, starboard_entry[0]))
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
                    starboard_channel = self.client.get_channel(1102065147046015099)
                    starboard_message = await starboard_channel.send(embed=embed)
                    cursor.execute('INSERT INTO starboard (message, original_message, stars) VALUES (?, ?, ?)', (starboard_message.id, message.id, stars.count))
                self.db.commit()
                cursor.close()
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload : nextcord.RawReactionActionEvent):
        if str(payload.emoji) != self.data.get('starboard_emoji'):
            return
        channel = self.client.get_channel(payload.channel_id)
        if channel.category is not None:
            message = await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
            emoji = str(payload.emoji) if str(payload.emoji).find('<') == -1 else payload.emoji
            stars = nextcord.utils.get(message.reactions, emoji=emoji)
            cursor = self.db.cursor()
            cursor.execute('SELECT message FROM starboard WHERE original_message = ?', (message.id,))
            starboard_entry = cursor.fetchone()
            if starboard_entry:
                stars = stars.count if stars else 0
                if stars == 0:
                    starboard_message = await self.client.get_channel(1102065147046015099).fetch_message(starboard_entry[0])
                    cursor.execute('DELETE FROM starboard WHERE original_message = ?', (message.id,))
                    await starboard_message.delete()
                else:
                    await self.update_stars(starboard_entry[0], stars)
                    cursor.execute('UPDATE starboard SET stars = ? WHERE message = ?', (stars, starboard_entry[0]))
                self.db.commit()
                cursor.close()
    
    def change_emoji(self, emoji : str):
        newemoji = ''
        if emoji.find('<') != -1:
            newemoji = emoji
        else:
            newemoji = f'\\u{hex(ord(emoji))[2:].zfill(4)}'
        self.datautil.updateData({'starboard_emoji':newemoji})
    
    # @nextcord.slash_command(guild_ids=[1093195040320389200])
    # async def getemoji(self, interaction : nextcord.Interaction, emoji):
    #     self.change_emoji(emoji)
    #     await interaction.response.send_message(str(emoji))

    def __del__(self):
        self.db.close()

def setup(client : nextcord.Client):
    client.add_cog(Starboard(client))