from onefad_web import *
from fa_parser import *
from append_handler import *
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
        
        elif k.startswith('eyde_') or k.startswith('mort_'):
            n = k
            if not k.endswith('_base'):
                n = '_'.join(k.split('_')[1:])
            
            try:
                ent['builtin'][n] = globals()[k]()
            except Exception as e:
                if 'required positional argument' not in str(e):
                    logging.error(f"class {k}", exc_info=True)


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
        if cfg.get('purge', True) and hasattr(v, 'purge'):
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


def timestamp_disp(t):
    if type(t) != datetime:
        t = datetime.utcfromtimestamp(t)
    
    return t.strftime('%b %d, %Y %H:%M')

'''
class builtin_test(builtin_base):
    
    def __init__(self, title='Test', icon=99):
        super().__init__(title, icon)
        self.pages = True
    
    def create_thumb(self, sid):
        data = sideposts.get(sid, {})
        return f'<img src="{data.get("thumb", "")}" loading="lazy" />'
    
    def page(self, handle, path):
        print(path)
        if type(path[-1]) != int:
            path.append(1)
        
        idx = path[-1]
        items = list(sideposts)
        nav = template_nav('Test', idx, int(len(items) / 25), enc=False)
        self.write(handle, nav)
        
        for sid in items[(idx-1)*25:idx*25]:
            self.write(handle, self.create_thumb(sid))
'''

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
    '''
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
    '''
    linkdes = thing
    href = '/{}'
    '''
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
    '''
    if kind == 'users':
        if thing in ent['userposts']:
            got = len(ent['userposts'][thing])
            linkdes += wrapme(got, f=' {:,}')
        
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


def pick_thumb(posts, do_ext=True):
    return 'parrot.svg'


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
        '''for m, d in apdmm.items():
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
        
        cull = self.hide_empty or mincount
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
            #if self.marktype == 'users' and cull:
            #    d, perc = users_marked.get(t, (0, 0))
            
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
        
        l = '/parrot.svg'
        if self.marktype == 'users':
            l = f'//192.168.0.66:6953/avatar/{item.replace("_", "")}.gif'
        
        label = f'<img loading="lazy" src="{l}" /><br>'
        #label = overicon(self.marktype, item, con=self.con) + label
        
        if type(data) != int:
            data = len(data)
        
        #if self.marktype == 'users' and cfg['docats']:
        #    data, perc = users_marked.get(item, (0, 0))
        
        labelt = [item, '-', wrapme(data)]
        
        #if self.marktype == 'users':
        #    labelt.append(wrapme(ent['ustats'].get(item, '?'), f='({:,})'))
        
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
        
        artm = ''#markicons_for(self.marktype, item)
        
        href = create_linktodathing(self.marktype, item, con=self.con, retmode='href')
        
        h += strings['thumb'].format(self.link.format(href), self.build_label(i, item, data, mode), ' ' + artm)
        
        return h
    
    def ez_build_item(self, i):
        return self.build_item(i, self.datas.get(i), self.marktype)
    
    def get_items(self):
        return self.items


def usersort():
    ent['usersort'] = ['.someone']
    ent['userposts'] = {'.someone': []}
    usertemp = set(['.someone'])
    
    for post, data in sideposts.items():
        if type(data) != dict:
            continue
        uploader = data.get('uploader', '.someone').replace('_', '').lower()
        
        if uploader not in usertemp:
            usertemp.add(uploader)
            ent['userposts'][uploader] = []
            ent['usersort'].append(uploader)
        
        ent['userposts'][uploader].append(post)
    
    return ent['usersort']


class mort_users(mort_base):
    
    def __init__(self, marktype='users', title='Users', link='/user/{}/1', icon=ii(0)):
        super().__init__(marktype, title, link, icon)
    
    def get_items(self):
        return ent['usersort']
    
    def gimme_idc(self):
        self.items = self.get_items()
        self.datas = ent['userposts']


def get_posts(posts):
    return {post: sideposts.get(post, {'got': False}) for post in posts}


class eyde_base(mort_base):

    def __init__(self, items=[], marktype='', icon=ii(89)):
        super().__init__()
        self.pagetype = 'eyde'
        self.items = items
        self.pages = True
        
        if icon is None:
            icon = ii(89)
        self.icon = icon
        
        self.marktype = marktype
        
        self.modes_default = 'full'
        self.modes = {
        'full': 'Full mode',
        'thumb': 'Thumb mode',
        'fa': 'FA mode'
        }
        
        self.name = ''
        self.title = 'EYDE'
        self.markid = 'mark_id_error'
        self.do_mark = True
        self.clear_threshold = 0
        self.hide_empty = self.marktype == 'users'
        
        self.headtext = ['', '', '']
        
        self.path_parts = 3
        self.page_options = [
            list(self.modes),
            ['cull', 'nocull', 'marked'],
            ['showalt', 'hidealt', 'onlyalt']
            ]
        self.filters = {}
    
    def page(self, handle, path):
        self.gimme(path)
    
        self.build_page(handle, path)
    
    @staticmethod
    def gimme(pargs):
        pass
    
    def modes_fallback(self):
        if cfg.get('eyde_default_mode') in self.modes:
            return cfg.get('eyde_default_mode')
        
        return self.modes_default
    
    def process_filters(self, thing, filters):
        return {label: link.format(thing)
                for label, link in filters.items()}
    
    def build_filters(self, thing):
        if not self.filters:
            return ''
        
        filters = self.process_filters(thing, self.filters)
        
        h = '<div class="linkthings centered">\n'
        c = 0
        for label, link in filters.items():
            if '/' not in link:
                link = f'/filter/{link}/1'
            
            h += f'<a href="{link}">{label}</a>\n'
            c += 1
        
        return h + '</div>\n'
    
    def cull_mode(self, compare, inc, exc):
        if not (inc or exc):
            return
        
        mode = inc and not exc
        
        self.f_items = [
            i for i in self.f_items
            if (i in compare) != mode]
    
    def build_page(self, handle, pargs):
        
        self.f_items = self.items
        
        pf = []
        if pargs and isinstance(pargs[-1], int):
            index_id = pargs[-1]
            if len(pargs) > 2:
                pf = str(pargs[-2]).split(' ')
        
        si = len(self.f_items)
        index_id = 1
        
        if pargs:
            index_id = pargs[-1]
        
        lse = self.page_count(si, index_id)
        last_page, sa, ea = lse
        
        h, list_mode, nav, si = self.build_page_wrap(pargs, lse)
        h += f'<!--\nclass: {type(self).__name__}\nmarktype: {self.marktype}\nname: {self.name}\ntitle: {self.title}\nmarkid: {self.markid}\n-->'
        
        h += self.build_page_mode(list_mode, lse)
        
        if index_id == last_page and sa < si:
            h += f'\n<p>Reached of list, shown {si:,} item{plu(si)}</p>'
        
        h += f'\n</div><div class="foot">{nav}\n<br>'
        try:
            self.write(handle, h)
        
        except UnicodeEncodeError as e:
            logging.error(f">Encountered a UnicodeDecodeError {handle.path}", exc_info=True)
            self.write(handle, f'<p>Encountered a UnicodeDecodeError: {e}</p>\n')
            self.write(handle, h)
        
        self.f_items = []
    
    def build_page_wrap(self, pargs, lse):
        index_id = 1
        
        if pargs:
            index_id = pargs[-1]
        
        pargs = [str(x) for x in pargs]
        last_page, sa, ea = lse
        
        if index_id < 1:
            index_id += last_page
        
        h = ''#strings['setlogic']
        
        si = len(self.f_items)
        last_page, sa, ea = lse
        
        list_mode, wr = self.mode_picker(pargs)
        
        nav = template_nav(self.title, index_id, last_page, enc=False)
        
        h += f'<div class="head">\n{nav}</div>\n'
        h += f'<div class="container">\n{wr}'
        
        h += self.build_filters(self.markid)
        
        h += self.headtext[0]
        
        #if self.do_mark:
        #    h += mark_for(self.marktype, self.markid, page=self.name)
        
        h += self.headtext[1]
        
        h += f'<p>{si:,} item{plu(si)}</p>\n'
        
        return h, list_mode, nav, si
    
    def build_page_mode(self, list_mode, lse):
        last_page, sa, ea = lse
        
        if list_mode == 'full':
            h = self.build_page_full(sa, ea)
        
        elif list_mode == 'thumb':
            h = self.build_page_thumb(sa, ea)
        
        elif list_mode == 'fa':
            h = self.build_page_fa(sa, ea)
        
        else:
            h = f'Unimplemented Mode: {list_mode}'
        
        return h
    
    def build_page_full(self, sa, ea):
        out = ''
        
        items = self.f_items[sa:ea]
        local = get_posts(items)
        
        for item in items:
            out += self.build_item_full(
                item,
                'No descs loaded',
                local.get(item, {'got': False}))
        
        return out
    
    def place_file(self, ext, link, srcbytes, prop='', dolinks=True):
        cat = file_category(ext)
        if cat == 'image':
            return f'<img loading="lazy" src="{link}"{prop}/>\n'
        
        ret = f'<p>{ext.upper()} file'
        if ext == 'txt':
            apwc = int(srcbytes / 6.5)# dumb word count
            ret += wrapme(apwc, f=' Approx {:,} words')
            link = link.replace('i/im', 'reader')
        
        ret += '</p>\n'
        
        if dolinks:
            ret += f'<a href="{link}" target="_blank">Click here to open in new tab</a>'
        
        return ret
    
    def get_file_link(self, post, data):
        ext = data.get('ext', 'png')
        fn = f'{post}.' + ext
        
        link = f'http://192.168.0.66:6770/i/im/{fn}'
        
        return self.place_file(ext, link, data.get('srcbytes', 0))
    
    def build_item_full(self, post, desc, data):
        title = data.get('title', f'Unavailable: {post}')
        
        ret = strings['eyde_post_title'].format(
            post, title)
        
        if data.get('origin') == 'alt':
            ret = f'<span class="altsrv">{ret}'
        
        ret = f'<div class="post post-full" id="{post}@post">\n' + ret
        
        ret += self.get_file_link(post, data)
        
        if True:
            ret += very_pretty_json(f'post:{post}', data)
        
        #ret += mark_for('posts', post)
        
        ret += '</div><br>\n'
        
        return ret
    
    def build_page_thumb(self, sa, ea):
        out = ''
        
        items = self.f_items[sa:ea]
        local = get_posts(items)
        
        for item in items:
            out += self.build_item_thumb(
                item,
                local.get(item, {'got': False}))
        
        return out
    
    def ez_build_item(self, item):
        return self.build_item_thumb(item, get_post(item))
    
    def build_item_thumb(self, post, data):
        
        title = data.get('title', f'Unavailable: {post}')
        
        cla = ''
        if data.get('origin') == 'alt':
            cla = ' altsrv'
        
        ret = f'<span class="tbox"><span class="thumb{cla}">\n<div class="thumba" id="{post}@post">'
        ret += f'<a class="title" href="/view/{post}/1">{title}</a>\n<a href="https://www.furaffinity.net/view/{post}/">view fa</a><br>\n'
        
        ret += self.get_file_link(post, data)
        
        ret += '</div></span>\n'
        
        #ret += '\n<br>\n' + mark_for(domark, post, size=40, page=self.name)
        
        ret += '</span></span>\n'
        
        return ret
    
    def build_page_fa(self, sa, ea):
        out = ''
        items = self.f_items[sa:ea]
        local = get_posts(items)
        
        for item in items:
            data = local.get(item, {'got': False})
            out += self.build_item_fa(item, data)
        
        return out

    def build_item_fa(self, post, data):
        cla = data.get('rating', 'error').lower()
        if data.get('origin') == 'alt':
            cla += ' altsrv'
        
        ret = f'''<figure id="sid-{post}" class="r-{cla} t-image">
<a class="t-inner" href="/view/{post}/">'''

        #ret += overicon('posts', post, con=None)
        
        ret += self.get_file_link(post, data)
        
        title = data.get('title', f'Unavailable: {post}')
        
        ret += f'</a>\n<figcaption>\n<p><a href="/view/{post}/" title="{title}">{title}</a></p>\n</figcaption>\n</figure>\n'
        
        return ret
    
    def purge(self, strength):
        if self.clear_threshold <= strength:
            self.items = []
            self.f_items = []
            self.title = ''
            self.name = ''
            self.headtext = ['', '', '']


class eyde_user(eyde_base):

    def __init__(self, items=[], marktype='users'):
        super().__init__(items, marktype)
        
        self.page_options.append(['escape'])
    
    def gimme(self, pargs):
        if len(pargs) > 1:
            user = str(pargs[1]).replace('_', '')
        else:
            user = ''
        
        if 'escape' in pargs:
            user = html.escape(user)
        
        self.name = f'user:{user}'
        self.title = user
        self.markid = user
        posts = ent['userposts']
        
        self.items = posts.get(user, [])
        
        h = ''
        
        for path, name in [["https://www.furaffinity.net/user/{}/", "FA Userpage"]]:
            path = path.format(user)
            h += f'<p><a href="{path}">{name}</a></p>\n'
        
        self.headtext[1] = h


class builtin_info(builtin_base):

    def __init__(self, title='Info', icon=51):
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
        self.stat(handle, 'Last Rebuilt', timestamp_disp(ent['built_at']))
        self.stat(handle, 'Posts', len(sideposts))
        self.stat(handle, 'Last Posts', ent['lastposts'])

        doc = '<table class="stripy">\n<tr>\n<td>Origin</td>\n<td>Count</td></tr>\n'
        c = 0
        cla = [' class="odd"', '']
        for no, ask in enumerate(cfg['ask_servers']):
            name = ask.get("name")
            if not name:
                name = f'{ask["ip"]}:{ask.get("port", 6970)}'
            
            doc += f'<tr{cla[c%2]}>\n\t'
            doc += f'<td>{name}</td>\n\t'
            doc += f'<td>{len(has[no]):,}</td>\n\t'
            c += 1
        
        doc += '</table></div>\n'
        self.write(handle, doc)


def big_action_list_time(reload=0):
    global has, sideposts, ent
    
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
        sideposts = appender()#_sharedkeys()
        sideposts.read(cfg['apd_dir'] + 'sideposts')
    
    ent['lastposts'] = len(sideposts)
    
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
    
    usersort()
    
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
    
    load_global('strings', {# todo migrate more from code and clean up
'thumb': '<span class="thumb{2}"><a class="thumba" href="{0}"><span>{1}</span></a></span>\n',
'eyde_post_title': '<a class="title" href="/view/{0}/1"><h2>{1}</h2></a>\n<a href="https://www.furaffinity.net/view/{0}/">view fa</a><br>\n',
})

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
        
        'usersort': [],
        'userposts': {},
        
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
