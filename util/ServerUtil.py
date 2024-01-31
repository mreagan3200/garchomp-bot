import asyncio
import logging
import os
import psutil
import subprocess

async def send_message(message):
    try:
        reader, writer = await asyncio.open_connection('127.0.0.1', 8888)
        writer.write(message.encode())
        await writer.drain()

        data = await reader.read(100)
        response = data.decode()
        writer.close()
        await writer.wait_closed()
        return response
    except ConnectionRefusedError as e:
        log_filename = 'logs/client_errors.log'
        if not os.path.exists(log_filename):
            open(log_filename, 'a').close()
        logging.basicConfig(filename=log_filename, level=logging.ERROR, 
                            format='%(asctime)s - %(levelname)s - %(message)s')
        logging.error(f'Failed to connect to server: {e}')

async def shut_down():
    try:
        pid_to_terminate = int(await send_message('getpid'))
        process = psutil.Process(pid_to_terminate)
        process.terminate()

        print(f"Terminated process with PID {pid_to_terminate}")
    except psutil.NoSuchProcess:
        print(f"No such process with PID {pid_to_terminate}")
    except psutil.AccessDenied:
        print(f"Permission denied to terminate process with PID {pid_to_terminate}")

async def start_bot(bot_command):
    try:
        subprocess.Popen(bot_command, shell=True)
    except subprocess.CalledProcessError as e:
        if e.returncode != 15:
            print(f"Error restarting the bot: {e}")