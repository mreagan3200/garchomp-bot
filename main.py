import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv

import os
import signal
import asyncio
import sys

import shared

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if shared.client is None:
    i = nextcord.Intents.all()
    shared.client = commands.Bot(intents=i, activity=nextcord.Game(name='VGC'))

@shared.client.event
async def on_ready():
    print(f'Logged in as {shared.client.user}')

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
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Received Ctrl+C. Exiting gracefully...")
    finally:
        client = shared.client
        if client:
            print('closing client')
            loop.run_until_complete(shared.client.close())
    pass
    loop.close()