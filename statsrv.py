from onefad_functions import *

ent['version'] = '26'

end_of_time = datetime.fromisoformat('9999-01-01')

def fromiso(d):
    f = '%Y-%m-%dT%H:%M:%S'[:len(d)-2]
    return datetime.strptime(d, f)


def load_apdmfile(path, pre, fn):
    global apdmm, apdm
    
    data = apdm.get(fn, appender())
    data.read(path + pre + fn, encoding='iso-8859-1')
    
    prop = apdmm.get(fn, {})
    if '//' in data:
        prop = data['//']
        del data['//']
    
    apdmm[fn] = apdmm.get(fn, {})
    
    for k, v in prop.items():
        apdmm[fn][k] = v

    if prop.get('type') == 'collection':
        if 'name_plural' not in apdmm[fn]:
            name = apdmm[fn].get('name', '')
            if not name:
                name = fn
            else:
                name += 's'
            
            apdmm[fn]['name_plural'] = name
        
        for k, d in list(data.items()):
            if d.get('delete', False):
                del data[k]
    
    elif prop.get('list', False) != False:
        if compare_for(prop, 'users'):
            data.setd({x.replace('_', '').lower(): 0 for x in data})
    
    else:
        for k, v in list(data.items()):
            if not v or list(v) == ['None']:
                del data[k]
            
            elif len(v) > 1:
                if v[0] != 'n/a':
                    data[k] = v
    
    apdm[fn] = data
    return prop.get('order', 1), fn


def load_apd():
    global ent, apdmm, apdm, dpref, dprefm
    
    logging.info('Reading Mark files')
    
    for k in ['dprefm', 'dpref']:
        if k not in globals():
            globals()[k] = {}

    apdmark = {}
    
    scandir = cfg['mark_dir']
    
    for f in os.listdir(scandir):
        if '.' in f or f[-1].isdigit():
            continue
        
        if f.startswith('ds_'):
            apdmark[f[3:]] = 0
    
    order = []
    for apdfile in apdmark:
        order.append(
            load_apdmfile(scandir, 'ds_', apdfile))
    
    ent['apdmark'] = [y for x, y in sorted(order)]
    
    ent['loaded_apd'] = True


def load_user_config():
    global ent
    
    read_config()
    
    if 'all_pages' not in menus['pages']:
        menus['pages']['all_pages'] = {
            "title": "All Pages",
            "mode": "wide-icons-flat",
            "buttons": "all_pages_buttons",
            "icon": [9, 9]
            }
    
    logging.info('Loaded strings')


def register_dynamic():
    global ent, menus
    
    for m, d  in apdmm.items():
        
        if d.get('type', False) == 'collection':
            name = d.get('name', m)
            
            if compare_for(d, 'posts', sw=True):
                if name.lower() not in ent['builtin']:
                    ent['builtin'][name.lower()] = builtin_collection(m)
            
            else:
                if name.lower() not in ent['builtin']:
                    ent['builtin'][name.lower()] = mort_collection(m)
            
            name_list = d.get('name_plural', name + 's')
            name_listl = name_list.lower()
            ent['_collections'][name_listl] = m
            
            if m not in ent['link_to']:
                ent['link_to'][m] = f'/{name}/{{}}/1'
            
            if name_listl not in ent['builtin']:
                ent['builtin'][name_listl] = mort_collection_list(m, name_list)
        
        if compare_for(d, 'posts', sw=True):
            #print(m, d, 'postmark')
            continue
            mode = 'posts'
            cla = mort_postamark
        
        elif compare_for(d, 'url'):
            #print(m, d, 'menumark')
            continue
            mode = 'other'
            cla = builtin_menu_mark
        
        else:
            #print(m, d, 'other')
            mode= 'other'
            cla = mort_amark
        
        for v in d.get('values', []):
            if v not in ent['builtin']:
                ent['builtin'][v] = cla(m, v)
    
    
    for m in menus['pages']:
        if m not in ent['builtin']:
            ent['builtin'][m] = builtin_menu(which=m)
    
    
    
    menus['all_pages_buttons'] = []
    rbcat = {
        'builtin': [],
        'builtin menu': [],
        'Remort': []
        }
    
    for m, v in ent['builtin'].items():
        c = ''
        pagetype = v.pagetype
        if not pagetype.startswith('builtin') and cfg.get('purge'):
            v.purge(1)
        
        icn = {'label': m, 'href': m, 'label2': ''}
        if pagetype.startswith('remort'):
            icn['label2'] = v.marktype
            c = 'Remort'
        
        elif pagetype == 'eyde':
            icn['label2'] = 'mark page'
            c = 'Eyde'
        
        elif pagetype.startswith('builtin'):
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
        
        if c not in rbcat:
            rbcat[c] = []
        
        rbcat[c].append((m, icn))
    
    for c, d in rbcat.items():
        menus['all_pages_buttons'].append({'type': 'section', 'label': c})
        menus['all_pages_buttons'] += [icn for m, icn in sorted(d)]


def apdm_divy():
    global ent, dprefm, dpref
    
    dprefm = {}
    dpref = {}
    
    ent['mark_buttons'] = {
        x: mark_button(mark=x) for x in ent.get('apdmark', [])
        }
    
    if not ent['mark_buttons']:
        return
    
    for apdfile in ent['apdmark']:
        if apdmm[apdfile].get('type') == 'collection':
            
            dprefm[apdfile] = {**apdmm[apdfile], 'apdm': apdfile}
            
            data = apdm[apdfile]
            dpref[apdfile] = set()
            for d, k, n in sort_collection(apdfile, rebuild=True):
                dpref[apdfile].update(set(data[k].get('items', [])))
        
            dpref[apdfile] = {x: 0 for x in dpref[apdfile]}
            continue
        
        elif apdmm[apdfile].get('list'):
            dprefm[apdfile] = apdmm[apdfile]
            dprefm[apdfile]['apdm'] = apdfile
            dpref[apdfile] = apdm[apdfile]
            continue
        
        for k, v in divy(apdm[apdfile]).items():
            dprefm[k] = apdmm[apdfile]
            dprefm[k]['apdm'] = apdfile
            dpref[k] = v


def build_entries(reload=0):
    global ent
    
    if ent['building_entries']:
        logging.warning('Am building')
        return
    
    ent['building_entries'] = True
    ent['generated'] = datetime.now()
    logging.info('Building')
    load_user_config()
    
    if reload > 1:
        init_apd()
        load_apd()
    
    apdm_divy()
    
    if reload > 1:
        sort_records()
    
    ent['mark_buttons'] = {
        x: mark_button(x) for x in apdmm
        }
    
    group_tags(force=True)
    save_config()
    
    register_dynamic()
    
    ent['building_entries'] = False
    logging.info('Ready.')


def sort_records():
    global ent, cfg
    
    ent['targets'] = {x.lower(): x for x in cfg['targetorder']}
    ent['apd'] = {
        'total': {'posts': {}, 'period': {}}
        }
    
    total_period = {}
    merge_period = {}
    
    for fn in sorted(os.listdir(cfg['data_dir'])):
        file = fn.lower()
        if file.endswith('_posts'):
            part = 'posts'
        
        elif file.endswith('_trunc'):
            part = 'period'
        
        else:
            continue
        
        user = file[:-6]
        logging.debug(f'Found {user} {part}')
        
        if user not in ent['apd']:
            ent['apd'][user] = {}
            if user not in ent['targets']:
                ent['targets'][user] = fn[:-6]
                cfg['targetorder'].append(fn[:-6])
        
        data = appender()
        data.read(cfg['data_dir'] + fn, dotime=True)
        ent['apd'][user][part] = data
        
        if user in cfg['total_ignore']:
            continue
        
        if part == 'posts':
            for t, p in ent['apd'][user]['posts'].items():
                ent['apd']['total']['posts'][t] = {
                    **p,
                    'user': ent['targets'][user]}
        
        if part == 'period':
            for t, p in ent['apd'][user]['period'].items():
                t = t[:13]
                if t not in total_period:
                    total_period[t] = {}
                
                total_period[t] = {**total_period[t], **p}
    
    last_period = None
    last_date = datetime(2000, 1, 1)
    
    for periodi, period_values in sorted(total_period.items()):
        period_date = fromiso(periodi)

        if last_date + timedelta(minutes=20) > period_date:
            for p in ent['apd']['total']['posts']:
                if (p not in merge_period[last_period] and
                    p in total_period[periodi]):
                    merge_period[last_period][p] = total_period[periodi][p]
            
        else:
            merge_period[periodi] = total_period[periodi]
            last_period = periodi
            last_date = period_date
    
    ent['apd']['total']['period'] = merge_period
    
    for m in menus['pages']:
        if m not in ent['builtin']:
            ent['builtin'][m] = builtin_menu(which=m)

def group_tags(ret=[], force=False):
    global ent
    
    if force or ent.get('tags') == None:
        ent['tags'] = {}
        tagi = set()# gotta go fast
        for post, info in sorted(ent['apd']['total']['posts'].items()):
            ptags = info['tags']
            if type(ptags) == str:
                ptags = [ptags]
            
            for tag in ptags:
                tag = tag.lower().replace('-', '').replace('_', '')
                if tag not in tagi:
                    ent['tags'][tag] = []
                    tagi.add(tag)
                
                ent['tags'][tag].append(post)
        
        for tag, items in ent['tags'].items():
            ent['tags'][tag] = sorted(set(items))
    
    if not ret:
        return ent['tags']
    
    # get the first one
    out = ent['tags'].get(ret[0], [])
    for tag in ret[1:]:
        out = [x for x in ent['tags'].get(tag, []) if x in out]
        # skip if empty
        if not out:
            break
    
    return out


def timestamp_disp(t):
    if type(t) != datetime:
        t = datetime.utcfromtimestamp(t)
    
    return t.strftime('%b %d, %Y %H:%M')


class builtin_info(builtin_base):
    
    def __init__(self, title='Info', icon=[3, 3]):
        super().__init__(title, icon)
    
    def stat(self, handle, label, value):
        if type(value) == int:
            value = f'{value:,}'
        
        self.write(handle, f'<p>{label}: {value}</p>\n')
    
    def page(self, handle, path):
        now  = datetime.now()
        doc = '<div class="head"><h2 class="pagetitle">Info</h2></div>\n'
        doc += '<div class="container list">\n'
        self.write(handle, doc)
        
        self.stat(handle, 'Server Time Now', timestamp_disp(now))
        self.stat(handle, 'Last Rebuilt', timestamp_disp(ent['generated']))
        
        doc = '<h2>Stats from:</h2>\n'
        for user in cfg['targetorder']:
            doc += f'<p>{user}</p>\n'
        
        self.write(handle, doc)


def matchmode(v, m):
    if '@' + v in m:
        return True
    
    elif '!@' + v in m:
        return False
    
    return None


def overicon(kind, thing, con=None):
    return '<div class="overicn">' + create_linktodathing(
        kind, thing, retmode='markonly', con=con) + '</div>'


class mort_base(builtin_base):

    def __init__(self, marktype='', title='', link='/{}/1', icon=ii(79), con=None):
        super().__init__()
        self.pagetype = 'remort'
        self.marktype = marktype
        self.title = title
        self.link = link
        self.pages = True
        self.icon = icon
        if self.icon is None:
            self.icon = ii(79)
        
        self.items = None
        self.iteminf = [None, None, None]
        self.datas = {}
        self.clear_threshold = 0
        self.con = con
        self.hide_empty = self.marktype == 'users'
        self.headtext = ['', '', '']
        
        self.can_list = True
        self.content_type = 'text/html'
        
        self.path_parts = 2
        self.page_options = [
            ['reversed'],
            ['count']
            ]
    
    def page(self, handle, path, text='', head=True):
        self.gimme(path)
        self.build_page(handle, path, head=head, text=text)
    
    def gimme_idc(self):
        self.items = []
        self.datas = {}
    
    def gimme(self, pargs):
        if self.items is None:
            self.gimme_idc()
    
    def purge(self, strength):
        if self.clear_threshold <= strength:
            self.items = None
            self.datas = {}
    
    @staticmethod
    def item_sorter_ez(i, d):
        if type(d) != int:d = len(d)# int int make int
        return [d] + list(i)
    
    @staticmethod
    def maketup(items):
        if items and not isinstance(items[0], tuple):
            return [(i, 0) for i in items]
        
        return items
    
    @staticmethod
    def page_count(flen, index_id, pc=''):
        # used to select elements per page of mort and eyde
        
        if type(pc) != int:
            pc = cfg.get('post_count', 25)
        
        last_page = max(math.ceil(flen / pc), 1)
        
        sa = (index_id - 1) * pc
        ea = index_id * pc
        
        if 0 < flen % pc <= cfg.get('over', 5):
            # bring extra items over rather than a short page
            last_page = max(last_page - 1, 1)
            if index_id == last_page:
                ea = flen
        
        if index_id < 1:# wrap back around
            index_id += last_page
            if index_id == last_page:
                ea = flen
        
        return last_page, sa, ea

    def item_sorter(self, data, items, mincount):
        so = sorted(self.item_sorter_ez(i, data.get(i[0], 0))
                    for i in items)
        
        return [tuple(x[1:])
                for x in so
                if x[0] >= mincount]
    
    def build_page(self, handle, pargs, head=True, text=''):
        index_id = 1
        pf = []
        
        if pargs:
            if isinstance(pargs[-1], str) and pargs[-1].isdigit():
                pargs[-1] = int(pargs[-1])
            
            if isinstance(pargs[-1], int):
                index_id = pargs[-1]
                if len(pargs) > 2:
                    pf = str(pargs[-2]).split(' ')
            
            elif len(pargs) > 1:
                pf = str(pargs[-1]).split(' ')
        
        items = self.items
        
        if items is None:
            items = []
        
        items = self.maketup(items)
        
        cols = {}
        
        done = []
        for m, d in apdmm.items():
            if not compare_for(d, self.marktype):
                continue
            
            mt = d.get('type', 'idk')
            if mt in ['multibutt', 'list']:
                
                if mt =='list':
                    if '!@' + m in pf:
                        mset = set(apdm[m])
                        items = [i for i in items if i[0] not in mset]
                        continue
                
                for v in d.get('values'):
                    mm = matchmode(v, pf)
                    
                    if mm is None:
                        continue
                    
                    done.append(v)
                    
                    mset = set(dpref[v])
                    items = [i for i in items if (i[0] in mset) == mm]
            
            elif mt == 'collection':
                cols[d.get('name', m).lower()] = m
                done.append(m)
        '''idk even
        for m, d in fpref.items():
            if not compare_for(d, self.marktype):
                continue
            
            if m in done:
                continue
            
            mm = matchmode(m, pf)
            if mm is None:
                continue
            
            mset = set(i[0] for i in maketup(ent['builtin'][m].get_items()))
            items = [i for i in items if (i[0] in mset) == mm]
        '''
        mincount = 'cull' in pf
        docat = self.marktype == 'users' and cfg['docats']
        cull = self.hide_empty or mincount or docat
        if 'nocull' in pf:
            cull = False
            mincount = -200
        
        i2 = []
        for i in items:
            t = i
            if isinstance(i, tuple) or isinstance(i, list):
                t = i[0]
            
            d = self.datas.get(t, '')
            if not isinstance(d, int):d = len(d)
            if self.marktype == 'users' and cull:
                d, perc = users_marked.get(t, (0, 0))
            
            i2.append(list(i) + [d])
        
        items = i2
        del i2
        
        tmark = {}
        for x in pf:
            
            if x.startswith('@'):
                tmark[x[1:]] = True
            
            elif x.startswith('!@'):
                tmark[x[2:]] = False
            
            elif '>' in x:
                cull = False
                x = x.split('>')
                if len(x) < 2:continue
                gt = int(mincount)
                pr = 1
                lt = math.inf # should be impossibe to reach
                
                if x[0].isdigit():
                    lt = int(x[0])
                else:
                    pr = ord(x[0]) - 97
                
                if x[1].isdigit():
                    gt = int(x[1])
                else:
                    pr = ord(x[1]) - 97
                
                if len(x) == 3:
                    if x[2].isdigit():
                        gt = int(x[2])
                
                if pr == 11:# 11 = L for Length
                    items = [i for i in items
                             if lt > ent['ustats'].get(i[0], .1) > gt]
                
                else:
                    items = [i for i in items if lt > i[pr] > gt]
        
        # this is a hack, i need to make this cleaner
        for m, e in tmark.items():
            t = ''
            if ':' in m:
                t = m.split(':')
                m = t[0]
                t = ':'.join(t[1:])
            
            if m not in cols:
                continue
            
            m = cols[m]
            v = find_collection(m, t)
            if v is False:
                continue
            
            v = set(apdm[m][v]['items'])
            items = [i for i in items if (i[0] in v) == e]
        
        if cull:
            items = [i for i in items if i[2]]
        
        # pick  what to sort by
        if not items:pass
        
        elif 'count' in pf:
            items = self.item_sorter(self.datas, items, mincount)
        
        elif 'unmarked' in pf:# only for users
            um = {i: v[0] for i, v in users_marked.items()}
            items = self.item_sorter(um, items, mincount)
        
        elif 'ustats' in pf:
            items = self.item_sorter(ent['ustats'], items, mincount)
        
        else:
            # arbitray data yay
            for x in range(len(items[0])):
                if f'p{x}' in pf:
                    items = sorted([[i[x]] + list(i) for i in items])
                    items = [tuple(x[1:]) for x in items]
                    break
        
        if 'reversed' in pf:
            items = list(reversed(items))
        
        #mode = pargs[0]
        if self.can_list:# nothing good would come from that
            seq = {'query': '/' + '/'.join([str(x) for x in pargs]), 'icon': self.icon}
            seq['items'] = []
            for i in items:
                if type(i) in [tuple, list]:seq['items'].append(i[0])
                else:seq['items'].append(i)
            
            '''ent['_lists'][self.marktype] = seq'''
        
        count = len(items)
        last_page, sa, ea = self.page_count(
            count,
            index_id,
            pc=cfg.get('list_count', 15))
        
        if index_id < 1:
            index_id += last_page
        
        nav = template_nav(self.title, index_id, last_page, enc=False)
        
        h = ''
        h += f'''<!--\nclass: {type(self).__name__}
marktype: {self.marktype}\nlink: {self.link}\ntitle: {self.title}
hide_empty: {self.hide_empty}\n-->'''
        
        if head:
            h += f'<div class="head">\n{nav}</div>\n'
        
        h += f'<div class="container list">\n{text}'
        h += self.headtext[0]
        h += f'<p>{count:,} items</p>\n'
        h += self.headtext[1]
        
        for i in items[sa:ea]:
            if type(i) in [list, tuple]:
                item = i[0]
                
            else:
                item = i
            
            h += self.build_item(i, self.datas.get(item, None), 'aaaaaaaaaaaaaaaaaaaaaa')
        
        h += f'\n</div><div class="foot">{nav}\n<br>'
        
        h += self.headtext[2]

        self.write(handle, h)
    
    def build_label(self, i, item, data, mode):
        
        if self.marktype == 'usersets':
            mdata = []
            for d in data:
                mdata += users.get(d, [])
        else:
            mdata = data
        
        f = pick_thumb(mdata)
        l = f'/t/{cfg.get("image_dir","im/")}{f}'
        if cfg['remote_images'] != '':
            l = cfg['remote_images'].format(f)
        
        label = f'<img loading="lazy" src="{l}" /><br>'
        label = overicon(self.marktype, item, con=self.con) + label
        
        if type(data) != int:
            data = len(data)
        
        if self.marktype == 'users' and cfg['docats']:
            data, perc = users_marked.get(item, (0, 0))
        
        labelt = [item, '-', wrapme(data)]
        
        if self.marktype == 'users':
            labelt.append(wrapme(ent['ustats'].get(item, '?'), f='({:,})'))
        
        for pos, inf in enumerate(self.iteminf):
            if inf is None or pos >= len(i):
                continue
            
            if inf[0] == 'str':
                if len(inf) == 2:f = inf[1]
                else:f = '{}'
                labelt.append(f.format(i[pos]))
            
            elif inf[0] == 'int':
                if len(inf) == 2:f = inf[1]
                else:f = '{:,}'
                labelt.append(wrapme(i[pos], f=f))
            
            elif inf[0] == 'date':
                if len(inf) == 2:f = inf[1]
                else:f = ' {}'
                labelt.append(f.format(jsdate(i[pos]).isoformat()[:10]))
            
            elif inf[0] == 'replace':
                if len(inf) != 2:continue
                labelt[inf[1]] = i[pos]
        
        return label + ' '.join(labelt)
    
    def build_item(self, i, data, mode):
        if type(i) in [tuple, list]:item = i[0]
        else:item = i
        
        h = f'<!-- {i} -->\n'
        
        if data is None:
            logging.info(f'No data for item: {item}')
            data = []
        
        artm = markicons_for(self.marktype, item)
        
        href = create_linktodathing(self.marktype, item, con=self.con, retmode='href')
        
        h += strings['thumb'].format(self.link.format(href), self.build_label(i, item, data, mode), ' ' + artm)
        
        return h
    
    def ez_build_item(self, i):
        return self.build_item(i, self.datas.get(i), self.marktype)
    
    def get_items(self):
        return self.items


class get_icon_collection(builtin_base):
    
    def get_icon(self, path):
        name = False
        if len(path) > 1:
            name = find_collection(self.colname, path[1])
        
        if name is False:
            return self.icon
        
        data = apdm[self.colname][name]
        if 'icon' in data:
            return data['icon']
        
        return self.icon
    
    def propButton(self, escname, markact, icon, state=True):
        if isinstance(icon, int):
            icon = ii(icon)
        
        if state:
            state = ['', ' on'][self.data.get(markact, False)]
        
        return ''#butt_maker(
            #escname, markact, 'propMagic(this)',
            #mark_button.icon_html(None, icon, 60),
            #state)
    
    def propCluster(self, escname):
        h =  '<br>\nOptions:\n'
        h += self.propButton(escname, 'lock', 50)
        h += self.propButton(escname, 'pin', 52)
        h += self.propButton(escname, 'sortmepls', 'Sort by ID', state='')
        h += self.propButton(escname, 'delete', 'Delete')
        return h


def mimic_data(mimic, pargs):
    if mimic in ent['builtin']:
        ent['builtin'][mimic].gimme(pargs)
        return ent['builtin'][mimic].datas
    
    else:
        return None


class mort_collection(mort_base, get_icon_collection):
    
    def __init__(self, colname):
        self.colname = colname
        marktype = apdmm[colname].get('for', 'posts')
        title = colname
        link = lister_linker(marktype)
        icon = apdmm[colname].get('icon', None)
        super().__init__(marktype, title, link, icon)
        self.hide_empty = False
        self.pagetype = 'remort_mark_item'
        self.path_parts = 3
    
    def gimme(self, pargs):
        name = find_collection(self.colname, pargs[1])

        if name is False:
            self.title = ''
            self.headtext = ['', '', '']
            self.purge(0)
            return
        
        self.title = name
        data = apdm[self.colname][name]
        self.data = data
        self.items = data['items']
        
        escname = re.sub(r'\W+', '', name.lower())
        h = f'<script>var con="{self.colname}";</script>\n'
        h += self.propCluster(escname)
        
        self.headtext[0] = h
        
        m = mimic_data(self.marktype, pargs)
        if m is None:
            self.datas = {}
        
        else:
            self.datas = m


class mort_amark(mort_base):
    
    def __init__(self, mark, val):
        self.mark = mark
        title = val
        self.val = val
        self.mdata = apdmm[mark]
        marktype = self.mdata.get('for', 'posts')
        icon = self.mdata.get('icon', self.mark)
        bp = self.mdata['values'].index(val)
        
        if len(self.mdata.get('valueicon', [])) > bp:
            icon = self.mdata['valueicon'][bp]
        
        link = lister_linker(marktype)
        
        super().__init__(marktype, title, link, icon)
        self.pagetype = 'remort_mark'
        if marktype == 'folders':
            self.iteminf[0] = ['str', '<br>id {}']
            self.iteminf[2] = ['replace', 0]
    
    def get_items(self):
        items = []
        for pname, pdate in dpref.get(self.val, {}).items():
            if self.marktype == 'folders':
                d = apdfafol.get(pname, {})
                items.append((
                    pname,
                    len(d.get('items', [])),
                    d.get('title', pname)))
            
            else:
                items.append((pdate, pname))
        
        if self.marktype != 'folders':
            items = [(n, d) for d, n in sorted(items)]
        
        return items
    
    def gimme(self, pargs):
        m = None
        if 'nomimic' not in pargs:
            m = mimic_data(self.marktype, pargs)
        
        if m is None:self.datas = {}
        else:self.datas = m
        
        if self.items is None:
            self.items = self.get_items()


class mort_tags(mort_base):
    
    def __init__(self, marktype='tags', title='Tags', link='/tag/{}/1', icon=ii(10)):
        super().__init__(marktype, title, link, icon)
    
    def get_items(self):
        return list(ent['tags'].keys())
    
    def gimme_idc(self):
        group_tags()
        self.items = self.get_items()
        self.datas = ent['tags']


def get_ext(i):
    return apdm.get('extovr', {}).get(i, ['png'])[0]

def pick_thumb(posts, do_ext=True):
    if isinstance(posts, int):
        posts = []#hack
    
    for i in posts[::-1]:
        d = get_ext(i)
        if file_category(d) == 'image':
            if do_ext:i += '.' + d
            return i
    
    return 'parrot.svg'


def trtd(things):
    ret = '<tr>'
    for t in things:
        ret += f'\n\t<td>{t}</td>'
    
    return ret + '\n</tr>\n'


class builtin_pie(builtin_base):
    
    def __init__(self, title='Pie', icon=None):
        super().__init__(title, icon)
    
    def page(self, handle, path):
        handle.wfile.write(b'<script src="chart.js"></script>\n')
        
        # source: https://lospec.com/palette-list/dawnbringer-16
        db16 = ['#140c1c', '#442434', '#30346d', '#4e4a4e', '#854c30', '#346524', '#d04648', '#757161', '#597dce', '#d27d2c', '#8595a1', '#6daa2c', '#d2aa99', '#6dc2ca', '#dad45e', '#deeed6']
        
        palette = cfg['usercolor'] + db16
        
        data = {}
        for d in cfg['targetorder'][1:]:
            data[d] = len(ent['apd'][d.lower()]['posts'])
        
        page = '<canvas id="piePosts" style="display: inline-block; width:100%;"></canvas>\n'
        page += '<script>'
        page += '''data = {
    datasets: [{
        data: ''' + json.dumps(list(data.values())) + ''',
    
    backgroundColor: ''' + json.dumps(palette) + ''',
    rotation: 0.5,
    borderWidth: 6,
    borderColor: "#121212"
    }],
    // These labels appear in the legend and in the tooltips when hovering different arcs
    labels: ''' + json.dumps(list(data)) + '''
};
'''
        page += '''new Chart("piePosts", {
type: 'pie',
data: data,
options: {
    title: {
                display: true,
                text: "Posts by Account"
    }}
});
'''
        page += '</script>'
        
        self.write(handle, page)


class builtin_chart(builtin_base):
    
    def __init__(self, title, icon):
        super().__init__(title, icon)
        
        self.chart_data = {}
        self.charts = {
            'posts':    {'title': 'Posts'},
            'posts_new':{'title': 'New Posts', 'start': False},
            'views':    {'title': 'Views'},
            'views_new':{'title': 'New Views', 'start': False},
            'faves':    {'title': 'Faves'},
            'faves_new':{'title': 'New Faves', 'start': False},
            
            'vpr':      {'title': 'Views per Post'},
            'vpr_new':  {'title': 'New Views per Post'},
            'fpr':      {'title': 'Faves per Post'},
            'fpr_new':  {'title': 'New Faves per Post'},
            
            'fvr':      {'title': 'Fave%'},
            'fvr_new':  {'title': 'New Fave%'}
            }
    
    def chart_element(self, cid, d):
        size = '49.5%'
        return '<canvas id="{}" style="display: inline-block; width:100%; max-width:{}"></canvas>\n'.format(cid, size)
    
    def chart_def(self, k, d):
        doc = 'new Chart("' + k + '", {\n'
        doc += '''
type: "line",
  data: {
    labels: chart_dates,
    datasets: [{
      fill: false,
      lineTension: 0,
      backgroundColor: "hsl(0deg 0% 62%)",
      borderColor: "hsl(0deg 0% 62% / 50%)",
      data: chart_''' + k
        doc += '''\n}]
  },
  options: {
    legend: {display: true},
            title: {
                display: true,
                text: "''' + d.get('title', k) + '"'
        doc += '}}});\n\n'
        
        return doc
    
    def js_vars(self):
        doc = '<Script>\n'
        for k, v in self.chart_data.items():
            doc += 'var chart_{} = {};\n'.format(k, json.dumps(v))
        
        return doc
    
    def add(self, t, v):
        self.chart_data[t].append(v)
        return v


class builtin_period(builtin_chart):

    def __init__(self, title='Period', icon=[0, 2]):
        super().__init__(title, icon)
        self.default_limit = None
        self.default_start = datetime.fromisoformat('2000-01-01')
        self.division = {
            'hour': 'Hourly',
            'day': 'Daily',
            'week': 'Weekly',
            'month': 'Monthly',
            'quart': 'Quarterly',
            'year': 'Yearly'
            }
        self.pagetype = 'period'
    
    def process_date(self, d, mode):
        if mode == 'day':       return d[:10]
        elif mode == 'month':   return d[:7]
        elif mode == 'year':    return d[:4]
        elif mode == 'hour':    return d[:13]
        elif mode == 'quart':
            m = int(d[5:7])
            return '{} q{}'.format(d[:4], math.ceil(m/3))
        
        elif mode == 'week':
            d = fromiso(d.split('.')[0]).isocalendar()
            return '{} w{}'.format(d[0], d[1])
    
    def elim_start(self, start, d, end):
        return start <= datetime.fromisoformat(d) <= end
    
    def daterip(self, vals, default, t):
        
        try:# try and grab a date
            for i, v in enumerate(vals):
                if len(v) < 4 or not v[0].isdigit():
                    continue
                    
                while len(v) < 10:
                    v += '-01'
                
                return (i,
                        datetime.fromisoformat(v),
                        '<p>{}: {}</p>\n'.format(t, v))
        
        except:
            pass
        
        return (1, default, '')
    
    def serve_table(self, handle, seq, name):
        
        handle.wfile.write(b'<script src="chart.js"></script>\n')
        
        fs = []
        c = 0
        posts_prev = 0
        views_prev = 0
        faves_prev = 0
        
        ilen = (len(seq.items())+1) % 2
        
        for k, v in seq.items():
            
            posts = len(v)
            if c and not posts:
                continue
            
            views = 0
            faves = 0
            for i, p in v.items():
                views += p['views']
                faves += p['faves']
            
            if posts - posts_prev < 0:
                continue
            
            posts_new, posts_prev = posts - posts_prev, posts
            views_new, views_prev = views - views_prev, views
            faves_new, faves_prev = faves - faves_prev, faves
            
            h = '<tr class="{}">'.format(['', 'odd'][c%2 == ilen])
            for i in [
                k, posts, views, faves,
                '', posts_new, views_new, faves_new]:
                if i == 0:i = ''
                
                h += '\n\t<td>{}</td>'.format(wrapme(i))

            self.add('dates', k)
            for ch, v in [
                ('posts', posts),
                ('views', views),
                ('faves', faves),
                ('posts_new', posts_new),
                ('views_new', views_new),
                ('faves_new', faves_new),
                
                ('vpr', views / max(posts, 1)),
                ('fpr', faves / max(posts, 1)),
                ('vpr_new', views_new / max(posts_new, 1)),
                ('fpr_new', faves_new / max(posts_new, 1)),
                
                ('fvr', (faves / max(views, 1))*100),
                ('fvr_new', (faves_new / max(views_new, 1))*100)
                ]:
                if c == 0 and not self.charts[ch].get('start', True):
                    v = 0
                
                self.add(ch, max(v, 0))
            
            h += '\n</tr>\n'
            fs.append(h)
            c += 1
        
        h = strings['stripeytablehead'].format(8, name)
        h += trtd(['Date', 'Posts', 'Views', 'Faves',
                   '', 'New Posts', 'New Views', 'New Faves'])
        
        h += ''.join(fs[::-1])
        self.write(handle, h + '</table>\n\n')

        doc = self.js_vars()
        for k, v in self.charts.items():
            doc += self.chart_def(k, v)
        
        doc += '</script>'
        self.write(handle, doc)
        
    def path_pick(self, path, options, default):
        
        for i in options:
            i = i.lower()
            if i in path:
                return i, path.index(i)
        
        return  default, -1
     
    def build_picker(self, path, options, default):
        target, idx = self.path_pick(path, options, default)
        if idx == -1:
            path.append(target)
        
        doc = []
        path = path[:]# don't modify source pls
        for k, n in options.items():
            if k == target:
                doc.append(f'<b>{n}</b>\n')
            
            else:
                path[idx] = k
                doc.append(f'<a href="/{"/".join(path)}">{n}</a>\n')
        
        return target, f'<p>{" - ".join(doc)}</p>\n'
    
    def sift_data(self, mode, target, start, end, posts):
        
        if type(posts) == list and posts and type(posts[0]) == tuple:
            posts = set(i for i, d in posts)
        
        else:
            posts = set()
        
        date_prev = ''
        label = 'Start'
        init = []
        
        seq = {}
        tmp = {}
        c = 0
        
        for k, v in sorted(ent['apd'][target]['period'].items())[self.default_limit:]:
            d = self.process_date(k, mode)
            
            if not self.elim_start(start, k, end):
                continue
            
            if d == date_prev:
                continue
            
            v = {x: y for x, y in v.items() if not posts or x in posts}
            seq[label] = v
            
            date_prev = d
            label = d
            tmp = v
            c += 1
        
        if end == end_of_time and tmp != {}:
            label = d
            v = {x: y for x, y in v.items() if x in posts}
            if len(v) > 0:
                seq[label] = v
            
            tnp = {}
        
        return seq
    
    def division_stuff(self, path):
        mode, pickmode = self.build_picker(path, self.division, 'day')
        modename = self.division.get(mode, mode)
        
        self.default_limit = {
            'hour': -7*24,
            'day': -24*24,# 24 days
            'week': -56*24# 8 weeks
            }.get(mode, None)
        
        if mode == 'hour':
            self.default_start = datetime.fromisoformat('2021-07-02')
        
        else:
            self.default_start = datetime.fromisoformat('2000-01-01')
        
        return mode, modename, pickmode
    
    def top_stuff(self, handle, path, text, cla=' list', charts=True):
        doc = f'<div class="head"><h2 class="pagetitle">{self.title}</h2></div>\n'
        doc += f'<div class="container{cla}">\n{text}'
        
        p, start, da = self.daterip(path, self.default_start, 'From')
        doc += da
        if self.default_start != start:
            self.default_limit = None
        
        p, end, da = self.daterip(path[p+1:], end_of_time, 'Until')
        doc += da
        
        if charts:
            self.chart_data = {'dates': []}
            for k, d in self.charts.items():
                doc += self.chart_element(k, d)
                self.chart_data[k] = []
            
            doc += '<br><br>\n'
        
        self.write(handle, doc)
        return start, end
    
    def page(self, handle, path):
        # mode, target, start, end
        
        if len(path) == 1:path.append('total')
        
        mode, modename, pickmode = self.division_stuff(path)
        
        target, picktarget = self.build_picker(path, ent['targets'], 'total')
        targetname = ent['targets'].get(target, target)
        
        self.title = f'{targetname} {modename} Stats'
        
        start, end = self.top_stuff(handle, path, pickmode + picktarget)
        
        seq = self.sift_data(mode, target, start, end, [])
        
        self.serve_table(handle, seq, self.title)
        
        self.write(handle, '\n</div>\n<div class="foot">')


class builtin_posts(builtin_period):
    
    def __init__(self, title='Posts', icon=[3, 1]):
        super().__init__(title, icon)
        #self.chart_data = None
        self.sorts_default = 'id'
        self.sorts = {
            'id': 'ID',
            'views': 'Views',
            'faves': 'Faves',
            'comments': 'Comments',
            'favper': 'Fave %'
            }
        self.modes_default = 'rows'
        self.modes = {
            'rows': 'Rows mode',
            'full': 'Full mode',
            'compact': 'Compact mode',
            'thumb': 'Thumb mode',
            'chart': 'Chart mode'
            }
        self.headtext = ''
        self.marktype = None
    
    def add_sort(self, idn, name, default=False):
        if not default:
            self.sorts[idn] = name
            return
        
        self.sorts_default = idn
        self.sorts = {**{idn: name}, **self.sorts}
    
    def get_last(self, showstats):
        targe = 'total'
        if showstats == True:
            last_period = sorted(ent['apd'][target]['period'])[-1]
            return ent['apd'][target]['period'][last_period]
        
        elif type(showstats) == dict:
            return showstats
        
        return {}# fail
    
    def postrow_item(self, postid, info, stats):
        line_item = '<div class="postflex{}">{}</div>\n'
        line_link = '<a href="{}">{}</a>'
        
        doc = ''
        remote = cfg.get('remote_images')
        if remote:# do remote link
            ext = get_ext(postid)
            fill = f'<img src="{remote.format(postid)}.{ext}" loading="lazy">'
            doc += line_item.format('', fill)
        
        fill = ''
        if stats:
            fill += line_item.format('-quad',
                f'{stats.get("views","?")}<span>Views</span>')
            fill += line_item.format('-quad',
                f'{stats.get("faves","?")}<span>Favourites</span>')
            fill += line_item.format('-quad',
                f'{stats.get("comments","?")}<span>Comments</span>')
            rating = info.get('rating', '?')
            fill += line_item.format('-quad' + ' r-' + rating.lower(),
                f'{rating}<span>Rating</span>')
        
        collectionlist = ''
        for p, c in ent['mark_buttons'].items():
            if not compare_for(apdmm[p], 'posts'):
                continue
            
            if not apdmm[p].get('type') == 'collection':
                continue
            
            groups = get_collectioni(p, postid, onlyin=True)
            mname = apdmm[p]['name_plural']
            
            style = '-quad'
            
            if groups:
                style += ' on'
                cfill = f'\n<div class="linkthings left">{mname}:'
                for group in groups:
                    cname = group[0]
                    cfill += '\n' + line_link.format(f'/{p}/{cname}', cname)
                
                collectionlist += cfill + '\n</div>'
            
            style += f'" name="{postid}@{p}" onclick="setsGetMagic(this)'
            fill += line_item.format(style, f'{len(groups):,} <span>{mname}</span>')
        
        doc += line_item.format('-col', fill)
        
        # groups = get_collectioni('postgroup', postid, onlyin=True)
        # lgroup = len(groups)
        # style = '-quad'
        # if lgroup:style += ' on'
        # style += f'" name="{postid}@postgroup" onclick="setsGetMagic(this)'
        # fill += line_item.format(style, f'{lgroup:,} <span>Groups</span>')
        # doc += line_item.format('-col', fill)
        
        fill = line_link.format(f'/view/{postid}', info.get('title', postid))
        fill += line_link.format(
            f'https://furaffinity.net/view/{postid}', ' [FA]') 
        dic = line_item.format('-wide', fill)
        
        if 'user' in info:
            fill = line_link.format(f'/posts/{info["user"]}', info['user'])
            dic += line_item.format('-wide', 'by ' + fill)
        
        if 'date' in info:
            dic += line_item.format('-wide', 'posted ' + info['date'])
        
        tags = info.get('tags', '_untagged')
        if type(tags) == str:
            tags = [tags]
        
        fill = '<div class="linkthings left">Tags:'
        for tag in tags:
            fill += '\n' + line_link.format(f'/tag/{tag}', tag)
        
        dic += line_item.format('-wide', fill + '</div>')
        
        if collectionlist:
            dic += line_item.format('-wide', collectionlist)
        # if groups:
            # fill = '\n<div class="linkthings left">Groups:'
            # for group in groups:
                # name = group[0]
                # fill += '\n' + line_link.format(f'/postgroup/{name}', name)
            
            # dic += line_item.format('-wide', fill + '</div>')
        
        doc += line_item.format('', dic)
        return f'<div class="postrow">{doc}</div>\n'
    
    def postrows(self, handle, posts, showstats=True):
        last_period = self.get_last(showstats)
        
        for k, v in posts:
            self.write(
                handle,
                self.postrow_item(k, v, last_period.get(k, {})))
    
    def postfull_item(self, postid, info, stats):
        line_item = '<div class="postflex{}">{}</div>\n'
        line_link = '<a href="{}">{}</a>'
        
        title = info.get('title', postid)
        doc = f'<div id="{postid}@post">\n'
        doc += strings['eyde_post_title'].format(
            postid, title)
        
        remote = cfg.get('remote_images')
        if remote:# do remote link
            ext = get_ext(postid)
            doc += f'<img src="{remote.format(postid)}.{ext}" loading="lazy">'
        
        desc = info.get('description', '')
        desc_word_count = len(re.findall(r'\w+', desc))
        
        if desc_word_count > 500:
            desc = f'''<details>
<summary>Description ({desc_word_count:,} words)</summary>
{desc}</details>\n<br>'''
        
        doc += f'<div class="desc">{desc}</div>\n'
        
        tags = info.get('tags', '_untagged')
        fill = '<div class="linkthings centered">\nTags:'
        for tag in tags:
            fill += f'\n<a href="/tag/{tag}">{tag}</a>'
        
        doc += fill + '</div>'
        
        doc += mark_for('posts', postid)
        
        return doc + '</div>\n'
    
    def postfull(self, handle, posts, showstats=True):
        last_period = self.get_last(showstats)
        
        for k, v in posts:
            self.write(
                handle,
                self.postfull_item(k, v, last_period.get(k, {})))
    
    def postbox_item(self, postid, info, stats):
        line_item = '<div class="postflex{}">{}</div>\n'
        line_link = '<a href="{}">{}</a>'
        
        rating = info['rating']
        doc = ''
        
        fill = line_link.format(f'/view/{postid}', info['title'])
        fill += line_link.format(
            f'https://furaffinity.net/view/{postid}', ' [FA]') 
        doc += line_item.format('-wide', fill)
        
        if 'user' in info:
            fill = line_link.format(f'/posts/{info["user"]}', info['user'])
            doc += line_item.format('-wide', 'by ' + fill)
        
        if 'date' in info:
            doc += line_item.format('-wide', 'posted ' + info['date'])
        
        if stats:
            for stat_key, stat_name, default in [
                ('views', 'View', '?'),
                ('faves', 'Favourite', '?'),
                ('comments', 'Comment', '?')]:
                stat_value = stats.get(stat_key, default)
                fill = f'{stat_value}'
                fill += f'<span>{stat_name}{plu(stat_value)}</span>'
                doc += line_item.format('-quad', fill)
        
        groups = get_collectioni('postgroup', postid, onlyin=True)
        lgroup = len(groups)
        style = '-quad'
        if lgroup:style += ' on'
        style += f'" name="{postid}@postgroup" onclick="setsGetMagic(this)'
        
        doc += line_item.format(style, f'{lgroup:,} <span>Groups</span>')
        
        return line_item.format(' r-' + rating.lower(), doc)
    
    def postbox(self, handle, posts, showstats=True):
        last_period = self.get_last(showstats)
        
        for k, v in posts:
            self.write(
                handle,
                self.postbox_item(k, v, last_period.get(k, {})))
    
    def postthumb_item(self, postid, info, stats):
        rating = info.get('rating', 'error').lower()
        ret = f'<figure class="r-{rating} t-image">\n'
        ret += f'<a class="t-inner" href="/view/{postid}/">'
        
        remote = cfg.get('remote_images')
        if remote:# do remote link
            ext = get_ext(postid)
            ret += f'<img src="{remote.format(postid)}.{ext}" loading="lazy">'
        
        title = info.get('title', f'Unavailable: {postid}')
        
        ret += '</a>\n<figcaption>\n'
        ret += f'<p><a href="/view/{postid}/" title="{title}">{title}</a></p>\n'
        ret += '</figcaption>\n</figure>\n'
        return ret
    
    def postthumb(self, handle, posts, showstats=True):
        last_period = self.get_last(showstats)
        
        for k, v in posts:
            self.write(
                handle,
                self.postthumb_item(k, v, last_period.get(k, {})))
    
    def postchart(self, handle, path, dse, posts, showstats=True):
        seq = self.sift_data(dse[0], dse[1], dse[2], dse[3], posts)
        
        self.serve_table(handle, seq, self.title)
    
    def items(self, path):
        target, self.headtext = self.build_picker(path, ent['targets'], 'total')
        self.name = ent['targets'].get(target, target)
        posts = ent['apd'][target].get('posts', {}).items()
        
        return target, posts
    
    def page(self, handle, path):
        target, posts = self.items(path)
        count = len(posts)
        
        sort, picksort = self.build_picker(path, self.sorts, self.sorts_default)
        list_mode, pickmode = self.build_picker(path, self.modes, self.modes_default)
        div, divname, pickdiv = self.division_stuff(path)
        
        cla = ''
        cha = False
        
        doc = ''
        if self.marktype:
            doc += mark_for(self.marktype, self.name.lower())
        doc += f'<p>{count:,} post{plu(count)}</p>\n'
        
        if list_mode in ['rows', 'chart']:
            cla = ' list'

        top = pickmode
        if list_mode == 'chart':
            self.title = f'{self.name} {divname} Stats'
            top += pickdiv
            doc = ''
            cha = True
        
        else:
            self.title = f'{self.name} Posts'
            top += picksort
        
        start, end = self.top_stuff(handle, path, top + self.headtext, cla=cla, charts=cha)
        
        doc += strings['setlogic']
        
        self.write(handle, doc)
        
        seq = self.sift_data('hour', target, start, end, posts)
        if len(seq.items()) == 0:
            self.write(handle, '<h2>No Content!</h2>\n<p>Might be loading.</p>\n<br>')
            return
        
        d, last_p = list(seq.items())[-1]
        
        last_period = {}
        startn = start.strftime('%Y-%m-%dT%H')
        if startn in seq:
            v = seq[startn]
            for i, p in last_p.items():
                last_period[i] = {
                    x: p[x] - v.get(i, {}).get(x, 0)
                    for x in ['views', 'faves', 'comments']
                    }
        
        else:
            last_period = last_p
        
        rev = 'low' not in path
        if sort == 'initial':
            sort = self.sorts_default
            rev = True
        
        if sort == 'id':
            posts = sorted(posts, reverse=rev)
        
        elif sort == 'favper':
            dat = []
            for x, v in posts:
                lx = last_period.get(x, {})
                dat.append([lx.get('views', 0) / max(lx.get('faves', 0), 1), (x, v)])
            
            posts = [v for x, v in sorted(dat, reverse=not rev)]
        
        elif sort in ['views', 'faves', 'comments']:
            posts = sorted([(last_period.get(x, {}).get(sort, 0), (x, v))
                            for x, v in posts],
                           reverse=rev)
            posts = [v for x, v in posts]
        
        if list_mode == 'rows':
            self.postrows(handle, posts, showstats = last_period)
        
        elif list_mode == 'full':
            self.postfull(handle, posts, showstats = last_period)
        
        elif list_mode == 'compact':
            self.postbox(handle, posts, showstats = last_period)
        
        elif list_mode == 'thumb':
            self.postthumb(handle, posts, showstats = last_period)
        
        elif list_mode == 'chart':
            self.postchart(handle, path, [div, target, start, end], posts, showstats = last_period)
        
        else:
            self.write(handle, list_mode)
        
        handle.wfile.write( b'\n</div>\n<div class="foot">')


class builtin_view(builtin_posts):
    
    def __init__(self, title='View', icon=[3, 1]):
        super().__init__(title, icon)
        self.add_sort('origin', 'Origin', True)
    
    def items(self, path):
        if len(path) < 2:path += ['', '']
        
        data = ent['apd']['total']['posts']
        posts = []
        for i in path[1].split(' '):
            n = str(i).split('.')[0]
            posts.append(i)
        
        self.name = 'View'
        
        posts = [(x, data.get(x, {})) for x in posts]
        
        return 'total', posts


class builtin_tag(builtin_posts):
    
    def __init__(self, title='Tag', icon=[3, 1]):
        super().__init__(title, icon)
        self.marktype = 'tags'
    
    def items(self, path):
        if len(path) < 2:path += ['', '']
        self.name = path[1].replace('-', '').replace('_', '').title()
        
        data = ent['apd']['total']['posts']
        posts = ent['tags'].get(self.name.lower(), [])
        posts = [(x, data.get(x, {})) for x in posts]
        
        return 'total', posts


class builtin_collection(builtin_posts):
    
    def __init__(self, colname):
        self.colname = colname
        title = colname
        link = colname
        icon = [0, 0]
        super().__init__(title, icon)
        self.add_sort('origin', 'Origin', True)
    
    def items(self, path):
        path += ['No Data']
        self.name = find_collection(self.colname, path[1])
        
        if not self.name:
            self.name = 'No Data'
            return 'total', {}
        
        data = ent['apd']['total']['posts']
        col = apdm[self.colname][self.name]
        posts = [(x, data.get(x, {})) for x in col.get('items', [])]
        
        return 'total', posts


def markicon(x, y, m=-60):
    return f'" style="background-position: {x*m}px {y*m}px;'


def valueicon(value, icons, default, values=[]):
    if type(value) != int:
        value = values.index(value)
    
    if len(icons) > value:
        return icons[value], True
    else:
        return default, False


def iconlist(di, thing):
    pgm = ''
    
    for name, icon, ext, cssc in di:
        if type(icon) == list:
            c = 'iconsheet' + cssc + markicon(*icon, m=-24)
            pgm += f'<i name="{thing}@ico.{name}" class="teenyicon {c}"></i>'
        else:
            pgm += f' {icon}'

        if ext == '':continue
        pgm += f'{ext} '
    
    return pgm


def lister_linker(kind):
    return ent['link_to'].get(kind, '/{}')


def create_linktodathing(kind, thing, onpage=False, retmode='full', con=None):
    pi = []
    linky = thing
    
    if onpage != 0:
        if onpage == 1:
            pi.append(['me', [6, 2], '', ''])
        elif onpage == 2:
            pi.append(['above', [7, 1], '', ''])
        elif onpage == 3:
            pi.append(['below', [7, 2], '', ''])
        else:
            pi.append(['somewhere', [5, 1], '', ''])
    
    di = []
    for m in apdmm:
        btnd = apdmm[m]
        if not btnd.get('for', 'posts').startswith(kind):continue
        
        v = mark_state(m, thing)
        
        if type(v) == list:
            vd = v[1:]
            v = v[0]
        
        if v == None or v == 'n/a':
            continue
        
        dis = ['', ' disabled'][btnd.get('disabled', False)]
        icon = [m, btnd.get('icon', m), '', dis]
        
        if btnd.get('type', False) == 'collection':
            hasicon = 0
            for col in vd[0]:
                if col[5] != None:
                    hasicon += 1
                    cdis = ['', ' disabled'][col[3]]
                    di.append([m, col[5], '', ''])
            
            if hasicon == len(vd[0]):
                # only draw collection icon if any others
                continue
        
        if len(btnd.get('values', [])) > 1:
            icon[1], ch = valueicon(v, btnd.get('valueicon', []), icon[1], btnd['values'],)
            if not ch:
                icon[2] = f'{v})'
        
        di.append(icon)
    
    linkdes = thing
    if con is None:
        href = lister_linker(kind)
    
    else:
        href = f'/{con.lower()}/{{}}'
        if re.sub(r'\W+ ', '', thing.lower()) != thing.lower():
            linky = f'id.{find_collection(kind, thing, retid=True)}'
        
        data = apdm[kind][thing]
        
        if compare_for(apdmm[kind], 'posts', sw=True):
            # show icon if read or unread
            prefr = set(dpref.get('read', {}))
            for p in data['items']:
                if p not in prefr:
                    break
            
            else:
                pi.append(['allread', ii(33), '', ''])
        
        if data.get('lock', False):
            pi.append(['locked', ii(50), '', ''])
        
        if data.get('pin', False):
            pi.append(['pinned', ii(52), '', ''])
        
        if data.get('icon') != None:
            pi.append(['', data['icon'], '', ''])
        
        linkdes += ' ' + wrapme(len(data['items']))
    
    if kind == 'users':
        if thing in ent['_allusers']:
            got = len(ent['_allusers'][thing])
            l8r = ent['ustats'].get(thing, '?')
            v = wrapme(got, f=' {:,}') + wrapme(l8r, ' ({:,})')
            
            if cfg['docats']:
                uns = len(ent['users'].get(thing, ''))
                if uns <= 0 < got:
                    pi.append(['seen', [3, 2], '', ''])
                
                elif uns != got:
                    v = wrapme(uns, f=' {:,} ') + wrapme(got) + wrapme(l8r, ' ({:,})')
                    pi.append(['partial', [0, 1], '', ''])
            
            linkdes += v
        
        else:
            pi.append(['notgot', [3, 4], '', ''])
    
    elif kind == 'posts':
        if thing not in apdfa:
            pi.append(['notgot', [3, 4], '', ''])
    
    elif kind == 'folders':
        linkdes = apdfafol.get(thing, {'title': 'Folder ' + thing})['title']
    
    elif kind == 'tags':
        pass
    
    if href == '/{}/1':
        pass#print('what?', kind, thing)
    
    if retmode == 'markonly':
        return iconlist(pi + di, thing)
    elif retmode == 'href':
        return linky
    
    href = href.format(linky)
    return f'<a href="{href}">{iconlist(pi, thing)} {linkdes} {iconlist(di, thing)}</a>'


def mark_state(mark, thing):
    if apdmm[mark].get('type') == 'collection':
        mt = get_collectioni(mark, thing, onlyin=True)
        ret = [[None, mark][len(mt) > 0], mt]
    
    elif apdmm[mark].get('list') == True:
        ret = [None, mark][thing in apdm[mark]]
    
    else:
        ret = apdm[mark].get(thing, [None])[0]
    
    if ret == 'n/a':ret = None
    #print(mark, thing, ret)
    return ret


class mark_button(object):

    def __init__(self, mark, action=None):
        
        self.mark = mark
        self.data = apdmm[mark]
        
        self.btype = self.data.get('type')
        self.action = action
    
    def disabled(self):
        return self.data.get('disabled', False)
    
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
            c = '<i class="iconsheet ico{} {}"></i>'
            return c.format(-size, markicon(*value, m=-size))
        
        return '<span>{str(value)}</span>'
    
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
        if state == None:
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
        
        if build_input == None:
            logging.warning(f'{self.mark} has unhandled mark type: {self.btype}')
            build_input = self.build_input_text
        
        self.t_thing = thing
        self.t_state = state
        self.t_press = pressed
        self.t_class = cla
        self.t_size  = size
        
        return build_input()
    
    def build_wrap(self, namep, cla, arg, inner):
        if namep[0] == None:return ''
        return '<div name="{}" class="markbutton mbutton {}"{}>{}</div>\n'.format(
            '@'.join(namep),
            cla, arg, inner)
    
    def build_input_text(self):
        #todo add icon
        inner = '<input type="text" class="niceinp" size="1" value="{}">'.format(self.t_state)
        return self.build_wrap(
            [self.t_thing, self.mark],
            self.t_press + self.t_class,
            '',
            inner), ''
    
    def build_input_int(self):
        #todo add icon
        inner = '<input type=""number" class="niceinp" size="1" value="{}">'.format(state)
        return self.build_wrap(
            [self.t_thing, self.mark],
            self.t_press + self.t_class,
            '',
            inner), ''
    
    def build_input_multibutt(self):
        
        values = self.data.get('values', [])
        
        out = '<span name="{0}@{1}">\n'.format(self.t_thing, self.mark)
        
        action = ' onclick="{}"'.format(self.pick_action())
        
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
            link = f'<div class="linkthings">\n{self.data["name_plural"]}:\n' + '\n'.join(links) + '</div>\n'
        
        return self.build_wrap(
            [self.t_thing, self.mark],
            self.t_press + self.t_class,
            action,
            inner), link
    
    def build_input_list(self):
        
        inner = self.pick_icon(self.t_state, self.t_size)
        inner += '<select class="niceinp" onchange="{}">\n'.format(self.pick_action())
        
        for value in [''] + self.data['values']:
            
            inner += '<option value="{0}" {1}>{0}</option>\n'.format(value, ['', 'selected'][value == self.t_state])
        
        inner += '</select>'
        
        return self.build_wrap(
            [self.t_thing, self.mark],
            self.t_press + self.t_class,
            '',
            inner), ''


def mark_for(kind, thing, wrap=False, size=60):
    # get all marks for a thing of a kind
    # wrap adds a container box
    out = ''
    link = ''
    
    for p, c in ent['mark_buttons'].items():
        if not compare_for(apdmm[p], kind):
            continue
        
        o, l = c.build_for(thing, size=size)
        
        out += o
        if l:
            if not link:
                link = '<br>\nIncluded in:'
            
            link += f'\n{l}'
    
    out = f'\n{out}\n{link}</div>\n'
    if wrap and out:
        p = lister_linker(kind).format(thing)
        out = f'<div class="floatingmark markbox">\nMarks for <A href="{p}">{kind} <b>{thing}</b></a>\n<br><br>{out}'
    
    else:
        out = f'<div class="floatingmark abox mark{kind}">{out}'
    
    return out


def markicons_for(kind, thing):
    artm = []
    
    for m, d in apdmm.items():
        if d.get('for', 'posts') != kind:continue
        
        if d.get('type', 'idk') in ['multibutt', 'list']:
            for v in d.get('values', []):
                if thing in dpref.get(v, []):
                    artm.append(v)
    
    return ' '.join(artm)


class mort_collection_list(mort_base):
    
    def __init__(self, colname, plural):
        self.colname = colname
        marktype = colname
        title = plural
        self.name = plural
        link = lister_linker(marktype)
        icon = apdmm[colname].get('icon', None)
        self.rebuildread = True
        super().__init__(marktype, title, link, icon, con=colname)
        
        self.hide_empty = False
    
    def pick_collection_thumb(self, d):
        t = pick_thumb(d[::-1], do_ext=False)
        if t != 'parrot.svg':
            return -1, t
        
        return -i-1, t
    
    def gimme(self, pargs):
        self.items = []
        self.datas = {}
        
        for d, k, n in sort_collection(self.colname, rebuild=True):
            self.items.append((k, d, n))
            self.datas[k] = apdm[self.colname][k]['items'].copy()
            
            i, t = self.pick_collection_thumb(self.datas[k])
            self.datas[k][i] = t
        
        self.title = self.name
        list_mode, wr = self.modes_default, ''
        self.headtext[0] = wr
    
    def purge(self, strength):
        super().purge(strength)
        
        if self.clear_threshold <= strength:
            self.read = {}
            self.rebuildread = True


class post_data(post_base):
    
    def post_logic(self, handle, pargs, data):
        if not cfg['allow_data']:# disallow
            return {'error': 'data access is disabled'}
        
        if pargs[-1] == '':
            pargs = pargs[:-1]
        
        if len(pargs) == 1:# 2 short 4 me
            return {'error': 'no request specified'}
        
        if pargs[1] == 'posts':
            return list(apdfa)
        
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
        self.write(handle, json.dumps(ret))

class post_editdetails(post_base):
    
    def post_logic(self, handle, pargs, data):
        return {}


class post_apref(post_base):
    
    def post_logic(self, handle, pargs, data):
        if cfg['static']:
            return {'status': 'Server set to Static'}
        
        md = cfg['mark_dir']
        ret = {}
        flag = pargs[1]

        logging.debug(f'Apref flag: {flag} {json.dumps(data)}')
        
        if flag not in apdmm:
            logging.warning(f'Unknown APDM: {flag}')
            return
        
        ch_apdm = {}
        for post, rating, dt in data:
            if post in apdm[flag]:
                c = apdm[flag][post]
                if c[0] == rating:
                    continue
                elif c[0] == "n/a" and rating is None:
                    continue
            
            # this kills my code otherwise xo
            if rating is None:
                rating = 'n/a'
            
            ch_apdm[post] = [rating, dt]
            ret[post] = [flag, rating]
        
        if ch_apdm:
            logging.debug(json.dumps(ch_apdm))
            apc_write(md + 'ds_' + flag, ch_apdm, {}, 1, volsize=None)
            for k in ch_apdm:
                apdm[flag][k] = ch_apdm[k]
        
        return ret


class post_collections(post_base):
    
    def post_logic(self, handle, pargs, data):
        global apdm
        
        if cfg['static']:
            return {'status': 'Server set to Static'}
        
        mode = pargs[-1]
        query = data.get('query')
        con = data.get('con')
        name = data.get('name')
        flag = data.get('flag')
        prop = data.get('prop')
        date = data.get('date')
        
        if con is None:
            return {'status': 'no con specified'}
        
        md = cfg['mark_dir']
        ret = {}
        
        if mode == 'for' and query != None:
            ret['sets'] = get_collectioni(con, query)
        
        elif mode == 'new' and name != None:
            if name not in apdm[con]:
                apdm[con].write({name: {'modified': data['time'], 'items': []}})
                ret['name'] = name
                sort_collection(con, ret=False, rebuild=True)
                ret['status'] = 'success'
        
        elif mode == '_flag' and flag != None and 'file' in data:
            flag = html.unescape(flag)
            
            files = data['file']
            if type(files) != list:
                files = [files]
            
            existing = apdm[con][flag]
            
            if existing.get('lock', False):
                ret['status'] = 'error'
                ret['message'] = 'Locked: {}'
                return ret
            
            for file in files:
                ret['status'] = [flag, file not in existing['items']]
                
                ret[file] = [con, True]
                
                if file in existing['items']:
                    existing['items'].remove(file)
                    ret[file][1] = get_collectioni(con, file, retcount=True) > 0
                
                else:
                    existing['items'].append(file)
            
            existing['modified'] =  data['time']
            apdm[con].write({flag: existing})
        
        elif mode == 'prop' and 'name' in data and 'prop' in data:
            stripset = {re.sub(r'\W+', '', x.lower()): x for x in apdm[con]}
            
            sname = name
            if name in stripset:
                sname = stripset[name]
            
            if sname not in apdm[con]:
                ret['status'] = 'error'
                ret['message'] = f'WTF is {name}'
                return ret
            
            existing = apdm[con][sname]
            ret[name] = [prop, not existing.get(prop, False)]
            existing[prop] = ret[name][-1]
            existing['modified'] =  data['time']
            
            if prop == 'delete':
                existing['delete'] = True
            
            elif prop == 'sortmepls':
                items = sorted([
                    int(i)
                    for i in existing['items']
                    if i.isdigit()
                    ])
                existing['items'] = [str(i) for i in items]
                del ent[mem][sname][prop]
            
            sort_collection(con, ret=False)
            apdm[con].write({sname: existing})
        
        return ret


class request_handler(BaseHTTPRequestHandler):
    
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
            ripdata = json.loads(post_data.decode('utf8'))
        
        except:
            ripdata  = {}
        
        if cfg['developer']:
            logging.debug(ripdata)
        
        if path_split[0] in ent['builtin_post']:
            ent['builtin_post'][path_split[0]].serve_post(self, path_split, ripdata)
            return
        
        ret = {}
        sta = 501
        
        if path_split[0] == 'rebuild':
            level = 0
            if len(path_split) > 1 and path_split[1].isdigit():
                level = int(path_split[1])
            build_entries(reload=level)
            ret['status'] = 'success'
        
        elif self.path.startswith('/poke'):
            logging.debug(f'poke! {urllib.parse.unquote(self.path)[6:]}')
            
            try:
                build_entries(reload=9)
                ret['status'] = 'success'
                sta = 200
            except:
                sta = 501
                ret['status'] = 'error'
                ret['message'] = 'An error occurred while rebuilding, see console for more details'
                logging.error('failed rebuild')
        
        self.send_response(sta)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        self.wfile.write(bytes(json.dumps(ret), 'utf8'))
        return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread.""" 


def init_apd():
    
    if not os.path.isdir(cfg['apd_dir']):
        os.mkdir(cfg['apd_dir'])
    
    if not os.path.isdir(cfg['mark_dir']):
        os.mkdir(cfg['mark_dir'])
    
    make_apd('ds_postgroup', {'//': {
        'icon':  ii(0),
        'name': "Postgroup",
        "name_plural": "Postgroups",
        'type': "collection",
        'for': "posts",
        "excludeMarked": False,
        'order': 1
    }})


def stop():
    logging.info('Stopping server')
    time.sleep(2)
    httpd.shutdown()


if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    init_logger('statsrv', disp=':' in code_path)
    
    load_global('cfg', {
        # these settings are not saved outside this file
        'developer': False,
        'server_name': 'StatSrv',
        'list_count': 15,# users/kewords per page
        'post_count': 25,# posts per page
        'over': 5,# how many posts over the limit a page may extend
        'apd_dir': 'data/',
        'mark_dir': 'data_mark/',
        'data_dir': 'data_period/',
        'res_dir': 'res/',
        'remote_images': '',
        'homepage_menu': 'nav',
        'dropdown_menu': 'nav',
        'targetorder': [
            'Total'
            ],
        'total_ignore': [],
        'allow_data': False,
        'static': False,
        'usercolor': []
        })
    
    load_global('menus', {
        'pages': {
            "nav": {
                "title": "StatSrv Navigator",
                "mode": "narrow-icons-flat",
                "buttons": "nav_buttons",
                'icon': [6, 9]
                }
            },
        'nav_buttons': [
            {"label": "Hourly", "href": "/period/total/hour"},
            {"label": "Daily", "href": "/period/total/day"},
            {"label": "Minthly", "href": "/period/total/month"},
            {"label": "Posts", "href": "posts"},
            {"href": "tags"},
            {"href": "postgroups"},
            {"href": "all_pages"},
            {"href": "info"},
            {"href": "pie"}
            ]
        })
    
    load_global('strings', {# todo migrate more from code and clean up
'b.utf8': b'<meta charset="UTF-8">\n\n',
'head': '<html>\n<head><title>{}</title>\n<link rel="stylesheet" href="/style.css">\n</head>\n<body>\n<div class="pageinner">',
'thumb': '<span class="thumb{2}"><a class="thumba" href="{0}"><span>{1}</span></a></span>\n',
'menubtn-narrow-icons': '<span class="menubtn"><a href="{href}" alt="{alt}"><span class="iconsheet" style="background-position:{x}px {y}px;"></span>{label}</a></span>\n',
'menubtn-wide-icons': '<span class="menubtn wide"><a href="{href}" alt="{alt}"><span class="iconsheet" style="background-position:{x}px {y}px;"></span> {label}</a></span>\n',
'menubtn-list': '<a class="btn wide" style="font-size:initial;" href="{href}" alt="{alt}">{label}</a>\n',
'menubtn-narrow-icons-flat': '<a href="{href}" alt="{alt}">\n<div class="menu-button">\n<span class="iconsheet" style="background-position:{x}% {y}%;"></span>\n<span class="menu-label">{label}</span>\n</div>\n</a>\n',
'ewc': '<div class="desc"><details><summary>{} (Estimated {} word count)</summary>\n{}</details>\n</div><br>\n',
'nb': '<a class="btn{2}" href="{1}">{0}</a>\n',
'markt': '<button name="{0}@{1}" onclick="{action}" class="mbutton {3}">{2}</button>\n',
'all': '<br>\nThat\'s all I\'ve got on record. {} {}{}.',
'b.popdown': b'<button class="mbutton" id="popdownbtn" onclick="popdown();">&#x1F53B;</button><div id="popdown">',
'setlogic': '<div id="sets-man" class="hidden">\n<div class="ctrl">\n<input class="niceinp" id="setsName" oninput="setSearch()">\n<button class="mbutton" onclick="setsNew()">+</button>\n<button class="mbutton" onclick="setsClose()">X</button>\n</div>\n<div class="list" id="sets-list">\n</div>\n</div>\n',
'setread': '<div name="set{}@readma" class="mbutton"><i class="iconsheet ico-60 " style="background-position: -180px -180px;" onclick="apdmAllRead(this)"></i><select class="niceinp" onchange="apdmAllRead(this)">\n<option value=""></option>\n<option value="no-text">no-text</option>\n<option value="unread">unread</option>\n<option value="read">read</option>\n<option value="setur">setur</option>\n</select></div>',
'menubtn-wide-icons-flat': '<a href="{href}" alt="{alt}">\n<div class="menu-button menu-button-wide">\n<span class="iconsheet" style="background-position:{x}% {y}%;"></span>\n<span class="menu-label">{label}</span>\n</div>\n</a>\n',
'b.scout_no_data': b'<br>No data for Scout to use, please run user_stats,py to gather information first.<br><br>',

'config_optionwrap': '\n<div class="setting">{}\n</div>',
'config_namelabel': '<div class="info">\n<h2>{}</h2>\n<p>{}</p>\n</div>',
'config_input': '<div>\n<input class="niceinp" id="{id}" type="{inptype}" value="{val}">\n<button class="mbutton" onclick="{scr}">Apply</button>\n</div>',
'markswrapbox': '<div class="floatingmark markbox">\nMarks for <A href="{}">{} <b>{}</b></a>\n<br><br>\n{}\n{}</div>\n',
'markswrap': '<div class="floatingmark abox {}">\n{}\n{}</div>\n',

'eyde_link_other': '{} file: <a href="{}" target="_blank">Click here to open in new tab</a>',
'eyde_link_ts': '<br>\nAttached document: {:,} words <a href="/i/im/ts/{}" target="_blank">Click here to open in new tab</a><br>\n',
'eyde_post_title': '<a class="title" href="/view/{0}/1"><h2>{1}</h2></a>\n<a href="https://www.furaffinity.net/view/{0}/">view fa</a><br>\n',
'link_tf': '<a href="/keyword/{}:{}/1">{}</a>:',
'btn_tmp': '\n<div class="setting">\n<div class="info">\n<h2>{name}</h2>\n<p>{label}</p>\n</div><div>\n<input class="niceinp" id="{id}" type="{inptype}" value="{val}">\n<button class="mbutton" onclick="{scr}">Apply</button>\n</div></div>',
'l8rscout_link': '<a href="/l8rscout/@!passed%20l>1/1"><h2>By Available/Got ({:,})</h2></a>\n<div class="container list">\n',
'l8ratio_link': '<a href="/l8ratio/reversed%20@!passed/1"><h2 id="perc">Highest Percent</h2></a>\n<div class="container list">\n',
'stripeytablehead': '<table class="stripy">\n<tr>\n\t<td colspan={}>{}</td>\n</tr>\n',
'pt_items': '<div class="desc tags"><details><summary>{} ({:,} items)</summary>\n{}</details>\n</div><br>\n',
'search_bar': '<input id="searchbar" class="niceinp" placeholder="Search..." oninput="search(false)" />\n'
    })
    
    load_global('ent', {
        'building_entries': False,
        
        'config_file': 'statoptions.json',
        'menu_file': 'statmenus.json',
        
        'resources': [
            'style.css',
            'parrot.svg',
            'icons.svg',
            'mark.js',
            'client.js',
            'chart.js'
            ],
        'link_to': {
            'tags': '/tag/{}/1',
            'posts': '/view/{}/1'
           },
        '_collections': {},
        'reentry_buttons': [
            (' rebuild', 'rebuild', 'Rebuild'),
            ('', 'rebuild/9', 'D')
            ],
        'builtin': {
            'data': post_data()
            },
        'builtin_post': {
            'dummy': post_base(),
            'collections': post_collections(),
            '_flag': post__flag(),
            '_apref': post_apref()
            }
        })
    
    for k in list(globals()):
        if k.startswith('builtin_') or k.startswith('eyde_') or k.startswith('mort_'):
            n = k
            if not k.endswith('_base'):
                n = '_'.join(k.split('_')[1:])
            
            try:
                ent['builtin'][n] = globals()[k]()
            except Exception as e:
                if 'required positional argument' not in str(e):
                    logging.error(f"class {k}", exc_info=True)
    
    build_entries(reload=9)
    httpd = ThreadedHTTPServer((cfg['server_addr'], cfg['server_port']), request_handler)
    httpd.serve_forever()
