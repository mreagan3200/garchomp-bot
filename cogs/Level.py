import nextcord
from nextcord.ext import commands
from typing import Optional

from util.RolesUtil import *
from util.DataUtil import *
from shared import *

import sqlite3
import numpy as np
from collections import defaultdict

class Level(commands.Cog):
    def __init__(self, client : commands.Bot):
        self.client = client
        self.datautil = DataUtil('data/data.json')
        self.data = self.datautil.load()
        self.db = sqlite3.connect('data/bot_data.db')
        self.cursor = self.db.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS levels (user INTEGER primary key, level INTEGER, total_xp INTEGER, held_item VARCHAR(20) DEFAULT NULL, money INTEGER DEFAULT 3000, bag BLOB, buffs BLOB, debuffs BLOB)')
    
    @commands.Cog.listener()
    async def on_member_join(self, member : nextcord.Member):
        await init_user_level(member)
        update_database(self.db)
    
    @commands.Cog.listener()
    async def on_message(self, message : nextcord.Message):
        if message.author.bot:
            return
        if message.guild.id == emote_server_id:
            return
        await addXP(self.cursor, message.author, message=True)
        update_database(self.db)

    @nextcord.slash_command(guild_ids=[server_id], name='init', description='Initialize a user\'s xp and reset level role.')
    async def init(self, interaction : nextcord.Interaction, user : Optional[nextcord.Member] = nextcord.SlashOption(required=False, description='member to initialize. member is self if omitted.')):
        if user is None:
            user = interaction.user
        elif not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You are not authorized to initialize other users', ephemeral=True)
            return
        if await init_user_level(self.cursor, user):
            await interaction.response.send_message(f'{user.name} initialized', ephemeral=True)
        else:
            await interaction.response.send_message(f'{user.name} is already initialized', ephemeral=True)
        update_database(self.db)

    @nextcord.slash_command(guild_ids=[server_id], name='summary', description='Generate a summary of a user\'s stats.')
    async def info(self, interaction : nextcord.Interaction, user : Optional[nextcord.Member] = nextcord.SlashOption(required=False, description='member to generate stats. member is self if omitted.')):
        if user is None:
            user = interaction.user
        self.cursor.execute('SELECT level, total_xp FROM levels WHERE user = ?', (user.id,))
        info_tuple = self.cursor.fetchone()
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
        await interaction.response.send_message(embed=embed)

    async def setxp(self, member : nextcord.Member, xp : int):
        level = max(np.floor(np.cbrt(xp)), 1)
        await init_user_level(self.cursor, member)
        for role in member.roles:
            if role.name in level_roles:
                await remove_role(member, role)
                break
        self.cursor.execute('UPDATE levels SET level = ?, total_xp = ? WHERE user = ?', (level, xp, member.id))
        await update_level_role(self.cursor, member)
        update_database(self.db)
        return f'{member.name}\'s XP set to {xp}'
    
    async def addxpcommand(self, member : nextcord.Member, xp : int):
        await addXP(self.cursor, member, xp)
        update_database(self.db)
        return f'Added {xp} XP to {member.name}'

    @nextcord.slash_command(guild_ids=[server_id], name='leaderboard', description='Generate a leaderboard of the top 10 highest leveled users.')
    async def leaderboard(self, interaction : nextcord.Interaction):
        self.cursor.execute('SELECT user, level FROM levels WHERE user != ? ORDER BY total_xp DESC ', (1093965324988194886,))
        result = self.cursor.fetchall()
        leaderboard_list = []
        for r in result:
            user = self.client.get_user(r[0])
            if user is not None:
                leaderboard_list.append(r)
        await generate_leaderboard(leaderboard_list)
        guild = self.client.get_guild(server_id)
        color = guild.get_member(self.client.user.id).color
        embed = nextcord.Embed(color=color)
        file = nextcord.File(f'data/leaderboard/leaderboard.png', filename='leaderboard.png')  
        embed.set_image(url=f'attachment://leaderboard.png')

        await interaction.response.send_message(file=file, embed=embed)

    @nextcord.slash_command(guild_ids=[server_id], description='Give item to a user.')
    async def giveitem(self, interaction : nextcord.Interaction, member : Optional[nextcord.Member] = nextcord.SlashOption(required=True, description='user to give item to'), item : Optional[str] = nextcord.SlashOption(required=True, description='item to give'), quantity : Optional[str] = nextcord.SlashOption(required=False, description='amount to give')):
        if quantity is not None:
            if quantity.lower() != 'all' and not quantity.isdigit():
                await interaction.response.send_message('invalid quantity', ephemeral=True)
                return
        item = formalize_item(item)
        items_dict = defaultdict(int)
        items_dict[item] = quantity
        if not interaction.user.guild_permissions.administrator:
            q = remove_item(self.cursor, interaction.user, items_dict)
            if q <= 0:
                await interaction.response.send_message('invalid request', ephemeral=True)
                return
            items_dict[item] = int(q)
        else:
            await administrator_command_executed(interaction)
        give_item(self.cursor, member, items_dict)
        update_database(self.db)
        await interaction.response.send_message('done', ephemeral=True)

    @nextcord.slash_command(guild_ids=[server_id], description='Use an item from the bag.')
    async def useitem(self, interaction : nextcord.Interaction, item : Optional[str] = nextcord.SlashOption(required=True, description='item to use'), quantity : Optional[str] = nextcord.SlashOption(required=False, description='amount to use')):
        if quantity is not None:
            if quantity.lower() != 'all' and not quantity.isdigit():
                await interaction.response.send_message('invalid quantity', ephemeral=True)
                return
        success = await use_item(self.cursor, interaction.user, item, quantity=quantity)
        if success:
            await interaction.response.send_message('done', ephemeral=True)
        else:
            await interaction.response.send_message('failed', ephemeral=True)
        update_database(self.db)
    
    @nextcord.slash_command(guild_ids=[server_id], description='Use a move tm from the bag.')
    async def usemove(self, interaction : nextcord.Interaction, move : str, target : Optional[nextcord.Member] = nextcord.SlashOption(required=False, description='target of the move')):
        self.cursor.execute('SELECT debuffs FROM levels WHERE user = ?', (interaction.user.id,))
        t1 = int(json.loads(self.cursor.fetchone()[0]).get('move_cd'))
        t2 = int(time())
        if t2 < t1:
            h, m, s = seconds_to_hms(t1-t2)
            await interaction.response.send_message(f'This command is on cooldown. Try again in {h}h {m}m {s}s', ephemeral=True)
            return
        move, success = await use_move(self.cursor, move, interaction.user, target, interaction)
        if success:
            embed = nextcord.Embed(title=f'{interaction.user.name} used {format_item(move)}!', 
                                    description=f'{success}\nThe {format_item(move)} TM was used up...',
                                    color=interaction.user.color)
            self.cursor.execute('SELECT debuffs FROM levels WHERE user = ?', (interaction.user.id,))
            debuffs = json.loads(self.cursor.fetchone()[0])
            debuffs['move_cd'] = int(t2 + 8*60*60)
            self.cursor.execute('UPDATE levels SET debuffs = ? WHERE user = ?', (json.dumps(debuffs), interaction.user.id))
            if interaction.response.is_done():
                await interaction.channel.send(embed=embed)
            else:
                await interaction.response.send_message(embed=embed)
        elif move: # Do not have TM
            await interaction.response.send_message(f'You do not have a {format_item(move)} TM', ephemeral=True)
        else: # Invalid Move
            await interaction.response.send_message('Invalid Move', ephemeral=True)
        update_database(self.db)

    @nextcord.slash_command(guild_ids=[server_id], name='bag', description='Generate bag contents.')
    async def bag(self, interaction : nextcord.Interaction):
        self.cursor.execute('SELECT money, bag, held_item FROM levels WHERE user = ?', (interaction.user.id,))
        q = self.cursor.fetchone()
        money = q[0]
        bag = json.loads(q[1])
        held_item = q[2]
        emote_guild = self.client.get_guild(emote_server_id)
        description = ''
        if held_item is not None:
            emoji = nextcord.utils.get(emote_guild.emojis, name=held_item)
            if emoji:
                description += f'Held Item: {emoji} {format_item(held_item)}\n'
            else:
                description += f'Held Item: {format_item(held_item)}\n'
        description += f'${money:,}\n'
        xp_candies = {k: v for k, v in bag.items() if 'candy' in k and v > 0}
        other_items = {k: v for k, v in bag.items() if 'candy' not in k and v > 0}
        custom_order = ['xp_candy_xs', 'xp_candy_s', 'xp_candy_m', 'xp_candy_l', 'xp_candy_xl', 'rare_candy']
        for item in sorted(other_items.keys()):
            if item in valid_moves:
                emoji = nextcord.utils.get(emote_guild.emojis, name='tm')
                description += f'{emoji} x{other_items[item]}\t`{format_item(item)}`\n'
            else:
                emoji = nextcord.utils.get(emote_guild.emojis, name=item)
                if emoji:
                    description += f'{emoji} x{other_items[item]}\t`{format_item(item)}`\n'
                else:
                    description += f'{format_item(item)} x{other_items[item]}\n'
        for item in custom_order:
            if item in xp_candies:
                emoji = nextcord.utils.get(emote_guild.emojis, name=item)
                if emoji:
                    description += f'{emoji} x{xp_candies[item]}\t`{format_item(item)}`\n'
                else:
                    description += f'{format_item(item)} x{xp_candies[item]}\n'
        embed = nextcord.Embed(description=description, color=interaction.user.color)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[server_id], description='Change held item')
    async def changehelditem(self, interaction : nextcord.Interaction, item : Optional[str] = nextcord.SlashOption(required=False, description='item to hold')):
        self.cursor.execute('SELECT held_item, bag FROM levels WHERE user = ?', (interaction.user.id,))
        q = self.cursor.fetchone()
        held_item = q[0]
        bag = json.loads(q[1])
        if item is None:
            if held_item is not None:
                bag[held_item] += 1
                self.cursor.execute(f'UPDATE levels SET held_item = ?, bag = ? WHERE user = ?', (None, json.dumps(bag), interaction.user.id))
                await interaction.response.send_message(f'You are no longer holding the {format_item(held_item)}', ephemeral=True)
            else:
                await interaction.response.send_message('You are not holding an item', ephemeral=True)
        else:
            item = search_dict(bag, item)
            if item is None or bag.get(item, 0) <= 0: # invalid item
                await interaction.response.send_message(f'You do not have {format_item(item)} or it is invalid', ephemeral=True)
                return
            if held_item == item: # already holding the item
                await interaction.response.send_message(f'You are already holding {format_item(item)}', ephemeral=True)
                return
            if held_item is None: # not holding an item
                bag[item] -= 1
                self.cursor.execute(f'UPDATE levels SET held_item = ?, bag = ? WHERE user = ?', (item, json.dumps(bag), interaction.user.id))
            else: # holding another item
                bag[held_item] += 1
                bag[item] -= 1
                self.cursor.execute(f'UPDATE levels SET held_item = ?, bag = ? WHERE user = ?', (item, json.dumps(bag), interaction.user.id))
            update_database(self.db)
            await interaction.response.send_message(f'Held item changed to {format_item(item)}', ephemeral=True)

    def __del__(self):
        self.db.close()

def setup(client : nextcord.Client):
    client.add_cog(Level(client))