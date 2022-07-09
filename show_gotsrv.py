from onefad_web import *
from fa_parser import *
from append_handler import appender
import requests

ent['version'] = 1
ent['internal_name'] = 'gotsrv'

def register_page(k, kind):
    global ent
    n = k
    if not k.endswith('_base'):
        n = '_'.join(k.split('_')[1:])
    
    try:
        ent[kind][n] = globals()[k]()
    
    except Exception as e:
        if 'required positional argument' not in str(e):
            logging.error(f"class {k}", exc_info=True)


def register_pages():
    for k in list(globals()):
        if k.startswith('builtin_'):
            register_page(k, 'builtin')
        
        elif k.startswith('post_'):
            register_page(k, 'builtin_post')


def create_menus():
    if 'all_pages' not in menus['pages']:
        menus['pages']['all_pages'] = {
            "title": "All Pages",
            "mode": "wide-icons-flat",
            "buttons": "all_pages_buttons",
            "icon": [9, 9]
            }
    
    for m, c in list(ent['builtin'].items()):
        if type(c) == builtin_menu:
            del ent['builtin'][m]
    
    for m in menus['pages']:
        ent['builtin'][m] = builtin_menu(which=m)
    
    menus['all_pages_buttons'] = []
    rbcat = {}
    
    for m, v in ent['builtin'].items():
        c = ''
        pagetype = v.pagetype
        if cfg.get('purge') and hasattr(v, 'purge'):
            v.purge(1)
        
        icn = {'label': m, 'href': m, 'label2': ''}
        sorter = '_' + m
        c = pagetype.replace('_', ' ')
        if pagetype == 'pages':
            icn['label'] = v.title
        
        elif pagetype.startswith('builtin'):
            if v.pages:
                icn['label2'] = ' pages'
            
            else:
                icn['href'] = '/'+icn['href']
        
        if icn['label'] == icn['label2']:
            del icn['label2']
        
        elif icn['label2'] != '':
            icn['label'] = f"<b>{icn['label']}</b><br><i>{icn['label2']}</i>"
            sorter = icn['label2'] + m
            del icn['label2']
        
        if c not in rbcat:
            rbcat[c] = []
        
        rbcat[c].append((sorter, icn))
    
    for c, d in rbcat.items():
        if not d:continue
        menus['all_pages_buttons'].append({'type': 'section', 'label': c.title()})
        menus['all_pages_buttons'] += [icn for m, icn in sorted(d)]


def big_action_list_time(reload=0):
    global has, sideposts
    if isinstance(reload, str):
        if reload.isdigit():reload = int(reload)
        else:reload = 0
    
    logging.info('Performing all actions')
    start = time.perf_counter()
    ent['built_at'] = datetime.now()
    
    ent['building_entries'] = True
    
    read_config()
    register_pages()
    create_menus()
    save_config()
    if reload > 2:
        sideposts = appender()
        sideposts.read(cfg['apd_dir'] + 'sideposts')
    
    # do work here
    has = {}
    for no, ask in enumerate(cfg['ask_servers']):
        logging.info(f'fAshking {ask.get("name", ask)}')
        protocol = ask.get('protocol', 'http://')
        ip = ask.get('ip', '127.0.0.1')
        port = ask.get('port', '6970')
        path = ask.get('path', '/data/posts')
        
        posts = requests.get(f'{protocol}{ip}:{port}{path}').json()
        logging.info(f'Know {len(posts)} posts')
        has[no] = set(posts)
    
    logging.info(f'Done in {time.perf_counter() - start}')
    ent['building_entries'] = False


class fa_req_handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        path_long = self.path[1:].lower()
        path_nice = urllib.parse.unquote(self.path)[1:]
        path_split = path_nice.lower().split('/')
        
        if path_split[-1] in ent['resources']:
            serve_resource(self, path_split[-1])
            return
        
        b = builtin_base()
        target = ent['builtin'].get(path_split[0], b)
        
        if path_split[0] in ent['builtin'] and target.pages is False:
            target.serve(self, path_split)
            return
        
        elif path_split == ['']:
            home = ent['builtin'].get(cfg['homepage_menu'])
            
            if home is None:
                home = ent['builtin'].get('all_pages', b)
            
            home.serve(self, path_split)
            return
        
        elif path_split[0] == 'unstuck':
            ent['building_entries'] = False
            self.send_response(307)
            self.send_header('Location', '/')
            self.end_headers()
            return
        
        elif path_split[0] == 'stop':
            b.do_head = True
            b.do_foot = True
            b.title = f'Server terminated'
            b.error(self, b.title, 'Goodbye')
            stop()
            return
        
        if path_split[-1].isdigit():
            path_split[-1] = int(path_split[-1])
        
        else:
            self.send_response(307)
            p = self.path
            if not p.endswith('/'):p += '/'
            self.send_header('Location', p + '1')
            self.end_headers()
            return
        
        if ent['building_entries']:
            b.do_head = True
            b.do_foot = True
            b.building_entries(self)
            return
        
        elif path_split[0] in ent['builtin']:
            target.serve(self, path_split)
            return

        b.do_head = True
        b.do_foot = True
        b.title = f'/{path_nice} not found'
        b.error(self, b.title, 'I don\'t know what do')
        return
    
    def do_POST(self):
        
        path_long = self.path[1:].lower()
        path_split = urllib.parse.unquote(self.path)[1:].lower().split('/')
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            ripdata = json.loads(post_data.decode('utf-8'))
        
        except:
            ripdata  = {}
        
        show = json.dumps(ripdata)
        if len(show) < 300:
            logging.debug(show)
        
        if path_split[0] in ent['builtin_post']:
            ent['builtin_post'][path_split[0]].serve_post(self, path_split, ripdata)
            return
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        ret = {}
        
        if path_split[0] == 'rebuild':
            level = 0
            if len(path_split) > 1:level = path_split[1]
            big_action_list_time(reload=level)
            ret['status'] = 'success'
        
        self.wfile.write(bytes(json.dumps(ret), 'utf-8'))
        return


class post_mgot(post_base):
    
    def post_head(self, handle, status=200):
        handle.send_response(status)
        handle.send_header('Content-type', self.content_type_post)
        handle.send_header("Access-Control-Allow-Headers", "*",)
        handle.send_header("Access-Control-Allow-Origin", "*")
        handle.end_headers()
    
    def per_post(self, post):
        for n, posts in has.items():
            if post not in posts:
                continue
            
            return cfg['ask_servers'][n].get('icon', 99)
        
        if post in sideposts:
            return 10
        
        return 0
    
    def post_logic(self, handle, pargs, data):
        return {post: self.per_post(post)
                for post in data}


class post_mgot_parse(post_mgot):
    
    def get_posts(self, path, raw):
        if not path or not raw:
            return {}
        
        if path.startswith('/gallery/') or path.startswith('/scraps/'):
            par = parse_gallery()
            par.loads(raw)
            return par.get('posts')
        
        elif path.startswith('/view/'):
            par = parse_postpage()
            par.loads(raw)
            par = par.get_all()
            
            if not 'id' in par:
                return {}
            
            posts = par.get('see_more', {})
            
            posts[par['id']] = {
                x: par[x] for x in [
                    'title', 'full', 'uploader', 'rating', 'tags']
                if par.get(x) != None
                }
            
            return posts
        
        elif path.startswith('/user/'):
            par = parse_userpage()
            par.loads(raw)
            par = par.get_all()
            return {
                **par.get('featured_post', {}),
                **par.get('recent_posts', {}),
                **par.get('recent_faved_posts', {})
                }
        
        else:
            par = parse_gallery()
            par.loads(raw)
            return par.get('posts')
        
        return {}
    
    def post_logic(self, handle, pargs, data):
        global sideposts
        
        posts = self.get_posts(
            data.get('path'), data.get('raw'))
        
        logging.debug(f'data give {len(posts)} {data.get("path", None)}')
        if posts:
            new = {post: info
                   for post, info in posts.items()
                   if post not in sideposts}
            
            sideposts.write(new, volsize=100000)
        
        posts = set(data.get('posts', []) + list(posts))
        
        return {post: self.per_post(post)
                for post in posts}


class post_data(post_base):
    
    def post_logic(self, handle, pargs, data):
        if not cfg['allow_data']:# disallow
            return {'error': 'data access is disabled'}
        
        if pargs[-1] == '':
            pargs = pargs[:-1]
        
        if len(pargs) == 1:# 2 short 4 me
            return {'error': 'no request specified'}
        
        if pargs[1] == 'postdata':
            datsrc = sideposts
            
            if pargs[-1].isdigit():
                return datsrc.get(pargs[-1], {'error': 'data not foud'})
            
            elif 'posts' not in data:
                if ' ' not in pargs[-1]:
                    return {'error': 'data list error'}
                
                data['posts'] = pargs[-1].split(' ')
            
            ret = {}
            for i in data['posts']:
                data = datsrc.get(i)
                if data:
                    ret[i] = data
            
            return ret
        
        if pargs[1] in globals():
            dat = globals()[pargs[1]]
            if len(pargs) > 2 and isinstance(dat, dict):
                
                if pargs[2] in dat:
                    return dat[pargs[2]]
                
                return {'error': 'variable does not exist'}
            
            return dat
        
        return {'error': 'unhandled request'}
    
    def serve(self, handle, path, head=True, foot=True, menu=False):
        self.post_head(handle)
        ret = self.post_logic(handle, path, {})
        handle.wfile.write(bytes(json.dumps(ret), 'utf8'))


def stop():
    logging.info('Stopping server')
    time.sleep(2)
    httpd.shutdown()


if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    os.chdir(code_path)
    
    name = ent.get('internal_name', '')
    if len(name) < 4:name += 'srv'
    init_logger(name, disp=':' in code_path)
    
    load_global('cfg', {
        'developer': False,
        
        'server_name': name,
        'server_addr': '127.0.0.1',
        'server_port': 6990,
        'allow_data': False,
        
        'apd_dir': 'data/',
        'res_dir': 'res/',# prepend resource files
        
        'homepage_menu': 'all_pages',
        'dropdown_menu': 'all_pages',
        
        'ask_servers': [],
        
        'static_cfg': False
        })
    
    load_global('menus', {
        'pages': {}
        })
    
    load_global('ent', {
        'resources': [
            'style.css',
            'parrot.svg',
            'icons.svg',
            'mark.js',
            'checkicons.svg'
            ],
        
        'builtin': {
            'data': post_data()
            },
        'builtin_post': {},
        
        'config_file': f'{name}_options.json',
        'menu_file': f'{name}_menus.json',
        'strings_file': f'{name}_strings.txt',
        
        'building_entries': False,
        
        'reentry_buttons': [
            (' rebuild', 'rebuild', 'Rebuild')
            ]
        })
    
    if not os.path.isdir(cfg['apd_dir']):
        os.mkdir(cfg['apd_dir'])
    
    register_pages()
    big_action_list_time(reload=3)
    
    httpd = ThreadedHTTPServer(
            (cfg['server_addr'], cfg['server_port']),
            fa_req_handler)
    httpd.serve_forever()
