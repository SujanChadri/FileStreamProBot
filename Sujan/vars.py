# (c) Sujan
import os
from os import getenv, environ
from dotenv import load_dotenv

load_dotenv()

class Var(object):
    MULTI_CLIENT = False
    API_ID = int(getenv('API_ID', '0'))  #Required
    API_HASH = str(getenv('API_HASH', ' ')) #Required
    BOT_TOKEN = str(getenv('BOT_TOKEN', ' ')) #Required
    name = str(getenv('name', 'FileStreamBot')) #Optional
    SLEEP_THRESHOLD = int(getenv('SLEEP_THRESHOLD', '60')) #Leave as it is.
    WORKERS = int(getenv('WORKERS', '4')) #Leave as it is.
    BIN_CHANNEL = int(getenv('BIN_CHANNEL', '-1002337612955')) #Required
    PORT = int(getenv('PORT', '8080')) #Leave as it is.
    BIND_ADRESS = str(getenv('WEB_SERVER_BIND_ADDRESS', '0.0.0.0')) #Leave as it is.
    PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))  # 20 minutes
    OWNER_ID = set(int(x) for x in os.environ.get("OWNER_ID", "5123039648").split())  #Required
    NO_PORT = bool(getenv('NO_PORT', True)) #Leave as it is.
    APP_NAME = None
    OWNER_USERNAME = str(getenv('OWNER_USERNAME', 'Sujan_Ch')) #Required
    if 'DYNO' in environ:
        ON_HEROKU = True
        APP_NAME = str(getenv('APP_NAME')) #Your app name or Leave as it is.
    else:
        ON_HEROKU = False
        
    FQDN = str(getenv('FQDN', '0.0.0.0:3000')) if not ON_HEROKU or getenv('FQDN') else APP_NAME+'.herokuapp.com'
    HAS_SSL = getenv('HAS_SSL', 'True').lower() == 'true'
    
    # URL from ENV or Default based on SSL (same pattern as other variables)
    if HAS_SSL:
        URL = str(getenv('SERVER_URL', "https://{}/".format(FQDN)))
    else:
        URL = str(getenv('SERVER_URL', "http://{}/".format(FQDN)))
    
    # Ensure URL ends with /
    if not URL.endswith('/'):
        URL = URL + '/'
        
    DATABASE_URL = str(getenv('DATABASE_URL', '')) #Required
    
    # Multiple UPDATE CHANNELS Support - Comma separated channel usernames/IDs without @
    # Example: UPDATES_CHANNEL = "channel1,channel2,channel3" or "channel1" for single channel
    # Set to "None" to disable update channel check
    UPDATES_CHANNEL = str(getenv('UPDATES_CHANNEL', 'Sujan_Ch,Sujan_BotZ')) #Required without @
    
    # Parse multiple update channels into a list
    @classmethod
    def get_update_channels(cls):
        """Get list of update channels from comma-separated string"""
        if not cls.UPDATES_CHANNEL or cls.UPDATES_CHANNEL == "None":
            return []
        # Split by comma and strip whitespace
        channels = [ch.strip() for ch in cls.UPDATES_CHANNEL.split(',') if ch.strip()]
        return channels
    
    # Backward compatibility - single channel
    @classmethod
    def get_first_update_channel(cls):
        """Get first update channel for backward compatibility"""
        channels = cls.get_update_channels()
        return channels[0] if channels else None
    
    BANNED_CHANNELS = list(set(int(x) for x in str(getenv("BANNED_CHANNELS", "-1001362659779")).split())) #Leave as it is.
