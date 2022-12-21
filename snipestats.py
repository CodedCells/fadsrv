from onefad import *
from append_handler import appender
import requests

def load_config():
    load_global('cfg', {
        'developer': False,
        'apd_dir': 'data/',
        'data_dir': 'data_period/',
        'collect': {},
        "poke_servers": {
            "StatSRV": { "port": 6700, "post": "poke/success" }
        }
        })
    
    load_global('cfg', 'stat_cfg.json')
    logging.debug('Loaded config')
    
    user_friendly_dict_saver('cfg/stat_cfg.json', cfg)


def get_stats_page(user, page, session):
    current = 0
    new_data = {}
    
    logging.debug(f'Page {page}')
    
    req = session.get(f'https://www.furaffinity.net/stats/{user}/submissions/{page}/')
    d = req.text
    
    for p in d.split('<div class="stats-page" id="id_')[1:]:
        p = p.split('</div>\n\n</div>\n\n')[0]
        tags = [
            get_prop('>', x, t='</')
            for x in p.split('<span class="tags"><a href="/search/@keywords ')[1:]]
        
        post = {
            'id': p.split('"')[0],
            'date': strdate(get_prop('class="popup_date">', p, t='</')).isoformat(),
            'title': get_prop('"><h3>', p, t='</h3'),
            'description': get_prop('<hr>', p, t='<br><br>').strip(),
            'tags': tags
            }
        
        for sblok in get_prop('submission-stats-container">', p, t='        </div>\n    </div>').split('<div class="')[1:]:
            sprop = sblok.split('"')[0]
            sval = get_prop('">', sblok.split('font-large')[1], t='</')
            if sval.isdigit():
                sval = int(sval)
            
            post[sprop] = sval
        
        new_data[post['id']] = post
        current += 1
    
    return current, new_data


def get_stats(user, secret, posts):
    logging.info(f'Updating stats for {user}')
    session = requests.session()
    session.cookies.update(secret)
    
    cur = datetime.now().isoformat()
    
    new_data = {}
    page = 1
    current = 1
    while current:
        if page > 1:
            time.sleep(2)
        
        current, nd = get_stats_page(user, page, session)
        new_data.update(nd)
        page += 1

    logging.debug(f'stats for {len(new_data):,} posts')
    
    new_posts = {}
    for k, d in new_data.items():
        d = {
                v: i for v, i in d.items()
                if v not in ['views', 'favorites', 'comments']}
        
        if not posts.get(k) or posts.get(k) != d:
            new_posts[k] = d
    
    if new_posts:
        logging.debug(f'recording {len(new_posts):,} new/updated posts')
        posts.write(new_posts)
    
    new_period = {}
    for k, d in new_data.items():
        new_period[k] = {
            'views': d['views'],
            'faves': d['favorites'],
            'comments': d['comments']
            }
    
    userp = appender()
    userp.write(
        {cur: new_period},
        filename=cfg['data_dir'] + f'{user}_period',
        volsize=2500)


def collect_stats(user, opt):
    posts = appender()
    posts.read(cfg['data_dir'] + f'{user}_posts')
    
    secret = opt.get('secret', None)
    if secret.get('source'):
        secret = None
        if os.path.isfile(secret['source']):
            secret = read_json(secret['source'])
    
    if not (type(secret) == dict and 'a' in secret and 'b' in secret):
        logging.error(f'Bad secret for {user}')
        return
    
    logging.info(f'Working on {user}')
    get_stats(user, secret, posts)
    

def main():
    now = datetime.now()
    run_anyways = 'idk'
    
    for user, opt in cfg['collect'].items():
        collect_stats(user, opt)


def poke_servers():
    logging.info('Notifying servers')
    for k, v in cfg['poke_servers'].items():
        logging.info(k)
        path = v.get('path',
                     'http://{}:{}/{}'.format(
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


if __name__ == '__main__':
    init_logger('snipestats', disp=True)#':' in code_path)

    load_config()
    
    main()
    import snipestats_trunc
    
    poke_servers()
