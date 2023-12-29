# script to get users who are watching you and make/modify a collection

import requests
import shutil

from onefad import *

def sget(url, d=0):
    #logging.debug(f'Retrieving {url}')
    sg = session.get(url)
    if sg.status_code == 502:
        logging.info(f'Server gave 502, waiting ({url})')
        time.sleep(10)
        return sget(url, d=d+1)
    
    #logging.debug(f'Got {url}')
    return sg


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


def configgy():
    global cfg, session
    load_global('cfg', {
        'username': '',
        'exitOnComplete': False,
        'apd_dir': 'data/',
        'data_store': {
            'pm/':  {'mode': 'split'}
            },
        'post_store': {
            'im/': {'mode': 'split'}
            },
        'poke_servers': {
            'FADSRV': {'port': 6970, 'post': 'findnew'}
            },
        'speed': 1.5,
        "squash_server": ""
        })
    
    pp = cfg['apd_dir']
    if not os.path.isdir(pp):
        os.mkdir(pp)
    
    load_global('cfg', 'grabpostoptions.json')
    #config_save()

    if not cfg['username']:
        logging.error('Set the username in the config')
        prompt_exit()
    
    cookies = read_secret(pp + 'secret.json')
    if not cookies:
        prompt_exit()
    
    session = requests.Session()
    session.cookies.update(cookies)


def poke_servers():
    logging.info('Notifying servers')
    for k, v in cfg['poke_servers'].items():
        logging.info(k)
        path = v.get('path',
                     'http://{}:{}/{}/get_post'.format(
                         v.get('ip', '127.0.0.1'),
                         v['port'],
                         v.get('post', '')
                         )
                     )
        try:
            x = requests.post(path)
        
        except:
            logging.info('Offline.')
            continue
        
        logging.info(f'Status: {x.status_code}')


def get_watching(user):
    page = 1
    count = 200
    users = set()
    while count >= 200:
        count = 0
        logging.info(f'Page {page}')
        sg = sget(f'https://www.furaffinity.net/watchlist/to/{user}/{page}')
        d = sg.text
        
        if '<a href="/user/' not in d:
            break
        
        for i in d.split('<a href="/user/')[1:]:
            i = i.split('/')[0]
            users.add(i)
            count += 1
        
        logging.info(f'Count: {count}')
        page += 1
    
    return users


def main():
    users = set()
    for acc in ['codedcells', 'codedsmells', 'bonussells', 'cells', 'polycells', 'boidd']:
        users.update(get_watching(acc))
    
    if not users:
        logging.warning('No users, quitting')
        prompt_exit()
    
    logging.info('Preparing output')
    outbuf = '\nWatcher\t'
    outbuf += json.dumps({
        "modified": int(datetime.now().timestamp()*1000),
        "icon": [4, 5],
        "items": list(users),
        "lock": True
        })
    
    logging.info('Appending output')
    with open('data_mark/ds_groups', 'a') as fh:
        fh.write(outbuf)
        fh.close()
    
    logging.info('Saved')


def prompt_exit():
    if user_control:
        input('\nTerminating')
    
    exit()

if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    user_control = ':' in code_path
    init_logger('get_watching_users', disp=user_control)
    
    configgy()
    main()
    
    logging.info('Done!')
    
    poke_servers()
