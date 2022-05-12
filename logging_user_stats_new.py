import requests

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


def cache(url, path, force):
    # returns data, and if asked remote
    if force or not os.path.isfile(path):
        p = sget(url)
        check_login(p, '{}\n{}\{}'.format(url, path, force))
        
        with open(path, 'w', encoding='utf8') as fh:
            fh.write(p.text)
            fh.close()
        
        return (p.text, True)
    
    else:
        return (read_file(path), False)


def rip_info(user):
    fn = 'userstats/h/user_{}.html'.format(user)
    with open(fn, 'r', encoding='utf8') as hfile:
        hdoc = hfile.read()
        hfile.close()
    
    data = {}
    
    data['_meta_filedate'] = os.path.getmtime(fn)
    
    # registered date
    tmp = get_prop('userpage-flex-item username">', hdoc, t='</div')
    
    if '"hideonmobile">' in tmp:
        data['user_title'] = get_prop('font-small">', tmp, t='<span ').strip()
    
    tmp = get_prop('Member Since:', tmp, t='</').strip()
    data['registered'] = strdate(tmp).timestamp()
    
    # stats
    for tmp in hdoc.split('<span class="highlight">')[1:]:
        thing, value = tmp[:40].lower().split('</span>')
        if thing.endswith(':'):thing = thing[:-1]
        value = value.split('<br')[0].strip()
        if value.isdigit():value = int(value)
        thing = thing.replace(' ', '_')
        data[thing] = value

    # accpeting commisions / trades
    for tmp in hdoc.split('userpage-profile-question"><strong class="highlight">')[1:]:
        thing, value = tmp[:90].lower().split('</strong></div>')
        value = value.split('<')[0].strip()
        value = value == 'yes'
        thing = thing.replace(' ', '_')
        data[thing] = value
    
    return data


def rip_new_users():
    douser = []

    for i in sorted(os.listdir('userstats/h')):
        if i.startswith('user_'):
            i = i[5:-5]
            if len(i) < 3:continue
            douser.append(i)
    
    c = 0
    outd = {}
    
    for u in douser:
        
        try:
            d = rip_info(u)
        
        except Exception as e:
            apc_write(pp + 'apduserdata_error', {u: str(e)}, {}, 1, encoding='utf8', volsize=None)
            continue

        outd[u] = d
        c += 1
        if c % 500 == 0:
            logging.info(f'{c}\t{datetime.now()}')
            if outd:
                apc_write(pp + 'apduserdata', outd, None, 1, encoding='utf8', volsize=None)
                outd = {}
    
    if outd:
        logging.info(f'{c}\t{datetime.now()}')
        apc_write(pp + 'apduserdata', outd, None, 1, encoding='utf8', volsize=None)
        outd = {}
    

def add_dates():
    # because i forgot to
    udata = apc_master().read(pp + 'apduserdata', encoding='utf8')
    c = 0
    for user, data in udata.items():
        if '_meta_filedate' not in data:
            data['_meta_filedate'] = os.path.getmtime('userstats/h/user_{}.html'.format(user))
            c += 1
            apc_write(pp + 'apduserdata2', {user: data}, {}, 1, encoding='utf8', volsize=None)
            if c % 500 == 0:
                logging.info(f'{c}\t{datetime.now()}')
        else:
            apc_write(pp + 'apduserdata2', {user: data}, {}, 1, encoding='utf8', volsize=None)


def rip_userinfo(user):
    try:
        d = rip_info(user)
    
    except Exception as e:
        apc_write(pp + 'apduserdata_error',
                  {user: str(e)}, {}, 1, encoding='utf8', volsize=None)
        return False
    
    apc_write(pp + 'apduserdata', {user: d}, {}, 1, encoding='utf8', volsize=None)
    return True


def userinfostate(user, force=True):
    info = {
        'lastChk': datetime.now().isoformat()
        }
    asked = force
    logging.info(f'User: {user}')
    
    u = 'https://www.furaffinity.net/{}/{}/'
    urlser = user.replace('_', '')
    h = 'userstats/h/{}_{}.html'
    
    p, a = cache(
        u.format('user', urlser),
        h.format('user', user),
        force)
    
    user_count = -1
    if a and asked:
        user_count = get_prop(
            '<strong>registered',
            p, t='>,', o=0, u=-1).strip()
        
        if user_count.isdigit():
            user_count = int(user_count)
        
        else:
            if len(user_count) < 50:
                logging.warn(f'User count non digit! {user_count}')
            
            user_count = -1
            #user_count = 6969420
    
    asked = asked or a
    
    if '">Click here to go back' in p or '">Continue &raquo;</a>' in p:
        info['status'] = 'deactive'
        logging.info('Status: Deactivated')
        return info, asked, user_count
    
    elif '<title>System Error</title>' in p and 'This user cannot be found.' in p:
        info['status'] = 'unf'
        logging.info('Status: Not Found')
        user_count = 2
        return info, asked, user_count
    
    posts = int(get_prop('>Submissions:</span>', p, '<').strip())
    info['posts'] = posts
    logging.info(f'Posts: {posts:,}')
    
    if posts > 0:
        
        last_date = datetime(2000, 1, 1)
        
        upbox = 'uploaded: <span class="preview_date">'
        last_id = -1
        last_id_scrap = -1
        
        if upbox in p:
            last_id = int(get_prop('View Gallery', p, t='/"><').split('/')[-1])
            last_date = get_prop(upbox, p, '</span')
        
        p, a = cache(
            u.format('scraps', urlser),
            h.format('scraps', user),
            force)
        asked = asked or a
        
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
            
            last_date = get_prop('<span class="hideonmobile">posted </span>', p, t='</strong')
        
        last_date = fa_datebox(last_date)
        last_date = strdate(last_date)
        
        info['lastPostID'] = last_id
        info['lastPostDate'] = last_date.isoformat()
        logging.info(f'Last Post ID: {last_id}')
        logging.info(f'Last Post Date: {last_date}')
    
    else:
        logging.info('No Posts')
    
    return info, asked, user_count
    

def gather_stats(user, force=False):
    # returns if queried fa, and registered users
    
    info, asked, user_count = userinfostate(user, force)
    
    apc_write(pp + 'apduserstats', {user: info}, {}, 1, volsize=None)
    rip_userinfo(user)
    
    return (asked, user_count)


def aaa_shouldcheck(user, now, hp):
    data = apduserstats[user]
    last_chk = datetime.fromisoformat(data['lastChk'])
    
    diff = (now - last_chk).days
    # todo query fadsrv for last faved dates too
    
    if data.get('status', '') in ['deactive', 'unf']:
        if diff >= 60:
            return [40, diff, user]
        return [False]
    
    elif 'lastPostID' not in data:
        return [False]
    
    post_id = data['lastPostID']
    if post_id > hp:
        post = data['lastPostDate']
        post = datetime.fromisoformat(post)
    else:
        post = datetime(2020, 1, 1)
    
    days = (now - post).days
    cdays = max(min(7, days), 30)
    
    if diff >= cdays:
        return [days, diff, user]
    
    return [False]


def aaa():
    user_new = []
    user_update = []
    high_post = {}
    
    for user, posts in user_post.items():
        posts = [int(x) for x in posts if x.isdigit()]
        if len(posts) == 0:
            logging.info(f'No posts for {user}')
            continue
        high_post[user] = sorted(posts)[-1]
    
    now = datetime.now()
    
    for user in user_post:
        if user.startswith('@'):
            continue
        
        user = user.lower()
        if user in got_json:
            v = aaa_shouldcheck(
                user, now,
                high_post.get(user, 9**256))
            
            if v[0]:
                user_update.append(v)
        
        else:
            user_new.append(user)
    
    return user_new, user_update


def get_new_users(u):
    logging.info(f'Gather stats for {len(u):,} new users')
    for user in u:
        asked, user_count = gather_stats(user)
        
        if asked:# don't ping too frequent
            time.sleep(cfg['speed'])


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


def config_save():
    user_friendly_dict_saver(
        pp + 'userstatsoptions.json',
        cfg)


def configgy():
    global cfg, session, pp
    load_global('cfg', {
        'exitOnComplete': False,
        'apd_dir': 'data/',
        'poke_servers': {
            'FADSRV': {'port': 6970, 'post': 'findnew/user_stats'},
            },
        'speed': 1.5
        })
    
    pp = cfg['apd_dir']
    if not os.path.isdir(pp):
        os.mkdir(pp)
    
    load_global('cfg', 'userstatsoptions.json')
    config_save()
    
    cookies = read_secret(pp + 'secret.json')
    
    session = requests.Session()
    session.cookies.update(cookies)


def main():
    global apduserstats, got_json, user_post
    
    if not cfg['poke_servers']:
        logging.error('No servers to get users from.')
        return
    
    if not os.path.isdir('userstats/h'):
        os.makedirs('userstats/h')
    
    apduserstats = apc_master().read(pp + 'apduserstats', do_time=True)
    got_json = set(apduserstats.keys())
    
    default = list(cfg['poke_servers'])[0]
    default = cfg['poke_servers'][default]
    ip = default.get('ip', 'localhost')
    port = default.get('port', '6970')
    # get new users if i can
    logging.info('Calling server')
    dq = f'http://{ip}:{port}/data/'
    try:
        users = requests.get(dq + 'users/')
        works = users.status_code == 200

    except Exception as e:
        logging.error('FADSRV did not respond', exc_info=True)
        return
    
    user_post = users.json()
    
    user_new, user_update = aaa()
    logging.info(f'{len(user_new)} mew users')
    
    if user_new:
        try:
            get_new_users(user_new)
        except Exception as e:
            logging.error('Crash during check', exc_info=True)
            return


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
        
        logging.debug(f'Status: {x.status_code}')


if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    init_logger('user_stats_new', disp=':' in code_path)
    
    configgy()
    main()
    
    logging.info('Done!')
    
    poke_servers()
