from stray_common import *


def relay(data):
    for k, v in cfg['relay_servers'].items():
        path = autopath(v)
        
        try:
            x = requests.post(path, data)
        
        except Exception as e:
            logging.error(f"Relay {k} exception", exc_info=True)


def process_user(user, page, mod=None):
    logging.debug(f'process user {user}')
    if mod == None:
        mod = int(datetime.now().timestamp())
    
    x = parse_userpage()
    x.loads(page)
    x.origin = 'web'
    big = x.get_all()
    
    ent['online'] = 999999999999
    if big.get('_online_users'):
        ent['online'] = big['_online_users']
    
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
    path = f'/user/{user}/'
    page = session_get('http://www.furaffinity.net' + path)
    
    with open(f"{cfg['data_dir']}{user}.html", 'wb') as fh:
        fh.write(page.content)
        fh.close()
    
    gs = {
        "posts": [],
        "raw": page.text,
        "path": path
    };
    
    relay(json.dumps(gs))
    
    smol, big = process_user(user, page.text)
    return smol


def get_user_save(user, to):
    try:
        data = get_user(user)
    
    except Exception as e:
        logging.error(f"Error on {user}", exc_info=True)
        data = None
    
    if not data:
        return
    
    to.write({user: data})


def load_users():
    ask_path = cfg['userstore']
    if ask_path == 'userstats':
        users = userstats.keys()
    
    elif '://' in ask_path:
        users = requests.get(ask_path).json().keys()
    
    elif ask_path.endswith('.json'):
        users = read_json(ask_path)
    
    else:
        users = appender()
        users.read(ask_path, keyonly=True)
    
    return users


def main():
    global userstats
    
    session_create()
    
    userstats = appender()
    userstats.read(cfg['apd_dir'] + 'userstats')
    
    users = load_users()
    newusers = [user for user in users
                if user.lower() not in userstats]
    
    if not newusers:
        logging.info('No new users to get')
        return
    
    logging.info(f'Getting {len(newusers):,} new users')
    
    c = 0
    for user in newusers:
        if c:
            time.sleep(cfg['speed'])
        
        c += 1
        get_user_save(user, userstats)
    
    logging.info('Finished getting user stats')


load_global('cfg', {
    'apd_dir': 'data/',
    'cfg_dir': 'cfg/',
    'data_dir': 'userstats/user/',
    'userstore': 'http://127.0.0.1:6970/data/users',
    'relay_servers': {
        'GOTSRV': {'port': 6990, 'post': 'mgot_parse'}
        },
    'poke_servers': {
        'FADSRV': {'port': 6970, 'post': 'findnew/user_stats'}
        },
    'speed': 1.5
    })


if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    if code_path:
        os.chdir(code_path)
    
    user_control = ':' in code_path
    init_logger('grab_userstats', disp=user_control)
    configgy("userstats")
    
    try:
        main()
    
    except Exception as e:
        logging.error("Exception occurred", exc_info=True)
    
    logging.info('Done')
    
    poke_servers(cfg['poke_servers'])
