from onefad_web import *

apdmm = {}
apdm = {}

def isdocats():
    docats = cfg['docats']
    v = ['-', 'o'][docats]
    return f'^{v}.{v}^ docats {str(docats).lower()}'


def read_page_meta(data):
    fd = get_prop(b'<!--\r\nFADMETA', data, t=b'-->').decode(cfg['encoding_serve'])
    try:
        fd = json.loads(fd)
    except Exception as e:
        logging.debug('You fucked up!')
        logging.error(f'While reading metadata for {path[0]} ', exc_info=True)
    
    return fd


def loadpages():
    global ent, cfg
    
    butt = []
    pos = []
    
    if cfg['allow_pages'] and os.path.isdir('pages/'):
        for i, f in enumerate(os.listdir('pages/')):
            path = f'pages/{f}'
            if not os.path.isfile(path):continue
            
            fn = f.split('.')[0]
            
            with open(path, 'rb') as fh:
                data = fh.read()
                fh.close()
            
            fd = {}
            if b'<!--\r\nFADMETA' in data:
                fd = read_page_meta(data)
            
            p = fd.get('order', i)
            while p in pos:# prevent duplicate issue
                p += 1
            
            pos.append(p)
            dat = {
                'label': fd.get('menuLabel', fn),
                'href': '/' + fn,
                'icon': fd.get('menuIcon', [5, 9])
                }
            butt.append((p, dat))
            
            ent['builtin'][fn.lower()] = builtin_pages(
                dat['label'], dat['icon'], data)
    
    back = []
    menu = cfg['homepage_menu']
    if menu in menus['pages']:
        back = [{'label': menus['pages'][menu].get('title', menu), 'href': menu}]
    
    menus['page_buttons'] = back + [b for i, b in sorted(butt)]


def compare_for(d, v, sw=False):
    # check if mark is for the right type
    if sw:return d.get('for', 'posts').startswith(v)
    return d.get('for', 'posts') == v


def make_apd(fn, data, origin=None):
    if origin == None:# default
        origin = cfg['mark_dir']
    
    dfn = origin + fn
    if not os.path.isfile(dfn):
        logging.info(f'Creating {dfn}')
        apc_write(dfn, data, None, 2)


def data_path(post, s='.', d='data'):
    path = cfg[f'{d}_dir']
    
    if cfg['post_split']:
        return path + f'{int(post.split(s)[0][-2:]):02d}/{post}'
    
    else:
        return path + post

## collection functions


def find_collection(col, name, retid=False):
    name = str(name).lower()
    
    if name.startswith('id.'):# if set is named something illegal
        name = name[3:]
        
        if name.isdigit():
            name = int(name)
            for d, k, n in sort_collection(col, rebuild=True):
                if name == n:
                    if retid:return n
                    else:return k
    
    k = 0
    for n in apdm.get(col, {}):
        if (n.lower() == name or
            re.sub(r'\W+', '', n.lower()) == name):
            if retid:return k
            else:return n
        
        k += 1
    
    return False


def get_collectioni(col, postid, retcount=False, onlyin=False):
    ret = []
    add = []
    pin = []
    
    sc = sort_collection(col)
    
    for d, k, n in sc:
        i = apdm[col].get(k)
        if not i:continue
        r = (
            k,
            len(i['items']),
            postid in i['items'],
            i.get('lock', False),
            i.get('pin', False),
            i.get('icon')
            )
        
        if r[2]:
            add.append(r)
        
        elif r[4]:
            pin.append(r)
        
        else:
            ret.append(r)
    
    if retcount:
        return len(add)
    
    if onlyin:
        return add
    
    return (ret + pin + add)[::-1]


def sort_collection(col, ret=True, rebuild=False):
    colsort = f'collection_{col}sort'
    
    if  not ent.get(colsort, 0) or rebuild:
        sort = []
        n = 0
        for k, d in apdm.get(col, {}).items():
            if k == '//' or k == '':
                continue
            
            sort.append((d.get('modified', 0), k, n))
            n += 1
        
        ent[colsort] = sorted(sort)
    
    if ret:
        return ent[colsort]


## additional classes

class builtin_pages(builtin_base):
    
    def __init__(self, title, icon, data):
        super().__init__(title, icon)
        self.pagetype = 'pages'
        self.pagehtml = data
        self.do_wrap = False
    
    def serve(self, handle, path):
        if cfg['developer'] or not self.pagehtml:
            self.pagehtml = ''
            if os.path.isfile('pages/{}.html'.format(path[0])):
                with open(f'pages/{path[0]}.html', 'rb') as fh:
                    self.pagehtml = fh.read()
                    fh.close()
        
        data = self.pagehtml
        fd = {}
        if b'<!--\r\nFADMETA' in data:
            fd = read_page_meta(data)
        
        self.do_time = fd.get('enableTime', True)
        self.do_script = fd.get('enableScript', True)
        self.do_style = fd.get('enableStyle', True)
        self.do_menu = fd.get('enableMenu', True) and self.do_script
        self.do_menu_name = ''
        
        if fd.get('forceMenu') in menus['pages']:
            self.do_menu_name = fd['forceMenu']
        
        self.do_rebut = fd.get('enableRebuild', True) and self.do_script
        
        self.head(handle)
        self.titledoc(handle)
        if self.do_menu:self.menu_ele(handle, path)
        handle.wfile.write(data)
