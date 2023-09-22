import nextcord
from nextcord.ext import commands
from typing import Optional

import json
import sqlite3

from util.DataUtil import *
from util.RolesUtil import administrator_command_executed
import shared

'''amulet coin, exp share, '''

def shopEmbed(pageNum=1):
    data = DataUtil('data/data.json').load()
    description = ''
    client = shared.client
    inventory = data.get('shop_inventory')
    emote_server = data.get('emote_server_id')
    emote_guild = client.get_guild(emote_server)
    page = inventory.get(f'{pageNum}')
    title = page.get('title')
    if page:
        for item in page.get('items'):
            name = item.get('name')
            price = item.get('price')
            desc = item.get('desc')
            if title == 'TMs':
                emoji = nextcord.utils.get(emote_guild.emojis, name='tm')
            else:
                emoji = nextcord.utils.get(emote_guild.emojis, name=name)
            if emoji:
                description += f'${price} {emoji} `{modify_string(name)}` {desc}\n'
            else:
                description += f'${price} `{modify_string(name)}` {desc} \n'
    embed = nextcord.Embed(title=title, description=description, color=nextcord.Colour(int(page.get('color')[1:], 16)))
    embed.set_footer(text=f'{pageNum}/{len(inventory)}')
    return embed

def modify_string(input_str):
    words = input_str.split('_')
    modified_words = []
    for word in words:
        if word.lower() in ('xp', 'xs', 'xl'):
            modified_words.append(word.upper())
        else:
            modified_words.append(word.capitalize())
    result_str = ' '.join(modified_words)
    return result_str

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
        self.db = sqlite3.connect('data/bot_data.db')

    @nextcord.slash_command(guild_ids=[1093195040320389200], description='View shop items.')
    async def shop(self, interaction : nextcord.Interaction):
        ui = ShopUI()
        embed = shopEmbed()
        await interaction.response.send_message(embed=embed, view=ui)

    @nextcord.slash_command(guild_ids=[1093195040320389200], description='Add an item to the shop. Must be an administrator to use.')
    async def addshopitem(self, interaction : nextcord.Interaction, name, price, desc, page):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You are not authorized to run this command', ephemeral=True)
            return
        await administrator_command_executed(interaction)
        name = name.strip().lower().replace(' ', '_')
        self.data = self.datautil.load()
        shop_inventory = self.data.get('shop_inventory')
        if not shop_inventory:
            shop_inventory = {}
        if not shop_inventory.get(page):
            shop_inventory[page] = {'items':[], 'title':'', 'color':'#000000'}
        shop_inventory[page]['items'].append({'name':name, 'price':price, 'desc':desc})
        self.datautil.updateData({'shop_inventory':shop_inventory})
        await interaction.response.send_message(f'{name} added to page {page}', ephemeral=True)
    
    @nextcord.slash_command(guild_ids=[1093195040320389200], description='Delete an item from the shop. Must be an administrator to use.')
    async def removeshopitem(self, interaction : nextcord.Interaction, name, page):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You are not authorized to run this command', ephemeral=True)
            return
        await administrator_command_executed(interaction)
        self.data = self.datautil.load()
        shop_inventory = self.data.get('shop_inventory')
        if not shop_inventory or not shop_inventory.get(page):
            await interaction.response.send_message('Invalid request', ephemeral=True)
            return
        name = name.strip().lower().replace(' ', '_')
        shop_page = shop_inventory.get(page)
        updated_list = [item for item in shop_page.get('items') if item.get('name').lower().replace(' ', '_') != name]
        if len(updated_list) == 0:
            del shop_inventory[page]
        else:
            shop_page['items'] = updated_list
        self.datautil.updateData({'shop_inventory':shop_inventory})
        await interaction.response.send_message(f'{name} removed from page {page}', ephemeral=True)
    
    @nextcord.slash_command(guild_ids=[1093195040320389200], description='Edit the shop. Must be an administrator to use.')
    async def editshop(self, interaction : nextcord.Interaction, key, value, page, name : Optional[str] = nextcord.SlashOption(required=False)):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You are not authorized to run this command', ephemeral=True)
            return
        await administrator_command_executed(interaction)
        self.data = self.datautil.load()
        shop_inventory = self.data.get('shop_inventory')
        if not shop_inventory or not shop_inventory.get(page):
            await interaction.response.send_message('Invalid request', ephemeral=True)
            return
        key = key.lower()
        if key in ('title', 'color'):
            shop_inventory.get(page)[key] = value
        elif key in ('name', 'price', 'desc'):
            if name is None:
                await interaction.response.send_message('Invalid request', ephemeral=True)
                return
            name = name.strip().lower().replace(' ', '_')
            found = False
            for item in shop_inventory.get(page).get('items'):
                if item.get('name').lower().replace(' ', '_') == name:
                    item[key] = value
                    found = True
            if not found:
                await interaction.response.send_message('Item not found', ephemeral=True)
                return
        else:
            await interaction.response.send_message('Invalid key', ephemeral=True)
            return
        self.datautil.updateData({'shop_inventory':shop_inventory})
        await interaction.response.send_message(f'{key} updated to {value}', ephemeral=True)

    @nextcord.slash_command(guild_ids=[1093195040320389200], description='Purchase an item from the shop!')
    async def buy(self, interaction : nextcord.Interaction, item_name : Optional[str] = nextcord.SlashOption(required=True, description='name of the item to be purchased'), quantity : Optional[int] = nextcord.SlashOption(required=False, description='number of items to purchase')):
        if not quantity:
            quantity = 1
        if quantity < 1:
            await interaction.response.send_message('invalid quantity', ephemeral=True)
            return
        item_name = item_name.strip().lower().replace(' ', '_')
        self.data = self.datautil.load()
        shop_inventory = self.data.get('shop_inventory')
        total = -1
        for key in shop_inventory.keys():
            value = shop_inventory.get(key)
            for item in value.get('items'):
                if item.get('name').strip().lower().replace(' ', '_') == item_name:
                    total = int(item.get('price'))*quantity
        if total < 0:
            await interaction.response.send_message('invalid item', ephemeral=True)
            return
        cursor = self.db.cursor()
        cursor.execute(f'SELECT money, {item_name} FROM bag WHERE user = ?', (interaction.user.id,))
        result = cursor.fetchone()
        money = result[0]
        item_q = result[1]
        if money < total:
            await interaction.response.send_message('you don\'t have enough money to buy that', ephemeral=True)
            cursor.close()
            return
        view = ConfirmView()
        await interaction.response.send_message(f'Are you sure you would like to buy `{modify_string(item_name)}` x{quantity} for `${total}`?', view=view, ephemeral=True)
        await view.wait()
        if view.value == True:
            cursor.execute('UPDATE bag SET money = ? WHERE user = ?', (money-total, interaction.user.id))
            cursor.execute(f'UPDATE bag SET {item_name} = ? WHERE user = ?', (item_q+quantity, interaction.user.id))
            self.db.commit()
        cursor.close()

    @nextcord.slash_command(guild_ids=[1093195040320389200], description='Sell items from your bag. Items sell for 25% of their purchase price. Rare candies cannot be sold.')
    async def sell(self, interaction : nextcord.Interaction, item_name : Optional[str] = nextcord.SlashOption(required=True, description='name of the item to be sold'), quantity : Optional[int] = nextcord.SlashOption(required=False, description='number of items to sell')):
        item_name = item_name.strip().lower().replace(' ', '_')
        if item_name == 'rare_candy':
            await interaction.response.send_message('invalid item', ephemeral=True)
            return
        if not quantity:
            quantity = 1
        if quantity < 1:
            await interaction.response.send_message('invalid quantity', ephemeral=True)
            return
        self.data = self.datautil.load()
        shop_inventory = self.data.get('shop_inventory')
        total = -1
        for key in shop_inventory.keys():
            value = shop_inventory.get(key)
            for item in value.get('items'):
                if item.get('name').strip().lower().replace(' ', '_') == item_name:
                    total = int(int(item.get('price'))*quantity*0.25)
        if total < 0:
            await interaction.response.send_message('invalid item', ephemeral=True)
            return
        cursor = self.db.cursor()
        cursor.execute(f'SELECT money, {item_name} FROM bag WHERE user = ?', (interaction.user.id,))
        result = cursor.fetchone()
        money = result[0]
        item_q = result[1]
        if quantity > item_q:
            await interaction.response.send_message(f'you do not have enough {modify_string(item_name)} to sell', ephemeral=True)
            cursor.close()
            return
        view = ConfirmView()
        await interaction.response.send_message(f'Are you sure you would like to sell `{modify_string(item_name)}` x{quantity} for `${total}`?', view=view, ephemeral=True)
        await view.wait()
        if view.value == True:
            cursor.execute('UPDATE bag SET money = ? WHERE user = ?', (money+total, interaction.user.id))
            cursor.execute(f'UPDATE bag SET {item_name} = ? WHERE user = ?', (item_q-quantity, interaction.user.id))
            self.db.commit()
        cursor.close()

    def __del__(self):
        self.db.close()

def setup(client : nextcord.Client):
    client.add_cog(Shop(client))