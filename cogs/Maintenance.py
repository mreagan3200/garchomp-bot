import nextcord
from nextcord.ext import commands

import os

class Mainenance(commands.Cog):
    def __init__(self, client : nextcord.Client):
        self.client = client
    
    async def dump_log_files(self):
        logs = os.listdir('./logs')
        mod_logs = self.client.get_guild(1093195040320389200).get_channel(1093921362961252372)
        for fileName in logs:
            message = fileName + '\n```'
            with open(f'logs/{fileName}', 'r') as log_file:
                message += log_file.read()
            message += '```'
            await mod_logs.send(message)
            os.remove(f'logs/{fileName}')
        if len(logs) == 0:
            await mod_logs.send('No errors or warnings to report for this week')

def setup(client : nextcord.Client):
    client.add_cog(Mainenance(client))