from onefad_web import *
from uuid import uuid4

ent['version'] = 9
ent['internal_name'] = 'tasker'

loggerlevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRIITCAL']

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


class log_filter(object):
    
    def __init__(self, level=None):
        self.levels = loggerlevels
        self.level = 0
        self.set_level(level)
    
    def set_level_digit(self, level):
        if 0 <= level < len(self.levels):
            self.level = level
    
    def set_level(self, level):
        if (isinstance(level, int) or
            (isinstance(level, str) and level.isdigit())):
            self.set_level_digit(int(level))
        
        elif isinstance(level, str):
            level = level.upper()
            if level not in self.levels:
                for l in self.levels:
                    if l.startswith(level):
                        level = l
                        break# fuzzy matched
                
                else:
                    return# fuzzy failed
            
            self.level = self.levels.index(level)
        
        # don't update if invalid
    
    def filter_line(self, line):
        for n, l in enumerate(self.levels):
            if f'\t{l}\t' in line:
                return n
        
        return -1
    
    def filter_all(self, lines):
        #if self.level == 0:return lines# no work needed
        
        trunc = []
        count = [0 for x in self.levels]
        add = True
        for line in lines:
            if len(line) > 0 and line[0].isdigit():
                # only modify if line starts with date
                add = self.filter_line(line)
                
                if add > -1:
                    count[add] += 1
            
            if add >= self.level:
                trunc.append(line)
        
        return trunc, count


class builtin_logs(builtin_base):
    
    def __init__(self, title='Logs', icon=22):
        super().__init__(title, icon)
        self.pagetype = 'builtin_tasker'
    
    def taskpage_latest(self, handle, path):
        pid = path[1]
        prog = ent['log_by_id'][pid]
        if pid not in ent['task_logs']:
            return False
        
        task = sorted(ent['task_logs'][pid].keys())[-1]
        path[2] = task
        return self.taskpage(handle, path)
    
    def taskpage(self, handle, path):
        pid = path[1]
        prog = ent['log_by_id'][pid]
        if pid not in ent['task_logs']:
            return False
        
        task = path[2][:-3].upper() + 'txt'
        if task not in ent['task_logs'][pid]:
            return False
        
        data = ent['task_logs'][pid][task]
        
        ldata = ent['log_data'][prog]
        fn = ldata['path'] + task
        title = ldata.get('name', ldata['prog'])
        
        htmlout = '<script src="/logger.js"></script>\n<div class="pageinner">'
        htmlout += f'<div class="head"><a href="/logs/{pid}"><h2 class="pagetitle"><span>{title}</span></h2></a></div>\n'
        htmlout += '<div class="container list">\n'
        htmlout += f'<p style="display:none" id="progName">{pid}</p>'
        diff = (datetime.now() - data['dmod']).total_seconds()
        htmlout += f'<p id="fileinfo"><span id="taskName">{task}</span> - Modified {self.ago(int(diff))}'
        if data.get('old'):
            htmlout += ' - <span id="isOld">Old</span>'
        
        htmlout += '</p>\n'
        
        self.write(handle, htmlout)
        
        lines = readfile(fn).split('\n')
        
        logf = log_filter(ldata.get('level'))
        if len(path) >= 4:
            logf.set_level(path[3])
            
        trunc, counts = logf.filter_all(lines)
        
        htmlout = '<div id="levelCount" class="linkthings centered">'
        for n, i in enumerate(loggerlevels):
            d = ['none', 'inherit'][counts[n] > 0]
            htmlout += f'<a class="log{i}" style="display:{d}" href="{i[0]}"><span>{counts[n]}</span> {i.title()}</a>'
        
        htmlout += '\n</div>\n'
        
        htmlout += '<div id="logOutput"></div>\n'
        self.write(handle, htmlout)
        
        actual = len(trunc)
        dl = cfg['display_lines']
        if dl > 0:
            trunc = trunc[-dl:]
        
        htmlout = '<script>\n'
        htmlout += f'var lines = {len(lines)};\n'
        htmlout += f'var level = {logf.level};\n'
        htmlout += f'var counts = {json.dumps(counts)};\n'
        htmlout += 'var logOutput = '
        self.write(handle, htmlout + json.dumps(trunc, indent='\t') + ';\n')
        
        htmlout = 'drawLogInit()</script>\n'
        if actual >= dl:
            htmlout += f'Trimmed to {dl} lines, full log {actual} lines long.'
        
        htmlout += '</div>'
        
        self.write(handle, htmlout)
        
        return True
    
    @staticmethod
    def ago(s):
        if s < 16:
            return f'just now'
        
        elif s < 61:
            return f'{s} seconds ago'
        
        elif s < 3601:
            return f'{s/60:0.0f} minutes ago'
        
        elif s < 86401:
            return f'{s/3600:.01f} hours ago'
        
        elif s < 604800:
            return f'{s/86400:.01f} days ago'
        
        elif s < 2629800:
            return f'{s/604800:.01f} weeks ago'
        
        elif s < 3153600001:
            return f'{s/2629800:.01f} months ago'
        
        else:
            return 'a long time ago'
    
    def loglink(self, pid, m, t, d):
        name = t.split('.')[0]
        mod = f'Modified {self.ago(int(m))}'
        
        return f'<a class="logitem" href="/logs/{pid}/{t}/"><span class="time">{name}</span><span class="mod">{mod}</span</a>\n'
    
    def tasklist(self, pid, showold):
        now = datetime.now()
        htmlout = ''
        sort = sorted([
            ((now - d['dmod']).total_seconds(), t, d)
            for t, d in ent['task_logs'][pid].items()])
        
        old = []
        for m, t, d in sort:
            if d.get('old'):
                old.append((m, t, d))
                continue
            
            htmlout += self.loglink(pid, m, t, d)
        
        if not (showold and old):
            return htmlout
        
        htmlout += '<h4>Old Logs:</h4\n>'
        
        for m, t, d in old:
            htmlout += self.loglink(pid, m, t, d)
        
        return htmlout
    
    def progpage(self, handle, path):
        pid = path[1]
        prog = ent['log_by_id'][pid]
        ldata = ent['log_data'][prog]
        title = ldata.get('name', ldata['prog'])
        htmlout = '<div class="pageinner"><div class="head">'
        htmlout += f'<h2 class="pagetitle"><span id="progName">{title}</span></h2></div>\n'
        htmlout += '<div class="container list">\n'
        
        htmlout += self.tasklist(pid, True)
        
        self.write(handle, htmlout)
    
    def loglistlink(self, pid):
        prog = ent['log_by_id'][pid]
        ldata = ent['log_data'][prog]
        title = ldata.get('name', ldata['prog'])
        htmlout = '<div class="tasklogbox">'
        htmlout += f'<a href="/logs/{ldata["id"]}">'
        htmlout += f'<span class="title">{title}</span>'
        logc = len(ent["task_logs"][pid])
        htmlout += f' ({logc:,})</a><br>\n'
        
        tl = self.tasklist(pid, False)
        if not tl:
            tl = '<p>No recent logs.</p>\n'
        
        htmlout += tl
        htmlout += '</div>'
        return htmlout
    
    
    def display_tasks(self, handle):
        for group, order in ent['log_group_order']:
            htmlout = '<div class="taskloglist">'
            
            gtasks = ent['log_group'][group]
            
            if not group.startswith('_'):
                self.write(handle, f'<h2>{group}</h2>\n')
            
            for task in gtasks:
                htmlout += self.loglistlink(task)
            
            self.write(handle, htmlout+'</div>')
    
    
    def page(self, handle, path):
        
        if len(path) >= 3 and path[2].endswith('.txt'):
            if self.taskpage(handle, path):
                return
        
        check_running_tasks()
        find_runningg_tasks()
        
        if len(path) >= 3 and path[2] == 'latest':
            if self.taskpage_latest(handle, path):
                return
        
        if path[-1] in ent['log_by_id']:
            self.progpage(handle, path)
            return
        
        htmlout = f'<div class="pageinner"><div class="head"><h2 class="pagetitle">{self.title}</h2></div>\n'
        htmlout += '<div class="container list">\n'
        self.write(handle, htmlout)
        
        self.display_tasks(handle)
        
        self.write(handle, '</div></div></div>')


class builtin_active(builtin_logs):

    def __init__(self, title='Active', icon=1):
        super().__init__(title, icon)
    
    def display_tasks(self, handle):
        self.write(handle, '<div class="taskloglist">')
        
        for group, order in ent['log_group_order']:
            gtasks = ent['log_group'][group]
            htmlout = ''
            
            for task in gtasks:
                htmlout += self.loglistlink(task)
            
            self.write(handle, htmlout)
        
        self.write(handle, '</div>')
    
    def loglistlink(self, pid):
        prog = ent['log_by_id'][pid]
        ldata = ent['log_data'][prog]
        title = ldata.get('name', ldata['prog'])
        htmlout = '<div class="tasklogbox">'
        htmlout += f'<a href="/logs/{ldata["id"]}">'
        htmlout += f'<span class="title">{title}</span>'
        logc = len(ent["task_logs"][pid])
        htmlout += f' ({logc:,})</a><br>\n'
        
        tl = self.tasklist(pid, False)
        if not tl:
            return ''
        
        return htmlout + tl + '</div>'


class builtin_run(builtin_logs):
    
    def __init__(self, title='Run', icon=11):
        super().__init__(title, icon)
    
    def do_it(self, data):
        cmd = cfg['script_types'].get(data['ext'], {}).get('cmd')
        if not cmd:
            return 'Don\'t know how to execute.'
        
        prog = data['filename']
        
        cmd = cmd.format(cfg['task_dir'] + prog)
        
        if data.get('sudo', True):
            cmd = 'sudo ' + cmd
        
        if not cfg.get('actually_run', True):
            return
        
        logging.info(f'Attempting to run {prog}')
        
        try:
            os.system(cmd)
            return
        
        except Exception as e:
            logging.error(f"Failed to run", exc_info=True)
            return 'Exception!'
    
    def taskpage(self, handle, path):
        if path[1] not in ent['tasks']:
            self.write(handle, f'<p>Could not find task script: {path[1]}</p>\n</div>')
        
        prog = path[1]
        data = ent['tasks'][prog]
        filename = data['filename']
        taskid = data.get('id', filename)
        check_running_task_dir(taskid)
        #print(prog, taskid)
        
        running = self.tasklist(taskid, False)
        if (data.get('preventMultiple') and
            running and path[-1] != 'y'):
            htmlout = '<p>This task is running or has ran recently:</p>\n'
            htmlout += running
            
            htmlout += '<br>\n<h3>Do you want to continue?</h3>\n'
            htmlout += f'<a href="/run/{prog}/y">Yes (may result in problems)</a>\n'
            htmlout += '</div></div>'
            self.write(handle, htmlout)
            return
        
        self.write(handle, '<p>Starting task...</p>')
        
        state = self.do_it(data)
        if state:
            htmlout = '<p>A broblem occurred.</p>\n'
            htmlout += f'<p>{state}</p>\n'
            self.write(handle, htmlout)
            return
        
        htmlout = f'<script>function taskRedir() {{window.location.href="/logs/{taskid}/latest/";;}}\n'
        htmlout += 'var x=setTimeout(taskRedir, 2500);</script>\n'
        htmlout += '<p>Attemping to take you to the log for this task.</p>\n'
        self.write(handle, htmlout)
    
    def taskicon(self, fn):
        d = ent['tasks'][fn]
        icon = d.get('icon', 99)
        if isinstance(icon, int):
            icon = ii(icon)

        ret = f'<div class="taskbutton"><a href="/run/{fn}" alt="{fn}">\n'
        x = icon[0]*-100
        y = icon[1]*-100
        ret += f'<i class="iconsheet ico-40" style="background-position:{x}% {y}%;"></i>\n'
        ret += f'<span class="menu-label"> {d.get("title", fn)}</span>\n</a>\n</div>\n'
        return ret
    
    def taskpickpage(self, handle, path):
        htmlout = ''
        for group, order in ent['task_group_order']:
            gtasks = ent['task_group'][group]
            if (not gtasks or group.startswith('#')) and 'all' not in path:
                continue# removed or hidden
            
            if not group.startswith('_'):
                if htmlout:
                    htmlout += '</div>\n\n'
                
                htmlout += '<div class="taskgroup">\n'
                htmlout += f'<h2 class="tasksheader">{group}</h2>\n'
            
            for task in gtasks:
                htmlout += self.taskicon(task)
        
        if htmlout:
            htmlout += '</div>\n\n'
        
        htmlout += '</div></div>'
        self.write(handle, htmlout)
    
    def page(self, handle, path):
        htmlout = '<div class="pageinner"><div class="head">'
        htmlout += f'<h2 class="pagetitle">Run Task</h2></div>\n'
        htmlout += '<div class="container list">\n'
        self.write(handle, htmlout)
        
        if len(path) < 2 or path[-1] == 'all' or path[-1].isdigit():
            self.taskpickpage(handle, path)
            return
        
        self.taskpage(handle, path)


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
    
    menus['all_pages_buttons'] = []
    rbcat = {}
    
    for m, c in list(ent['builtin'].items()):
        if type(c) == builtin_menu:
            del ent['builtin'][m]
    
    for m in menus['pages']:
        ent['builtin'][m] = builtin_menu(which=m)
    
    for m, v in ent['builtin'].items():
        c = ''
        pagetype = v.pagetype
        if cfg.get('purge') and hasattr(v, 'purge'):
            v.purge(1)
        
        icn = {'label': m, 'href': m, 'label2': ''}
        sorter = '_' + m
        c = pagetype.replace('_', ' ')
        if pagetype.startswith('remort'):
            if hasattr(v, 'marktype'):
                icn['label2'] = v.marktype
        
        elif pagetype == 'pages':
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


def config_save():
    user_friendly_dict_saver(
        cfg['apd_dir'] + 'taskeroptions.json',
        cfg)
    
    user_friendly_dict_saver(
        cfg['apd_dir'] + 'taskermenus.json',
        menus,
        ignore_keys=['all_pages_buttons', 'page_buttons'])


def group_flush(kind):
    for k in ['_group', '_group_order']:
        if kind + k in ent:
            del ent[kind + k]


def group_manage(kind, thing, data):
    groupd = kind + '_group'
    if groupd not in ent:
        ent[groupd] = {'_ungrouped': []}
        ent[groupd + '_order'] = {'_ungrouped': 6979}
    
    groupd, groupo = ent[groupd], ent[groupd + '_order']
    
    group = data.get('group', data.get('log_dir', '_ungrouped'))
    order = data.get('order', 0)
    if group not in groupd:
        groupd[group] = []
        groupo[group] = 0
    
    groupd[group].append((order, thing))
    
    order = data.get('group_order')
    if isinstance(order, int) and order < groupo[group]:
        groupo[group] = order


def group_sort(kind):
    kind += '_group'
    
    for g, i in ent[kind].items():# sort each group
        ent[kind][g] = [y for x, y in sorted(i)]
    
    kind += '_order'
    ent[kind] = sorted(ent[kind].items(), key=itemgetter(1))


def find_avialble_tasks():
    ent['tasks'] = {}
    group_flush('task')
    
    for fn in os.listdir(cfg['task_dir']):
        for ext, data in cfg['script_types'].items():
            if fn.lower().endswith(ext):
                comment = data.get('comment', '//')
                break
        
        else:
            continue
        
        data = {'filename': fn, 'ext': ext}
        
        for line in readfile(cfg['task_dir'] + fn).split('\n'):
            if not line.startswith(comment):break# no data
            
            line = line.split('\t')
            if len(line) != 3:continue
            data[line[1]] = json.loads(line[2])
        
        safe = fn.replace('.', '_')
        
        ent['tasks'][safe] = data# store data
        logging.debug(data)
        
        group_manage('task', safe, data)
    
    group_sort('task')


def check_task(pid, task):
    global ent
    logging.debug(f'Cehcking {pid} {task}')
    
    data = ent['task_logs'][pid][task]
    prog = ent['log_by_id'][pid]
    info = ent['log_data'][prog]
    fn = info['path'] + task
    if os.path.isfile(fn):
        mtime = os.path.getmtime(fn)
        data['mod'] = mtime
        d = datetime.fromtimestamp(mtime)
        data['dmod'] = d
        
        data['old'] = (datetime.now() - d).total_seconds() > 300
    
    return data


def check_running_task_dir(pid):
    tasks = ent['task_logs'].get(pid, {})
    
    for n, d in enumerate(sorted(tasks.items(), reverse=True)):
        if not d[1]['old'] or n == 0:
            check_task(pid, d[0])


def check_running_tasks():
    
    for prog in ent['task_logs']:
        check_running_task_dir(prog)


def log_info(progd, make=True):
    infod = progd + 'info.json'
    data = {}
    exists = os.path.isfile(infod)
    if exists:
        data = read_json(infod)
    
    if 'id' not in data:
        data['id'] = str(uuid4())
        exists = False
    
    ent['log_by_id'][data['id']] = progd
    
    if make and not exists:
        save_json(infod, data)
    
    return data


def find_runningg_tasks():
    global ent
    if ent.get('fru_running'):
        return
    
    ent['fru_running'] = True
    now = datetime.fromisoformat('2000-01-01')
    
    group_flush('log')
    
    for logd in cfg['log_dirs']:
        if not logd.endswith('/'):
            logd += '/'
        
        if not os.path.isdir(logd):
            continue
        
        for prog in os.listdir(logd):
            progd = logd + prog + '/'
            if not os.path.isdir(progd):
                continue# not program
            
            progi = progd
            data = {
                'path': progd,
                'log_dir': logd,
                'prog': prog
                }
            
            data = {**log_info(progd), **data}
            pid = data['id']
            
            ent['log_data'][progd] = data
            group_manage('log', pid, data)
            
            if pid not in ent['task_logs']:
                ent['task_logs'][pid] = {}
            
            for c, task in enumerate(sorted(os.listdir(progd), reverse=True)):
                if not (task[0].isdigit() and task.endswith('.txt')):
                    
                    continue# not task log
                
                if task not in ent['task_logs'][pid]:
                    old = c > 20
                    
                    mod = datetime.strptime(task[:-4], '%Y-%m-%dT%H-%M-%S.%f')
                    
                    ent['task_logs'][pid][task] = {
                        'mod': mod.timestamp() * 1000,
                        'dmod': mod,
                        'old': old
                        }
                    
                    if not old:
                        check_task(pid, task)
    
    group_sort('log')
    ent['fru_running'] = False


def big_action_list_time(reload=0):
    logging.info('Performing all actions')
    start = time.perf_counter()
    ent['built_at'] = datetime.now()
    
    ent['building_entries'] = True
    
    read_config()
    register_pages()
    create_menus()
    save_config()
    
    find_avialble_tasks()
    check_running_tasks()
    find_runningg_tasks()
    
    logging.info(f'Done in {time.perf_counter() - start}')
    ent['building_entries'] = False


class post_logupdate(post_base):
    
    def __init__(self, title='', icon=99):
        super().__init__(title, icon)
    
    def post_logic(self, handle, pargs, data):
        ret = {'output': []}
        has = data.get('has', 0)
        mod = data.get('mod', 0)
        
        if not isinstance(has, int):
            return {'output': [], 'old': True, 'status': 'wtf has'}
        
        if not isinstance(mod, int):
            return {'output': [], 'old': True, 'status': 'wtf mod'}
        
        if not ('prog' in data and 'task' in data):
            return {'output': [], 'old': True, 'status': 'missing fields'}
        
        pid, task = data['prog'], data['task']
        prog = ent['log_by_id'].get(pid)
        ldata = ent['log_data'][prog]
        logf = log_filter(ldata.get('level'))
        
        if 'level' in data:
            logf.set_level(data['level'])
        
        if pid not in ent['task_logs'] or task not in ent['task_logs'][pid]:
            return {'output': [], 'old': True, 'status': 'not found'}
        
        taskd = check_task(pid, task)
        ret['old'] = taskd.get('old', False)
        ret['mod'] = taskd['mod']
        ret['lines'] = has
        
        if taskd['mod'] != mod:
            if has > 1:has -= 1
            ret['old'] = False
            lines = readfile(ldata['path'] + task).split('\n')
            ret['lines'] = len(lines)
            
            ret['output'], ret['counts'] = logf.filter_all(lines[has:])
            
        
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
        target = ent['builtin'].get(path_split[0])
        
        if target and target.pages is False:
            target.serve(self, path_split)
            return
        
        elif path_split == ['']:
            home = ent['builtin'].get(cfg['homepage_menu'])
            
            if home is None:
                home = ent['builtin']['all_pages']
            
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
        
        elif target:
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
    time.sleep(2)
    httpd.shutdown()


if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    if code_path:
        os.chdir(code_path)
    
    name = ent.get('internal_name', '')
    if len(name) < 4:name += 'srv'
    init_logger(name, disp=':' in code_path, level=logging.INFO)
    
    load_global('cfg', {
        'developer': False,
        
        'server_name': name,
        'server_addr': '127.0.0.1',
        'server_port': 6979,
        
        'apd_dir': 'data/',
        'res_dir': 'res/',# prepend resource files
        'task_dir': 'tasks/',
        'log_dirs': ['log/'],
        'display_lines': 500,
        
        'homepage_menu': 'menu',
        'dropdown_menu': 'menu',

        'static_cfg': False,
        'allow_data': False,
        
        'script_types': {
            '.sh': {'cmd': 'bash {}', 'comment': '#'}
            }
        })
    
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
            { "href": "all_pages" },
            { "href": "run" },
            { "href": "logs" },
            ],
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
            ],
        
        'builtin': {},
        'builtin_post': {},
        
        'config_file': f'{name}_options.json',
        'menu_file': f'{name}_menus.json',
        'strings_file': f'{name}_strings.txt',
        
        'building_entries': False,
        'tasks': {},
        'log_data': {},
        'task_logs': {},
        'log_by_id': {},
        
        'reentry_buttons': [
            (' rebuild', 'rebuild', 'Rebuild')
            ]
        })
    
    big_action_list_time(reload=3)
    
    httpd = ThreadedHTTPServer(
            (cfg['server_addr'], cfg['server_port']),
            fa_req_handler)
    httpd.serve_forever()
