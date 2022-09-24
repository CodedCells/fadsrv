import requests

from append_handler import *
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


def config_save():
    user_friendly_dict_saver(
        cfg['apd_dir'] + 'grabpostoptions.json',
        cfg)


def file_id_split(fd, s='.'):
    return set(x.split(s)[0] for x in os.listdir(fd))


def load_local_data(path, thing, split='.'):
    data = cfg[thing][path]
    
    if os.path.isfile(path + 'apdlist'):
        with open(path + 'apdlist', 'r') as fh:
            out = set(fh.read().split('\n')[1:])
            fh.close()
        
        if data['mode'] == 'split':
            for i in range(100):
                i = path + '{:02d}/'.format(i)
                if not os.path.isdir(i):
                    os.makedirs(i)
        
        return out
    
    if data.get('list', True):
        logging.info(f'Building list for {path}')
    
    if data['mode'] == 'single':
        if not os.path.isdir(path):
            os.makedirs(path)
        out = file_id_split(path, s=split)
    
    elif data['mode'] == 'split':
        out = set()
        for i in range(100):
            i = path + '{:02d}/'.format(i)
            if os.path.isdir(i):
                out.update(file_id_split(i, s=split))
            else:
                os.makedirs(i)
    
    else:
        logging.warning(f'Unknown mode: {data["mode"]} for path {path}')
        return set()
    
    if data.get('list', True):
        with open(path + 'apdlist', 'w') as fh:
            fh.write('# apdfile {}apdlist\n'.format(path))
            fh.write('\n'.join(out))
            fh.close()
    
    return out


def list_local_store(mode):
    logging.info(f'Listing local store: {mode}')
    store = {}
    main = None
    spl = '.'
    if mode.startswith('data'):
        spl = '_desc'
    
    for k in cfg[mode]:
        if main == None:
            main = k
        
        store[k] = load_local_data(k, mode, split=spl)
        logging.info('Path: {}\t{:,}'.format(k, len(store[k])))
    
    stores = list(enumerate(store))
    return store, stores, main


def list_local_data():
    global data_store, data_stores, main_data
    global post_store, post_stores, main_post
    
    data_store, data_stores, main_data = list_local_store('data_store')
    post_store, post_stores, main_post = list_local_store('post_store')


def check_import():
    if not os.path.isdir('dl/'):
        return

    logging.info('Checking import')
    for fn in os.listdir('dl/'):
        if not fn.endswith('.html'):
            continue
        
        with open('dl/' + fn, 'rb') as fh:
            d = str(fh.read())
            fh.close()
        
        if 'www.furaffinity.net/view/' in d:
            postid = get_prop('www.furaffinity.net/view/', d, t='/')
            logging.info(f'Adding {postid}')
            
            os.rename('dl/' + fn, 'put/{}_desc.html'.format(postid))
            check_post(postid, where='put/')


def download_data(post):
    logging.info(f'get data {post}')
    
    state = True
    sg = sget('https://www.furaffinity.net/view/{}/'.format(post))
    
    x = check_login(sg.text, post)
    if x:
        dst = data_path(post, 'data_store', main_data, fmt='{}_desc.html')
        
        with open(dst, 'wb') as fh:
            fh.write(sg.content)
            fh.close()
    
    elif x == False:exit()# HALT
    
    else:
        state = False
    
    return sg, state


def check_post(post, where):
    request = False
    data_src = data_path(post, 'data_store', where, fmt='{}_desc.html')
    if not os.path.isfile(data_src):
        logging.error(f'data file not found! {data_src}')
        return
    
    try:
        # iso-whatever breaks rus, idk
        with open(data_src, 'r', encoding='utf8') as fh:
            data = fh.read()
            fh.close()
    
    except UnicodeDecodeError as e:
        try:
            logging.info(f'UTF UDE {post} {e}')
            with open(data_src, 'r', encoding='ISO-8859-1') as fh:
                data = fh.read()
                fh.close()
        
        except UnicodeDecodeError as e:
            loggind.info(f'Double UDE {post} {e}')
            with open(data_src, 'rb') as fh:
                data = str(fh.read())
                fh.close()
    
    if not check_login(data, 'STORED: ' + post):
        return request# stored 404 oh no
    
    mt = 'download'
    if 'class="download"><a href="' in data:
        fp = get_prop('class="download"><a href="', data)
    
    elif 'data-fullview-src="' in data:
        fp = get_prop('data-fullview-src="', data)
        mt = 'fullview'
    
    else:
        logging.warning(f'Missing image url {post}')
        return request
    
    fd = data_path(post, 'post_store', main_post, fmt='')
    fn = '{}.{}'.format(post, fp.split('.')[-1])
    if not os.path.isdir(fd):
        os.makedirs(fd)
    
    hd = has_post(post, '{}.' + fp.split('.')[-1])
    
    if hd == 'no':
        logging.info(f'get img {post}')
        sg = sget('https:' + fp)
        request = True
        
        con = sg.content
        if len(con) == 3072 and con.startswith(b'GIF89ax\x00x\x00\xe7\xa3\x00.;A.;B/;B/<B/<C0<C0=C0=D1=D1>D1>E2>E2'):
            # error result
            logging.error(f'!!! RESPONSE RETURNED ERROR GIF FOR {post} !!!')
            return
        
        with open(fd + fn, 'wb') as fh:
            fh.write(sg.content)
            fh.close()
    
    elif hd.startswith('added'):
        pass
    
    elif hd == 'already':
        pass
    
    elif hd == 'err':
        pass
    
    else:
        logging.error(f'Post {post} post state {hd}')
    
    if not os.path.isfile(fd + fn):
        # todo test if we have it elsewhere else
        # code moved to no
        pass
    
    prepsys(fd, fn)
    
    return request


def crawl_favourites_post(e):
    e = '<figure id="' + e.split('-->')[0]
    
    post = get_prop('figure id="sid-', e)
    if post in knows:
        return 'got'
    
    return post, {
        'title':  get_prop(' title="', e, o=2),
        'user':   get_prop(' title="', e, o=3),
        'rating': get_prop('r-', e, t=' ')
        }


def crawl_favourites():
    global know, knows
    
    url = 'https://www.furaffinity.net/favorites/{}/'
    seqgal = 'class="gallery s-'

    page = 1
    link = url.format(cfg['username'])
    
    while link != '':
        logging.info(f'Page {page}')
        
        req = sget(link)
        d = req.text
        if seqgal not in d:
            logging.warning('uh-oh')
            return# no more
        
        add = {}
        new = 0
        got = 0
        
        page_posts = get_prop(seqgal, d, t='</section>'
                              ).split('<figure id="')[1:]
        
        for e in page_posts:
            e = crawl_favourites_post(e)
            if e == 'got':
                got += 1
            
            else:
                post, data = e
                add[post] = data
                knows.add(post)
        
        if len(add) > 0:
            logging.debug(f'New posts {add.keys()}')
            
            logging.info(f'Adding {len(add)} new known posts')
            know.write(add, volsize=100000)
        
        # check for next page link
        if 'button standard right" href="' in d:
            nlink = get_prop('button standard right" href="', d)
            if nlink.startswith('/'):
                nlink = 'https://www.furaffinity.net' + nlink
            
            if link == nlink:
                logger.warning('HALT: Same URL')
                nlink = ''
            
            link = str(nlink)
        
        else:
            link = ''
        
        # check if we got any new posts
        if len(page_posts) == got:
            logging.info('Got all new posts')
            return
        
        page += 1
        time.sleep(cfg['speed'])
    
    logging.info('Reached end of list')


def data_path(post, thing, path, fmt='{}'):
    mode = cfg[thing][path]['mode']
    
    if mode == 'single':
        return path + fmt.format(post)
    
    elif mode == 'split':
        return path + ('{:02d}/' + fmt).format(int(post[-2:]), post)
    
    else:
        logging.warning(f'Unknown mode: {mode} for path {path}')


def has_data(post):
    # check data lists
    
    for n, k in data_stores:
        if post in data_store[k]:
            if n == 0:
                return 'already'
            
            else:
                src  = data_path(post, 'data_store', k, fmt='{}_desc.html')
                if not os.path.isfile(src):
                    logging.warning(f'{post} was not in store {k}')
                    continue
                
                logging.info(f'COPYDATA {post} (from {k})')
                dst = data_path(post, 'data_store', main_data, fmt='{}_desc.html')
                shutil.copyfile(src, dst)
                return 'added'
    
    # check directories for unlisted files
    for n, k in data_stores:
        data = cfg['data_store'][k]
        src  = data_path(post, 'data_store', k, fmt='{}_desc.html')
        
        if os.path.isfile(src):
            if n == 0:
                return 'added_unlist'
            
            else:
                logging.info(f'COPYDATA {post} (from {k})')
                dst = data_path(post, 'data_store', main_data, fmt='{}_desc.html')
                shutil.copyfile(src, dst)
                return 'added'
    
    return 'no'


def has_post(post, ext):
    
    for n, k in post_stores:
        if post in post_store[k]:
            src  = data_path(post, 'post_store', k, fmt=ext)
            if not os.path.isfile(src):
                logging.warning(f'{post} was not in store {k}')
                continue
            
            if n == 0:
                return 'already'
            
            logging.info(f'COPYIMG {post} (from {k})')
            dst = data_path(post, 'post_store', main_post, fmt=ext)
            shutil.copyfile(src, dst)
            return 'added'
    
    # check directories for unlisted files
    for n, k in post_stores:
        data = cfg['post_store'][k]
        src  = data_path(post, 'post_store', k, fmt=ext)
        
        if os.path.isfile(src):
            if n == 0:
                return 'added_unlist'
            
            else:
                logging.info(f'COPYIMG {post} (from {k})')
                dst = data_path(post, 'post_store', main_post, fmt=ext)
                shutil.copyfile(src, dst)
                return 'added'
    
    return 'no'


def apdlist_add(d):
    logging.info('Appending apdlists')
    
    with open(main_data + 'apdlist', 'a') as fh:
        fh.write('\n' + '\n'.join(d))
        fh.close()
    
    with open(main_post + 'apdlist', 'a') as fh:
        fh.write('\n' + '\n'.join(d))
        fh.close()


def get_new_data():
    fnf = apc_master().read(cfg['apd_dir'] + 'posts404')
    
    logging.info('Finding new posts')
    
    c = 0
    la = 0
    apd = []
    
    for post in reversed(list(know.keys())):
        request = False
        c += 1
        
        if str(post) in skip:
            continue
        
        # data check
        hd = has_data(post)
        if post in fnf:
            hd = 'err'
        
        if hd == 'no':
            sg, state = download_data(post)
            request = True
            if state:
                apd.append(post)
            else:
                apc_write(cfg['apd_dir'] + 'posts404', {post: ''}, fnf, 1)
                fnf[post] = ''
        
        elif hd.startswith('added'):
            apd.append(post)
        
        elif hd == 'already':
            pass
        
        elif hd == 'err':
            pass
        
        else:
            raise Exception('Post {} data state {}'.format(post, hd))
        
        if request:
            time.sleep(cfg['speed'])
            request = False
        
        if post in post_store[main_post]:
            continue
        
        request = check_post(post, where=main_data)
        
        if c//500 > la:
            logging.info(f'\taddloop\t{(c // 500) * 500}')
            la = c // 500
            
            if len(apd) > 0:
                apdlist_add(apd)
                
                apd = []
        
        if request:
            time.sleep(cfg['speed'])

    if len(apd) > 0:
        apdlist_add(apd)


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
        "squash_server": "",
        "squash_tell": ""
        })
    
    pp = cfg['apd_dir']
    if not os.path.isdir(pp):
        os.mkdir(pp)
    
    load_global('cfg', 'grabpostoptions.json')
    config_save()

    if not cfg['username']:
        logging.error('Set the username in the config')
        prompt_exit()
    
    cookies = read_secret(pp + 'secret.json')
    if not cookies:
        prompt_exit()
    
    session = requests.Session()
    session.cookies.update(cookies)


def main():
    global know, knows, skip
    know = appender()
    know.read(cfg['apd_dir'] + 'known_faves', keyonly=True, dotime=True)
    knows = set(know.keys())
    
    skip = appender()
    skip.read(cfg['apd_dir'] + 'grabskip.txt')
    
    list_local_data()
    
    check_import()
    
    crawl_favourites()
    logging.info(f'Know {len(know)}')
    
    get_new_data()


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


def copy_skip(f, e):
    if e.lower() == 'swf':
        return 'flssh'
    
    if f in rem:
        return 'has remote'
    
    if e != 'jpg':
        return copy_skip(f.replace(e, 'jpg'), 'jpg')
    
    return None


def what_to_copy():
    copyf = []
    c = 0
    
    for file in files:
        
        try:
            postid, rext = file.split('.')
        
        except Exception as e:
            postid = file.split('.')[0]
            rext = ''
        
        if copy_skip(file, rext) != None:
            continue
        
        postfn = data_path(postid, 'post_store', main_post, fmt='')
        
        if prepsys(postfn, file):
            c += 1
        
        if c % 100 == 0:
            logging.info(c)
            if c % 500 == 0:
                time.sleep(2)
    
    return copyf


def tell_unpack():
     x = requests.post(cfg['squash_tell'])
     logging.info(f'status: {x.status_code}')


def squash_more():
    if not cfg['squash_tell']:
        logging.info("No squash server set")
        return
    
    logging.info('Poking server...')
    tell_unpack()
    return
    global files, com, rem
    
    mode = cfg['post_store'][main_post].get('mode', None)
    
    if mode == 'split':
        files = []
        for i in range(100):
            files += os.listdir(f'{main_post}/{i:02d}/')
    
    elif mode == 'single' or mode == None:
        files = os.listdir(main_post)
    
    logging.info(f'{len(files):,} local files')
    com = set(os.listdir('ncomp'))
    logging.info(f'{len(com):,} compressed')
    
    fl = cfg["squash_server"] + 'data/filelist'
    if not os.path.isfile(fl):
        logging.warning(f'Can\'t find filelist at {fl}')
        return
    
    rem = set(apc_master().read(fl).keys())
    
    logging.info(f'{len(rem):,} remote')
    
    copyf = what_to_copy()
    logging.info('Pinging')
    tell_unpack()


def prompt_exit():
    if user_control:
        input('\nTerminating')
    
    exit()

if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    user_control = ':' in code_path
    init_logger('grab_post', disp=user_control)
    
    configgy()
    logging.info(f"squash parth is {cfg['squash_server']}")
    from onefad_squash import *
    
    try:
        main()
    except Exception as e:
        logging.error("Exception occurred", exc_info=True)
    
    logging.info('Done!')
    del data_store
    del post_store
    
    if cfg['squash_server']:
        squash_more()
    
    poke_servers()
