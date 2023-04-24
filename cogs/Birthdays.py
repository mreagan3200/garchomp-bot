import nextcord
from nextcord.ext import commands
from typing import Optional

import sqlite3
from dateutil import parser
from datetime import date

class Birthdays(commands.Cog):
    def __init__(self, client : commands.Bot):
        self.client = client
        self.db = sqlite3.connect('data/bot_data.db')
        cursor = self.db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS birthdays (user INTEGER, year SMALLINT, month SMALLINT, day SMALLINT)')
        cursor.close()
    
    async def print_birthday_message(self, birthdays_list, year):
        embed = nextcord.Embed(description='test')
        for entry in birthdays_list:
            user_id, year = entry
            print(f'{user_id=}', f'{year=}')
        bot_commands = self.client.get_channel(1094723044888547448)
        await bot_commands.send(embed=embed)
        
    
    async def get_birthdays(self):
        today = date.today()
        year, month, day = (int(i) for i in str(today).split(sep='-'))
        cursor = self.db.cursor()
        cursor.execute('SELECT user, year FROM birthdays WHERE month = ? AND day = ?', (month, day))
        birthdays_list = cursor.fetchall()
        cursor.close()
        if len(birthdays_list) > 0:
            await self.print_birthday_message(birthdays_list, year)
    
    @nextcord.slash_command(guild_ids=[1093195040320389200], name='getbirthdays')
    async def getbirthdays(self, interaction : nextcord.Interaction):
        await self.get_birthdays()
        await interaction.response.send_message('done', ephemeral=True)
    
    @nextcord.slash_command(guild_ids=[1093195040320389200], name='setbirthday', description='Set your birthday')
    async def setbirthday(self, interaction : nextcord.Interaction, month : int, day : int, year : Optional[int] = nextcord.SlashOption(required=False)):
        """
        month: int
            Birthday Month
        day: int
            Birthday Day
        year: int
            Birthday Year
        """
        date_string = ''
        if year is None:
            date_string = '-'.join(('2000', str(month), str(day)))
        else:
            date_string = '-'.join((str(year), str(month), str(day)))
        try:
            if bool(parser.parse(date_string)):
                cursor = self.db.cursor()
                cursor.execute('SELECT * FROM birthdays WHERE user = ?', (interaction.user.id,))
                entry = cursor.fetchone()
                if entry is None:
                    cursor.execute('INSERT INTO birthdays (user, year, month, day) VALUES (?, ?, ?, ?)', (interaction.user.id, year, month, day))
                else:
                    cursor.execute('UPDATE birthdays SET year = ?, month = ?, day = ? WHERE user = ?', (year, month, day, interaction.user.id))
                self.db.commit()
                cursor.close()
                await interaction.response.send_message('Birthday set', ephemeral=True)
            else:
                await interaction.response.send_message('An unexpected error occurred', ephemeral=True)
        except:
            await interaction.response.send_message('Birthday is invalid', ephemeral=True)

    def __del__(self):
        self.db.close()
    
def setup(client : nextcord.Client):
    client.add_cog(Birthdays(client))