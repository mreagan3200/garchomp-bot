import nextcord
from nextcord.utils import MISSING
from shared import *
from collections import defaultdict
import random
import numpy as np
import json
from time import time
import io
from PIL import Image, ImageDraw, ImageFont
import random

level_roles = ['Level 1', 'Level 10', 'Level 20', 'Level 30', 'Level 40', 'Level 50', 
               'Level 60', 'Level 70', 'Level 80', 'Level 90', 'Level 100']
xp_map = {'xs':100, 's':800, 'm':3000, 'l':10000, 'xl':30000}
valid_moves = ['disable', 'knock_off', 'thief', 'pay_day']

async def add_role(member : nextcord.Member, role : nextcord.Role):
    if role not in member.roles:
        await member.add_roles(role)

async def remove_role(member : nextcord.Member, role : nextcord.Role):
    if role in member.roles:
        await member.remove_roles(role)

async def change_role_color(role : nextcord.Role, color):
    await role.edit(color=color)

async def administrator_command_executed(interaction : nextcord.Interaction):
    command_name = interaction.data.get('name')
    command = f'/{command_name}'
    iddict = interaction.data
    if iddict.get('type') == 6:
        command += ' ' + str(iddict.get('name')) + ': ' + str(client.get_user(int(iddict.get('value'))).mention)
    else:
        command += ' ' + str(iddict.get('name')) + ': ' + str(iddict.get('value'))
    channel = client.get_channel(1093921362961252372)
    embed = nextcord.Embed(title='command executed', description=command, color=interaction.user.color)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    # await channel.send(embed=embed) TODO: remove

def search_dict(d, item):
    item = normalize_item(item)
    for key in d.keys():
        if normalize_item(key) == item:
            return key
    return None

def search_list(l, item):
    item = normalize_item(item)
    for i in l:
        if normalize_item(i) == item:
            return i
    return None

def add_column(cursor, column_name : str, column_type, default=''):
    column_name = column_name.strip().lower().replace(' ', '_')
    cursor.execute(f'ALTER TABLE bag ADD COLUMN {column_name} {column_type} DEFAULT {default}')
    return column_name

def give_item(cursor, member : nextcord.Member, items_dict : defaultdict):
    cursor.execute('SELECT bag FROM levels WHERE user = ?', (member.id,))
    bag = json.loads(cursor.fetchone()[0])
    bag = {k: bag.get(k, 0) + items_dict.get(k, 0) for k in set(bag|items_dict)}
    for key, value in items_dict.items():
        if value == 0:
            bag[key] += 1 # default for items_dict is 1 for adding
    if 'money' in bag:
        money = bag['money']
        del bag['money']
        cursor.execute('SELECT money FROM levels WHERE user = ?', (member.id,))
        cursor.execute(f'UPDATE levels SET money = ?, bag = ? WHERE user = ?', (money + cursor.fetchone()[0], json.dumps(bag), member.id))
    else:
        cursor.execute(f'UPDATE levels SET bag = ? WHERE user = ?', (json.dumps(bag), member.id))

def remove_item(cursor, member : nextcord.Member, items_dict):
    cursor.execute('SELECT bag FROM levels WHERE user = ?', (member.id,))
    bag = json.loads(cursor.fetchone()[0])
    for key,value in items_dict.items():
        if str(value).lower() == 'all': # remove all
            bag[key] = 0
        elif value > bag[key]: # removing more than owned, error
            return False
        elif value == 0: # default for items_dict is 1 for removing
            bag[key] += 1
        else: # remove amount
            bag[key] -= value
    cursor.execute(f'UPDATE levels SET bag = ? WHERE user = ?', (json.dumps(bag), member.id))
    return True

async def use_item(cursor, member : nextcord.Member, item, quantity=1):
    cursor.execute(f'SELECT bag from levels WHERE user = ?', (member.id,))
    bag = json.loads(cursor.fetchone()[0])
    item = search_dict(bag, item)
    if item is None:
        return False
    q = bag.get(item, 0)
    if quantity is None:
        quantity = 1
    elif quantity.lower() == 'all':
        quantity = q
    else:
        quantity = int(quantity)
    if quantity > q:
        return False
    if item.startswith('xp'):
        xp = xp_map[item[item.rfind('_')+1:]]*quantity
    elif item == 'rare_candy':
        cursor.execute('SELECT level, total_xp from levels WHERE user = ?', (member.id,))
        level, total_xp = cursor.fetchone() 
        xp = (level+quantity)**3 - total_xp
    await addXP(cursor, member, xp)
    cursor.execute(f'SELECT bag from levels WHERE user = ?', (member.id,))
    bag = json.loads(cursor.fetchone()[0])
    bag[item] = q-quantity
    cursor.execute(f'UPDATE levels SET bag = ? WHERE user = ?', (json.dumps(bag), member.id))
    return True

def get_levelup_rewards(prevLevel, currLevel):
    rewards = defaultdict(int)
    for level in range(prevLevel, currLevel):
        level += 1
        rewards['money'] += level*100
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
    return rewards

async def update_level_role(cursor, member : nextcord.Member):
    current_role = None
    for role in member.roles:
        if role.name in level_roles:
            current_role = role
    cursor.execute('SELECT level FROM levels WHERE user = ?', (member.id,))
    level = cursor.fetchone()
    if level is None:
        if await init_user_level(member):
            level = (1)
        else:
            return
    level = level[0]
    if current_role is None:
        new_role_index = min(level//10,10)
        guild = client.guilds[0]
        role = nextcord.utils.get(guild.roles, name=level_roles[new_role_index])
        await add_role(member, role)
    else:
        current_role_index = int(current_role.name[6:])//10
        new_role_index = min(level//10,10)
        if new_role_index != current_role_index:
            guild = client.get_guild(server_id)
            role = nextcord.utils.get(guild.roles, name=level_roles[new_role_index])
            await add_role(member, role)
            await remove_role(member, current_role)

async def init_user_level(cursor, member : nextcord.Member):
    cursor.execute('SELECT * FROM levels WHERE user = ?', (member.id,))
    entry = cursor.fetchone()
    if entry is not None:
        await update_level_role(cursor, member)
        return False
    else:
        t = int(time())
        bag = json.dumps({})
        buffs = json.dumps({'disable':t})
        debuffs = json.dumps({'last_xp_s': t, 'move_cd': t})
        cursor.execute('INSERT INTO levels (user, level, total_xp, bag, buffs, debuffs) VALUES (?, ?, ?, ?, ?, ?)', (member.id, 1, 0, bag, buffs, debuffs))
        await update_level_role(cursor, member)
        return True
    
async def sendLevelUpMessage(user : nextcord.Member, newLevel, rewards):
    bot_commands = client.get_channel(bot_commands_id)
    emote_guild = client.get_guild(emote_server_id)
    description = 'Rewards'
    for k,v in rewards.items():
        description += '\n'
        if k == 'money':
            description += f'${v:,}'
        else:
            emoji = nextcord.utils.get(emote_guild.emojis, name=k.lower().replace(' ', '_'))
            if emoji:
                description += f'{emoji} x{v}\t`{k}`'
            else:
                description += f'{k} x{v}'
    embed = nextcord.Embed(title=f'{user.display_name} leveled up to level {newLevel:.0f}!',
                            description=description, color=user.color)
    embed.set_thumbnail(url=user.display_avatar.url)
    await bot_commands.send(embed=embed)

async def addXP(cursor, user : nextcord.Member, xp=0, message=False):
    cursor.execute('SELECT level, total_xp FROM levels WHERE user = ?', (user.id,))
    info_tuple = cursor.fetchone()
    if info_tuple is None:
        if await init_user_level(user):
            info_tuple = (1, 0)
        else:
            return
    if message:
        cursor.execute('SELECT debuffs FROM levels WHERE user = ?', (user.id,))
        debuffs = json.loads(cursor.fetchone()[0])
        last_xp_s = debuffs.get('last_xp_s')
        current_time = int(time())
        cursor.execute('SELECT held_item FROM levels WHERE user = ?', (user.id,))
        mult = info_tuple[0] * 1.1
        if cursor.fetchone()[0] == 'lucky_egg':
            mult *= 2
        xp = getXPToAdd(last_xp_s, current_time, mult)
    if xp > 0:
        totalxp = info_tuple[1] + xp
        newlevel = int(np.floor(np.cbrt(totalxp)))
        if message:
            debuffs['last_xp_s'] = current_time
            cursor.execute('UPDATE levels SET level = ?, total_xp = ?, debuffs = ? WHERE user = ?', (newlevel, totalxp, json.dumps(debuffs), user.id))
        else:
            cursor.execute('UPDATE levels SET level = ?, total_xp = ? WHERE user = ?', (newlevel, totalxp, user.id))
        if newlevel > info_tuple[0]:
            cursor.execute('SELECT held_item from levels WHERE user = ?', (user.id,))
            rewards = get_levelup_rewards(info_tuple[0], newlevel)
            if cursor.fetchone()[0] == 'amulet_coin':
                rewards['money'] *= 2
            give_item(cursor, user, rewards)
            await update_level_role(cursor, user)
            await sendLevelUpMessage(user, newlevel, rewards)

def getXPToAdd(last_xp_s : int, current_time : int, mult : float):
    time_elapsed = current_time - last_xp_s
    base = time_elapsed//60 if time_elapsed < 300 else int(min(10, time_elapsed//360))
    return int(np.round(base*mult))

async def generate_leaderboard(leaderboard_list : list):
    image_path = 'data/images/leaderboard.png'
    length = len(leaderboard_list)
    image = Image.new('RGBA', (680, length*70+(length-1)*5), color = (0,0,0,0))
    draw = ImageDraw.Draw(image)

    for i in range(length):
        user_id, level = leaderboard_list[i]
        guild = client.get_guild(server_id)
        member = guild.get_member(user_id)

        draw.rectangle((0, i*75, 680, i*75+70), fill='black')
        font = ImageFont.truetype('calibrib.ttf', size=40)
        text = f'#{i+1}'
        _, _, t, b = font.getbbox(text)
        w = font.getlength(text)
        h = t-b
        draw.text((80 + (70-w)//2, (i*75) + (50-h)//2), text, fill='#394173', font=font)
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
        _, _, t, b = font.getbbox(member_text)
        w = font.getlength(member_text)
        h = t-b
        draw.text((170, (i*75) + (90-h)//2), member_text, fill=color, font=font)
        
        font = ImageFont.truetype('calibri.ttf', size=30)
        level_text = f'Level: {level}'
        _, _, t, b = font.getbbox(level_text)
        w = font.getlength(level_text)
        h = t-b
        draw.text((520, (i*75) + (70-h)//2), level_text, fill='#5A6A9C', font=font)
    image.save(image_path)

def format_item(item_name : str):
    tokens = item_name.split('_')
    formatted = []
    for token in tokens:
        if token in ['xp', 'xs', 'xl']:
            formatted.append(token.upper())
        else:
            formatted.append(token.capitalize())
    return ' '.join(formatted)

def formalize_item(item_name : str):
    return item_name.strip().lower().replace(' ', '_')

def normalize_item(item_name : str):
    return item_name.strip().lower().replace(' ', '').replace('_', '')

class WagerView(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @nextcord.ui.button(label="10%", style=nextcord.ButtonStyle.green)
    async def ten_button(self, button, interaction : nextcord.Interaction):
        self.value = 0.1
        self.stop()

    @nextcord.ui.button(label="25%", style=nextcord.ButtonStyle.blurple)
    async def twentyfive_button(self, button, interaction : nextcord.Interaction):
        self.value = 0.25
        self.stop()
    
    @nextcord.ui.button(label="50%", style=nextcord.ButtonStyle.blurple)
    async def fifty_button(self, button, interaction : nextcord.Interaction):
        self.value = 0.5
        self.stop()

    @nextcord.ui.button(label="100%", style=nextcord.ButtonStyle.danger)
    async def onehundred_button(self, button, interaction : nextcord.Interaction):
        self.value = 1
        self.stop()

async def thief(cursor, target : nextcord.Member=None, user : nextcord.Member=None, interaction : nextcord.Interaction=None):
    cursor.execute('SELECT money, held_item FROM levels WHERE user = ?', (target.id,))
    r = cursor.fetchone()
    target_money = r[0]
    target_item = r[1]
    if target_item == 'covert_cloak':
        return f'but {target.name} was protected by their Covert Cloak!'
    else:
        cursor.execute('SELECT money, held_item FROM levels WHERE user = ?', (user.id,))
        r = cursor.fetchone()
        user_money = r[0]
        user_item = r[1]
        stolen_money = min(int(max(random.normalvariate(0.3, 0.1),0.05)*target_money),target_money)
        cursor.execute('UPDATE levels SET money = ? WHERE user = ?', (target_money-stolen_money, target.id))
        received_money = stolen_money * 2 if user_item == 'amulet_coin' else stolen_money
        cursor.execute('UPDATE levels SET money = ? WHERE user = ?', (user_money+stolen_money, user.id))
        return f'{target.name} lost ${stolen_money} and {user.name} gained ${received_money}!'

async def knock_off(cursor, target : nextcord.Member=None, user : nextcord.Member=None, interaction : nextcord.Interaction=None):
    cursor.execute('SELECT held_item FROM levels WHERE user = ?', (target.id,))
    target_item = cursor.fetchone()[0]
    if target_item is None:
        return 'but it failed.'
    else:
        cursor.execute('UPDATE levels SET held_item = ? WHERE user = ?', (None, target.id,))
        return f'{target.name}\'s {format_item(target_item)} was knocked off!'

async def disable(cursor, target : nextcord.Member=None, user : nextcord.Member=None, interaction : nextcord.Interaction=None):
    cursor.execute('SELECT buffs, debuffs FROM levels WHERE user = ?', (target.id,))
    q = cursor.fetchone()
    buffs = json.loads(q[0])
    debuffs = json.loads(q[1])
    current_time = time()
    if current_time < buffs.get('disable'): #immune to disable
        return f'but {target.name} is immune.'
    print(buffs)
    print(debuffs)
    buffs['disable'] = int(current_time + 7*24*60*60)
    debuffs['move_cd'] = int(current_time + 24*60*60)
    cursor.execute('UPDATE levels SET buffs = ?, debuffs = ? WHERE user = ?', (json.dumps(buffs), json.dumps(debuffs), target.id))
    return f'{target.name}\'s moves have been disabled for 24 hours!'

async def pay_day(cursor, target : nextcord.Member=None, user : nextcord.Member=None, interaction : nextcord.Interaction=None):
    cursor.execute('SELECT money, held_item FROM levels WHERE user = ?', (user.id,))
    money, held_item = cursor.fetchone()
    
    view = WagerView()
    message = await interaction.response.send_message(f'Choose your wager amount! (total bank: ${money})', view=view, ephemeral=True)
    await view.wait()
    percent = view.value
    wager = int(money*percent)
    await message.edit(content=f'Amount wagered: {int(percent*100)}% (${wager})', view=None)
    r = random.random()
    net = 0
    if held_item == 'loaded_dice':
        r *= 2
    if r < 0.3:
        net = wager * 0.5
    elif r < 0.6:
        net = wager * 1.1
    elif r < 0.8:
        net = wager * 1.3
    elif r < 0.9:
        net = wager * 1.5
    elif r < 1:
        net = wager * 2
    else:
        net = wager*(4+(r-1))
        net -= wager
        net = int(net)
        return f'JACKPOT!!!\n {user.name} earned ${net}!'
    if held_item == 'amulet_coin':
        net *= 2
    net -= wager
    net = int(net)
    if net >= 0:
        return f'{user.name} earned ${net}!'
    else:
        return f'{user.name} lost ${abs(net)}'

async def use_move(cursor, move : str, user : nextcord.Member, target : nextcord.Member, interaction : nextcord.Interaction):
    move = search_list(valid_moves, move)
    if move:
        q = remove_item(cursor, user, {move: 1})
        if q == 0:
            return format_item(move), None
        if target is not None:
            cursor.execute('SELECT held_item FROM levels WHERE user = ?', (target.id,))
            if cursor.fetchone()[0] == 'bright_powder' and random.random() > 0.9:
                return format_item(move), 'but it missed.'
        return format_item(move), await globals()[move](cursor, target, user, interaction)
    else:
        return None, None

def seconds_to_hms(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return hours, minutes, seconds

def update_database(db):
    db.commit()