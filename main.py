import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv
from typing import Optional

import os
import asyncio
import shared

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if shared.client is None:
    i = nextcord.Intents.all()
    shared.client = commands.Bot(intents=i)

@shared.client.event
async def on_ready():
    print(f'Logged in as {shared.client.user}')

@shared.client.slash_command(guild_ids=[1093195040320389200], description='Secret commands. Must be an administrator to use.')
async def command(interaction : nextcord.Interaction, command : str, args : Optional[str] = nextcord.SlashOption(required=False), member : Optional[nextcord.Member] = nextcord.SlashOption(required=False)):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('You are not authorized to run this command', ephemeral=True)
        return
    command = command.lower()
    args = args.lower()
    message = f'Invalid args: {str(args)}'
    args = [] if args is None else args.split(' ')
    match command:
        case 'addshopitem':
            if len(args) == 4:
                message = await getattr(shared.client.get_cog('Shop'), 'addshopitem')(*args)
        case 'editshop':
            if len(args) in [3,4]:
                message = await getattr(shared.client.get_cog('Shop'), 'editshop')(*args)
        case 'removeshopitem':
            if len(args) == 2:
                message = await getattr(shared.client.get_cog('Shop'), 'removeshopitem')(*args)
        case 'addxp':
            if len(args) == 1 and member is not None:
                message = await getattr(shared.client.get_cog('Level'), 'addxpcommand')(member, int(args[0]))
        case 'setxp':
            if len(args) == 1 and member is not None:
                message = await getattr(shared.client.get_cog('Level'), 'setxp')(member, int(args[0]))
        case 'changeminstars':
            if len(args) == 1:
                message = await getattr(shared.client.get_cog('Starboard'), 'changeminstars')(int(args[0]))
        case 'resetreactionroles':
            interaction.response.defer()
            await getattr(shared.client.get_cog('ReactionRoles'), 'resetreactionroles')()
            interaction.followup.send('done', ephemeral=True)
            return
        case 'restorebackup':
            message = await getattr(shared.client.get_cog('Maintenance'), 'restore_backup')()
        case _:
            message = f'Invalid command: {command}'
    await interaction.response.send_message(message, ephemeral=True)


async def invoke_cog(cogName, methodName):
    cog = shared.client.get_cog(cogName)
    if cog is not None:
        method = getattr(cog, methodName)
        await method()
    else:
        print('Could not find cog')

async def handle_client(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    message_tokens = str(message).split()
    if message_tokens[0] == 'invoke_cog' and len(message_tokens) == 3:
        await invoke_cog(message_tokens[1], message_tokens[2])
        writer.write(f"Command Executed: {message}".encode())
    elif message_tokens[0] == 'getpid':
        pid = os.getpid()
        writer.write(str(pid).encode())
    else:
        writer.write(f"Invalid Command: {message}".encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()

async def start_server():
    server = await asyncio.start_server(handle_client, '127.0.0.1', 8888)
    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

async def load_extensions():
    if not shared.loaded:
        for fileName in os.listdir('./cogs'):
            if fileName.endswith('.py'):
                initial_extensions.append(f'cogs.{fileName[:-3]}')
        shared.client.load_extensions(initial_extensions)
        ipc_task = asyncio.ensure_future(start_server())
        shared.loaded = True
        await asyncio.gather(main())

async def main():
    await load_extensions()
    await shared.client.start(TOKEN)

if __name__ == '__main__':
    initial_extensions = []
    loop = asyncio.get_event_loop()
    try:
        loop.create_task(main())
        loop.run_forever()
    except KeyboardInterrupt:
        print("Received Ctrl+C. Exiting gracefully...")
    finally:
        client = shared.client
        if client:
            print('closing client')
            loop.run_until_complete(shared.client.close())
    loop.close()