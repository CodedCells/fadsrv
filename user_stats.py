import os
import shutil
import requests
import json
import time
from datetime import datetime

from fad_utils import *

port = '6970'

if os.path.isfile('data/secret.json'):
    try:
        cookies = read_json('data/secret.json')
    except Exception as e:
        input('secret json error ' + str(e))
        exit()
else:
    input('secret missing')
    exit()


session = requests.Session()
session.cookies.update(cookies)
'''
# quick login check
x = session.get('https://www.furaffinity.net/view/34445360/')
check_login(x.text, 'Start')
del x
'''

def cache(url, path, force):
    # returns data, and if asked remote
    if force or not os.path.isfile(path):
        p = session.get(url)
        check_login(p, '{}\n{}\{}'.format(url, path, force))
        with open(path, 'w', encoding='utf8') as fh:
            fh.write(p.text)
            fh.close()
        return (p.text, True)
    
    else:
        return (read_file(path), False)

deactivated = []
def gather_stats(user, force=False):
    asked = force
    
    print(user.rjust(30), end='\t')
    u = 'https://www.furaffinity.net/{}/{}/'
    urlser = user.replace('_', '')
    h = 'userstats/h/{}_{}.html'
    p, a = cache(
        u.format('user', urlser),
        h.format('user', user),
        force)
    asked = asked or a
    
    if '">Click here to go back' in p or '">Continue &raquo;</a>' in p:
        deactivated.append(user)
        return
    
    posts = int(get_prop('>Submissions:</span>', p, '<').strip())
    print('{:,}'.format(posts).rjust(6), end='\t')
    
    if posts == 0:
        print('')
        return asked
    
    last_date = datetime(2000, 1, 1)
    upbox = 'uploaded: <span class="preview_date"><span title="'
    last_id = -1
    if posts > 0 and upbox in p:
        last_id = int(get_prop('View Gallery', p, t='/"><').split('/')[-1])
        last_date = get_prop(upbox, p, '<').split('"')[-1][1:].strip()
        last_date = strdate(last_date)
    
    p, a = cache(
        u.format('scraps', urlser),
        h.format('scraps', user),
        force)
    asked = asked or a
    
    last_id_scrap = -1
    if '<a href="/view/' in p:
        last_id_scrap = int(get_prop('<a href="/view/', p, t='/'))
    
    if last_id_scrap > last_id:
        last_id = last_id_scrap
        p = 'p/{}_desc.html'.format(last_id)
        if os.path.isfile(p):
            p = read_file(p)
        else:
            p, a = cache(
                u.format('view', last_id),
                h.format('view', last_id),
                force)
            asked = asked or a
        
        last_date = get_prop('popup_date">', p, t='</')
        # MMM DDth, CCYY hh:mm AM
        last_date = strdate(last_date)
    
    info = {
        user: {
            'posts': posts,
            'lastPostDate': last_date.isoformat(),
            'lastPostID': last_id,
            'lastChk': datetime.now().isoformat()
            }
        }
    
    print(last_date)
    
    write_apd('data/apduserstats', info, {}, 1)
    return asked


apduserstats = read_apd('data/apduserstats', do_time=True)
got_json = set(apduserstats.keys())
deac = []


# get new users if i can
print('Calling server')
dq = 'http://127.0.0.1:{}/data/'
try:
    users = requests.get(dq.format(port) + 'users/')
    works = users.status_code == 200

except Exception as e:
    print('server error', e)
    works = False


user_new = []
user_update = []

if works:
    high_post = {}
    user_post = requests.get(dq.format(port) + 'userids/').json()
    for user, posts in user_post.items():
        high_post[user] = sorted([int(x) for x in posts if x.isdigit()])[-1]
    
    del user_post
    
    now = datetime.now()
    
    for user in users.json():
        
        if user.startswith('@'):
            continue
        
        user = user.lower()
        if user in got_json:
            
            data = apduserstats[user]
            last_chk = datetime.fromisoformat(data['lastChk'])
            
            diff = (now - last_chk).days
            # todo query fadsrv for last faved dates too
            
            if data.get('status', '') == 'deactive':
                continue
            
            post_id = data['lastPostID']
            if post_id > high_post.get(user, 9**256):
                post = data['lastPostDate']
                post = datetime.fromisoformat(post)
            else:
                post = datetime(2020, 1, 1)
            
            days = (now - post).days
            cdays = max(min(7, days), 40)
            
            if diff >= cdays:
                user_update.append((days, diff, user))
        
        else:
            user_new.append(user)

if len(user_new) > 0:
    print('\nGather stats for {:,} new users\n'.format(len(user_new)))
    for user in user_new:
        if gather_stats(user):
            # don't ping too frequent
            time.sleep(2)

# check up on old stats
if len(user_update) > 0:
    print('\nGather stats for {:,} users\n'.format(len(user_update)))
    for days, diff, user in sorted(user_update, reverse=True):
        print(diff, days, sep='\t', end='\t')
        gather_stats(user, force=True)
        time.sleep(2)

# user wants any?

while True:
    user = input('Name:').lower()
    if user == '':
        break
    
    gather_stats(user, force=True)
