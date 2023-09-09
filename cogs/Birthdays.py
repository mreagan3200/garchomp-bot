import nextcord
from nextcord.ext import commands
from typing import Optional

import sqlite3
from dateutil import parser
from datetime import date
import random
import os

class Birthdays(commands.Cog):
    def __init__(self, client : nextcord.Client):
        self.client = client
        self.db = sqlite3.connect('data/bot_data.db')
        cursor = self.db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS birthdays (user INTEGER, year SMALLINT, month SMALLINT, day SMALLINT)')
        cursor.close()
    
    def ordinal(self, n: int):
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        else:
            suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
        return str(n) + suffix

    async def send_birthday_message(self, birthdays_list, current_year):
        guild = self.client.get_guild(1093195040320389200)
        description = ''
        for entry in birthdays_list:
            user_id, year = entry
            member = guild.get_member(user_id)
            if year is not None:
                description += f'Happy {self.ordinal(int(current_year)-int(year))} birthday to {member.mention}!\n'
            else:
                description += f'Happy birthday to {member.mention}!\n'
        color = guild.get_member(random.choice(birthdays_list)[0]).color

        embed = nextcord.Embed(title='Happy Birthday!', description=description, color=color)

        path = 'data/shinybirthdayimages' if random.randint(0, 255)==7 else 'data/birthdayimages'
        img = random.choice(os.listdir(path))
        file = nextcord.File(f'{path}/{img}', filename=img)  
        embed.set_thumbnail(url=f'attachment://{img}')

        channel = guild.get_channel(1094286349550485644)
        await channel.send(file=file, embed=embed)
    
    async def check_birthdays(self):
        year, month, day = str(date.today()).split('-')
        cursor = self.db.cursor()
        cursor.execute('SELECT user, year FROM birthdays WHERE month = ? AND day = ?', (month, day))
        birthdays_list = cursor.fetchall()
        if len(birthdays_list) > 0:
            await self.send_birthday_message(birthdays_list, year)
    
    @nextcord.slash_command(guild_ids=[1093195040320389200], name='setbirthday', description='Set your birthday. Year is optional')
    async def setbirthday(self, interaction : nextcord.Interaction, month : int, day : int, year : Optional[int] = nextcord.SlashOption(required=False), member : Optional[nextcord.Member] = nextcord.SlashOption(required=False)):
        if (member is not None) and (not interaction.user.guild_permissions.administrator):
            await interaction.response.send_message('You are not authorized to set other user\'s birthdays', ephemeral=True)
            return
        cursor = self.db.cursor()
        date_string = ''
        if year is not None:
            date_string = '-'.join((str(year), str(month), str(day)))
        else:
            date_string = '-'.join(('2000', str(month), str(day)))
        try:
            if bool(parser.parse(date_string)):
                cursor.execute('SELECT * FROM birthdays WHERE user = ?', (interaction.user.id,))
                entry = cursor.fetchone()
                if entry is not None:
                    cursor.execute('UPDATE birthdays SET year = ?, month = ?, day = ? WHERE user = ?', (year, month, day, interaction.user.id))
                    await interaction.response.send_message('Birthday updated', ephemeral=True)
                else:
                    cursor.execute('INSERT INTO birthdays (user, year, month, day) VALUES (?, ?, ?, ?)', (interaction.user.id, year, month, day))
                    await interaction.response.send_message('Birthday set', ephemeral=True)
                self.db.commit()
        except:
            await interaction.response.send_message('Birthday is invalid', ephemeral=True)
        finally:
            cursor.close()
    
    @nextcord.slash_command(guild_ids=[1093195040320389200], name='removebirthday', description='Remove your birthday')
    async def removebirthday(self, interaction : nextcord.Interaction, member : Optional[nextcord.Member] = nextcord.SlashOption(required=False)):
        if (member is not None) and (not interaction.user.guild_permissions.administrator):
            await interaction.response.send_message('You are not authorized to remove other user\'s birthdays', ephemeral=True)
            return
        user_id = interaction.user.id 
        if member is not None:
            user_id = member.id
        cursor = self.db.cursor()
        cursor.execute('DELETE FROM birthdays WHERE user = ?', (user_id,))
        self.db.commit()
        cursor.close()
        await interaction.response.send_message('Birthday deleted', ephemeral=True)
    
    def __del__(self):
        self.db.close()

def setup(client : nextcord.Client):
    client.add_cog(Birthdays(client))