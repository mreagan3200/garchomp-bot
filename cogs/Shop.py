import nextcord
from nextcord.ext import commands
from typing import Optional
import sqlite3

from util.DataUtil import *
from util.RolesUtil import *
import shared

''' 
Pay Day, Lock On, Trick
'''

class DBConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBConnection, cls).__new__(cls)
            cls._instance.db = sqlite3.connect('data/bot_data.db')
        return cls._instance

    def __del__(self):
        self.db.close()

def shopEmbed(pageNum=1):
    conn = DBConnection()
    description = ''
    client = shared.client
    emote_guild = client.get_guild(emote_server_id)
    cursor = conn.db.cursor()
    cursor.execute('SELECT title, color FROM shopdata WHERE page = ?', (pageNum,))
    title, color = cursor.fetchone()
    cursor.execute('SELECT COUNT(*) FROM shopdata')
    length = cursor.fetchone()[0]
    if title.startswith('XP'):
        cursor.execute('SELECT name, price, desc FROM shop WHERE page = ? ORDER BY price ASC', (pageNum,))
    else:
        cursor.execute('SELECT name, price, desc FROM shop WHERE page = ? ORDER BY name ASC', (pageNum,))
    for row in cursor.fetchall():
        name, price, desc = row
        if title == 'TMs':
            emoji = nextcord.utils.get(emote_guild.emojis, name='tm')
        else:
            emoji = nextcord.utils.get(emote_guild.emojis, name=name.lower().replace(' ', '_'))
        if emoji:
            description += f'${price} {emoji} `{format_item(name)}` {desc}\n'
        else:
            description += f'${price} `{format_item(name)}` {desc} \n'
    cursor.close()
    color = int(color.hex(), 16) if type(color) == bytes else int(color)
    embed = nextcord.Embed(title=title, description=description, color=nextcord.Colour(color))
    embed.set_footer(text=f'{pageNum}/{length}')
    return embed

class ShopUI(nextcord.ui.View):
    def __init__(self):
        super().__init__()
    
    @nextcord.ui.button(label='⬅️', style=nextcord.ButtonStyle.blurple)
    async def prev(self, button : nextcord.ui.Button, interaction : nextcord.Interaction):
        footer_text = interaction.message.embeds[0].footer.text
        current_page = int(footer_text[:footer_text.find('/')])
        if current_page > 1:
            await interaction.message.edit(embed=shopEmbed(pageNum=current_page-1))

    @nextcord.ui.button(label='➡️', style=nextcord.ButtonStyle.blurple)
    async def next(self, button : nextcord.ui.Button, interaction : nextcord.Interaction):
        footer_text = interaction.message.embeds[0].footer.text
        slash = footer_text.find('/')
        current_page = int(footer_text[:slash])
        total_pages = int(footer_text[slash+1:])
        if current_page < total_pages:
            await interaction.message.edit(embed=shopEmbed(pageNum=current_page+1))

class ConfirmView(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @nextcord.ui.button(label="Yes", style=nextcord.ButtonStyle.success)
    async def yes_button(self, button, interaction : nextcord.Interaction):
        await interaction.edit(content='Action confirmed', view=None)
        self.value = True
        self.stop()

    @nextcord.ui.button(label="No", style=nextcord.ButtonStyle.danger)
    async def no_button(self, button, interaction : nextcord.Interaction):
        await interaction.edit(content='Action canceled', view=None)
        self.value = False
        self.stop()

class Shop(commands.Cog):
    def __init__(self, client : nextcord.Client):
        self.client = client
        self.datautil = DataUtil('data/data.json')
        self.data = self.datautil.load()
        conn = DBConnection()
        self.db = conn.db
        self.cursor = self.db.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS shop (name VARCHAR(30) UNIQUE, price SMALLINT, desc VARCHAR(60), page TINYINT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS shopdata (page TINYINT, title VARCHAR(30), color BINARY(3))')
    
    def get_item_and_price(self, item_name):
        item_name = normalize_item(item_name)
        self.cursor.execute('SELECT name, price FROM shop')
        for row in self.cursor.fetchall():
            if normalize_item(row[0]) == item_name:
                return row
        return None, None

    @nextcord.slash_command(guild_ids=[1093195040320389200], description='View shop items.')
    async def shop(self, interaction : nextcord.Interaction):
        ui = ShopUI()
        embed = shopEmbed()
        await interaction.response.send_message(embed=embed, view=ui)

    async def addshopitem(self, name, price, desc, page):
        message = ''
        name = formalize_item(name)
        try:
            self.cursor.execute('INSERT INTO shop (name, price, desc, page) VALUES (?, ?, ?, ?)', (name, price, desc, page))
            self.cursor.execute('SELECT COUNT(*) FROM shopdata WHERE page = ?', (page,))
            if self.cursor.fetchone()[0] == 0:
                self.cursor.execute('INSERT INTO shopdata (page, title, color) VALUES (?, ?, ?)', (page, 'title', 0))
            message = f'{format_item(name)} added to page {page}'
        except sqlite3.IntegrityError:
            message = f'{format_item(name)} already exists'
        finally:
            update_database(self.db)
        return message
    
    async def removeshopitem(self, name, page):
        message = ''
        name = formalize_item(name)
        self.cursor.execute('DELETE FROM shop WHERE name = ? AND page = ?', (name, page))
        if self.cursor.rowcount:
            self.cursor.execute('SELECT COUNT(*) FROM shop WHERE page = ?', (page,))
            if self.cursor.fetchone()[0] == 0:
                self.cursor.execute('DELETE FROM shopdata WHERE page = ?', (page,))
            message = f'{format_item(name)} removed from page {page}'
        else:
            message = f'{format_item(name)} not found on page {page}'
        update_database(self.db)
        return message
    
    async def editshop(self, key, value, page, name=None):
        if key == 'title':
            self.cursor.execute(f'UPDATE shopdata SET title = ? WHERE page = ?', (value, page))
        elif key == 'color':
            self.cursor.execute(f'UPDATE shopdata SET color = UNHEX(?) WHERE page = ?', (value, page))
        elif key in ('name', 'price', 'desc'):
            if name is None:
                return 'Invalid request'
            name = formalize_item(name)
            self.cursor.execute(f'UPDATE shop SET {key} = ? WHERE name = ? AND page = ?', (value, name, page))
        else:
            return 'Invalid key'
        if self.cursor.rowcount:
            update_database(self.db)
            return f'{key} updated to {value}'
        else:
            return 'Item not found'

    @nextcord.slash_command(guild_ids=[1093195040320389200], description='Purchase an item from the shop!')
    async def buy(self, interaction : nextcord.Interaction, item_name : Optional[str] = nextcord.SlashOption(required=True, description='name of the item to be purchased'), quantity : Optional[int] = nextcord.SlashOption(required=False, description='number of items to purchase')):
        if not quantity:
            quantity = 1
        if quantity < 1:
            await interaction.response.send_message('invalid quantity', ephemeral=True)
            return
        item_name = normalize_item(item_name)
        item_name, price = self.get_item_and_price(item_name)
        if item_name is None or price is None:
            await interaction.response.send_message('invalid item', ephemeral=True)
            return
        total = price*quantity
        self.cursor.execute(f'SELECT money FROM levels WHERE user = ?', (interaction.user.id,))
        result = self.cursor.fetchone()
        money = result[0]
        if money < total:
            await interaction.response.send_message(f'You don\'t have enough money to buy {format_item(item_name)}', ephemeral=True)
            return
        view = ConfirmView()
        await interaction.response.send_message(f'Are you sure you would like to buy `{format_item(item_name)}` x{quantity} for `${total}`?', view=view, ephemeral=True)
        await view.wait()
        if view.value == True:
            give_item(self.cursor, interaction.user, {item_name: quantity})
            self.cursor.execute('UPDATE levels SET money = ? WHERE user = ?', (money-total, interaction.user.id))
            update_database(self.db)

    @nextcord.slash_command(guild_ids=[1093195040320389200], description='Sell items from your bag. Items sell for 25% of their purchase price. Rare candies cannot be sold.')
    async def sell(self, interaction : nextcord.Interaction, item_name : Optional[str] = nextcord.SlashOption(required=True, description='name of the item to be sold'), quantity : Optional[int] = nextcord.SlashOption(required=False, description='number of items to sell')):
        if item_name == 'rarecandy':
            await interaction.response.send_message('invalid item', ephemeral=True)
            return
        if not quantity:
            quantity = 1
        if quantity < 1:
            await interaction.response.send_message('invalid quantity', ephemeral=True)
            return
        item_name = normalize_item(item_name)
        item_name, price = self.get_item_and_price(item_name)
        if item_name is None or price is None:
            await interaction.response.send_message('invalid item', ephemeral=True)
            return
        total = (price*quantity)//4
        self.cursor.execute(f'SELECT money, {item_name} FROM bag WHERE user = ?', (interaction.user.id,))
        result = self.cursor.fetchone()
        money = result[0]
        bag = json.loads(result[1])
        if item_name in bag:
            item_q = bag[item_name]
        else:
            item_q = 0
        if quantity > item_q:
            await interaction.response.send_message(f'You don\'t have enough {format_item(item_name)} to sell', ephemeral=True)
            return
        view = ConfirmView()
        await interaction.response.send_message(f'Are you sure you would like to sell `{format_item(item_name)}` x{quantity} for `${total}`?', view=view, ephemeral=True)
        await view.wait()
        if view.value == True:
            bag[item_name] -= quantity
            self.cursor.execute('UPDATE levels SET money = ?, bag = ? WHERE user = ?', (money+total, json.dumps(bag), interaction.user.id))
            update_database(self.db)

    def __del__(self):
        pass

def setup(client : nextcord.Client):
    client.add_cog(Shop(client))