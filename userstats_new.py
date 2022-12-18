from onefad import *
from fa_parser import *
import os
import json
import time
import requests
from datetime import datetime
from append_handler import appender


def process_user(user, page, mod=None):
    logging.debug(f'process user {user}')
    if mod == None:
        mod = int(datetime.now().timestamp())
    
    x = parse_userpage()
    x.loads(page)
    big = x.get_all()
    
    smol = {k: big[i] for k, i in [
        ('error', '_status'),
        ('title', 'user_title'),
        ('registered', 'registered_date'),
        ('posts', 'submissions'),
        ('faves', 'favs'),
        ] if i in big}
    
    if big.get('user_status', 'regular') != 'regular':
        smol['status'] = big['user_status']
    
    smol['_meta'] = mod
    for post, info in sorted(big.get('recent_posts', {}).items(), reverse=True):
        smol['new_post'] = info['upload_date']
        break
    
    return smol, big


def get_user(user):
    logging.info(f'get user {user}')
    page = session.get(f'http://www.furaffinity.net/user/{user}/')
    
    path = 'userstats/user/'
    if not os.path.isdir(path):
        os.makedirs(path)
    
    with open(f'{path}{user}.html', 'wb') as fh:
        fh.write(page.content)
        fh.close()
    
    smol, big = process_user(user, page.text)
    return smol


def read_secret(path):
    logging.info(f'Reading secret from {path}')
    if not os.path.isfile(path):
        logging.error('Secret File Missing')
        return None
    
    try:
        with open(path, 'r') as fh:
            cookies = json.load(fh)
            fh.close()
    
    except Exception as e:
        logging.error("Exception occurred", exc_info=True)

    if (isinstance(cookies.get('a'), str) and
        isinstance(cookies.get('b'), str)):
        return cookies
    
    logging.error('Secret File Incomplete, must have a and b cookies')
    return None


def main():
    global session
    init_logger('userstat', disp=True)
    
    cookies = read_secret('data/secret.json')
    if not cookies:
        exit()
    
    userstats = appender()
    userstats.read('data/userstats')
    
    session = requests.Session()
    session.cookies.update(cookies)
    
    users = requests.get('http://192.168.0.66:6970/data/users').json().keys()

    newusers = []
    
    for user in users:
        user = user.lower()
        if user in userstats:
            continue
        
        newusers.append(user)
    
    if not newusers:
        logging.info('No new users to get')
        return
    
    logging.info(f'Getting {len(newusers):,} new users')
    
    c = 0
    new = {}
    
    for user in newusers:
        if c:
            time.sleep(2)
        
        c += 1
        try:
            data = get_user(user)
        except Exception as e:
            logging.error(f"Error on {user}", exc_info=True)
            data = None
        
        if not data:
            continue
        
        userstats.write({user: data})
    
    logging.info('Finished getting')
    return len(newusers)


if __name__ == '__main__':
    work = main()
    logging.info('DOne')
