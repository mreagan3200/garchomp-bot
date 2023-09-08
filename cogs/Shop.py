import nextcord
from nextcord.ext import commands
from typing import Optional

import json
import sqlite3

from util.DataUtil import *
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
                emoji = nextcord.utils.get(emote_guild.emojis, name=name.strip().lower().replace(' ', '_'))
            if emoji:
                description += f'${price} {emoji} `{name}` {desc}\n'
            else:
                description += f'${price} `{name}` {desc} \n'
    embed = nextcord.Embed(title=title, description=description, color=nextcord.Colour(int(page.get('color')[1:], 16)))
    embed.set_footer(text=f'{pageNum}/{len(inventory)}')
    return embed

class ShopUI(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None
    
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

class Shop(commands.Cog):
    def __init__(self, client : nextcord.Client):
        self.client = client
        self.datautil = DataUtil('data/data.json')
        self.data = self.datautil.load()
        self.db = sqlite3.connect('data/bot_data.db')

    @nextcord.slash_command(guild_ids=[1093195040320389200])
    async def shop(self, interaction : nextcord.Interaction):
        ui = ShopUI()
        embed = shopEmbed()
        await interaction.response.send_message(embed=embed, view=ui)

    @nextcord.slash_command(guild_ids=[1093195040320389200])
    async def addshopitem(self, interaction : nextcord.Interaction, name, price, desc, page):
        self.data = self.datautil.load()
        shop_inventory = self.data.get('shop_inventory')
        if not shop_inventory:
            shop_inventory = {}
        if not shop_inventory.get(page):
            shop_inventory[page] = {'items':[]}
        shop_inventory[page]['items'].append({'name':name, 'price':price, 'desc':desc})
        self.datautil.updateData({'shop_inventory':shop_inventory})
        await interaction.response.send_message('done', ephemeral=True)

    @nextcord.slash_command(guild_ids=[1093195040320389200])
    async def buy(self, interaction : nextcord.Interaction, item_name, quantity : Optional[int] = nextcord.SlashOption(required=False)):
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
            return
        cursor.execute('UPDATE bag SET money = ? WHERE user = ?', (money-total, interaction.user.id))
        cursor.execute(f'UPDATE bag SET {item_name} = ? WHERE user = ?', (item_q+quantity, interaction.user.id))
        self.db.commit()
        cursor.close()
        await interaction.response.send_message('done', ephemeral=True)

    def __del__(self):
        self.db.close()

def setup(client : nextcord.Client):
    client.add_cog(Shop(client))