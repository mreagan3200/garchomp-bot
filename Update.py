import os
import subprocess
import requests
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

from util.ServerUtil import *

load_dotenv()
GIT_TOKEN = os.getenv('GIT_TOKEN')

repo_owner = 'mreagan3200'
repo_name = 'garchomp-bot'
bot_command = 'python main.py'

headers = {'Authorization': f'token {GIT_TOKEN}'}
since_time = (datetime.now() - timedelta(days=2)).isoformat()

api_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/commits'

def check_for_changes():
    response = requests.get(api_url, headers=headers, params={'since':since_time})
    if response.status_code == 200:
        pr_data = response.json()
        return bool(pr_data)
    return False

async def update_and_restart_bot():
    try:
        subprocess.check_call(['git', 'pull', 'origin', 'main'])
    except subprocess.CalledProcessError as e:
        print(f"Error pulling updates: {e}")
        return
    await restart()

async def restart():
    await shut_down()
    await start_bot(bot_command)

async def main():
    if check_for_changes():
        await update_and_restart_bot()
    else:
        print("No changes found. Exiting.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass