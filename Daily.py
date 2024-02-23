import asyncio
from util.ServerUtil import *

asyncio.run(send_message('invoke_cog ReactionRoles change_stellar_tera'))
asyncio.run(send_message('invoke_cog Birthdays check_birthdays'))
asyncio.run(send_message('invoke_cog Maintenance create_backup'))