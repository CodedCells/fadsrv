import requests
from append_handler import *
from onefad import *
from fa_parser import *


def configgy(name):
    global cfg
    
    load_global('cfg', f'{name}_options.json')
    
    user_friendly_dict_saver(f'cfg/{name}_options.json', cfg)


def read_secret(path):
    logging.info(f'Reading secret from {path}')
    if not os.path.isfile(path):
        logging.error('Secret File Missing')
        return None
    
    try:
        cookies = read_json(path)
    
    except Exception as e:
        logging.error("Exception occurred", exc_info=True)


    if (isinstance(cookies.get('a'), str) and
        isinstance(cookies.get('b'), str)):
        return cookies
    
    logging.error('Secret File Incomplete, must have a and b cookies')
    return None


def session_create():
    global session
    
    cookies = read_secret(cfg['apd_dir'] + 'secret.json')
    if not cookies:
        prompt_exit()
    
    session = requests.Session()
    session.cookies.update(cookies)


def prompt_exit():
    if user_control:
        input('\nTerminating')
    
    exit()


def session_get(url, d=0):
    sg = session.get(url)
    if sg.status_code == 502:
        logging.info(f'Server gave 502, waiting ({url})')
        time.sleep(10)
        return sget(url, d=d+1)
    
    return sg


def autopath(v):
    return v.get('path',
        'http://{}:{}/{}'.format(
            v.get('ip', '127.0.0.1'),
            v['port'],
            v.get('post', '')
            )
        )


def poke_servers(poke):
    logging.info('Notifying servers')
    for k, v in poke.items():
        logging.info(k)
        path = autopath(v)
        
        try:
            x = requests.post(path)
        
        except:
            logging.info('Offline.')
            continue
        
        logging.info(f'Status: {x.status_code}')
