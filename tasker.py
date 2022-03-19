from onefad_web import *

ent['version'] = 7

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


class builtin_logs(builtin_base):
    
    def __init__(self, title='Logs', link='/logs', icon=ii(22), pages=False):
        super().__init__(title, link, icon, pages)
    
    @staticmethod
    def get_prog_title(prog):# task id -> script id -> title
        return ent['tasks'].get(
            ent['taskidfn'].get(prog, prog), {}
            ).get('title', 'logs/' + prog)
    
    def taskpage(self, handle, path):
        prog = path[1]
        if prog not in ent['task_logs']:
            return False
        
        task = path[2][:-3].upper() + 'txt'
        if task not in ent['task_logs'][prog]:
            return False
        
        data = ent['task_logs'][prog][task]
        fn = data['path'] + task
        
        title = self.get_prog_title(prog)
        
        htmlout = '<script src="/logger.js"></script>\n<div class="pageinner">'
        htmlout += f'<div class="head"><h2 class="pagetitle"><span id="progName">{title}</span></h2></div>\n'
        htmlout += '<div class="container list">\n'
        diff = (datetime.now() - data['dmod']).total_seconds()
        htmlout += f'<p id="fileinfo"><span id="taskName">{task}</span> - Modified {int(diff)} seconds ago'
        if data.get('old'):
            htmlout += ' - <span id="isOld">Old</span>'
        
        htmlout += '</p>\n<div id="logOutput"></div>\n'
        htmlout += '<script>\nvar logOutput = '
        self.write(handle, htmlout)
        
        lines = readfile(fn).split('\n')
        trunc = lines[-1000:] # probably too many anyways
        
        self.write(handle, json.dumps(trunc) + ';\n')
        htmlout = f'var lines = {len(lines)};\n'
        htmlout += 'drawLogInit()</script>\n</div>'
        
        self.write(handle, htmlout)
        
        return True
    
    @staticmethod
    def ago(s):
        if s < 61:
            return f'{s} second{plu(s)} ago'
        
        elif s < 3601:
            return f'{s/60:0.0f} minute{plu(s)} ago'
        
        elif s < 86401:
            return f'{s/3600:.01f} hour{plu(s)} ago'
        
        else:
            return f'{s/86400:.01f} day{plu(s)} ago'
    
    def loglink(self, prog, m, t, d):
        name = '.'.join(t.split('.')[:-1])
        name += f'<br><i>Last modified {self.ago(int(m))}</i>'
            
        return f'<p><a href="/logs/{prog}/{t}">{name}</a></p>\n'
    
    def tasklist(self, prog, showold):
        now = datetime.now()
        htmlout = ''
        sort = sorted([
            ((now - d['dmod']).total_seconds(), t, d)
            for t, d in ent['task_logs'][prog].items()])
        
        old = []
        for m, t, d in sort:
            if d.get('old'):
                old.append((m, t, d))
                continue
            
            htmlout += self.loglink(prog, m, t, d)
        
        if not (showold and old):
            return htmlout
        
        htmlout += '<h4>Old Logs:</h4\n>'
        for m, t, d in old:
            htmlout += self.loglink(prog, m, t, d)
        
        return htmlout
    
    def progpage(self, handle, path):
        prog = path[1]
        title = self.get_prog_title(prog)
        htmlout = '<div class="pageinner"><div class="head">'
        htmlout += f'<h2 class="pagetitle"><span id="progName">{title}</span></h2></div>\n'
        htmlout += '<div class="container list">\n'
        tl = self.tasklist(prog, True)
        if tl.startswith('<h4>Old'):
            htmlout += '<p>No recently updated logs.</p>\n'
        
        htmlout += tl
        
        self.write(handle, htmlout)
    
    def page(self, handle, path):
        check_running_tasks()
        find_runningg_tasks()
        if path[-1].endswith('.txt') and len(path) == 3:
            if self.taskpage(handle, path):
                return
        
        elif path[-1] in ent['task_logs']:
            self.progpage(handle, path)
            return
        
        htmlout = '<div class="pageinner"><div class="head"><h2 class="pagetitle">Task Logs</h2></div>\n'
        htmlout += '<div class="container list">\n'
        self.write(handle, htmlout)
        
        htmlout = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;">'
        now = datetime.now()
        for prog in ent['task_logs']:
            title = self.get_prog_title(prog)
            htmlout += '<div>'
            htmlout += f'<h2>{title}</h2>\n'
            logc = len(ent["task_logs"][prog])
            htmlout += f'{logc:,} log{plu(logc)} on disk,\n'
            htmlout += f'<a href="/logs/{prog}">View All</a><br>\n'
            tl = self.tasklist(prog, False)
            if not tl:tl = '<p>No recently updated logs.</p>\n'
            htmlout += tl
            htmlout += '</div>'
        
        htmlout += '</div></div></div>'
        self.write(handle, htmlout)


class builtin_run(builtin_logs):
    
    def __init__(self, title='Run', link='/run', icon=ii(11), pages=False):
        super().__init__(title, link, icon, pages)
    
    def taskpage(self, handle, path):
        check_running_tasks()
        if path[1] not in ent['tasks']:
            self.write(handle, f'<p>Could not find task script: {path[1]}</p>\n</div>')
            return
        
        prog = path[1]
        data = ent['tasks'][prog]
        taskid = data.get('id', prog)
        print(prog, taskid)

        running = self.tasklist(taskid, False)
        if (data.get('preventMultiple') and
            running and
            path[-1] != 'y'):
            htmlout = '<p>This task is running or has ran recently:</p>\n'
            htmlout += running
            
            htmlout += '<br>\n<h3>Do you want to continue?</h3>\n'
            htmlout += f'<a href="/run/{prog}/y">Yes (may result in problems)</a>\n'
            htmlout += '</div></div>'
            self.write(handle, htmlout)
            return
        
        logging.debug(f'Attempting to run {prog}')
        try:
            os.system(f'sudo bash {cfg["task_dir"]}{prog}')
        except Exception as e:
            logging.error(f"Failed to run", exc_info=True)
        
        htmlout = f'<script>function taskRedir() {{window.location.href="/logs/{taskid}";;}}\n'
        htmlout += 'var x=setTimeout(taskRedir, 2500);</script>\n'
        htmlout += '<p>Attemping to take you to the task list for this program.</p>\n'
        self.write(handle, htmlout)
    
    def taskicon(self, fn):
        d = ent['tasks'][fn]
        icon = d.get('icon', 99)
        if isinstance(icon, int):
            icon = ii(icon)
        
        return strings['menubtn-narrow-icons-flat'].format(
            href=f'/run/{fn}',
            alt=fn, x=icon[0]*-100, y=icon[1]*-100,
            label=d.get("title", fn)
            )
    
    def page(self, handle, path):
        htmlout = '<div class="pageinner"><div class="head">'
        htmlout += f'<h2 class="pagetitle">Run Task</h2></div>\n'
        htmlout += '<div class="container list">\n'
        self.write(handle, htmlout)
        
        if not path[1].isdigit():
            self.taskpage(handle, path)
            return
        
        htmlout = ''
        for group, order in ent['group_order']:
            gtasks = ent['taskgroups'][group]
            if not gtasks:continue
            if not group.startswith('_'):
                if htmlout:htmlout += '<hr>\n'
                htmlout += f'<h2>{group}</h2>\n'
            
            for task in gtasks:
                htmlout += self.taskicon(task)
        
        htmlout += '</div></div>'
        self.write(handle, htmlout)


def register_pages():
    for k in list(globals()):
        if k.startswith('builtin_'):
            register_page(k, 'builtin')
        
        elif k.startswith('post_'):
            register_page(k, 'builtin_post')


def create_menus():
    menus['remort_buttons'] = []
    
    for m in menus['pages']:
        if m not in ent['builtin']:
            ent['builtin'][m] = builtin_menu(which=m)
    
    for m, v in ent['builtin'].items():
        icn = {'label': m, 'href': m, 'label2': ''}
        pagetype = v.pagetype
        if pagetype.startswith('builtin'):
            c = 'builtin'
            icn['label2'] = 'builtin'
            if '_' in pagetype:
                icn['label2'] = pagetype.split('_')[-1]
            
            if v.pages:
                icn['label2'] += ' pages'
            else:
                icn['href'] = '/'+icn['href']
        
        if c and '_' in pagetype:
            c += ' ' + pagetype.split('_')[-1]
        
        if icn['label2'] != '':
            icn['label'] = f"<b>{icn['label']}</b><br><i>{icn['label2']}</i>"
            del icn['label2']
        
        menus['remort_buttons'].append(icn)


def config_save():
    user_friendly_dict_saver(
        cfg['apd_dir'] + 'taskeroptions.json',
        cfg)
    
    user_friendly_dict_saver(
        cfg['apd_dir'] + 'taskermenus.json',
        menus,
        ignore_keys=['remort_buttons', 'page_buttons'])


def find_avialble_tasks():
    tGO = 'group_order'
    tTG = 'taskgroups'
    tUG = '_ungrouped'
    
    ent['tasks'] = {}
    ent['taskidfn'] = {}
    ent[tTG] = {tUG: []}
    taskg = ent[tTG]
    ent[tGO] = {tUG: 6979}
    
    for fn in os.listdir(cfg['task_dir']):
        if not fn.endswith('.sh'):continue
        data = {'filename': fn}
        
        for line in readfile(cfg['task_dir'] + fn).split('\n'):
            if not line.startswith('#'):break# no data
            
            line = line.split('\t')
            if len(line) != 3:continue
            data[line[1]] = json.loads(line[2])
        
        ent['tasks'][fn] = data# store data
        ent['taskidfn'][data.get('id', fn)] = fn
        logging.debug(data)
        
        # menu ordering
        group = data.get('group', tUG)
        order = data.get('order', 0)
        if group not in taskg:
            taskg[group] = []
            ent[tGO][group] = 0
        
        taskg[group].append((order, fn))
        
        if tGO in data and data[tGO] < ent[tGO][group]:
            ent[tGO][group] = data[tGO]
    
    for g, i in ent[tTG].items():# sort each group
        ent[tTG][g] = [y for x, y in sorted(i)]
    
    ent[tGO] = sorted(ent[tGO].items(), key=itemgetter(1))


def check_task(prog, task):
    global ent
    logging.debug(f'Cehcking {prog} {task}')
    
    data = ent['task_logs'][prog][task]
    fn = data['path'] + task
    if os.path.isfile(fn):
        mtime = os.path.getmtime(fn)
        data['mod'] = mtime
        d = datetime.fromtimestamp(mtime)
        data['dmod'] = d
        
        data['old'] = (datetime.now() - d).total_seconds() > 300


def check_running_tasks():
    
    for prog, tasks in ent['task_logs'].items():
        [check_task(prog, d[0])
         for n, d in enumerate(sorted(tasks.items(), reverse=True))
         if not d[1]['old'] or n == 0]


def find_runningg_tasks():
    global ent
    now = datetime.now()
    
    for logd in cfg['log_dirs']:
        for prog in os.listdir(logd):
            progd = logd + prog + '/'
            if not os.path.isdir(progd):
                continue# not program
            
            if prog not in ent['task_logs']:
                ent['task_logs'][prog] = {}
            
            for task in os.listdir(progd):
                if not (task[0].isdigit() and task.endswith('.txt')):
                    continue# not task log
                
                if task not in ent['task_logs'][prog]:
                    ent['task_logs'][prog][task] = {
                        'path': progd,
                        'mod': 0,
                        'old': False
                        }
                
                    check_task(prog, task)


def big_action_list_time(reload=0):
    logging.debug('Performing all actions')
    start = time.perf_counter()
    ent['built_at'] = datetime.now()
    
    load_global('cfg', 'taskeroptions.json')
    load_global('menus', 'taskermenus.json')
    config_save()
    
    create_menus()
    register_pages()
    
    find_avialble_tasks()
    check_running_tasks()
    find_runningg_tasks()
    
    logging.debug(f'Done in {time.perf_counter() - start}')


class post_logupdate(post_base):
    
    def __init__(self, title='', link='/_logupdate', icon=ii(99), pages=False):
        super().__init__(title, link, icon, pages)
        
    def post_logic(self, handle, pargs, data):
        ret = {'lines': []}
        has = data.get('has', 0)
        mod = data.get('mod', 0)
        
        if not isinstance(has, int):
            return {'lines': [], 'old': True, 'status': 'wtf has'}
        
        if not isinstance(has, int):
            return {'lines': [], 'old': True, 'status': 'wtf mod'}
        
        if not ('prog' in data and 'task' in data):
            return {'lines': [], 'old': True, 'status': 'missing fields'}
        
        prog, task = data['prog'], data['task']
        if prog not in ent['task_logs'] or task not in ent['task_logs'][prog]:
            return {'lines': [], 'old': True, 'status': 'not found'}
        
        check_task(prog, task)
        taskd = ent['task_logs'][prog][task]
        ret['old'] = taskd.get('old', False)
        ret['mod'] = taskd['mod']
        
        if taskd['mod'] != mod:
            ret['old'] = False
            with open(taskd['path'] + task) as fh:
                for n, line in enumerate(fh.readlines()):
                    if n >= has:
                        ret['lines'].append(line)
        
        return ret


class fa_req_handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        path_long = self.path[1:].lower()
        path_nice = urllib.parse.unquote(self.path)[1:]
        path_split = path_nice.lower().split('/')
        
        if path_split[-1] in ent['resources']:
            serve_resource(self, path_split[-1])
            return
        
        b = builtin_base()
        
        if ent['builtin'].get(path_split[0], b).pages is False:
            ent['builtin'][path_split[0]].serve(self, path_split)
            return
        
        elif path_split == ['']:
            home = ent['builtin'].get(cfg['homepage_menu'])
            
            if home is None:
                home = ent['builtin'].get('remort', b)
            
            home.serve(self, path_split)
            return
        
        elif path_split[0] == 'unstuck':
            ent['building_entries'] = False
            self.send_response(307)
            self.send_header('Location', '/')
            self.end_headers()
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
            ent['builtin'][path_split[0]].serve(self, path_split)
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


if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    init_logger('tasker', disp=':' in code_path)
    
    os.chdir(code_path)
    
    load_global('cfg', {
        'developer': False,
        
        'server_name': 'TASKER',
        'server_addr': '127.0.0.1',
        'server_port': 6979,
        
        'apd_dir': 'data/',
        'res_dir': 'res/',# prepend resource files
        'task_dir': 'tasks/',
        'log_dirs': ['log/'],
        
        'homepage_menu': 'menu',
        'dropdown_menu': 'menu',

        'static_cfg': False,
        'allow_data': False,
        })
    
    load_global('cfg', 'taskeroptions.json')
    
    load_global('menus', {
        'pages': {
            "menu": {
                "title": "Main Menu",
                "mode": "narrow-icons-flat",
                "buttons": "menu_buttons",
                "icon": [0, 5]
                },
            },
        'menu_buttons': [
            { "label": "remort", "href": "/remort" },
            { "label": "Run", "href": "run" },
            { "label": "Logs", "href": "logs" },
            ],
        })
    
    load_global('menus', 'taskermenus.json')
    
    if 'remort' not in menus['pages']:
        menus['pages']['remort'] = {
            "title": "Remort Menu",
            "mode": "wide-icons-flat",
            "buttons": "remort_buttons",
            "icon": [9, 9]
            }
    
    config_save()
    
    load_global('ent', {
        'resources': [
            'style.css',
            'parrot.svg',
            'icons.svg',
            'mark.js',
            'client.js',
            'chart.js',
            'logger.js',
            ],
        
        'builtin': {},
        'builtin_post': {},
        
        'building_entries': False,
        'tasks': {},
        'task_logs': {},
        
        'reentry_buttons': [
            (' rebuild', 'rebuild', 'Rebuild')
            ]
        })
    
    register_pages()
    
    for fn in ent['resources']:
        dfn = cfg['res_dir'] + fn
        fn = '_' + fn
        ent[fn] = b''
        if os.path.isfile(dfn):
            ent[fn] = readfile(dfn, mode='rb', encoding=None)

    big_action_list_time(reload=3)
    
    httpd = ThreadedHTTPServer(
            (cfg['server_addr'], cfg['server_port']),
            fa_req_handler)
    httpd.serve_forever()
