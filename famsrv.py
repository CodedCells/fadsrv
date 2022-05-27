from onefad_web import *

ent['version'] = 1
ent['internal_name'] = 'fam'

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


def filelist():
    dd = cfg['apd_dir']
    files = apc_read(dd + 'filelist')
    if files:
        return set(files.keys())
    
    logging.info('Building file list')
    files = None
    
    for i in range(100):
        i = cfg['media_dir'] + f'{i:02d}/'
        logging.debug(i)
        
        if os.path.isdir(i):
            new = {x: 0 for x in os.listdir(i)}
            apc_write(dd + 'filelist', new, files, 1)
            if not files:
                files = {}
            files.update(new)
    
    if files:
        return files
    
    return {}


def find_new_files():
    add = []
    src = cfg.get('import_dir', 'add/')
    if not os.path.isdir(src):
        logging.warning(f'No {src} directory')
        return
    
    for f in os.listdir(src):
        i = f.split('.')[0][-2:]
        if not i.isdigit():
            logging.debug(f'File {f} is non-digit name, skipping.')
            continue
        
        d = cfg['media_dir'] + f'{int(i):02d}/'
        add.append(f)
        logging.debug(f'Moving {src}{f} to {d}{f}')
        shutil.move(src + f, d + f)
    
    if not add:
        logging.debug('No files to add')
        return
    
    logging.info(f'Adding {len(add):,} files')
    apc_write(cfg['apd_dir'] + 'filelist',
              {k: 0 for k in add},
              {k: 0 for k in ent['filelist']},
              1)
    
    ent['filelist'].update(set(add))
    ent['idlist'].update(set(x.split('.')[0] for x in add))


def big_action_list_time(reload=0):
    logging.info('Performing all actions')
    start = time.perf_counter()
    ent['built_at'] = datetime.now()

    ent['building_entries'] = True
    
    read_config()
    register_pages()
    create_menus()
    save_config()
    
    ent['filelist'] = filelist()
    ent['idlist'] = set(x.split('.')[0] for x in ent['filelist'])
    find_new_files()
    
    logging.info(f'Done in {time.perf_counter() - start}')
    ent['building_entries'] = False


def post_path(fp):
    if cfg.get('post_split', True):
        fid = fp.split('.')[0]
        
        if fid.isdigit():
            fp = f'{int(fid[-2:]):02d}/' + fp
    
    return cfg['media_dir'] + fp


def serve_image(handle, path, head=True):
    if '.' not in path:path += '.'
    ext = path.split('.')[-1]
    
    fp = post_path(path.split('/')[-1])
    
    if fp and os.path.isfile(fp):
        if head:
            handle.send_response(200)
            handle.send_header('Content-type', ctl.get(ext, 'text/plain'))
            handle.send_header('Cache-Control', 'max-age=3600, must-revalidate')
            handle.end_headers()
        handle.wfile.write(safe_readfile(fp, mode='rb'))
    
    elif ext != 'jpg':
        serve_image(handle, path.replace('.' + ext, '.jpg'), head=head)
    
    else:
        logging.warning(f'File missing: {path}')
        serve_resource(handle, 'parrot.svg', code=404)


class builtin_info(builtin_base):

    def __init__(self, title='Info', icon=51):
        super().__init__(title, icon)
    
    def stat(self, handle, label, value):
        if type(value) == int:
            value = f'{value:,}'
        self.write(handle, f'<p>{label}: {value}</p>\n')
    
    def page(self, handle, path):
        now  = datetime.now()
        out = '<div class="errorpage">\n<h1>System Information</h1>\n'
        self.write(handle, out)
        self.stat(handle, 'Posts', len(ent['idlist']))
        self.stat(handle, 'Files', len(ent['filelist']))
        self.stat(handle, 'Server Time Now', now.isoformat()[:19])
        self.stat(handle, 'Last Rebuilt:', ent['built_at'].isoformat()[:19])


class builtin_reader(builtin_base):

    def __init__(self, title='Reader', icon=33):
        super().__init__(title, icon)
    
    def post_path(self, path):
        return post_path(path)
    
    def find_file(self, handle, path):
        if len(path) < 2 or not path[1]:
            self.write(handle, 'Specify a file.')
            return
        
        path = path[1]
        if '.' not in path:path += '.'
        
        fp = self.post_path(path)
        
        if not os.path.isfile(fp):
            self.write(handle, 'File not found.')
            return
        
        return fp
    
    def page(self, handle, path):
        h = '<div class="container list">\n'
        h += '<div class="talking">\n<p>'
        self.write(handle, h)
        
        fp = self.find_file(handle, path)
        if fp:
            h = readfile(fp, mode='rb')
            h = h.replace(b'\n', b'</p>\n<p>')
            handle.wfile.write(h)
        
        h = '</p>\n</div>'
        h += '</div>\n<div class="foot">\n'
        self.write(handle, h)


class fa_req_handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        path_long = self.path[1:].lower()
        path_nice = urllib.parse.unquote(self.path)[1:]
        path_split = path_nice.lower().split('/')
        
        if path_split[-1] in ent['resources']:
            serve_resource(self, path_split[-1])
            return
        
        elif (path_long.startswith('i/') or
              path_long.startswith('t/')):
            serve_image(self, path_long[2:])
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


class post_hasfiles(post_base):
    
    def hasfile(self, f):
        if f in ent['filelist']:
            return [True, f.split('.')[-1]]
        
        f = f.split('.')[0]
        if i in ent['idlist']:
            for e in ctl:
                if f'{f}.{e}' in ent['filelist']:
                    return [True, e]
        
        return [False, None]
    
    def post_logic(self, handle, pargs, data):
        return {'files': {
            k: self.hasfile(f) for f in data.get('files', [])
            }}


class post_mgot(post_base):

    def gotm(self, f):
        if f in ent['idlist']:
            return 'got'
        
        return 'not'
    
    def post_logic(self, handle, pargs, data):
        ret = {f: f'check{self.gotm(f)}.svg' for f in data}
        return ret


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
        'server_port': 6770,
        
        'apd_dir': 'data/',
        'res_dir': 'res/',# prepend resource files
        'import_dir': 'add/',
        'media_dir': 'im/',
        
        'homepage_menu': 'menu',
        'dropdown_menu': 'menu',

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
            'client.js',
            'chart.js',
            'logger.js',
            'checkgot.svg',
            'checknot.svg',
            'checknotx.svg',
            'checktg.svg'
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
    
    httpd = ThreadedHTTPServer(
            (cfg['server_addr'], cfg['server_port']),
            fa_req_handler)
    httpd.serve_forever()
