import nextcord
from nextcord.ext import commands
from typing import Optional

from .ReactionRoles import type_roles
from util.RolesUtil import *

import sqlite3
import math
import random
from time import time
import json

level_roles = ['Level 1', 'Level 10', 'Level 20', 'Level 30', 'Level 40', 'Level 50', 'Level 60', 
               'Level 70', 'Level 80', 'Level 90', 'Level 100']

class Level(commands.Cog):
    def __init__(self, client : commands.Bot):
        self.client = client
        with open('data/data.json', 'r') as data_file:
            self.data = json.load(data_file)
        self.db = sqlite3.connect('data/bot_data.db')
        cursor = self.db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS levels (user INTEGER, level INTEGER, total_xp INTEGER, base_hp INTEGER, base_atk INTEGER, base_def INTEGER, base_spa INTEGER, base_spd INTEGER, base_spe INTEGER, last_xp_s INTEGER)')
        cursor.close()
    
    async def update_level_role(self, member : nextcord.Member):
        current_role = None
        for role in member.roles:
            if role.name in level_roles:
                current_role = role
        cursor = self.db.cursor()
        cursor.execute('SELECT level FROM levels WHERE user = ?', (member.id,))
        level = cursor.fetchone()
        cursor.close()
        if level is None:
            if await self.init_user_level(member):
                level = (1)
            else:
                return
        level = level[0]
        if current_role is None:
            new_role_index = level//10
            guild = self.client.guilds[0]
            role = nextcord.utils.get(guild.roles, name=level_roles[new_role_index])
            await addRole(member, role)
        else:
            current_role_index = int(current_role.name[6:])//10
            new_role_index = level//10
            if new_role_index > current_role_index:
                guild = self.client.guilds[0]
                role = nextcord.utils.get(guild.roles, name=level_roles[new_role_index])
                await addRole(member, role)
                await removeRole(member, current_role)
    
    def generate_base_stats(self, bst=600, minimum=60):
        baseStats = [minimum]*6
        maximum = bst//4
        bst = (bst - minimum*6)//10
        l = list(range(6))
        while bst > 0:
            choice = random.choice(l)
            baseStats[choice] += 10
            if baseStats[choice] >= maximum:
                l.remove(choice)
            bst -= 1
        return baseStats
    
    def get_stats(self, base_stats : list, level : int):
        new_stats = ['']*6
        new_stats[0] = (base_stats[0]*2*level)//100 + level + 10
        for i in range(1, 6):
            new_stats[i] = (base_stats[i]*2*level)//100 + 5
        return tuple(new_stats)
    
    def get_level_up_stats(self, base_stats : list, old_level : int, new_level : int):
        stats = ['']*6
        old_stats = self.get_stats(base_stats, old_level)
        new_stats = self.get_stats(base_stats, new_level)
        for i in range(6):
            stats[i] = f'{new_stats[i]}(+{new_stats[i]-old_stats[i]})'
        return tuple(stats)

    async def init_user_level(self, member : nextcord.Member):
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM levels WHERE user = ?', (member.id,))
        entry = cursor.fetchone()
        if entry is not None:
            cursor.close()
            return False
        else:
            baseStats = self.generate_base_stats()
            cursor.execute('INSERT INTO levels (user, level, total_xp, base_hp, base_atk, base_def, base_spa, base_spd, base_spe, last_xp_s) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (member.id, 1, 0, baseStats[0], baseStats[1], baseStats[2], baseStats[3], baseStats[4], baseStats[5], int(time())))
            self.db.commit()
            cursor.close()
            await self.update_level_role(member)
            return True
    
    @commands.Cog.listener()
    async def on_member_join(self, member : nextcord.Member):
        await self.init_user_level(member)
    
    async def sendLevelUpMessage(self, user : nextcord.Member, oldLevel, newLevel):
        bot_commands = self.client.get_channel(1094723044888547448)
        cursor = self.db.cursor()
        cursor.execute('SELECT base_hp, base_atk, base_def, base_spa, base_spd, base_spe FROM levels WHERE user = ?', (user.id,))
        base_stats = cursor.fetchone()
        p_hp, p_atk, p_def, p_spa, p_spd, p_spe = self.get_level_up_stats(list(base_stats), oldLevel, newLevel)
        embed = nextcord.Embed(title=f'{user.display_name} leveled up to level {newLevel}!')
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name='HP', value=p_hp, inline=True)
        embed.add_field(name='ATK', value=p_atk, inline=True)
        embed.add_field(name='DEF', value=p_def, inline=True)
        embed.add_field(name='SPA', value=p_spa, inline=True)
        embed.add_field(name='SPD', value=p_spd, inline=True)
        embed.add_field(name='SPE', value=p_spe, inline=True)
        cursor.close()
        await bot_commands.send(embed=embed)

    async def addXP(self, user : nextcord.Member, xp=0, message=False):
        cursor = self.db.cursor()
        cursor.execute('SELECT level, total_xp FROM levels WHERE user = ?', (user.id,))
        info_tuple = cursor.fetchone()
        if info_tuple is None:
            if await self.init_user_level(user):
                info_tuple = (1, 0)
            else:
                cursor.close()
                return
        if message:
            cursor.execute('SELECT last_xp_s FROM levels WHERE user = ?', (user.id,))
            last_xp_s = cursor.fetchone()[0]
            current_time = int(time())
            xp = self.getXPToAdd(last_xp_s, current_time)
        if xp > 0:
            totalxp = min(info_tuple[1] + xp, 1000000)
            newlevel = math.floor(math.cbrt(totalxp))
            if message:
                cursor.execute('UPDATE levels SET level = ?, total_xp = ?, last_xp_s = ? WHERE user = ?', (newlevel, totalxp, current_time, user.id))
            else:
                cursor.execute('UPDATE levels SET level = ?, total_xp = ? WHERE user = ?', (newlevel, totalxp, user.id))
            self.db.commit()
            cursor.close()
            if newlevel > info_tuple[0]:
                await self.update_level_role(user)
                await self.sendLevelUpMessage(user, info_tuple[0], newlevel)
        else:
            cursor.close()
    
    def getXPToAdd(self, last_xp_s : int, current_time : int):
        time_elapsed = current_time - last_xp_s
        print(time_elapsed)
        if time_elapsed < 300:
            return time_elapsed//60
        else:
            return int(min(10, time_elapsed//360))
    
    @commands.Cog.listener()
    async def on_message(self, message : nextcord.Message):
        if message.author.bot:
            return
        if message.guild.id == self.data['emote_server_id']:
            return
        await self.addXP(message.author, message=True)

    @nextcord.slash_command(guild_ids=[1093195040320389200], name='init', description='init level')
    async def init(self, interaction : nextcord.Interaction, user : nextcord.Member):
        if await self.init_user_level(user):
            await interaction.response.send_message('execution successful')
        else:
            await interaction.response.send_message('execution failed')

    @nextcord.slash_command(guild_ids=[1093195040320389200], name='summary', description='Generate a summary of a user\'s stats')
    async def info(self, interaction : nextcord.Interaction, user : Optional[nextcord.Member] = nextcord.SlashOption(required=False)):
        """
        user: Member
            member to generate stats. member is self if omitted.
        """
        if user is None:
            user = interaction.user
        cursor = self.db.cursor()
        cursor.execute('SELECT level, total_xp FROM levels WHERE user = ?', (user.id,))
        info_tuple = cursor.fetchone()
        if info_tuple is None:
            await interaction.response.send_message('That user has not yet been initialized')
            return
        level = info_tuple[0]
        xp = info_tuple[1]
        xp_to_next = (level+1)**3 - xp
        cursor.execute('SELECT base_hp, base_atk, base_def, base_spa, base_spd, base_spe FROM levels WHERE user = ?', (user.id,))
        base_stats = cursor.fetchone()
        p_hp, p_atk, p_def, p_spa, p_spd, p_spe = self.get_stats(list(base_stats), level)
        cursor.close()
        color = None
        for role in user.roles:
            if role.name in type_roles:
                color = role.color
                break
        description = f'Exp. Points: {xp}\n'
        description += f'To Next Level: {xp_to_next}' if level < 100 else 'MAX LEVEL'
        embed = nextcord.Embed(title=f'Level {level}', 
                            description=description, 
                            color=color
                            )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_author(name=user.display_name)
        embed.add_field(name='HP', value=p_hp, inline=True)
        embed.add_field(name='ATK', value=p_atk, inline=True)
        embed.add_field(name='DEF', value=p_def, inline=True)
        embed.add_field(name='SPA', value=p_spa, inline=True)
        embed.add_field(name='SPD', value=p_spd, inline=True)
        embed.add_field(name='SPE', value=p_spe, inline=True)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[1093195040320389200], name='setxp', description='Set a user\'s xp. Must be an administrator to use.')
    async def setxp(self, interaction : nextcord.Interaction, member : nextcord.Member, xp : int):
        """
        member: Member
            target member
        xp: int
            xp value
        """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You are not authorized to run this command', ephemeral=True)
            return
        cursor = self.db.cursor()
        level = max(math.floor(math.cbrt(xp)), 1)
        await self.init_user_level(member)
        for role in member.roles:
            if role.name in level_roles:
                await removeRole(member, role)
                break
        cursor.execute('UPDATE levels SET level = ?, total_xp = ? WHERE user = ?', (level, xp, member.id))
        self.db.commit()
        cursor.close()
        await self.update_level_role(member)
        await interaction.response.send_message('done')
    
    @nextcord.slash_command(guild_ids=[1093195040320389200], name='addxp', description='Add to a user\'s xp. Must be an administrator to use.')
    async def addxpcommand(self, interaction : nextcord.Interaction, member : nextcord.Member, xp : int):
        """
        member: Member
            target member
        xp: int
            xp value
        """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You are not authorized to run this command', ephemeral=True)
            return
        await self.addXP(member, xp)
        await interaction.response.send_message('done')

    def __del__(self):
        self.db.close()

def setup(client : nextcord.Client):
    client.add_cog(Level(client))