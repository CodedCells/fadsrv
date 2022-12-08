from onefad_web import *
import requests

ent['version'] = 1
ent['internal_name'] = 'glancer'

class builtin_base(builtin_base):
    
    def head(self, handle, status=200):
        super().head(handle, status=200)
        if self.do_style:
            self.write(
                handle, '<link rel="stylesheet" href="/glancer.css">\n')


class builtin_info(builtin_base):

    def __init__(self, title='Info', link='/info', icon=51):
        super().__init__(title, icon)
        self.do_foot = False
        self.do_menu = False
    
    def page(self, handle, path):
        doc = '<div id="content">\n<div id="masthead-container">'
        doc += '<h2>Glancer</h2>\n</div>'
        doc += '<div id="guide" class="full">'
        self.write(handle, doc)
        
        doc = ''
        for server, data in cfg['checksys'].items():
            url = server_path(data)
            cla = ['', ' offline'][states.get(server) == 'Offline']
            doc += f'<a class="guide-item {cla}" href="{url}">\n'
            icon = data.get('icon', [9, 9])
            if type(icon) == int:
                icon = ii(icon)
            
            doc += f'<i class="icon" style="background-position:-{icon[0]*100}% -{icon[1]*100}%;"></i>\n'
            doc += f'<span>{server}</span>\n</a>\n'
        
        self.write(handle, doc + '</div>')
        
        target = ent['builtin'].get('wares')
        if target:
            target.page(handle, '')
        else:
            self.write(handle, '<p>Wares page does not exist.</p>')


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
    logging.info('Performing all actions')
    start = time.perf_counter()
    ent['built_at'] = datetime.now()
    
    ent['building_entries'] = True
    
    read_config()
    register_pages()
    create_menus()
    save_config()
    
    # do work here
    checksys_now()
    
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

        logging.debug(json.dumps(ripdata))
        
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


def stop():
    logging.info('Stopping server')
    ent['running'] = False
    time.sleep(2)
    httpd.shutdown()
    exit()


def server_path(data):
    path = data.get('url', 'http://{}:{}/{}')
    if '{}' in path:
        path = path.format(
            data.get('ip', '127.0.0.1'),
            data.get('port', 80),
            data.get('path', ''))
    
    return path


def checksys_now():
    global states
    
    if 'states' not in globals():
        states = {}
    
    for server, data in cfg['checksys'].items():
        
        path = server_path(data)
        
        try:
            x = requests.get(path, timeout=1)
            state = x.status_code
            #rsp = x.elapsed.total_seconds()
        
        except:
            state = 'Offline'
        
        if state != states.get(server):
            logging.info(f'{server} is {state}')
        
        states[server] = state


def checksys_loop():
    while ent['running']:
        time.sleep(120)
        checksys_now()


if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    os.chdir(code_path)
    
    name = ent.get('internal_name', '')
    if len(name) < 4:name += 'srv'
    init_logger(name, disp=':' in code_path, level=logging.INFO)
    
    load_global('cfg', {
        'developer': False,
        
        'server_name': name,
        'server_port': 6989,
        
        'apd_dir': 'data/',
        'res_dir': 'res/',# prepend resource files
        
        'homepage_menu': 'all_pages',
        'dropdown_menu': 'all_pages',
        
        'checksys': {},
        
        'static_cfg': False
        })
    
    load_global('menus', {
        'pages': {}
        })
    
    load_global('ent', {
        'running': True,
        'resources': [
            'style.css',
            'parrot.svg',
            'icons.svg',
            'mark.js',
            'client.js',
            'chart.js',
            'logger.js',
            'glancer.css'
            ],
        
        'builtin': {},
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
    
    logging.info(f'Starting serivce on {cfg["server_addr"]}:{cfg["server_port"]}')
    httpd = ThreadedHTTPServer(
        (cfg['server_addr'], cfg['server_port']),
        fa_req_handler)
    
    checksys = threading.Thread(target=checksys_loop)
    checksys.start()
    
    httpd.serve_forever()
