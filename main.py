import datetime
import time
import json
import os
import re
import logging
from configparser import ConfigParser
from pathlib import Path
from loguru import logger
from telethon import TelegramClient
from aiohttp import web


logger.add('dev.log', rotation='1 MB', compression='zip')
file_conf = Path('config.ini')
conf = ConfigParser()
if not file_conf.exists():
    logger.error("Немає файлу конфгурацій!")
conf.read(file_conf.absolute())
tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
folder_losses = Path('losses_files')

if not folder_losses.exists():
    os.mkdir(folder_losses.absolute())
routes = web.RouteTableDef()
api_id = int(conf['Telegram']['app_id'])
name = conf['Telegram']['session_name']
api_hash = conf['Telegram']['app_hash']
client = TelegramClient(name, api_id, api_hash)



def get_time(dt: datetime) -> int:
    """ Повертає часову мітку у форматі секунд unix """
    d = dt.astimezone(tz).strftime('%d.%m.%Y %H:%M:%S')
    return int(time.mktime(time.strptime(d, "%d.%m.%Y %H:%M:%S")))



async def get_air_messages() -> list:
    limit = int(conf['Telegram']['limit_message'])
    buffer = []
    losses = []
    await client.start()
    async for message in client.iter_messages(conf['Telegram']['channel_air'], limit=limit):
        buffer.append({
            "date": get_time(message.date),
            "message": message.text
        })

    async for message in client.iter_messages('GeneralStaffZSU', limit=7):
        if message.photo and re.search(r'Загальні бойові втрати', message.text):
            file_path = folder_losses / str(str(get_time(message.photo.date)) + '.jpg')
            if not file_path.exists():
                path = await client.download_media(message.media, file_path.absolute())
            else:
                continue
            logger.debug(f"Send losses: {path}, to chat: {conf['Telegram']['losses_channel']}")
            await client.send_file(conf['Telegram']['losses_channel'], path, caption=message.text)
    # client.disconnect()
    return {"messages": buffer, "losses": losses}


@routes.get('/')
async def resp_air(request):
    js = await get_air_messages()
    # logger.debug('Response air')
    return web.json_response(js)


if __name__ == "__main__":
    app = web.Application()
    logger.debug("Сервер працює http://%s:%s" % (conf['Server']['host'], int(conf['Server']['port'])))
    app.add_routes(routes)
    web.run_app(app, port=int(conf['Server']['port']), host=conf['Server']['host'])
    
    

