from onefad import *
from fa_parser import *
import os
import json
import time
import requests
from datetime import datetime
from append_handler import appender


online = 0

def process_user(user, page, mod=None):
    global online
    
    logging.debug(f'process user {user}')
    if mod == None:
        mod = int(datetime.now().timestamp())
    
    x = parse_userpage()
    x.loads(page)
    x.origin = 'web'
    big = x.get_all()
    
    if big.get('_online_users'):
        online = big['_online_users']
    
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
    page = session.get(f'https://www.furaffinity.net/user/{user}/')
    
    with open(f'userstats/user/{user}.html', 'wb') as fh:
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


def check_user(user, data, when):
    checked = data.get('_meta')
    if not checked:
        return 9999
    
    checked = datetime.fromtimestamp(checked)
    
    if data.get('error') == 'not_found':
        return
    
    new_post = data.get('new_post')
    days = (when - checked).days
    days = min(days, 48)
    if days < 14:
        return
    
    return days
    
    diff = 56
    if new_post:
        new_post = datetime.fromtimestamp(new_post)
        diff = abs(new_post - checked).days
    
    if diff > days:
        return diff - days


def should_check(users, when):
    check = []
    for user in users:
        data = userstats.get(user, {})
        priority = check_user(user, data, when)
        if priority is not None:
            check.append((priority, user))
    
    return {user: priority for priority, user in sorted(check, reverse=True)}


def main():
    global session, userstats, online
    init_logger('userstat_update', disp=True)
    
    cookies = read_secret('data/secret.json')
    if not cookies:
        exit()
    
    userstats = appender()
    userstats.read('data/userstats')
    
    session = requests.Session()
    session.cookies.update(cookies)
    
    users = requests.get('http://192.168.0.66:6970/data/users').json().keys()
    
    update = should_check(users, datetime.now())
    
    if not update:
        logging.info('No users to update')
        return
    
    work = len(update)
    logging.info(f'Updating {work:,} users')
    
    c = 0
    new = {}
    
    for user, d in update.items():
        if c:
            time.sleep(5)
        
        c += 1
        
        try:
            data = get_user(user)
        except:
            logging.warning(f'Error on {user}')
        
        if not data:
            continue
        
        userstats.write({user: data})
        
        if c % 500 == 0:
            logging.info(f'Updated {c:,} of {work:,}')
            if online > 10000:
                logging.info(f'Halting, {online:,} registerd users')
                break
    
    logging.info('Finished getting')
    return len(update)


if __name__ == '__main__':
    work = main()
    logging.info('Done')
