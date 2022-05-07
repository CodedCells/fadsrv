from onefad import *

load_global('strings',{# todo migrate more from code and clean up
'menubtn-narrow-icons': '<span class="menubtn"><a href="{href}" alt="{alt}"><span class="iconsheet" style="background-position:{x}px {y}px;"></span>{label}</a></span>\n',
'menubtn-wide-icons': '<span class="menubtn wide"><a href="{href}" alt="{alt}"><span class="iconsheet" style="background-position:{x}px {y}px;"></span> {label}</a></span>\n',
'menubtn-list': '<a class="btn wide" style="font-size:initial;" href="{href}" alt="{alt}">{label}</a>\n',
'menubtn-narrow-icons-flat': '<a href="{href}" alt="{alt}">\n<div class="menu-button">\n<span class="iconsheet" style="background-position:{x}% {y}%;"></span>\n<span class="menu-label">{label}</span>\n</div>\n</a>\n',
'menubtn-wide-icons-flat': '<a href="{href}" alt="{alt}">\n<div class="menu-button menu-button-wide">\n<span class="iconsheet" style="background-position:{x}% {y}%;"></span>\n<span class="menu-label">{label}</span>\n</div>\n</a>\n',
'nb': '<a class="btn{2}" href="{1}">{0}</a>\n',
'popdown': '<div class="pdbox{}"><button class="mbutton" onclick="popdown(this);">&#9660;</button>\n<div id="popdown" class="popdown">',
'error': '<div class="errorpage">\n<div>\n<h2>{}</h2>{}</div><img src="/parrot.svg" alt="Got his fibre, on his way." /></span>\n<br>',

'cfg.developer.name': 'Developer Mode',
'cfg.developer.label': 'Enables some debugging features, including reloading resources.',
'cfg.apd_dir.name': 'Append Data Directory',
'cfg.apd_dir.label': 'Path to core server files',
'cfg.res_dir.name': 'Resource Directory',
'cfg.res_dir.label': 'Path to server resources',
'cfg.server_name.name': 'Server Name',
'cfg.server_name.label': 'Set a different name for identifying.',
'cfg.server_addr.name': 'Server Address',
'cfg.server_addr.label': 'IP Address, Changes will not be reflected until restart!',
'cfg.server_port.name': 'Server Port',
'cfg.server_port.label': 'Port Number, Changes will not be reflected until restart!',
'cfg.homepage_menu.name': 'Homepage Menu',
'cfg.homepage_menu.label': 'Choose which menu should be displayed as home',
'cfg.dropdown_menu.name': 'Dropdown Menu',
'cfg.dropdown_menu.label': 'Choose which menu should drop down\nLeave blank for no dropdown',
'cfg.static_cfg.name': 'Static Config',
'cfg.static_cfg.label': 'Disable changing this config from the web',
'cfg.allow_data.name': 'Allow /data/*',
'cfg.allow_data.label': 'Enable data access over http, used for tools'
    })


def serve_resource(handle, resource, code=200):
    global ent
    handle.send_response(code)
    handle.send_header('Content-type', ext_content(resource))
    
    fn = cfg.get('res_dir', 'res/') + resource
    rf = f'_{resource}'
    
    should_load = cfg.get('developer') or f'_{resource}' not in ent
    if should_load and os.path.isfile(fn):
        logging.debug(f'loading resource {resource} from {fn}')
        ent[rf] = readfile(fn, mode='rb')
    
    else:
        handle.send_header('Cache-Control', 'max-age=3600, must-revalidate')
    
    handle.end_headers()
    handle.wfile.write(ent.get(rf, b''))


def template_nav(title, index, last, enc=True):
    nav = ''
    
    if 1 < index <= last:
        nav += strings['nb'].format('&lt;', index-1, ' nav-prev')
    
    elif index != last:
        nav += strings['nb'].format('&gt;|', last, ' nav-last')
    
    nav += f'<h2 class="pagetitle">{title}'
    if last != 1:
        nav += f' - {index:,}'
    
    nav += '</h2>\n'
    
    if last <= index and index != 1:
        nav += strings['nb'].format('|&lt;', 1, ' nav-first')
    
    elif index != last:
        nav += strings['nb'].format('&gt;', index+1, ' nav-next')
    
    if enc:
        nav = bytes(nav, 'utf-8')
    
    return nav


class mark_button(object):

    def __init__(self, mark, action=None):
        
        self.mark = mark
        self.data = apdmm[mark]
        
        self.btype = self.data.get('type')
        self.action = action
    
    def disabled(self):
        return self.data.get('disabled', False) or cfg.get('static')
    
    def pick_action(self):
        
        if self.disabled():
            return ''
        
        if self.action != None:
            return self.action
        
        if self.btype == 'collection':
            return 'setsGetMagic(this)'
        
        return 'aprefMagic(this)'
    
    def icon_html(self, value, size):
        
        if type(value) == list:
            return f'<i class="iconsheet ico{-size} {markicon(*value, m=-size)}"></i>'
        
        return f'<span>{value}</span>'
    
    def pick_icon(self, state, size):
        
        icon = self.data.get('icon')
        
        if state in self.data.get('values', []):
            icon, ch = valueicon(state,
                                 self.data.get('valueicon', []),
                                 icon, self.data['values'])
        
        return self.icon_html(icon, size)
    
    def build_for(self, thing, state=None, size=60):
        
        if self.data.get('hidden'):
            return '', ''
        
        state = mark_state(self.mark, thing)
        self.col = []
        if type(state) == list:# collections
            state, self.col = state[0], state[1]
        
        pressed = 'on '
        if state is None:
            state, pressed = '', ''
        
        cla = ''
        if self.disabled():
            cla = 'disabled '
        
        build_input = {
        'text':         self.build_input_text,
        'int':          self.build_input_int,
        'multibutt':    self.build_input_multibutt,
        'list':         self.build_input_list,
        'collection':   self.build_input_collection
            }.get(self.btype, None)
        
        if build_input is None:
            logging.warning(f'{self.mark} has unhandled mark type: {self.btype}')
            build_input = self.build_input_text
        
        self.t_thing = thing
        self.t_state = state
        self.t_press = pressed
        self.t_class = cla
        self.t_size  = size
        
        return build_input()
    
    def build_wrap(self, namep, cla, arg, inner):
        if namep[0] is None:return ''
        return f'<div name="{"@".join(namep)}" class="markbutton mbutton {cla}"{arg}>{inner}</div>\n'
    
    def build_input_text(self):
        #todo add icon
        inner = f'<input type="text" class="niceinp" size="1" value="{self.t_state}">'
        return self.build_wrap(
            [self.t_thing, self.mark],
            self.t_press + self.t_class,
            '',
            inner), ''
    
    def build_input_int(self):
        #todo add icon
        inner = f'<input type=""number" class="niceinp" size="1" value="{self.t_state}">'
        return self.build_wrap(
            [self.t_thing, self.mark],
            self.t_press + self.t_class,
            '',
            inner), ''
    
    def build_input_multibutt(self):
        
        values = self.data.get('values', [])
        
        out = f'<span name="{self.t_thing}@{self.mark}">\n'
        action = f' onclick="{self.pick_action()}"'
        
        for value in values:
            out += self.build_wrap(
                [self.t_thing, value, self.mark],
                ['', self.t_press][value == self.t_state] + self.t_class,
                action,
                self.pick_icon(value, self.t_size))
        
        return out + '</span>\n', ''
    
    def build_input_collection(self):
        links = []
        action = f' onclick="{self.pick_action()}"'
        inner = self.pick_icon(self.t_state, self.t_size)
        
        for coln in self.col:
            links.append(
                create_linktodathing(
                    self.mark,
                    coln[0],
                    con=self.data.get('name', self.mark)
                    ))
        
        link = ''
        if links:
            link = f'<div class="tags">\n{self.data["name_plural"]}:<br>\n' + '\n'.join(links) + '</div>\n'
        
        return self.build_wrap(
            [self.t_thing, self.mark],
            self.t_press + self.t_class,
            action,
            inner), link
    
    def build_input_list(self):
        
        inner = self.pick_icon(self.t_state, self.t_size)
        inner += f'<select class="niceinp" onchange="{self.pick_action()}">\n'
        
        for value in [''] + self.data['values']:
            inner += '<option value="{0}" {1}>{0}</option>\n'.format(value, ['', 'selected'][value == self.t_state])
        
        inner += '</select>'
        
        return self.build_wrap(
            [self.t_thing, self.mark],
            self.t_press + self.t_class,
            '',
            inner), ''


class builtin_base(object):
    
    def __init__(self, title='', icon=59):
        self.pagetype = 'builtin'
        self.title = title
        
        self.pages = False
        self.do_time = True
        self.metric = None
        self.do_menu = True
        self.do_menu_name = ''
        self.do_script = True
        self.do_style = True
        self.do_rebut = True
        
        self.do_head = True
        self.do_foot = True
        
        if icon is None:icon = 59
        if isinstance(icon, int):
            icon = ii(icon)
        
        self.icon = icon
        self.content_type = 'text/html'
        
        self.path_parts = 1
        self.page_options = []
        self.modes_default = ''
        self.modes = {}

    @staticmethod
    def write(handle, h):
        handle.wfile.write(bytes(h, 'utf-8'))
    
    def get_icon(self, path):
        return self.icon
    
    def metric_start(self):
        self.metric = time.perf_counter()
    
    def metric_stop(self):
        if self.metric is None:
            return 'ERR'
        
        m = time.perf_counter() - self.metric
        self.metric = None
        return int(m * 1000)
    
    def error(self, handle, ti, message, status=404):
        if self.do_head:
            self.head(handle, status=status)
        
        h = strings['error'].format(ti, message)
        self.write(handle, h)
        self.menu_ele(handle, ['error'])
        self.foot(handle)
    
    def building_entries(self, handle):
        self.head(handle)
        
        handle.wfile.write(b'''<div class="errorpage">
<div>
<h1>Building Entries</h1>
<p>The program is busy building entries.</p>
<br>
<div class="lds-ring parrot-ring">
<div></div><div></div><div></div><div></div></div>
<br><br>
<a href="/unstuck">Click Here if the program is stuck.</a>
</div>
<script>
var t = setTimeout(function(){window.location.reload(1);}, 5000);
</script>''')
    
    def head(self, handle, status=200):
        if self.metric is None:
            self.metric_start()
        
        handle.send_response(status)
        handle.send_header('Content-type', self.content_type)
        handle.end_headers()
        
        handle.wfile.write(b'<meta charset="utf-8">\n')
        h = ''
        if self.do_style:
            h += '<link rel="stylesheet" href="/style.css">\n'
        
        if self.do_script:
            h += '<script src="/mark.js"></script>\n'
        
        h += '</head>\n<body onload="page_load()">\n<div class="pageinner">'
        self.write(handle, h)
    
    def titledoc(self, handle):
        self.write(handle, f'<html>\n<head><title>{self.title}</title>\n')
    
    def newparg(self, path, pargs, v, i):
        r = pargs + [i]
        if v in pargs:
            r = list(pargs)
            r[pargs.index(v)] = i
            if v == i:
                r.remove(i)
        
        r = ' '.join(r)
        outp = list(path)
        if len(path) == self.path_parts:
            outp.append(path[-1])

        if len(outp) > 1:
            outp[-2] = r
        
        return '/'.join([str(x) for x in outp])
    
    def mode_picker(self, path):
        # create a nice picker element and give the mode
        pargs = []
        
        if len(path) > 1:
            pargs = path[-2]
            pdat = max(self.path_parts-2, 0)
            
            if pargs == path[pdat]:
                pargs = []# path has no data
            
            else:
                pargs = pargs.split(' ')
        
        current = self.modes_default    
        # find the current mode
        for i in self.modes:
            if i in pargs:
                current = i
                break
        
        out = ''
        for i, n in self.modes.items():
            r = self.newparg(path, pargs, current, i)
            if i == current or i in pargs:
                n = f'<b>{n}</b>'# selected
            
            if out:out += ' - '# spacer
            out += f'<a href="/{r}">{n}</a>\n'
        
        return current, out
    
    def optiondoc(self, handle, path):
        if not self.page_options:return
        
        outopt = []
        if not path:
            pargs = []
        
        elif isinstance(path[-1], int):
            path[-1] = str(path[-1])
            pargs = path[-2]
        
        else:
            pargs = path[-1]
        
        if len(path) == self.path_parts:
            pargs = []
        
        elif path:
            pargs = pargs.split(' ')
        
        for cat in self.page_options:
            outopt.append('')
            
            for i in cat:
                if i in pargs:
                    if not outopt[-1]:
                        outopt[-1] = i
        
        h = strings['popdown'].format(' pageopt')
        h += '<div class="page-toptions">\n'
        h += '<h2>Page options:</h2>\n'
        for n, v in enumerate(outopt):
            
            for i in self.page_options[n]:
                on = ['', 'on'][i in pargs]
                r = self.newparg(path, pargs, v, i)
                h += f'<a class="option {on}" href="/{r}">{i}</a>\n'
            
            h += '<br>\n'
        
        h += '</div></div></div>'
        self.write(handle, h)
    
    def popdown(self, handle, name):
        drop = ent['builtin'].get(name)
        if drop is None:
            return False
        
        h = strings['popdown'].format('')
        self.write(handle, h)
        drop.page(handle, [])
        handle.wfile.write(b'</div></div>')
        return True
    
    def bookmark_hook(self, handle):
        pass
    
    def foot(self, handle):
        dur = self.metric_stop()
        h = ''
        
        butts = ent.get('reentry_buttons', [])
        if self.do_rebut and butts:
            h += '<span>'
            for clas, func, text in butts:
                h +=  f'<a class="btn{clas}" onclick="postReload(this, \'/{func}\')">{text}</a>\n'
            
            h += '</span>'
            h += '<div id="rebuildLoad" class="lds-ring hide"><div></div><div></div><div></div><div></div></div>'
        
        srvname = cfg.get('server_name')
        if type(srvname) != str or not srvname:
            srvname = 'FADSRV'
        
        h += f'\n<p>{srvname} build#{ent.get("version", "unknown")}'
        
        if self.do_time:
            h += f' - Served in {wrapme(dur)}ms'
        
        h += '</p>'
        self.bookmark_hook(handle)
        
        self.write(handle, h)
    
    @staticmethod
    def page(handle, path):
        handle.wfile.write(b'<p>Sphinx of black quartz, judge my vow.</p>\n')
    
    def menu_ele(self, handle, path):
        self.optiondoc(handle, path)
        
        p = self.do_menu_name
        d = path + [cfg.get('homepage_menu')]
        
        if not p:p = cfg.get('dropdown_menu')
        if d[0] != p:
            self.popdown(handle, p)
    
    def serve(self, handle, path, head=True, foot=True, menu=True):
        if self.do_head and head:self.head(handle)
        
        self.page(handle, path)
        self.titledoc(handle)
        
        if self.do_foot and foot:self.foot(handle)
        
        if self.do_menu and menu:self.menu_ele(handle, path)


class builtin_menu(builtin_base):

    def __init__(self, title='Menu', icon=None, which=None):
        if icon is None and 'icon' in menus['pages'].get(which, {}):
            icon = menus['pages'][which]['icon']
        
        super().__init__(title, icon)
        self.which = which
        self.pagetype = 'builtin_menu'
        self.page_options = []
    
    def build_menu(self, handle, which, minfo, eles):
        title = minfo.get('title', f'Undefined: {which}')
        htmlout = f'<div class="head"><h2 class="pagetitle"><a href="/{which}">{title}</a></h2></div>\n'
        htmlout += '<div class="container list">\n'
        
        mode = minfo.get('mode', 'list')
        btn = strings.get(f'menubtn-{mode}', None)
        if btn is None:
            logging.warning(f'Missing markup string for menubtn-{mode}')
            btn = '<a href="{href}" alt="{alt}">{label}</a><br>\n'
        
        for d in eles:
            
            if d.get('type', 'button') == 'section':
                htmlout += f'<h2>{d.get("label", "Section")}</h2>\n'
                continue
            
            i = {'href': d.get('href', ''),
                 'label': d.get('label'),
                 'alt': d.get('alt', ''),
                 'x': 1, 'y': 5}
            
            part = i['href'].lower().split('/')
            if i['href'] and '/' not in i['href']:
                i['href'] = f'/{i["href"]}/1'
            else:
                part = part[1:]
            
            if 'icon' in d:
                icon = d['icon']
                if isinstance(icon, int):
                    icon = ii(icon)
                i['x'], i['y'] = icon
            
            elif 'x' in d and 'y' in d:
                i['x'], i['y'] = d['x'], d['y']
            
            elif part and part[0] in ent['builtin']:
                icon = ent['builtin'][part[0]].get_icon(part)
                if not i['label']:
                    i['label'] = ent['builtin'][part[0]].title
                
                if type(icon) == list and len(icon) == 2:
                    i['x'], i['y'] = icon
                else:
                    i['x'], i['y'] = 9, 9
            
            i['x'] *= -100
            i['y'] *= -100
            if not i['label']:label = 'Error'
            
            htmlout += btn.format(**i)
        
        self.write(handle, htmlout + '</div>\n')
    
    def page(self, handle, path):
        minfo = menus['pages'].get(self.which, {})
        butts = minfo.get('buttons', f'{self.which}_buttons')
        eles = menus.get(butts, {})
        
        self.build_menu(handle, self.which, minfo, eles)


class builtin_config(builtin_base):

    def __init__(self, title='Configure', icon=12, name='cfg'):
        super().__init__(title, icon)
        self.name = name
        if self.name != 'cfg':
            self.title += ' ' + self.name
    
    def page(self, handle, path):
        
        handle.wfile.write(b'<div class="head">')
        nav = template_nav(self.title, 1, 1)
        handle.wfile.write(nav + b'</div>\n')
        
        handle.wfile.write(b'<div class="container">\n')
        
        self.mode = globals().get(self.name, {})
        cfgsub = 'cfg.'
        if self.name != 'cfg':
            cfgsub += f'{self.name}.'
        
        body = ''
        for k, v in self.mode.items():
            name = strings.get(cfgsub + f'{k}.name', k)
            label = strings.get(cfgsub + f'{k}.label', '').replace('\n', '<br>')
            inner = f'<div class="info">\n<h2>{name}</h2>\n<p>{label}</p>\n</div>'
            
            inptype = 'unknown'
            if isinstance(v, bool):
                inptype = 'checkbox'
                if self.mode.get(k, False):
                    v = '" checked nul="'
                
            elif isinstance(v, int):
                inptype = 'number'
            
            elif isinstance(v, str):
                inptype = 'text'
            
            if inptype == 'unknown':
                if not label:
                    inptype = type(v)
                    inner += f'<div>\n<p>Unrepresentable type: {inptype.__name__}'
                    if inptype in [dict, list, set]:
                        inner += f'<br>Contains {len(v):,} items'
                    if cfg.get('allow_data'):
                        inner += f'<br><a href=/data/{self.name}/{k}>View as data</a>'
                    inner += '</p>\n</div>'
            
            else:
                scr = f"cfg('{k}', '{self.name}')"
                inner += f'''<div>
<input class="niceinp" id="{k}" type="{inptype}" value="{v}">
<button class="mbutton" onclick="{scr}">Apply</button>\n</div>'''
                    
            
            body += f'\n<div class="setting">{inner}\n</div>'
        
        handle.wfile.write(bytes(body, 'utf-8'))
        handle.wfile.write(b'</div>\n')


class post_base(builtin_base):
    
    def __init__(self, title='', icon=99):
        super().__init__(title, icon)
        self.pagetype = 'post'
        self.content_type_post = 'application/json'
    
    def post_head(self, handle, status=200):
        handle.send_response(status)
        handle.send_header('Content-type', self.content_type_post)
        handle.end_headers()
    
    def post_logic(self, handle, pargs, data):
        return "pog"
    
    def serve_post(self, handle, pargs, data):
        self.post_head(handle)
        ret = self.post_logic(handle, pargs, data)
        handle.wfile.write(bytes(json.dumps(ret), 'utf-8'))


def read_config():
    global strings
    
    load_global('cfg', ent['config_file'])
    load_global('menus', ent['menu_file'])
    
    dd = cfg.get('apd_dir', 'data/')
    
    sf = ent.get('strings_file')
    if not sf or not os.path.isfile(dd + sf):
        return
    
    sf = safe_readfile(dd + sf)
    for line in sf.split('\n')[1:]:
        line = line.split('\t')
        if len(line) == 2:
            line[1] = line[1].replace('\\n', '\n')
            if line[0].startswith('b.'):
                line[1] = bytes(line[1][2:-1], 'utf8')
            
            strings[line[0]] = line[1]


def save_config():
    if ent.get('config_read_error'):
        logging.warning('Preventing accidental config loss, please fix config file.')
        return
    
    dd = cfg.get('apd_dir', 'data/')
    
    if ent.get('config_file'):
        user_friendly_dict_saver(
            dd + ent['config_file'], cfg)
    
    if ent.get('menu_file'):
        user_friendly_dict_saver(
            dd + ent['menu_file'], menus,
            ignore_keys=['remort_buttons', 'page_buttons'])
    
    sf = ent.get('strings_file')
    if sf and not os.path.isfile(dd + sf):
        out = '// strings for FADSRV, name <tab> value'
        
        for k, v in strings.items():
            out += '\n{}\t{}'.format(k, str(v).replace('\n', '\\n'))
        
        with open(dd + sf, 'w') as fh:
            fh.write(out)
            fh.close()


class post__flag(post_base):
    # code used to be for marks
    # back when they were much, much simpler
    # using json files to store them
    # bad performance when files got big
    # but stiill works well for simple data modifications
    
    def __init__(self, title='', icon=99):
        super().__init__(title, icon)
        
    def post_logic(self, handle, pargs, data):
        global cfg, ent
        if cfg.get('static_cfg'):
            return {'status': 'Server set to Static for cfg'}
        
        dd = cfg.get('apd_dir', 'data/')
        ret = {}
        
        flag = pargs[1]
        pref = {}
        logging.debug(f'Legacy flag: {flag} {json.dumps(data)}')
        
        if flag == 'cfg':
            pref['cfg'] = cfg
        
        if flag == 'ent':
            pref['ent'] = ent
        
        for file in data:
            if data[file] is None:continue
            ret[file] = [flag, file not in pref[flag]]
            pref[flag][file] = data[file]
        
        if flag == 'cfg':
            cfg = pref['cfg']
            save_config()
            del pref['cfg']
        
        if flag == 'ent':
            ent = pref['ent']
            del pref['ent']
        
        return ret
