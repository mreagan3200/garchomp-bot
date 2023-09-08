import nextcord
from nextcord.ext import commands
from typing import Optional

from .ReactionRoles import type_roles
from util.RolesUtil import *
from util.DataUtil import *

import sqlite3
import numpy as np
import random
from time import time
import json
from PIL import Image, ImageDraw, ImageFont
import io

level_roles = ['Level 1', 'Level 10', 'Level 20', 'Level 30', 'Level 40', 'Level 50', 'Level 60', 
               'Level 70', 'Level 80', 'Level 90', 'Level 100']
xp_map = {'xs':100, 's':800, 'm':3000, 'l':10000, 'xl':30000}

class Level(commands.Cog):
    def __init__(self, client : commands.Bot):
        self.client = client
        self.datautil = DataUtil('data/data.json')
        self.data = self.datautil.load()
        self.db = sqlite3.connect('data/bot_data.db')
        cursor = self.db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS levels (user INTEGER, level INTEGER, total_xp INTEGER, base_hp INTEGER, base_atk INTEGER, base_def INTEGER, base_spa INTEGER, base_spd INTEGER, base_spe INTEGER, last_xp_s INTEGER)')
        cursor.execute('CREATE TABLE IF NOT EXISTS bag (user INTEGER, money INTEGER DEFAULT 3000, xp_candy_xs SMALLINT DEFAULT 0, xp_candy_s SMALLINT DEFAULT 0, xp_candy_m SMALLINT DEFAULT 0, xp_candy_l SMALLINT DEFAULT 0, xp_candy_xl SMALLINT DEFAULT 0, rare_candy SMALLINT DEFAULT 0)')
        cursor.close()

    def get_user_bag(self, member : nextcord.Member):
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM bag WHERE user = ?', (member.id,))
        entry = cursor.fetchone()
        if entry:
            cursor.close()
            return entry
        else:
            cursor.execute('INSERT INTO bag (user) VALUES (?)', (member.id,))
            self.db.commit()
            cursor.close()
            return self.get_user_bag(member)

    def give_item(self, member : nextcord.Member, item, quantity=1):
        cursor = self.db.cursor()
        cursor.execute(f'SELECT {item} FROM bag WHERE user = ?', (member.id,))
        result = cursor.fetchone()
        if result:
            cursor.execute(f'UPDATE bag SET {item} = ? WHERE user = ?', (result[0]+int(quantity), member.id))
        else:
            cursor.execute(f'INSERT INTO bag (user, {item}) VALUES (?, ?)', (member.id, quantity))
        self.db.commit()
        cursor.close()
    
    async def use_item(self, member : nextcord.Member, item, quantity=1):
        cursor = self.db.cursor()
        try:
            cursor.execute(f'SELECT {item} from bag WHERE user = ?', (member.id,))
            q = int(cursor.fetchone()[0])
            if quantity == 'all':
                quantity = q
            else:
                quantity = int(quantity)
            if quantity > q:
                cursor.close()
                return False
            if item.startswith('xp'):
                xp = xp_map[item[item.rfind('_')+1:]]*quantity
                cursor.execute(f'UPDATE bag SET {item} = ? WHERE user = ?', (q-quantity, member.id))
                self.db.commit()
                await self.addXP(member, xp=xp)
                cursor.close()
                return True
            elif item == 'rare_candy':
                cursor.execute('SELECT level, total_xp from levels WHERE user = ?', (member.id,))
                level, total_xp = cursor.fetchone()
                if level + quantity > 100:
                    cursor.close()
                    return False
                xp = (level+quantity)**3 - total_xp
                cursor.execute(f'UPDATE bag SET {item} = ? WHERE user = ?', (q-quantity, member.id))
                self.db.commit()
                await self.addXP(member, xp=xp)
                cursor.close()
                return True
        except Exception as e:
            print(e)
            cursor.close()
            return False
    
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
            await add_role(member, role)
        else:
            current_role_index = int(current_role.name[6:])//10
            new_role_index = level//10
            if new_role_index > current_role_index:
                guild = self.client.guilds[0]
                role = nextcord.utils.get(guild.roles, name=level_roles[new_role_index])
                await add_role(member, role)
                await remove_role(member, current_role)
    
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
        embed = nextcord.Embed(title=f'{user.display_name} leveled up to level {newLevel}!',
                                color=user.color)
        embed.set_thumbnail(url=user.display_avatar.url)
        if self.data.get('show_stats'):
            cursor = self.db.cursor()
            cursor.execute('SELECT base_hp, base_atk, base_def, base_spa, base_spd, base_spe FROM levels WHERE user = ?', (user.id,))
            base_stats = cursor.fetchone()
            p_hp, p_atk, p_def, p_spa, p_spd, p_spe = self.get_level_up_stats(list(base_stats), oldLevel, newLevel)
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
            newlevel = np.floor(np.cbrt(totalxp))
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
    
    async def generate_leaderboard(self, leaderboard_list : list):
        image_path = 'data/leaderboard/leaderboard.png'
        length = len(leaderboard_list)
        image = Image.new('RGBA', (680, length*70+(length-1)*5), color = (0,0,0,0))
        draw = ImageDraw.Draw(image)

        for i in range(length):
            user_id, level = leaderboard_list[i]
            guild = self.client.get_guild(1093195040320389200)
            member = guild.get_member(user_id)

            draw.rectangle((0, i*75, 680, i*75+70), fill='black')
            font = ImageFont.truetype('calibrib.ttf', size=40)
            text = f'#{i+1}'
            w, h = font.getsize(text)
            draw.text((80 + (70-w)//2, (i*75) + (70-h)//2), text, fill='#394173', font=font)
            color = str(member.color)
            color = '#ffffff' if color == '#000000' else color
            member_text = member.name
            avatar_bytes = await member.display_avatar.read()
            with io.BytesIO(avatar_bytes) as image_buffer:
                pfp = Image.open(image_buffer)
                pfp = pfp.resize((70,71))
                pfp = pfp.convert('RGBA')
                image.paste(pfp, (0, i*75), pfp)
                        
            font = ImageFont.truetype('calibri.ttf', size=30)
            max_width = 300
            text_width = draw.textlength(member_text, font=font)
            while text_width > max_width:
                font = ImageFont.truetype('calibri.ttf', size=font.size-1)
                text_width = draw.textlength(member_text, font=font)
            w, h = font.getsize(member_text)
            draw.text((170, (i*75) + (70-h)//2), member_text, fill=color, font=font)
            
            font = ImageFont.truetype('calibri.ttf', size=30)
            level_text = f'Level: {level}'
            w, h = font.getsize(level_text)
            draw.text((520, (i*75) + (70-h)//2), level_text, fill='#5A6A9C', font=font)
        image.save(image_path)

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
        description = f'Exp. Points: {xp}\n'
        description += f'To Next Level: {xp_to_next}' if level < 100 else 'MAX LEVEL'
        embed = nextcord.Embed(title=f'Level {level}', 
                            description=description, 
                            color=user.color)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_author(name=user.display_name)
        if self.data.get('show_stats'):
            cursor.execute('SELECT base_hp, base_atk, base_def, base_spa, base_spd, base_spe FROM levels WHERE user = ?', (user.id,))
            base_stats = cursor.fetchone()
            p_hp, p_atk, p_def, p_spa, p_spd, p_spe = self.get_stats(list(base_stats), level)
            embed.add_field(name='HP', value=p_hp, inline=True)
            embed.add_field(name='ATK', value=p_atk, inline=True)
            embed.add_field(name='DEF', value=p_def, inline=True)
            embed.add_field(name='SPA', value=p_spa, inline=True)
            embed.add_field(name='SPD', value=p_spd, inline=True)
            embed.add_field(name='SPE', value=p_spe, inline=True)
        cursor.close()
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
        level = max(np.floor(np.cbrt(xp)), 1)
        await self.init_user_level(member)
        for role in member.roles:
            if role.name in level_roles:
                await remove_role(member, role)
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

    @nextcord.slash_command(guild_ids=[1093195040320389200], name='leaderboard', description='Generate a leaderboard of the top 10 highest leveled users')
    async def leaderboard(self, interaction : nextcord.Interaction):
        cursor = self.db.cursor()
        cursor.execute('SELECT user, level FROM levels WHERE user != ? ORDER BY total_xp DESC ', (1093965324988194886,))
        result = cursor.fetchall()
        cursor.close()
        leaderboard_list = []
        for r in result:
            user = self.client.get_user(r[0])
            if user is not None:
                leaderboard_list.append(r)
        await self.generate_leaderboard(leaderboard_list)
        
        embed = nextcord.Embed()
        file = nextcord.File(f'data/leaderboard/leaderboard.png', filename='leaderboard.png')  
        embed.set_image(url=f'attachment://leaderboard.png')

        await interaction.response.send_message(file=file, embed=embed)

    @nextcord.slash_command(guild_ids=[1093195040320389200])
    async def giveitem(self, interaction : nextcord.Interaction, member : nextcord.Member, item, quantity):
        self.give_item(member, item, quantity=quantity)
        await interaction.response.send_message('done', ephemeral=True)

    @nextcord.slash_command(guild_ids=[1093195040320389200])
    async def useitem(self, interaction : nextcord.Interaction, item, quantity):
        success = await self.use_item(interaction.user, item, quantity=quantity)
        if success:
            await interaction.response.send_message('done', ephemeral=True)
        else:
            await interaction.response.send_message('failed', ephemeral=True)

    @nextcord.slash_command(guild_ids=[1093195040320389200])
    async def bag(self, interaction : nextcord.Interaction):
        bag_contents = self.get_user_bag(interaction.user)
        emote_guild = self.client.get_guild(self.data.get('emote_server_id'))
        cursor = self.db.cursor()
        cursor.execute('PRAGMA table_info(bag);')
        entry = cursor.fetchall()
        cursor.close()
        description = ''
        for i, item, _, _, _, _ in entry:
            if i == 0:
                continue
            elif i == 1:
                description += f'${bag_contents[i]}\n'
            else:
                if bag_contents[i] > 0:
                    emoji = nextcord.utils.get(emote_guild.emojis, name=item)
                    if emoji:
                        description += f'{emoji} x{bag_contents[i]}\t`{item}`\n'
                    else:
                        description += f'{item} x{bag_contents[i]}\n'
        embed = nextcord.Embed(description=description, color=interaction.user.color)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    def __del__(self):
        self.db.close()

def setup(client : nextcord.Client):
    client.add_cog(Level(client))