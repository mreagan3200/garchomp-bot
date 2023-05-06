import asyncio
import logging
import os

async def send_message(message):
    try:
        reader, writer = await asyncio.open_connection('127.0.0.1', 8888)
        print(f'Sending message to server: {message}')
        writer.write(message.encode())
        await writer.drain()

        data = await reader.read(100)
        response = data.decode()
        print(f'Response from server: {response}')

        writer.close()
        await writer.wait_closed()
    except ConnectionRefusedError as e:
        log_filename = 'logs/client_errors.log'
        if not os.path.exists(log_filename):
            open(log_filename, 'a').close()
        logging.basicConfig(filename=log_filename, level=logging.ERROR, 
                            format='%(asctime)s - %(levelname)s - %(message)s')
        logging.error(f'Failed to connect to server: {e}')

# Send a message from the client
asyncio.run(send_message('invoke_cog Birthdays check_birthdays'))