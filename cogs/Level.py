import nextcord
from nextcord.ext import commands
from typing import Optional

from .ReactionRoles import type_roles
from util.RolesUtil import *
from util.DataUtil import *
from .Shop import modify_string

import sqlite3
import numpy as np
import random
from time import time
import json
from PIL import Image, ImageDraw, ImageFont
import io
from collections import defaultdict

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
        cursor.execute('CREATE TABLE IF NOT EXISTS levels (user INTEGER, level INTEGER, total_xp INTEGER, last_xp_s INTEGER)')
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

    def give_item(self, member : nextcord.Member, items_dict : defaultdict):
        cursor = self.db.cursor()
        for item,quantity in items_dict.items():
            cursor.execute(f'SELECT {item} FROM bag WHERE user = ?', (member.id,))
            result = cursor.fetchone()
            if result:
                cursor.execute(f'UPDATE bag SET {item} = ? WHERE user = ?', (result[0]+int(quantity), member.id))
            else:
                cursor.execute(f'INSERT INTO bag (user, {item}) VALUES (?, ?)', (member.id, int(quantity)))
        self.db.commit()
        cursor.close()
    
    async def use_item(self, member : nextcord.Member, item, quantity=1):
        cursor = self.db.cursor()
        item = item.strip().lower().replace(' ', '_')
        try:
            cursor.execute(f'SELECT {item} from bag WHERE user = ?', (member.id,))
            q = int(cursor.fetchone()[0])
            if quantity is None:
                quantity = 1
            elif quantity == 'all':
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
    
    def get_levelup_rewards(self, prevLevel, currLevel):
        rewards = defaultdict(int)
        for level in range(prevLevel, currLevel):
            level += 1
            rewards['money'] += level*100
            if level % 10 == 0:
                candy = None
                if level <= 10:
                    candy = 'xp_candy_s'
                elif level <= 30:
                    candy = 'xp_candy_m'
                elif level <= 50:
                    candy = 'xp_candy_l'
                else:
                    candy = 'xp_candy_xl'
                rewards[candy] += 5
                rewards['rare_candy'] += 1
            if level % 5 == 0:
                if level >= 0:
                    rewards['xp_candy_xs'] += 2
                if level >= 30:
                    rewards['xp_candy_s'] += 2
                if level >= 50:
                    rewards['xp_candy_m'] += 2
                if level >= 70:
                    rewards['xp_candy_l'] += 2
                if level > 70:
                    rewards['xp_candy_xl'] += 2
        return rewards
    
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

    async def init_user_level(self, member : nextcord.Member):
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM levels WHERE user = ?', (member.id,))
        entry = cursor.fetchone()
        if entry is not None:
            await self.update_level_role(member)
            cursor.close()
            return False
        else:
            cursor.execute('INSERT INTO levels (user, level, total_xp, last_xp_s) VALUES (?, ?, ?, ?)', (member.id, 1, 0, int(time())))
            self.db.commit()
            cursor.close()
            await self.update_level_role(member)
            return True
    
    @commands.Cog.listener()
    async def on_member_join(self, member : nextcord.Member):
        await self.init_user_level(member)
    
    async def sendLevelUpMessage(self, user : nextcord.Member, oldLevel, newLevel, rewards):
        bot_commands = self.client.get_channel(1094723044888547448)
        emote_guild = self.client.get_guild(self.data.get('emote_server_id'))
        description = 'Rewards'
        for k,v in rewards.items():
            description += '\n'
            if k == 'money':
                description += f'${v}'
            else:
                emoji = nextcord.utils.get(emote_guild.emojis, name=k)
                item = modify_string(k)
                if emoji:
                    description += f'{emoji} x{v}\t`{item}`'
                else:
                    description += f'{item} x{v}'
        embed = nextcord.Embed(title=f'{user.display_name} leveled up to level {newLevel:.0f}!',
                                description=description, color=user.color)
        embed.set_thumbnail(url=user.display_avatar.url)
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
            totalxp = info_tuple[1] + xp
            newlevel = int(np.floor(np.cbrt(totalxp)))
            if message:
                cursor.execute('UPDATE levels SET level = ?, total_xp = ?, last_xp_s = ? WHERE user = ?', (newlevel, totalxp, current_time, user.id))
            else:
                cursor.execute('UPDATE levels SET level = ?, total_xp = ? WHERE user = ?', (newlevel, totalxp, user.id))
            self.db.commit()
            cursor.close()
            if newlevel > info_tuple[0]:
                rewards = self.get_levelup_rewards(info_tuple[0], newlevel)
                self.give_item(user, rewards)
                await self.update_level_role(user)
                await self.sendLevelUpMessage(user, info_tuple[0], newlevel, rewards)
        else:
            cursor.close()
    
    def getXPToAdd(self, last_xp_s : int, current_time : int):
        time_elapsed = current_time - last_xp_s
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

    @nextcord.slash_command(guild_ids=[1093195040320389200], name='init', description='Initialize a user\'s xp and reset level role.')
    async def init(self, interaction : nextcord.Interaction, user : Optional[nextcord.Member] = nextcord.SlashOption(required=False, description='member to initialize. member is self if omitted.')):
        if user is None:
            user = interaction.user
        elif not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You are not authorized to initialize other users', ephemeral=True)
            return
        if await self.init_user_level(user):
            await interaction.response.send_message(f'{user.name} initialized', ephemeral=True)
        else:
            await interaction.response.send_message(f'{user.name} is already initialized', ephemeral=True)

    @nextcord.slash_command(guild_ids=[1093195040320389200], name='summary', description='Generate a summary of a user\'s stats.')
    async def info(self, interaction : nextcord.Interaction, user : Optional[nextcord.Member] = nextcord.SlashOption(required=False, description='member to generate stats. member is self if omitted.')):
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
        description += f'To Next Level: {xp_to_next}'
        embed = nextcord.Embed(title=f'Level {level}', 
                            description=description, 
                            color=user.color)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_author(name=user.display_name)
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
        await administrator_command_executed(interaction)
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
        await interaction.response.send_message('done', ephemeral=True)
    
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
        await administrator_command_executed(interaction)
        await self.addXP(member, xp)
        await interaction.response.send_message('done', ephemeral=True)

    @nextcord.slash_command(guild_ids=[1093195040320389200], name='leaderboard', description='Generate a leaderboard of the top 10 highest leveled users.')
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
        guild = self.client.get_guild(1093195040320389200)
        color = guild.get_member(self.client.user.id).color
        embed = nextcord.Embed(color=color)
        file = nextcord.File(f'data/leaderboard/leaderboard.png', filename='leaderboard.png')  
        embed.set_image(url=f'attachment://leaderboard.png')

        await interaction.response.send_message(file=file, embed=embed)

    @nextcord.slash_command(guild_ids=[1093195040320389200], description='Give item to a user. Must be an administrator to use.')
    async def giveitem(self, interaction : nextcord.Interaction, member : nextcord.Member, item : str, quantity : int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You are not authorized to run this command', ephemeral=True)
            return
        await administrator_command_executed(interaction)
        item = item.strip().lower().replace(' ', '_')
        items_dict = defaultdict(int)
        items_dict[item] = quantity
        self.give_item(member, items_dict)
        await interaction.response.send_message('done', ephemeral=True)

    @nextcord.slash_command(guild_ids=[1093195040320389200], description='Use an item from the bag.')
    async def useitem(self, interaction : nextcord.Interaction, item : Optional[str] = nextcord.SlashOption(required=True, description='item to use'), quantity : Optional[str] = nextcord.SlashOption(required=False, description='amount to use')):
        success = await self.use_item(interaction.user, item, quantity=quantity)
        if success:
            await interaction.response.send_message('done', ephemeral=True)
        else:
            await interaction.response.send_message('failed', ephemeral=True)

    @nextcord.slash_command(guild_ids=[1093195040320389200], name='bag', description='Generate bag contents.')
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
                    item = modify_string(item)
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