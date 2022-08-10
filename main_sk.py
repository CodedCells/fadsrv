#############################################################################
# pep8 non-compliant :(
import requests
import gc

from onefad_functions import *

ent['version'] = '31#2022-07-11'

class builtin_base(builtin_base):
    
    def bookmark_hook(self, handle):
        path = handle.path.replace('@', '%64')
        self.write(handle, mark_for('url', path))


def get_post_alt(path, rd):
    global altfa
    
    req = requests.post(path, json=rd)
    req = req.json()
    
    if not req or 'error' in req:
        return {}
    
    altfa.write(req)
    return req


def get_post(post):
    data = apdfa.dget(post)
    if data:
        return data
    
    data = altfa.dget(post)
    if data:
        data['origin'] = 'alt'
        return data
    
    return {'got': False}


def get_posts(posts):
    local = {}
    find = []
    for post in posts:
        data = get_post(post)
        if data.get('got', True):
            local[post] = data
            
            if data.get('filedate'):
                continue
        
        find.append(post)
    
    for srv, tag in cfg['altdatsrv']:
        if not find:break
        try:
            logging.debug(f'Asking {srv} for {len(find):,} posts')
            remote = get_post_alt(srv, {tag: find})
            for post, data in remote.items():
                find.remove(post)
                data['origin'] = 'alt'
                local[post] = data
        
        except requests.exceptions.ConnectionError:
            logging.debug(f'Gave up on {srv}')
            continue
    
    return local


def markedposts():
    global ent
    
    ent['built_markedposts'] = False
    mark = set()
    
    exclude = [m for m, d in apdmm.items()
               if compare_for(d, 'posts')
               and d.get('excludeMarked', True)]
    
    for x in exclude:
        if apdmm[x].get('type') == 'collection':
            item = dpref.get(x, {}).items()
        else:
            item = apdm[x].items()
        
        items = set()
        for k, d in item:
            if d[0] == 'n/a':
                continue
            items.add(k)
        
        mark.update(items)

    ent['_marked'] = mark
    ent['_posts'] = set(apdfa)
    
    ent['built_markedposts'] = True
    
    return mark


def datasort():
    global ent, users, users_has, users_marked, users_mod, kwd, kws
    
    mark = ent['_marked']
    posthas = ent.get('_posts', set())
    partial = {}
    users_marked = {}
    start = time.perf_counter()
    
    if ent['added_content'] or ent['force_datasort']:
        users = {}
        ent['usersort'] = []
        users_has = set()
        users_mod = {}
        kwd = {}
        kws = set()
    
    
    want_users = len(users) == 0
    want_tags = len(kws) == 0

    allposts = set((i, False) for i in altfa)
    allposts.update(set((i, True) for i in apdfa))
    for post, has in allposts:
        if has:
            data = apdfa.dget(post)
        else:
            data = altfa.dget(post)
        
        if not post or data.get('data') == 'deleted':
            continue
        
        if want_users:
            user = data.get('uploader', '.badart').lower().replace('_', '')
            
            if user not in users_has:
                users[user] = []
                partial[user] = 0
                users_has.add(user)
            
            posti = post
            if post.isdigit():
                posti = int(post)
            
            users[user].append(posti)
            
            m = data.get('filedate', -1)
            if isinstance(m, float) and users_mod.get(user, 0) < m:
                users_mod[user] = m
            
            if post in posthas:
                partial[user] += post not in mark
        
        if want_tags:
            if not data.get('tags'):
                data['tags'] = ['_untagged']
            
            for kw in data['tags']:
                if kw not in kws:
                    kws.add(kw)
                    kwd[kw] = []
                
                kwd[kw].append(post)
    
    if want_tags:
        kws = sorted(kws, key=lambda k: len(kwd[k]))
    
    for user, posts in users.items():
        users[user] = [str(x) for x in sorted(posts)]
        marked = partial.get(user, 0)
        posts = [post for post in posts if post in posthas]
        if not want_users:# not did above stuff
            marked = sum([post not in mark for post in posts])
        
        users_marked[user] = marked, marked / max(len(posts), 1)
    
    ent['force_datasort'] = False
    ent['usersort'] = sorted(users, key=lambda k: len(users[k]))
    
    logging.info(f'Users and Tags in {time.perf_counter()-start:,.01f}s')


def apd_findnew():
    global apdfa, apdfadesc, apdfafol, xlink
    
    logging.info('Finding posts to include...')
    made_changes = 0
    
    fields = {
        'ext',      'uploader', 'date',     'title',
        'tags',     'desclen',  'descwc',   'folders',
        'srcbytes', 'rating',   'filedate', 'resolution'
        }
    
    knowns = None
    knownf = None
    
    if os.path.isdir('put/'):
        for fn in os.listdir('put/'):
            logging.info(f'Adding {fn} from put')
            dst = data_path(fn, s='_desc.html')
            
            if os.path.isfile(dst):
                os.remove(dst)
            
            shutil.move(f'put/{fn}', dst)
            fi = fn.split('_')[0]
            
            if fi in apdfa:
                del apdfa[fi]
    
    c = 0
    
    ch_apdfa = {}
    ch_apdfadesc = {}
    ch_apdfafol = {}
    
    if cfg['post_split']:
        files = []
        for i in range(100):
            i = cfg['image_dir'] + f'{i:02d}/'
            if os.path.isdir(i):
                files += os.listdir(i)
    else:
        files = []
        if os.path.isdir(cfg['image_dir']):
            files = os.listdir(cfg['image_dir'])
    
    for file in files:
        # todo this extension management is horrible
        
        if '.' not in file:
            logging.info(f'File missing extension: {file}')
            file += '.'
        
        try:
            postid, postext = file.split('.')
        except Exception as e:
            logging.info(f'File has funky extension: {file}')
            continue
        # this all between
        
        pd = {**apdfa.dget(postid, {})}
        
        add = [x for x in fields
               if x not in pd
               or (x in ['title', 'uploader'] and not pd[x].strip())]
        
        if not add:continue
        if file == 'apdlist':continue
        
        add.append('desc')
        
        logging.info(f'Adding data for {file}, adding {json.dumps(add)}')
        c += 1
        if not c % 200:
            logging.info(f'{c:>5,} posts so far')
        
        made_changes += 1
        if 'ext' in add:
            pd['ext'] = postext
            add.remove('ext')
            if not add:
                ch_apdfa[postid] = pd
                continue
        
        if 'rating' in add:
            if knowns is None:
                knownf = appender_sharedkeys()
                knownf.read(cfg['data_dir'] + 'known_faves')
                knownf = {x: y['rating'] for x, y in knownf.items()}
                knowns = set(knownf)
            
            if postid in knowns:
                pd['rating'] = knownf[postid]
                add.remove('rating')
                if not add:
                    ch_apdfa[postid] = pd
                    continue
        
        datafn = data_path(postid, s='_desc.html') + '_desc.html'
        
        try:
            data = readfile(datafn)
        
        except UnicodeDecodeError:# prevent strange files messing up
            logging.warning(f'Unicode error when opening {datafn}')
            data = str(readfile(datafn, mode='rb', encoding=None))
        
        except FileNotFoundError:
            logging.warning(f'Missing data {datafn}')
            made_changes -= 1
            continue
        
        if 'rating' in add:
            if 'name="twitter:data2" content="' in data:
                rat = get_prop('name="twitter:data2" content="', data).lower()
                pd['rating'] = rat
            
            elif '<div class="rating">' in data:
                rat = get_prop('<div class="rating">', data, t='</span')
                pd['rating'] = rat.split(' ')[-1].lower()
            
            else:
                logging.warning(f'Rating container not found for {postid}')
                pd['rating'] = None
        
        if 'filedate' in add:
            if 'Server Time: ' in data:
                rat = get_prop('Server Time: ', data, t='</div').strip()
                pd['filedate'] = strdate(rat).timestamp()
            
            else:
                logging.warning(f'File Date container not found for {postid}')
                pd['filedate'] = None
        
        if 'resolution' in add:
            if 'Size</strong> <span>' in data:
                rat = get_prop('Size</strong> <span>', data,
                               t='</span').split(' x ')
                
                pd['resolution'] = [int(rat[0]), int(rat[1])]
            
            elif '<b>Resolution:</b> ' in data:
                rat = get_prop('<b>Resolution:</b> ', data,
                               t='<br>').split('x')
                
                pd['resolution'] = [int(rat[0]), int(rat[1])]
            
            else:
                logging.warning(f'Size container not found for {postid}')
                pd['resolution'] = None
        
        if 'srcbytes' in add:
            pd['srcbytes'] = os.path.getsize(data_path(file, d='image'))
        
        if not data:
            ch_apdfa[postid] = pd
            continue
        
        if 'tags' in add:
            ks = '@keywords _untagged"'
            
            if '"/search/@keywords' not in data:# no tags
                pass
            
            elif '<div id="keywords">' in data:# old theme
                ks = get_prop('<div id="keywords">', data, t='</div>')
            
            elif '<section class="tags-row">' in data:# new theme
                ks = get_prop('<section class="tags-row">',
                              data, t='</section>')
            
            else:
                logging.warning(f'Keyword container not found for {postid}')
                made_changes -= 1
                continue
            
            pd['tags'] = [x.split('"')[0].lower()
                              for x in ks.split('@keywords ')[1:]]
        
        if 'date' in add:
            datesplit = '<span class="hideonmobile">posted'
            oldatesplit = '<b>Posted:</b> <span'
            if datesplit in data:
                date = fa_datebox(get_prop(datesplit, data, t='</strong>'))
                # MMM DDth, CCYY hh:mm AM
                pd['date'] = strdate(date).timestamp()
            
            elif oldatesplit in data:
                date = fa_datebox(get_prop(oldatesplit, data, t='</span>'))
                # MMM DDth, CCYY hh:mm AM
                pd['date'] = strdate(date).timestamp()
            
            else:
                logging.warning(f'Date container not found for {postid}')
                made_changes -= 1
                continue
        
        if 'folders' in add:
            pd['folders'] = []
            if 'Listed in Folders' in data:
                for f in get_prop('Listed in Folders</h3>',
                                  data, t='</section').split('</div>')[:-1]:
                    fpath = get_prop('href="', f)
                    folid = fpath.split('/')[4]
                    pd['folders'].append(folid)
                    
                    if folid in ch_apdfafol:
                        if postid not in ch_apdfafol[folid]['items']:
                            ch_apdfafol[folid]['items'].append(postid)
                    
                    elif folid in apdfafol:
                        ch_apdfafol[folid] = apdfafol.dget(folid).copy()
                        if postid not in ch_apdfafol[folid]['items']:
                            ch_apdfafol[folid]['items'].append(postid)
                    
                    else:
                        ch_apdfafol[folid] = {
                            'path': fpath,
                            'title': get_prop('span>', f, t='</'),
                            'count': int(get_prop('title="', f, t=' ')),
                            'items': [postid]
                            }
            
        if 'title' in add:
            titlec = [
                '<div class="submission-title">',
                '"classic-submission-title information">',
                '<table cellpadding="0" cellspacing="0" border="0" width="100%">'
                ]
            if titlec[0] in data:
                title = get_prop(titlec[0],
                                 data, t='</p>').split('<p>')[1]
            
            elif titlec[1] in data:# pretty old
                title = get_prop(titlec[1],
                                 data, t='</h2>').split('<h2>')[1]
            
            elif titlec[2] in data:# old as balls
                title = get_prop(titlec[2],
                                 data, t='</th>').split('class="cat">')[1]
            
            else:
                logging.warning(f'Title container not found for {postid}')
                continue
            
            title = html.unescape(title).strip()
            if not title:
                title = 'Untitled'
            
            pd['title'] = title
        
        if 'uploader' in add:
            pd['uploader'] = get_prop('property="og:title" content="',
                                  data).split(' ')[-1].lower()
        
        # modern theme
        ctheme = '<div class="submission-description user-submitted-links">'
        ctheme2 = '<td valign="top" align="left" width="70%" class="alt1" style="padding:8px">'
        if ctheme in data:
            desc = get_prop(
                ctheme,
                data, t='</div>').strip()
        
        # pre-2020 theme modern theme?
        elif '<div class="submission-description">' in data:
            desc = get_prop('<div class="submission-description">',
                            data, t='</div>').strip()
        
        # pre-2020 classic theme?
        elif ctheme2 in data:
            desc = get_prop(ctheme2, data, t='</td>')
        
        else:
            logging.warning(f'Description container not found for {postid}')
            made_changes -= 1
            continue
        
        desc = '"https://www.furaffinity.net/gallery/'.join(
            desc.split('"/user/'))
        
        desc = '\n'.join([x.strip() for x in desc.split('\\n')])
        desc = '\n'.join([x.strip() for x in desc.split('\n')])
        pd['desclen'] = len(desc)
        pd['descwc'] = len(re.findall(r'\w+', desc))
        
        url = get_prop('"og:url" content="', data)
        urlid = url.split('/')[-2]
        if urlid != postid:
            logging.warning(f'{postid} doesn\'t match {url}')
        
        ch_apdfa[postid] = pd
        ch_apdfadesc[postid] = desc
    
    if not made_changes:
        logging.info('No changes found, skipping...')
    
    dd = cfg['apd_dir']
    if c:
        logging.info(f'{c:>5,} posts done')
        
        logging.info('Writing Big APD')
        apdfa.write(ch_apdfa, volsize=100000)
        apdfafol.write(ch_apdfafol)
        
        if cfg['desc_split']:
            ch_descblocks = {}
            for item, data in ch_apdfadesc.items():
                block = desc_fol(item)
                if block not in ch_descblocks:
                    ch_descblocks[block] = {}
                
                ch_descblocks[block][item] = data
            
            for block, data in ch_descblocks.items():
                if not data:continue
                out = appender()
                out.write(data, filename=dd + f'outdesc/{block}')
        
        out = appender()
        out.write(ch_apdfadesc, volsize=100000, filename=dd + 'apdfadesc')
        
        logging.info('Done writing and apply changes')
    
    logging.info('Building new desc links')
    
    descpost = set(xlink['descpost'])
    descuser = set(xlink['descuser'])
    
    ch_descpost = {}
    ch_descuser = {}
    if not cfg['desc_split']:
        ch_apdfadesc = apdfadesc
    
    for postid, desc in ch_apdfadesc.items():
        thispostids = set()
        
        if postid not in descpost:
            if type(desc) != str:continue
            for linky in ['view/', 'full/']:
                if linky in desc:
                    for x in desc.split(linky)[1:]:
                        ogi = ''
                        for c in x.split('"')[0].strip():
                            # nested way too deep
                            if c.isdigit():ogi += c
                            else:break
                        
                        thispostids.add(ogi)
            
            ch_descpost[postid] = list(thispostids)
        
        thispostids = set()
        if postid not in descuser:
            # get a string error sometimes idk why
            me = apdfa.dget(postid, {}).get('uploder', '.badart')
            
            for linky in ['user/', 'gallery/', 'scraps/']:
                if linky in desc:
                    for x in desc.split(linky)[1:]:
                        og = x.split('"')[0].lower()
                        # nested way too deep
                        if '/' in og:og = og.split('/')[0]
                        if og == me:continue
                        
                        thispostids.add(og)
            
            ch_descuser[postid] = list(thispostids)
    
    # todo copy pasta
    if ch_descpost:
        logging.info('Writing descpost')
        xlink['descpost'].write(ch_descpost, volsize=100000)
    
    if ch_descuser:
        logging.info('Writing descuser')
        xlink['descuser'].write(ch_descuser, volsize=100000)
    
    logging.info('Completed new desc links')
    
    return made_changes


def load_text_attach():
    # load and build ts information
    global ent, apdmm, apdm, dprefm, dpref
    
    apdmm['textattach'] = {
        "icon": ii(68),
        "type": "multibutt",
        "values": ["textattach"],
        "excludeMarked": False,
        "order": 200,
        "disabled": True,
        "hidden": True
        }
    
    if 'textattach' not in ent['apdmark']:
        ent['apdmark'].append('textattach')

    if '_attach' not in ent:
        ent['_attach'] = appender()
    
    attach = ent['_attach']
    apdm['textattach'] = {}
    tadir = cfg['image_dir'] + '_ta/'
    
    if os.path.isdir(tadir):
        attach.read(tadir + 'apdta')
        ch_attach = {}
        if not attach:
            logging.info('Preparing text attach info')
        
        for fn in os.listdir(tadir):
            if not fn.endswith('.txt'):continue# only txt
            
            postid = fn.split('.')[0]
            if postid in attach:continue# not has
            
            with open(tadir + fn, 'rb') as fh:
                words = len(fh.read().split(b' '))
                fh.close()
            
            ch_attach[postid] = {'filename': fn, 'words': words}
        
        if ch_attach:
            logging.info('Adding', len(ch_attach), 'attach')
            attach.write(ch_attach)
    
    else:
        logging.info('No text attach dir')
    
    apdm['textattach'] = {x: ['textattach', 0] for x in attach}


def get_subs(user):
    data = ustat.dget(user, {})
    return data.get('posts', .1)


def new_userstat():
    global ent, ustat
    
    if 'ustat' not in globals():
        ustat = appender_sharedkeys()
    
    ustat.read(cfg['apd_dir'] + 'userstats')


def fpref_make():
    global fpref
    fpref = {}
    
    for name, page in ent['builtin'].items():
        if not page.pagetype.startswith('remort'):
            continue
        
        if not (hasattr(page, 'marktype') and page.marktype):
            continue
        
        fpref[name] = {'icon': page.icon, 'for': page.marktype}


def register_dynamic():
    global ent, menus
    
    for m, d  in apdmm.items():
        
        if d.get('type', False) == 'collection':
            name = d.get('name', m)
            
            if compare_for(d, 'posts', sw=True):
                if name.lower() not in ent['builtin']:
                    ent['builtin'][name.lower()] = eyde_collection(m)
            
            else:
                if name.lower() not in ent['builtin']:
                    ent['builtin'][name.lower()] = mort_collection(m)
            
            name_list = d.get('name_plural', name + 's')
            ent['_collections'][name_list.lower()] = m
            
            if m not in ent['link_to']:
                ent['link_to'][m] = f'/{name}/{{}}/1'
            
            if name_list.lower() not in ent['builtin']:
                ent['builtin'][name_list.lower()] = mort_collection_list(m, name_list)
        
        if compare_for(d, 'posts', sw=True):
            mode = 'posts'
            cla = mort_postamark
        
        elif compare_for(d, 'url'):
            mode = 'other'
            cla = builtin_menu_mark
        
        else:
            mode= 'other'
            cla = mort_amark
        
        for v in d.get('values', []):
            if v not in ent['builtin']:
                ent['builtin'][v] = cla(m, v)
        
        if d.get('stats') and 'charts' in d['stats']:
            ent['builtin'][f'stats{m}'] = builtin_statsmark(m)
    
    for m, c in list(ent['builtin'].items()):
        if type(c) == builtin_menu:
            del ent['builtin'][m]
    
    for m in menus['pages']:
        ent['builtin'][m] = builtin_menu(which=m)
    
    
    menus['all_pages_buttons'] = []
    rbcat = {
        'builtin': [],
        'builtin stats': [],
        'builtin menu': [],
        'remort': [],
        'remort mark': [],
        'eyde': [],
        'remort postmark': []
        }
    
    for m, v in ent['builtin'].items():
        c = ''
        pagetype = v.pagetype
        if cfg['purge'] and hasattr(v, 'purge'):
            v.purge(1)
        
        icn = {'label': m, 'href': m, 'label2': ''}
        sorter = '_' + m
        c = pagetype.replace('_', ' ')
        if pagetype.startswith('remort'):
            if hasattr(v, 'marktype'):
                icn['label2'] = v.marktype
        
        elif pagetype == 'pages':
            icn['label'] = v.title
            icn['href'] = '/'+icn['href']
        
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


def load_altfa():
    global altfa
    
    if not 'altfa' in globals():
        altfa = appender_sharedkeys()
    
    altfa.read(cfg['apd_dir'] + 'altfa')


def build_heavy(reload=0):
    if reload > 2:
        init_apd()
    
    if reload > 1:
        load_apd()
    
    if reload > 2:
        willload = reload > 4
        load_altfa()
        willload = load_bigapd(willload)
        
        if willload and not cfg.get('skip_findnew'):
            ent['force_datasort'] = True
            ent['added_content'] = apd_findnew()
    
    load_text_attach()
    fpref_make()
    new_userstat()
    loadpages()


def build_entries(reload=0):
    global ent
    
    if isinstance(reload, str):
        if reload.isdigit():reload = int(reload)
        else:reload = 0
    
    if ent['building_entries']:
        logging.info('Already building entries! goto /unstuck if this is an error')
        return
    
    ent['building_entries'] = True
    ent['generated'] = datetime.now()
    logging.info('Started building entries')
    logging.info(f'reload level: {reload}')
    ent['visited_rebuild'] = []
    
    start = time.perf_counter()
    load_user_config()
    if reload:
        build_heavy(reload)
    
    save_config()
    
    apdm_divy()
    markedposts()
    logging.info(f'Processing took {time.perf_counter() - start:,.01f}s')
    datasort()
    register_dynamic()
    
    logging.info(f"{len(ent['usersort']):,} users")
    ent['added_content'] = False
    ent['building_entries'] = False
    logging.info('Ready.')
    return


def lister_items(kind):
    si = ent['_lists'].get(kind, {})
    q = []
    if 'ent' in si:
        q = ent.get(si['ent'], [])
    elif 'items' in si:
        q = si['items']
    
    if type(q) == dict:
        q = list(q)
    
    else:
        if 'i' in si:
            q = [i[si['i']] for i in q]#aye aye aye
        else:
            q = list(q)
    
    return q


def lister_linker(kind):
    return ent['link_to'].get(kind, '/{}/1')


def lister_get(kind, thing):
    qpos = -1
    
    si = ent['_lists'].get(kind, {})
    
    q = lister_items(kind)
    hd = lister_linker(kind)
    
    bprev, bnext = '', ''
    
    icon = si.get('icon', '?')
    ogm = icon
    if type(icon) == list:
        ogm = 'iconsheet' + markicon(*icon, m=-24)
        ogm = f'<i class="teenyicon {ogm}"></i>'
    
    if thing in q:
        qpos = q.index(thing)
        bprev = strings['nb'].format(
            '&lt; ' + ogm, hd.format(q[qpos-1]), '')
        
        bnext = strings['nb'].format(
            ogm + ' &gt;', hd.format(q[(qpos+1)%len(q)]), '')
    
    return bprev, bnext


def page_count(flen, index_id, pc=''):
    # used to select elements per page of mort and eyde
    
    if type(pc) != int:
        pc = cfg['post_count']
    
    last_page = max(math.ceil(flen / pc), 1)
    
    sa = (index_id - 1) * pc
    ea = index_id * pc
    
    if 0 < flen % pc <= cfg['over']:
        # bring extra items over rather than a short page
        last_page = max(last_page - 1, 1)
        if index_id == last_page:
            ea = flen
    
    if index_id < 1:# wrap back around
        index_id += last_page
        if index_id == last_page:
            ea = flen
    
    return last_page, sa, ea


def markicon(x, y, m=-60):
    return f'" style="background-position: {x*m}px {y*m}px;'


def valueicon(value, icons, default, values=[]):
    if type(value) != int:
        value = values.index(value)
    
    if len(icons) > value:
        return icons[value], True
    else:
        return default, False


def mark_state(mark, thing):
    if apdmm[mark].get('type') == 'collection':
        mt = get_collectioni(mark, thing, onlyin=True)
        ret = [[None, mark][len(mt) > 0], mt]
    
    elif apdmm[mark].get('list') is True:
        ret = [None, mark][thing in apdm[mark]]
    
    else:
        ret = apdm[mark].get(thing, [None])[0]
    
    if ret == 'n/a':ret = None
    #print(mark, thing, ret)
    return ret


class mark_button(object):

    def __init__(self, mark=None, action=None):
        
        self.mark = mark
        self.data = apdmm.get(mark, {})
        
        self.btype = self.data.get('type')
        self.action = action
    
    def disabled(self):
        return self.data.get('disabled', False) or cfg['static']
    
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
    
    def build_for(self, thing, state=None, size=60, origin=None, page=None):
        
        if self.data.get('hidden') and not cfg.get('show_hidden_marks'):
            return '', ''
        
        state = mark_state(self.mark, thing)
        self.col = []
        if type(state) == list:# collections
            state, self.col = state[0], state[1]
        
        pressed = ' on'
        if state is None:
            state, pressed = '', ''
        
        cla = ''
        if self.disabled():
            cla = ' disabled '
        
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
        self.t_origin = origin
        self.t_page = page
        
        return build_input()
    
    def ez(self, thing, mark, action, text, icon, state):
        
        icon = self.icon_html(icon, 60)
        
        if '{' in action:
            action = action.format(thing, mark, icon, state)
        
        return self.build_wrap([thing, mark], state, f' title="{text}" onclick="{action}"', icon)
    
    def build_wrap(self, namep, cla, arg, inner):
        if namep[0] is None:return ''
        
        if not cla or cla[0] == ' ':
            cla = 'markbutton mbutton' + cla
        
        return f'<div name="{"@".join(namep)}" class="{cla}"{arg}>{inner}</div>\n'
    
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

        haspage = False
        for coln in self.col:
            if self.t_page == f'{self.t_state}:{coln[0]}':
                haspage = True
            
            links.append(
                create_linktodathing(
                    self.mark,
                    coln[0],
                    con=self.data.get('name', self.mark),
                    origin=self.t_origin
                    ))
        
        if haspage and len(links) == 1:
            links = []
        
        link = ''
        if links:
            link = '<div class="linkthings">\n'
            link += f'{self.data["name_plural"]}:\n'
            link += '\n'.join(links) + '</div>\n'
        
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


def mark_for(kind, thing, wrap=False, size=60, page=None):
    # get all marks for a thing of a kind
    # wrap adds a container box
    out = ''
    link = ''
    
    for p, c in ent['mark_buttons'].items():
        if not compare_for(apdmm[p], kind):
            continue
        
        o, l = c.build_for(thing, size=size, origin=thing, page=page)
        
        out += o
        if not l:
            continue
        
        if not link:
            link = '<div class="flexbreak">Included in:</div>'
        
        link += f'\n{l}'
    
    if wrap:
        p = lister_linker(kind).format(thing)
        hout = '<div class="floatingmark markbox">\nMarks for '
        hout += f'<a href="{p}">{kind} <b>{thing}</b></a>\n'
        if out or link:
            hout += f'\n<br><br>\n{out}\n{link}'
        
        hout += '</div>\n'
    
    else:
        hout = f'<div class="floatingmark abox mark{kind}">'
        hout += f'\n{out}\n{link}</div>\n'
    
    return hout


def markicons_for(kind, thing):
    artm = []
    
    for m, d in apdmm.items():
        if not compare_for(d, kind, sw=True):
            continue
        
        if d.get('type', 'idk') in ['multibutt', 'list']:
            for v in d.get('values', []):
                if thing in dpref.get(v, []):
                    artm.append(v)
    
    return ' '.join(artm)


def post_things(label, items, itype, me=None, op=None, all_here = False, con=None):
    # cleaner link builder for posts
    do_op = False
    if op != None and me != None:
        if me in op:
            pos = op.index(me)
            do_op = True
    
    not_here = 0
    if not items:
        return ''
    
    if len(items) == 1 and me in items:
        return ''
    
    links = ''
    for i in items:
        ipos = int(i == me)
        if ipos != 1 and do_op and i in op:
            ipos = [2, 3][op.index(i) > pos]
        
        all_here = all_here and ipos
        if not ipos:
            not_here += 1
        
        links += create_linktodathing(itype, i, onpage=ipos, con=con) + '\n'
    
    if label.startswith('/'):
        label = f'<a class="linkhead" href="{label}</a>'
    
    out = f'<div class="linkthings centered">\n{label}\n{links}</div>\n'
    if itype != 'posts':
        return out
    
    if cfg['collapse_linkylength'] <= len(items):
        if not_here:
            label += f'({not_here:,} not in page)'
        
        out = '<details>'
        out += '<summary class="linkthings centered">'
        out += f'{label} ({len(items):,} items)</summary>\n'
        out += f'<div class="linkthings centered">{links}</div>'
        out += '</details>\n</div>\n'
    
    return out


class descman(object):

    def __init__(self):
        self.ret = {}
    
    def get_block(self, block, posts):
        data = appender()
        data.read(
            cfg['apd_dir'] + f'outdesc/{block}',
            parse=False)
        
        for post in posts:
            desc = data.get(post)
            if desc:
                self.ret[post] = json.loads(desc)
    
    def get_apc(self, posts):
        out = {}
        for post in posts:
            desc = apdfadesc.dget(str(post))
            if desc:
                out[post] = desc
        
        return out
    
    def get_for(self, posts):
        if not cfg['desc_split']:
            return self.get_apc(posts)
        
        blocks = {}
        
        for post in posts:
            block = desc_fol(post)
            if block not in blocks:
                blocks[block] = []
            
            blocks[block].append(post)
        
        load = 0
        for block, bposts in blocks.items():
            self.get_block(block, bposts)
            load += 1
        
        logging.info(f'Loaded {len(posts)} from {load} blocks')
        return self.ret


class eyde_base(builtin_base):

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
        
        hide_default = cfg['docats'] and self.hide_empty
        
        if 'nocull' not in pf:
            self.cull_mode(
                ent['_marked'],
                'cull' in pf or hide_default,
                'marked' in pf)
        
        if 'showalt' not in pf:
            self.cull_mode(
                apdfa,
                'onlyalt' in pf,
                'hidealt' in pf or hide_default)
        
        si = len(self.f_items)
        index_id = 1
        
        if pargs:
            index_id = pargs[-1]
        
        lse = page_count(si, index_id)
        last_page, sa, ea = lse
        
        h, list_mode, nav, si = self.build_page_wrap(pargs, lse)
        h += f'<!--\nclass: {type(self).__name__}\nmarktype: {self.marktype}\nname: {self.name}\ntitle: {self.title}\nmarkid: {self.markid}\n-->'
        
        h += self.build_page_mode(list_mode, lse)
        
        if index_id == last_page and sa < si:
            h += f'\n<p>Reached of list, shown {si:,} item{plu(si)}</p>'
        
        h += f'\n</div><div class="foot">{nav}\n<br>'
        try:
            handle.wfile.write(bytes(h, cfg['encoding_serve']))
        
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
        
        h = strings['setlogic']
        
        si = len(self.f_items)
        last_page, sa, ea = lse
        
        list_mode, wr = self.mode_picker(pargs)
        
        nav = template_nav(self.title, index_id, last_page, enc=False)
        if cfg['lister_buttons']:
            nav = nav.join(lister_get(self.marktype, self.title))
        
        h += f'<div class="head">\n{nav}</div>\n'
        h += f'<div class="container">\n{wr}'
        
        h += self.build_filters(self.markid)
        
        h += self.headtext[0]
        
        if self.do_mark:
            h += mark_for(self.marktype, self.markid, page=self.name)
        
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
        descs = descman().get_for(items)
        
        for item in items:
            out += self.build_item_full(
                item,
                descs.get(item),
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
        
        link = f"/i/{fn}"
        if cfg['remote_images'] != '':# do remote link
            link = cfg['remote_images'].format(fn)
        
        return self.place_file(ext, link, data.get('srcbytes', 0))
    
    def build_item_full(self, post, desc, data):
        title = data.get('title', f'Unavailable: {post}')
        
        ret = strings['eyde_post_title'].format(
            post, title)
        
        if data.get('origin') == 'alt':
            ret = f'<span class="altsrv">{ret}'
        
        ret = f'<div class="post post-full" id="{post}@post">\n' + ret
        
        ret += self.get_file_link(post, data)
        
        if post in ent['_attach']:
            ta = ent['_attach'][post]
            
            ret += f'<p><a href="/textattach/{ta.get("filename")}" target="_blank">'
            ret += f'View Attached Document, {ta.get("words"):}</a></p>\n'
        
        if cfg['show_unparsed']:
            ret += very_pretty_json(f'post:{post}', data, ignore_keys=['tags'])
        
        if desc == None:
            desc = '<b>DESCRIPTION NOT FOUND!!!</b>'
        
        if desc:
            if desc.count('<div') > desc.count('</div'):
                desc += '</div>'
            
            desc_word_count = data.get('descwc', -1)
            
            if desc_word_count > cfg['collapse_desclength']:
                desc = f'''<details>
<summary>Description ({desc_word_count:,} words)</summary>
{desc}</details>\n<br>'''
            
            ret += f'<br>\n<div class="desc">{desc}</div>\n'
        
        if data.get('got', True):
            ret += post_things(
                'Tags:', data.get('tags', ''), 'tags')
            
            ret += post_things(
                f'/filter/linkto:{post}/1">Linking to',
                xlink['descpost'].get(post, []),
                'posts',
                post,
                self.f_items,
                all_here=True)
            
            thisusers = [data.get('uploader', '.badart').lower().replace('_', '')]
            thisusersl = [x.lower().replace('_', '')
                          for x in xlink['descuser'].get(post, [])]
            thisusers += [x for x in thisusersl if x not in thisusers]
            
            ret += post_things(
                'Users:',
                thisusers,
                'users',
                self.name[5:])
            
            ret += post_things(
                'Folders:',
                data.get('folders', []),
                'folders')
        
        for w, d in wpm.items():
            if compare_for(d, 'posts', sw=True):
                if str(post) in wp[w]:
                    ret += format_wp(w, str(post))
        
        ret += post_things(
            f'/filter/linkfrom:{post}/1">Linked From',
            sorted(xlink.get('descpostback', {}).get(post, [])),
            'posts',
            post,
            self.f_items,
            all_here=True)
        
        ret += '\n'
        if cfg['all_marks_visible'] or data.get('origin') or not data.get('got', True):
            ret += mark_for('posts_unav', post)
        
        ret += mark_for('posts', post)
        
        if self.name.startswith('user:@') and 'uploader' in data:
            ret += mark_for('users', data['uploader'], wrap=True) + '<br>'
        
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
        
        domark = 'posts'
        if (data.get('origin') == 'alt' or
            not data.get('got', True) or cfg['all_marks_visible']):
            domark = 'posts_unav'
        
        ret += '\n<br>\n' + mark_for(domark, post, size=40, page=self.name)
        
        ret += '</span></span>\n'
        
        return ret
    
    def build_page_fa(self, sa, ea):
        #todo incomplete
        out = '''<div class="abox">
<label for="action">Click Action:</label>
<select id="action" name="action" onchange="setFAction()" class="niceinp">'''

        act = [('link', 'Open FADSRV page'),
               ('link', 'Open Fur Affinity page')]
        
        for m, d  in apdmm.items():
            if not compare_for(d, 'posts'):
                continue
            
            if d.get('hidden') and not cfg.get('show_hidden_marks'):
                continue
            
            mtype = d.get('type')
            if mtype == 'collection':
                act.append(('col@' + m, 'Modify ' + d.get('name', m)))
        
        for a, t in act:
            out += f'\n<option value="{a}">{t}</option>'
        
        out += '\n</select>\n</div><br>\n'
        
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

        if cfg['all_marks_visible'] or not data.get('got', True):
            ret += overicon('posts_unav', post, con=None)
        
        ret += overicon('posts', post, con=None)
        
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
    
    def propButton(self, escname, markact, text, icon, state=True):
        if isinstance(icon, int):
            icon = ii(icon)
        
        if state:
            state = ['', ' on'][self.data.get(markact, False)]
        
        #thing, mark, action, text, icon, state
        return mark_button().ez(
            escname, markact,
            'propMagic(this)',
            text, icon, state)
    
    def propCluster(self, escname):
        h = '<div class="floatingmark abox options">Options:\n'
        h += self.propButton(escname, 'lock', 'Lock', 50)
        h += self.propButton(escname, 'pin', 'Pin', 52)
        h += self.propButton(escname, 'pos', 'Show Positions', 80)
        h += self.propButton(escname, 'sortmepls', 'Sort by ID', 51, state='')
        h += self.propButton(escname, 'delete', 'Delete', 'Delete')
        h += '</div>\n'
        return h


class eyde_collection(eyde_base, get_icon_collection):
    
    def __init__(self, colname):
        items = []
        marktype = colname
        self.colname = colname
        super().__init__(items, marktype)
        self.markid = colname + 'ERROR'
        
        self.filters = {
            'Filter': '@{col}:{name}',
            'Filter ID': '@{col}:id.{pos}'
            }
    
    def process_filters(self, thing, filters):
        namesingle = apdmm.get(self.colname, {}).get('name', self.colname)
        items = list(apdm[self.colname])
        pos = 0
        if thing in items:
            pos = items.index(thing)
        
        escname = re.sub(r'\W+', '', thing.lower())
        
        return {label: links.format(col=namesingle, name=escname, pos=pos)
                for label, links in filters.items()}
    
    def gimme(self, pargs):
        name = find_collection(self.colname, pargs[1])
        self.markid = self.colname + 'ERROR'
        
        if name is False:
            self.purge(0)
            return
        
        self.title = name
        self.markid = name
        self.name = f'{self.colname}:{name}'
        data = apdm[self.colname][name]
        self.data = data
        ent['visited_rebuild'].append([self.colname, name])
        self.items = data['items']
        
        escname = re.sub(r'\W+', '', name.lower())
        h = f'<script>var con="{self.colname}";</script>\n'
        h += self.propCluster(escname)
        
        self.headtext[0] = h
        
        h = ''
        if cfg['show_unparsed']:
            h += very_pretty_json(f'{self.marktype}:{name}', data, ignore_keys=['items'])
        
        if apdmm[self.colname].get('doReadCount', False):
            unread = 0
            prefr = set(dpref.get('read', {}))
            for p in self.items:
                if p not in prefr:
                    unread += 1
            
            h = 'All read - '
            if unread:
                h = f'{unread:,} unread - '
            
        self.headtext[1] = '<br>' + h


class eyde_view(eyde_base):
    
    def __init__(self, items=[], marktype=''):
        super().__init__(items, marktype)
        self.markid = 'VIEWERROR'
    
    def gimme(self, pargs):
        if len(pargs) < 3:
            pargs.append(1)
        
        if ' ' in str(pargs[1]):
            self.items = pargs[1].split(' ')
        else:
            self.items = [str(pargs[1])]
        
        self.items = [x.split('.')[0] for x in self.items]

        #print(json.dumps(apdfa.dget(self.items[0], {}), indent='\t'))
        
        si = len(self.items)
        if si == 1:
            self.title = self.items[0]
        else:
            self.title = f'View ({si} items)'
        
        #self.titledoc(handle, self.title)


class eyde_dataurl(eyde_base):
    
    def __init__(self, items=[], marktype=''):
        super().__init__(items, marktype)
        self.markid = 'VIEWERROR'
    
    def gimme(self, pargs):
        parse = pargs[1:-1]
        if not parse:return
        parse = parse[0]
        
        self.items = []
        data = {}
        
        data = json.loads(parse)
        
        new = {}
        for i, d in data.items():
            if apdfa.dget(i):continue# has
            
            if altfa.dget(i, {}).get('filedate'):
                continue# don't overwrute actual data
            
            new[i] = d
        
        if new:
            altfa.write(new)
        
        self.items = list(data)
        
        si = len(self.items)
        self.title = f'Data URL ({si:,} items)'
        if si == 1:
            self.title = self.items[0]


def format_wp(file, thing):
    d = wp.get(file, {}).get(thing, '')
    i = wpm[file]
    
    if not isinstance(d, str):return ''
    ret = d.replace('\n', '<br>\n') + ' '

    add = ''
    
    if ':' in ret:
        p = ''
        for k in ret.split(':'):
            
            t = k.split(' ')[0]
            if p.endswith('user'):p = 'users'
            elif p.endswith('tag'):p = 'tags'
            elif p.endswith('post'):p = 'posts'
            else:p = ''
            
            if p != '':
                ret = ret.replace(f'{p[:-1]}:{t} ',
                           create_linktodathing(p, t))
            
            p = k
    
    if ret:
        ret = f'\n<br>\n<div class="tags">\n{i.get("title", file)}:<br>{ret}\n</div>'
        if add:ret += '\n<br>'
        ret += f'{add}\n<br>\n'
    
    return ret


def timestamp_disp(t):
    t = datetime.utcfromtimestamp(t)
    return t.strftime('%b %d, %Y %H:%M')


class eyde_user(eyde_base):

    def __init__(self, items=[], marktype='users'):
        super().__init__(items, marktype)
        
        self.page_options.append(['escape'])
        self.filters = {
            'Filter': 'user:{}',
            'Linked From': 'userl:{}',
            'Desc Posts': 'userdescpost:{}',
            'Userlist': '/userlink/{}/1'
            }
    
    def gimme(self, pargs):
        if len(pargs) > 1:
            user = str(pargs[1]).replace('_', '')
        else:
            user = ''
        
        self.name = f'user:{user}'
        ent['visited_rebuild'].append([self.marktype, user])
        self.title = user
        self.markid = user
        self.items = users.get(user, [])
        
        if 'escape' in pargs:
            user = html.escape(user)
        
        h = ''
        
        count = len(users.get(user, ''))
        know = max(get_subs(user), count)
        perc = count / max(know, 1)
        
        h += '<div class="userinfo">\n'
        
        info = ustat.dget(user, {})
        
        if info:
            h += '<p>'
            for i, l, t in [
                ('title', '', 'text'),
                ('registered', 'Registered', 'date'),
                ('_meta', 'Checked', 'date'),
                ('status', 'Account status', 'text'),
                ('error', 'Profile status', 'text'),
                ('new_post', 'Last posted', 'date')]:
                i = info.get(i)
                if not i:continue
                
                if t == 'date':
                    i = timestamp_disp(i)
                
                if l:
                    l += ': '
                
                h += f'{l}{i}<br>\n'
            
            h += '</p>'
        
        passed = dpref.get('passed', {}).get(user)
        if passed:
            h += f'<p>Passed: {timestamp_disp(passed / 1000)}</p>\n'
        
        for path, name in cfg['altlinks'].get('users', []):
            path = path.format(user)
            h += f'<p><a href="{path}">{name}</a></p>\n'
        
        for w, d in wpm.items():
            if compare_for(d, self.marktype, sw=True):
                if user in wp[w]:
                    h += format_wp(w, user)
        
        h += f'<p>Got {count:,} of {get_subs(user):,} posts ({perc:.02%})</p>'
        
        if cfg['show_unparsed']:
            h += very_pretty_json(f'user:{user}', info)
        
        h += '\n</div>'
        self.headtext[1] = h


class eyde_postmark(eyde_base):
    # todo what is this, unused
    def __init__(self, items=[], marktype='postmarks'):
        super().__init__(items, marktype)
        self.headtext = ['', '', '']
    
    def gimme(self, pargs):
        if len(pargs) > 1:
            user = str(pargs[1]).replace('_', '')
        else:
            user = ''
        
        self.name = f'postmark:{user}'
        ent['visited_rebuild'].append([self.marktype, user])
        self.title = user
        #self.titledoc(handle, user)
        self.markid = user
        
        if compare_for(dprefm.get(user, {}), 'posts', sw=True):
            self.items = list(dpref.get(user, {}))
        
        else:
            self.items = []
        
        h = '<br>Filter:\n'
        h += f'<a href="/filter/@{user}/1">mark</a>\n'
        h += '<br>\n'
        
        self.headtext[0] = h

class eyde_folder(eyde_base):
    def __init__(self, items=[], marktype='folders'):
        super().__init__(items, marktype)
        
        self.page_options.append(['nosort', 'sorted'])
        self.filters = {
            'Filter': 'folder:{}'
            }
    
    def dosort(self, folid, pargs):
        if 'nosort' in pargs:return False
        elif 'sortid' in pargs:return True
        
        return folid in dpref.get('folsort', {})
    
    def gimme(self, pargs):
        folid = str(pargs[1])
        self.markid = folid
        
        if not folid in apdfafol:
            self.purge(0)
            return
        
        f = apdfafol.dget(folid)
        self.title = f['title']
        ent['visited_rebuild'].append([self.marktype, folid])
        #self.titledoc(handle, self.title)
        self.name = f'folder:{folid}'
        self.items = f['items']
        
        h = ''
        for path, name in cfg['altlinks'].get('folders', []):
            path = path.format(f["path"])
            h += f'<p><a href="{path}">{name}</a></p>\n'
        
        if self.dosort(folid, pargs):
            self.items = sorted([int(x) for x in self.items])
            self.items = [str(x) for x in self.items]
        
        h += '<script>\n'
        escname = f['title'].replace('"', '\\"')
        h += f'var defaultSetName = "{escname}";\n'
        h += 'var posts = ['
        h += ','.join([f'\n\t"{i}"' for i in self.items])
        h += '\n];\n</script>\n'

        addto = ''
        for m  in ent['mark_buttons']:
            d = apdmm[m]
            if not compare_for(d, 'posts', sw=True):
                continue
            
            if d.get('type', False) != 'collection':
                continue
            
            name = d.get('name', m)

            addto += mark_button().ez(
                folid, 'create',
                f"folderToSet('Name the new {name}', '{m}')",
                name, name, 'item')
        
        if addto:
            h += f'<div class="linkthings centered">\nAdd all to: {addto}</div>'
        
        h += '<div class="userinfo">\n'
        got = len(self.items)
        know = max(got, f['count'])
        perc = got / max(know, 1)
        
        h += f'<p>Got {got:,} of {know:,} posts ({perc:.02%})</p>\n'
        if cfg['show_unparsed']:
            h += very_pretty_json(f'folder{folid}', f, ignore_keys=['items'])
        
        self.headtext[1] = h + '</div>\n'


class post_sort_prop(object):
    
    def __init__(self, prop, default):
        self.prop = prop
        self.default = default
    
    def value(self, postid):
        return apdfa.dget(postid, {}).get(self.prop, self.default)


class post_sort_prop_none(post_sort_prop):
    
    def __init__(self, prop, default):
        super().__init__(prop, default)
    
    def value(self, postid):
        v = super().value(postid)
        if v is None:
            return self.default
        
        return v


class post_sort_id(object):
    
    def __init__(self, prop, default):
        self.prop = prop
        self.default = default
    
    def value(self, postid):
        if postid.isdigit():
            return int(postid)
        
        return postid


class post_sort_linked(object):
    
    def __init__(self, prop):
        self.prop = prop
    
    def value(self, postid):
        return len(xlink[self.prop].get(postid, []))


class eyde_tag(eyde_base):
    
    def __init__(self, items=[], marktype='tags'):
        super().__init__(items, marktype)
        self.filters = {
            'Filter': '{}'
            }
    
    def gimme(self, pargs):
        tag = ''
        if len(pargs) > 1:
            tag = str(pargs[1])
        
        self.name = f'tag:{tag}'
        ent['visited_rebuild'].append([self.marktype, tag])
        self.title = tag
        self.markid = tag
        self.items = kwd.get(tag, [])


class eyde_filter(eyde_base):

    def __init__(self, items=[], marktype='filters'):
        super().__init__(items, marktype)
        
        self.icon = ii(55)
        self.f_sort = 'id'
        self.f_sorts = {
        'id':       [post_sort_id, '', ''],
        'filedate': [post_sort_prop_none, 'filedate', '0'],
        'uploader': [post_sort_prop, 'uploader', '.badart'],
        'title':    [post_sort_prop, 'title', '00000'],
        'descwc':   [post_sort_prop, 'descwc', 0],
        'bytes':    [post_sort_prop, 'srcbytes', 0],
        #'faves':    [post_sort_prop, 'faves', 0],
        #'views':    [post_sort_prop, 'views', 0],
        'linked':   [post_sort_linked, 'descpostback'],
        'linking':  [post_sort_linked, 'descpost']
        }
        self.f_sortflip = False
        self.f_colstrip = {}
        
        self.page_options += [
            ['@unavilable'],
            ['@all', '@unmarked', '@marked'],
            ['@reversed']
            ]
    
    def filter_widget(self, itype, nameid, label, values, state):
        h = ''
        if isinstance(label, str):label = [label]
        if label[0]:
            h += f'<label for="ctx{nameid}">{label[0]}</label>\n'
        
        if itype == 'text':
            h += f'<input class="niceinp widebar" name="ctx{nameid}" id="ctx{nameid}" value="{state}">\n'
        
        elif itype == 'select':
            h += f'<select class="niceinp" name="ctx{nameid}" id="ctx{nameid}">\n'
            for v in values:
                h += f'\t<option value="{v}"{["", " selected"][v == state]}>{v}</option>\n'
            
            h += '</select>\n'
        
        elif itype == 'checkbox':
            check = ['', ' checked'][state]
            h += f'<input type="checkbox" name="ctx{nameid}" id="ctx{nameid}"{check} />\n'
        
        elif itype == 'radio':
            check = ['', ' checked'][state]
            h += f'<input type="radio" name="ctx{label[2]}" id="ctx{nameid}"{check} />\n'
        
        else:
            pass
        
        if len(label) > 1:
            h += f'<label for="ctx{nameid}">{label[1]}</label>\n'
        
        return h + '<br>\n'
    
    def filter_items_by(self, s, m):
        self.items = [f for f in self.items if (f in s) == m]
    
    def filter_param_str(self, p):
        if ':' in p:
            k = p.split(':')
            return k[0], ':'.join(k[1:])
        
        elif p.startswith('@'):
            return '@', p[1:]
        
        return 'tag', p
    
    def filter_arg_sort(self, k, v):
        
        if k == 'sort' and v in self.f_sorts:
            self.f_sort = v
            d = self.f_sorts[v]
            sort = d[0](*d[1:])
            #print([(sort.value(x), x) for x in self.items])
            items = []
            for x in self.items:
                y = sort.value(x)
                if isinstance(y, str):y = -1
                items.append((y, x))
            
            self.items = [x for y, x in sorted(items)]
            return True
        
        elif k == '@':
            if v == 'reversed':
                self.f_sortflip ^= True
                return True
            
            elif v == 'nosort':
                # do nothing
                return True
    
    def filter_param_user_data(self, k, v):
        if   k == 'user':    return users
        elif k == 'userl':   return xlink.get('descuserback', {})
        
        elif k == 'userdescpost':
            out = []
            for x in users.get(v, []):
                out += xlink['descpost'].get(x, [])
            
            return {v: out}
        
        elif k == 'folder':
            out = apdfafol.dget(v, {}).get('items', [])
            return {v: out}
        
        elif k == 'linkto':  return xlink.get('descpost', {})
        elif k == 'linkfrom':return xlink.get('descpostback', {})
        return {}
    
    def filter_param_user(self, k, v):
        return set(self.filter_param_user_data(k, v).get(v, []))
    
    def filter_param_dpref(self, k, v):
        v = self.dprefs.get(v, '')
        return set(dpref.get(v, []))
    
    def filter_param_colname(self, k, v):
        return find_collection(k, v)
    
    def filter_param_col(self, k, v):
        k = self.col[k]
        
        v = self.filter_param_colname(k, v)
        
        if v is False:
            return set()
        
        return set(apdm[k][v]['items'])
    
    def filter_param_tag(self, k, v):
        return set(kwd.get(v, []))
    
    def filter_post_key(self, k, v):
        out = []
        for i in self.items:
            d = apdfa.dget(i, {}).get(k, 'unset')
            if d == v:
                out.append(i)

        return set(out)
    
    def filter_param_get(self, k, v):
        f = None
        if k in ['user', 'userl', 'userdescpost', 'linkto', 'linkfrom', 'folder']:
            f = self.filter_param_user

        elif k == 'rating':
            f = self.filter_post_key
            
        elif k == '@' and v in self.dprefs:
            f = self.filter_param_dpref
        
        elif k in self.col:
            f = self.filter_param_col
        
        elif k == 'tag':
            f = self.filter_param_tag
        
        else:
            #print(k, v)
            return set()
        
        return f(k, v)
    
    def filter_arg_do(self, k, v):
        if (self.filter_arg_sort(k, v) or
            False):
            pass
        
        elif v == 'unmarked':
            self.filter_items_by(ent['_marked'], False)
        
        elif v == 'marked':
            self.filter_items_by(ent['_marked'], True)

        elif v == 'descpost':
            items = set()
            for i in self.items:
                items.update(set(xlink['descpost'].get(i, [])))
            
            self.items = items
        
        else:
            pass#print(k, v)
    
    def filter_widgets(self, pbar, p_or, p_and, p_not, p_arg):
        
        h = '<div class="filterContainer" id="filterParams">\n'
        h += '<h3>Filter Options</h3>\n'
        
        h += self.filter_widget('text', 'Pargs', '', [], pbar)
        
        h += '<div class="filterWidgets">\n'
        h += '<div class="filterTab">\n'
        a = [''.join(x) for x in p_arg]
        
        state = 'All'
        for k in ['All', 'Unmarked', 'Marked']:
            if '@'+k.lower() in a:
                state = k
        
        for k in ['All', 'Unmarked', 'Marked']:
            h += self.filter_widget(
                'radio', k, ['', k, 'markstate'], [], k==state)
        
        h += '</div>\n<div class="filterTab">\n'
        
        for k in ['Unavailable', 'Descpost']:
            h += self.filter_widget(
                'checkbox', k, ['', k], [], '@'+k.lower() in a)
        
        h += '</div>\n<div class="filterTab">\n'
        h += self.filter_widget(
            'select', 'Sort', 'Sort:',
            self.f_sorts,
            self.f_sort)
        k = 'Reversed'
        h += self.filter_widget(
            'checkbox', k, ['', k], [], '@'+k.lower() in a)
        
        h += '</div>\n<div class="filterTab">\n'
        h += '<button class="mbutton " onclick="filterGo()">Filter</button>\n'
        h += '</div>\n</div>\n</div>\n<br>\n'
        return h
    
    def gimme(self, pargs):
        
        params = []
        if len(pargs) > 1:
            params = str(pargs[1]).split(' ')
        
        if params == ['']:
            params = []
        
        name = f'filter:{" ".join(params)}'
        if name == self.name:
            return
        
        # todo optional logging for user recollection
        with open('filtermemory', 'a') as fh:
            fh.write('\n' + name)
            fh.close()
        
        self.name = name
        self.title = 'Filter'
        #self.titledoc(handle, self.title)
        
        self.f_sortflip = False
        
        self.dprefs = {
            k.lower(): k for k, d in dprefm.items()
            if compare_for(d, 'posts', sw=True)
            }
        
        self.col = {
            '@' + d.get('name', k).lower(): k
            for k, d in apdmm.items()
            if d.get('type') == 'collection' and
            compare_for(d, 'posts', sw=True)
        }
        
        p_arg = []
        p_or  = []
        p_not = []
        p_and = []
        pbar = []
        has_sort = False
        
        for p in list(params):
            m, t, b = p_and, 0, True
            if p in [
                '@unavailable',
                '@all',
                '@unmarked',
                '@marked',
                '@reversed',
                '@descpost']:
                m, b = p_arg, False
            
            elif p == '@nosort' or p.startswith('sort:'):
                m, has_sort, b = p_arg, True, False
            
            elif p.startswith('*'):
                m, t = p_or, 1
            
            elif p.startswith('!'):
                m, t = p_not, 1
            
            m.append(self.filter_param_str(p[t:]))
            if b:
                pbar.append(p)
        
        pbar = ' '.join(pbar)
        
        l_or =  len(p_or)
        l_and = len(p_and)
        l_nit = len(p_not)
        
        self.items = set()
        and_skip = None
        unav_skip = False
        #print(p_arg)
        if not l_or + l_and:# no positives
            if (('@', 'unavailable') in p_arg and
                not ('@', 'descpost') in p_arg):
                self.items = xlink.get('descpostback', {})
                self.filter_items_by(ent['_posts'], False)
                unav_skip = True
                
            else:
                self.items = set(apdfa)
        
        elif not l_or:# must have >1 and
            self.items = self.filter_param_get(*p_and[0])
            and_skip = 1
        
        else:
            for k, v in p_or:# include any
                s = self.filter_param_get(k, v)
                self.items.update(s)
        
        for k, v in p_arg:# process args
            self.filter_arg_do(k, v)
        
        for k, v in p_not:# do not include
            s = self.filter_param_get(k, v)
            self.filter_items_by(s, False)
        
        for k, v in p_and[and_skip:]:# must include
            s = self.filter_param_get(k, v)
            self.filter_items_by(s, True)
        
        if not unav_skip and ('@', 'unavailable') in p_arg:
            self.filter_items_by(ent['_posts'], False)
        
        if not has_sort:# default sort
            self.filter_arg_do('sort', 'id')
        
        if self.f_sortflip:# do a flip
            self.items = self.items[::-1]
        
        self.items = list(self.items)
        
        h = self.filter_widgets(pbar, p_or, p_and, p_not, p_arg)
        m = ''
        
        linked = set()
        for k, v in p_or + p_and + p_not + p_arg:
            if k in ['user', 'userl']:
                uv = f'user:{v}'
                if uv in linked:continue
                linked.add(uv)
                h += mark_for('users', v, wrap=True)
            
            elif k in ['linkto', 'linkfrom']:
                uv = f'post:{v}'
                if uv in linked:continue
                linked.add(uv)
                h += mark_for('posts', v, wrap=True)
            
            elif k == '@' and v in self.dprefs:
                pass
            
            elif k in self.col:
                uv = f'{k}:{v}'
                if uv in linked:continue
                linked.add(uv)
                k = self.col[k]
                v = self.filter_param_colname(k, v)
                if v != False:
                    h += mark_for(k, v, wrap=True)
            
            elif k == 'tag':
                h += mark_for('tags', v, wrap=True)
            
            continue
        
        self.headtext = [h, '', '']
    
    def purge(self, strength):
        super().purge(strength)
        
        if self.clear_threshold <= strength:
            self.name = None


def iconlist(di, thing, sp=False):
    pgm = ''
    
    for name, icon, ext, cssc in di:
        cur = f' {icon}'
        if isinstance(icon, list):
            cur = f'{thing}@ico.{name}" class="teenyicon iconsheet'
            cur += f'{cssc + markicon(*icon, m=-24)}">'
            cur = f'<i name="{cur}</i>'
        
        pgm += cur
        if not ext:
            continue
        
        pgm += f'{ext} '
    
    if sp:
        return f'<span class="icons">{pgm}</span>'
    
    return pgm


def create_linktodathing(kind, thing, onpage=False, retmode='full', con=None, origin=None):
    pi = []
    linky = thing
    
    if onpage:
        if onpage == 1:
            pi.append(['me', ii(62), '', ''])
        elif onpage == 2:
            pi.append(['above', ii(71), '', ''])
        elif onpage == 3:
            pi.append(['below', ii(72), '', ''])
        else:
            pi.append(['somewhere', ii(51), '', ''])
    
    if (cfg['show_visited_recently'] and
        [kind, thing] in ent['visited_rebuild']):
        pi.append(['visited', ii(68), '', ''])
    
    di = []
    for m in ent['mark_buttons']:
        btnd = apdmm[m]
        if not compare_for(btnd, kind, sw=True):
            continue
        
        v = mark_state(m, thing)
        
        if isinstance(v, list):
            vd = v[1:]
            v = v[0]
        
        if v is None or v == 'n/a':
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
        href = f'/{con.lower()}/{{}}/1'
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
        
        if data.get('pos') and origin:
            pos = data['items'].index(origin) + 1
            linkdes += f'<span class="position">#{pos}</span>'
        
        count = len(data['items'])
        linkdes += f'<span class="count">({count:,})</span>'
    
    if kind == 'users':
        if thing in users:
            got = len(users[thing])
            v = wrapme(got, f=' {:,}')
            
            if cfg['docats']:
                uns, perc = users_marked.get(thing, (0, 0))
                if not uns:
                    pi.append(['seen', ii(32), '', ''])
                
                elif uns < got:
                    v = wrapme(uns, f=' {:,} ') + wrapme(got)
                    pi.append(['partial', ii(1), '', ''])
            
            l8r = get_subs(thing)
            linkdes += v + wrapme(l8r, ' ({:,})')
        
        else:
            pi.append(['notgot', ii(34), '', ''])
    
    elif kind == 'posts':
        if thing not in ent['_posts']:
            pi.append(['notgot', ii(34), '', ''])
    
    elif kind == 'folders':
        linkdes = apdfafol.dget(thing, {'title': f'Folder {thing}'})['title']
    
    elif kind == 'tags':
        pass
    
    if href == '/{}/1':
        pass#print('what?', kind, thing)
    
    if retmode == 'markonly':
        return iconlist(pi + di, thing)
    elif retmode == 'href':
        return linky
    
    href = href.format(linky)
    return f'<a href="{href}">{iconlist(pi, thing, sp=True)} {linkdes} {iconlist(di, thing, sp=True)}</a>'


def overicon(kind, thing, con=None):
    return '<div class="overicn">' + create_linktodathing(
        kind, thing, retmode='markonly', con=con) + '</div>'


def maketup(items):
    if items and not isinstance(items[0], tuple):
        return [(i, 0) for i in items]
    
    return items


def matchmode(v, m):
    if '@' + v in m:
        return True
    
    elif '!@' + v in m:
        return False
    
    return None


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
        self.markid = 'mark_id_error'
        
        self.can_list = True
        self.content_type = 'text/html'
        
        self.path_parts = 2
        self.page_options = [
            ['reversed'],
            ['cull', 'nocull'],
            ['count']
            ]
        
        if self.marktype == 'users':
            self.page_options[2] += ['unmarked', 'ustats']
    
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
        if type(d) != int and type(d) != float:
            d = len(d)# int int make int
        
        return [d] + list(i)
    
    def item_sorter(self, data, items, mincount):
        so = sorted(self.item_sorter_ez(i, data.get(i[0], 0))
                    for i in items)
        
        return [tuple(x[1:])
                for x in so
                if x[0] >= mincount]
    
    def build_page(self, handle, pargs, head=True, text=''):
        index_id = 1
        pf = []
        if pargs and isinstance(pargs[-1], int):
            index_id = pargs[-1]
            if len(pargs) > 2:
                pf = str(pargs[-2]).split(' ')
        
        items = self.items
        
        if items is None:
            items = []
        
        items = maketup(items)
        
        cols = {}
        
        done = []
        for m, d in apdmm.items():
            if not compare_for(d, self.marktype):
                continue
            
            mt = d.get('type', 'idk')
            if mt in ['multibutt', 'list']:
                for v in d.get('values'):
                    mm = matchmode(v, pf)
                    if mm is None:
                        continue
                    
                    done.append(v)
                    
                    mset = set(dpref.get(v, {}))
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
                             if lt > get_subs(i[0]) > gt]
                
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
            um = {k: get_subs(k) for k in ustat}
            items = self.item_sorter(um, items, mincount)
        
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
            
            ent['_lists'][self.marktype] = seq
        
        count = len(items)
        last_page, sa, ea = page_count(count, index_id, pc=cfg['list_count'])
        if index_id < 1:
            index_id += last_page

        nav = template_nav(self.title, index_id, last_page, enc=False)
        if cfg['lister_buttons']:
            nav = nav.join(lister_get(self.marktype, self.title))
        
        h = ''
        h += f'''<!--\nclass: {type(self).__name__}
marktype: {self.marktype}\nlink: {self.link}\ntitle: {self.title}
hide_empty: {self.hide_empty}\n-->'''
        
        h += strings['setlogic']
        
        if head:
            h += f'<div class="head">\n{nav}</div>\n'
        
        h += f'<div class="container list">\n{text}'
        h += self.headtext[0]
        
        h += f'<p>{count:,} item{plu(count)}</p>\n'
        h += self.headtext[1]
        
        for i in items[sa:ea]:
            item = i
            if type(i) in [list, tuple]:
                item = i[0]
            
            h += self.build_item(
                i, self.datas.get(item, None), 'aaaaaaaaaaaaaaaaaaaaaa')
        
        h += f'\n</div><div class="foot">{nav}\n<br>'
        
        h += self.headtext[2]
        
        handle.wfile.write(bytes(h, cfg['encoding_serve']))
    
    def build_label(self, i, item, data, mode):
        
        if self.marktype == 'usersets':
            mdata = []
            for d in data:
                mdata += users.get(d, [])
        else:
            mdata = data
        
        f = choose_thumb(self.marktype, item)
        
        l = f'/t/{f}'
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
            labelt.append(wrapme(get_subs(item), f='({:,})'))
        
        for pos, inf in enumerate(self.iteminf):
            if inf is None or pos >= len(i):
                continue
            
            f = '{}'
            if len(inf) == 2:f = inf[1]
            app = None
            
            if inf[0] == 'str':
                app = f.format(i[pos])
            
            elif inf[0] == 'int':
                if len(inf) < 2:f = '{:,}'
                app = wrapme(i[pos], f=f)
            
            elif inf[0] == 'dateiso':
                d = datetime.fromisoformat(i[pos])
                app = d.strftime('<br>%b %d, %Y %H:%M')
            
            elif inf[0] == 'date':
                app = jsdate(i[pos]).isoformat()[:10]
            
            elif inf[0] == 'replace':
                if len(inf) != 2:continue
                labelt[inf[1]] = i[pos]
            
            if app:
                labelt.append(app)
        
        return label + ' '.join(labelt)
    
    def build_item(self, i, data, mode):
        if type(i) in [tuple, list]:item = i[0]
        else:item = i
        
        h = f'<!-- {i} -->\n'
        
        if data is None:
            logging.debug(f'No data for item: {item}')
            data = []
        
        artm = markicons_for(self.marktype, item)
        
        href = create_linktodathing(self.marktype, item, con=self.con, retmode='href')
        
        h += strings['thumb'].format(self.link.format(href), self.build_label(i, item, data, mode), ' ' + artm)
        
        return h
    
    def ez_build_item(self, i):
        return self.build_item(i, self.datas.get(i), self.marktype)
    
    def get_items(self):
        return self.items


class mort_userlink(mort_base):
    
    def __init__(self, marktype='users', title='User Link', link='/user/{}/1', icon=ii(25)):
        super().__init__(marktype, title, link, icon)
        self.path_parts = 3
        self.hide_empty = False
    
    def gimme(self, pargs):
        self.datas = users
        self.items = []
        
        if len(pargs) > 1:
            user = str(pargs[1]).replace('_', '')
        else:
            user = ''
        
        self.title = user
        items = set()
        for p in users.get(user, []):
            items.update(set(xlink['descuser'].get(p, [])))
        
        self.items = list(items)
        self.headtext[0] = mark_for('users', user, wrap=True) + '<br>'


class mort_users(mort_base):
    
    def __init__(self, marktype='users', title='Users', link='/user/{}/1', icon=ii(0)):
        super().__init__(marktype, title, link, icon)
    
    def get_items(self):
        return ent['usersort']
    
    def gimme_idc(self):
        self.items = self.get_items()
        self.datas = users


class mort_collection_list(mort_base):
    
    def __init__(self, colname, plural):
        self.colname = colname
        marktype = colname
        title = plural
        self.name = plural
        link = lister_linker(marktype)
        self.meta = apdmm[colname]
        icon = self.meta.get('icon', None)
        self.rebuildread = True
        self.doread = apdmm[self.colname].get('doReadCount', False)
        super().__init__(marktype, title, link, icon, con=colname)
        
        self.markid = colname
        
        if self.doread:
            self.modes_default = 'all'
            self.modes = {
                'all': 'All',
                'unread': 'Unread',
                'read': 'Read',
                'part': 'Partial'
                }
            self.page_options.append(list(self.modes))
        
        self.hide_empty = False
        self.pagetype = 'remort_mark'
    
    def gimme(self, pargs):
        self.items = []
        self.datas = {}
        if self.rebuildread and self.doread:
            prefr = set(dpref.get('read', {}))
        
        for d, k, n in sort_collection(self.colname, rebuild=True):
            self.items.append((k, d, n))
            self.datas[k] = apdm[self.colname][k]['items'].copy()
            
            for i, u in enumerate(self.datas[k]):
                t = choose_thumb(
                    self.meta.get('for', 'posts'),
                    u)
                
                if t != 'parrot.svg':
                    self.datas[k][i] = t
                    break
            
            if self.rebuildread and self.doread:
                self.read[k] = 0
                for p in self.datas[k]:
                    if p not in prefr:
                        self.read[k] += 1
        
        self.title = self.name
        list_mode, wr = self.mode_picker(pargs)
        if self.modes:
            if list_mode != 'all':
                self.title += f' ({self.modes[list_mode]})'
            
            if list_mode == 'unread':
                self.items = [(k, d, n)
                              for k, d, n in self.items
                              if self.read.get(k, 0)]
            
            elif list_mode == 'read':
                self.items = [(k, d, n)
                              for k, d, n in self.items
                              if not self.read.get(k, 0)]
            
            elif list_mode == 'part':
                self.items = [(k, d, n)
                              for k, d, n in self.items
                              if 0 < self.read.get(k, 0) < len(self.datas[k])]
        
        self.headtext[0] = wr
    
    def purge(self, strength):
        super().purge(strength)
        
        if self.clear_threshold <= strength:
            self.read = {}
            self.rebuildread = True


def mimic_data(mimic, pargs):
    if mimic in ent['builtin']:
        pargs = pargs[:-1] + ['nomimic', pargs[-1]]
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
        ent['visited_rebuild'].append([self.colname, name])
        data = apdm[self.colname][name]
        self.data = data
        self.items = data['items']
        
        escname = re.sub(r'\W+', '', name.lower())
        h = f'<script>var con="{self.colname}";</script>\n'
        h += self.propCluster(escname)
        
        if cfg['show_unparsed']:
            skip = len(data['items']) > 100
            h += very_pretty_json(f'{self.marktype}:{name}',
                                  data, ignore_keys=['', 'items'][skip])
        
        self.headtext[0] = h
        m = None
        if 'nomimic' not in pargs:
            m = mimic_data(self.marktype, pargs)
        
        if m is None:
            self.datas = {}
        
        else:
            self.datas = m


class mort_tags(mort_base):
    
    def __init__(self, marktype='tags', title='Tags', link='/tag/{}/1', icon=ii(10)):
        super().__init__(marktype, title, link, icon)
    
    def get_items(self):
        return kws
    
    def gimme_idc(self):
        self.items = self.get_items()
        self.datas = kwd


class mort_shuffle(mort_base):

    def __init__(self, marktype='users', title='Shuffle', link='/user/{}/1', icon=ii(30)):
        super().__init__(marktype, title, link, icon)
        self.clear_threshold = 2
        self.headtext[2] = '<a class="btn shuffle" onclick="postReload(\'/reshuffle\', \'\')">Shuffle</a>\n'
    
    def get_items(self):
        return [x for x in ent['usersort']]
    
    def gimme_idc(self):
        self.datas = users
        self.items = self.get_items()
        shuffle(self.items)


class mort_unlinked(mort_base):

    def __init__(self, marktype='users', title='Unlinked', link='/user/{}/1', icon=ii(30)):
        super().__init__(marktype, title, link, icon)
    
    def get_items(self):
        linked = set(xlink.get('descuserback', {}))
        return [x for x in ent['usersort']
                if x not in linked]
    
    def gimme_idc(self):
        self.datas = users
        self.items = self.get_items()


class mort_list(mort_base):
    
    def __init__(self, marktype='', title='List', link='/{}/1', icon=ii(68)):
        super().__init__(marktype, title, link, icon)
        self.can_list = False
        self.page_options = []
    
    def gimme(self, pargs):
        if len(pargs) < 2:
            mimic = 1
        else:
            mimic = pargs[1]
        
        self.items = []
        self.datas = {}
        self.message = None
        self.query = None
        
        if mimic in ent['_lists']:
            self.marktype = mimic
            self.link = lister_linker(mimic)
            self.items = lister_items(mimic)
            if 'query' in ent['_lists'][mimic]:
                self.query = ent['_lists'][mimic]['query']
            
            m = None
            if 'nomimic' not in pargs:
                m = mimic_data(self.marktype, pargs)
            
            if m is None:
                self.datas = {}
                self.message = f"Don't know how to handle {mimic}"
            else:
                self.datas = m
                
        
        elif isinstance(mimic, int):# probably index_id idc
            #get meta
            self.marktype = 'list'
            self.message = 'bodge i may like'
            self.link = '/list/{}/1'
            self.items = list(ent['_lists'])
            self.datas = {k: len(lister_items(k)) for k in self.items}
        
        else:
            self.message = f'No sequence for {mimic[1]}.'
        
        if self.query:
            self.headtext[1] = f'<p>Query: <a href="{self.query}">{self.query}</a></p>\n'
        
        if self.message:
            self.headtext[1] = f'<p>{self.message}</p>\n'


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
                d = apdfafol.dget(pname, {})
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


class mort_postamark(mort_amark):
    
    def __init__(self, mark, val):
        super().__init__(mark, val)
        self.val = val
        self.title = val
        self.iteminf[1] = ['int', '<br>{:,} ' + val]
        self.marktype = 'users'
        self.link = f'/filter/@{val} user:{{}}/1'
        self.pagetype = 'remort_postmark'
        self.page_options += [
            ['user', 'mark', 'marked']
            ]
    
    def get_items(self):
        datas = {}
        for file in dpref.get(self.val, []):
            if file not in ent['_posts'] or apdfa.dget(file, {}).get('data') == 'deleted':
                continue
            
            user = apdfa.dget(file)['uploader'].replace('_', '')
            if user not in datas:datas[user] = []
            datas[user].append(file)
        
        items = [(k, i) for i, k in sorted([(len(i), k) for k, i in datas.items()])]
        self.datas = datas
        
        return items
        
    def gimme(self, pargs):
        if not self.items or not self.datas:
            self.items = self.get_items()
        
        self.link = f'/filter/@{self.val} user:{{}}/1'
        if 'user' in pargs:
            self.link = '/user/{}/1'
        
        elif 'marked' in pargs:
            self.link = f'/filter/@marked user:{{}}/1'
        
        for i in self.items:
            if i[0] not in self.datas:
                self.datas[i[0]] = []


class mort_unavcheck(mort_base):
    
    def __init__(self,
                 marktype='users',
                 title='Unav Check',
                 link='/filter/userdescpost:{} !@maybe !@no !@dead @unavailable/1',
                 icon=ii(1)):
        
        super().__init__(marktype, title, link, icon)
        self.iteminf[1] = ['int', '- {:,}']
    
    def unav_count(self, posts):
        out = set()
        for post in posts:
            out.update(set([x
                for x in xlink['descpost'].get(post, [])
                if (x.isdigit() and
                    x not in self.sys_has and
                    x not in self.unav_marked)]))
        
        return len(out)
    
    def get_items(self):
        self.sys_has = set([x for x in apdfa])
        self.unav_marked = set([x
            for x, y in apdm.get('unava', {}).items()
            if y[0] != 'n/a'])

        out = {}
        for user, posts in users.items():
            count = self.unav_count(posts)
            if count > 0:
                out[user] = count
        
        return sorted(out.items(), key=itemgetter(1), reverse=True)
    
    def gimme_idc(self):
        self.datas = users
        self.items = self.get_items()


class mort_partial(mort_base):
    
    def __init__(self,
                 marktype='users',
                 title='Partial',
                 link='/user/{}/1',
                 icon=ii(1)):
        
        super().__init__(marktype, title, link, icon)
        self.iteminf[1] = ['int', '- {:.01%}']
    
    def get_items(self):
        return sorted({user:1 - perc[1]
            for user, perc in users_marked.items()
            if 0 < perc[1] < 1}.items()
            , key=itemgetter(1), reverse=True)
    
    def gimme_idc(self):
        self.datas = users
        # use percentage from usersort
        self.items = self.get_items()


class mort_gone(mort_base):
    
    def __init__(self, marktype='users', title='Gone', link='/user/{}/1', icon=ii(50)):
        super().__init__(marktype, title, link, icon)
    
    def get_items(self):
        return [x for x in ustat if 'error' in ustat.dget(x)]
    
    def gimme_idc(self):
        self.datas = users
        self.items = self.get_items()


class mort_activity(mort_base):
    
    def __init__(self, marktype='users', title='Activity', link='/user/{}/1', icon=ii(22)):
        super().__init__(marktype, title, link, icon)
        self.iteminf[1] = ['dateiso', '<br>{}']
    
    def gimme(self, pargs):
        self.datas = users
        tusers = []
        for a in ustat:
            d = ustat.dget(a)
            if d.get('new_post'):
                tusers[a] = (d.get('new_post'), a)
        
        self.items = [(a, d) for d, a in sorted(tusers)]
        
        try:# try and grab a date
            target = datetime.fromisoformat(pargs[1])
        except:
            target = 0
        
        if target:
            for i, da in enumerate(self.items):# find where it is
                if datetime.fromisoformat(da[1]) >= target:
                    break
            self.items = self.items[i:]


class mort_addedpost(mort_base):
    
    def __init__(self, marktype='users', title='Added Post', link='/user/{}/1', icon=ii(22)):
        super().__init__(marktype, title, link, icon)
        self.iteminf[1] = ['dateiso', '<br>{}']
    
    def gimme_idc(self):
        self.datas = users
        tusers = [(d, a) for a, d in users_mod.items()]
        self.items = [(a, trim_date(d*1000)) for d, a in sorted(tusers)]


class mort_review(mort_base):
    
    def __init__(self, marktype='users', title='Review', link='/user/{}/1', icon=ii(61)):
        super().__init__(marktype, title, link, icon)
        self.iteminf[1] = ['int', '<br>{:,} days']
    
    def gimme_idc(self):
        if self.items is None:
            self.items = {}
            passed = dpref.get('passed', {})
            for user, date in passed.items():
                up = user.get(user, {}).get('new_post')
                if up:
                    pd = jsdate(date)
                    up = datetime.utcfromtimestamp(up)
                    if up > pd:
                        self.items[user] = (up - pd).days
            
            self.items = sorted(self.items.items(), key=itemgetter(1), reverse=True)
        
        self.datas = users


class mort_addedreview(mort_base):
    
    def __init__(self, marktype='users', title='Added Review', link='/user/{}/1', icon=ii(61)):
        super().__init__(marktype, title, link, icon)
        self.iteminf[1] = ['int', '<br>{:,} days']
    
    def gimme_idc(self):
        if self.items is None:
            self.items = {}
            passed = dpref.get('passed', {})
            for user, date in passed.items():
                pd = jsdate(date)
                up = users_mod.get(user)
                if up is None:continue
                up = datetime.fromtimestamp(up)
                if up > pd:
                    self.items[user] = (up - pd).days
            
            self.items = sorted(self.items.items(), key=itemgetter(1), reverse=True)
        
        self.datas = users


class mort_folders(mort_base):
    
    def __init__(self, marktype='folders', title='Folders', link='/folder/{}/1', icon=ii(81)):
        super().__init__(marktype, title, link, icon)
        self.folsort = []
        self.iteminf[0] = ['str', '<br>id {}']
        self.iteminf[2] = ['replace', 0]
    
    def gimme_idc(self):
        self.items = []
        self.datas = {}
        
        for k in apdfafol:
            d = apdfafol.dget(k)
            i = d['items']
            self.items.append((k, len(i), d['title']))
            self.datas[k] = i
    
    def ez_build_item(self, i):
        return self.build_item(
            (i, len(self.datas[i]), apdfafol.dget(i)['title']),
            self.datas.get(i), self.marktype)
    
    def purge(self, strength):
        super().purge(strength)
        
        if self.clear_threshold <= strength:
            self.folsort = []


class mort_filetypes(mort_base):
    
    def __init__(self, marktype='filetypes', title='Filetypes', link='/filetype/{}/1', icon=ii(81)):
        super().__init__(marktype, title, link, icon)
    
    def gimme_idc(self):
        items = {}
        for k in apdfa:
            d = apdfa.dget(k)
            i = d.get('ext')
            if not i:
                i = 'error'
            
            if i not in items:
                items[i] = []
            
            items[i].append(k)
        
        self.items = []
        self.datas = {}
        for k, d in items.items():
            self.items.append((k, len(d)))
            self.datas[k] = d


class eyde_filetype(eyde_base):
    def __init__(self, items=[], marktype='filetypes'):
        super().__init__(items, marktype)
        self.datas = {}
    
    def itemget(self):
        items = {}
        for k in apdfa:
            d = apdfa.dget(k)
            i = d.get('ext')
            if not i:
                i = 'error'
            
            if i not in items:
                items[i] = []
            
            items[i].append(k)
        
        self.datas = items
    
    def gimme(self, pargs):
        ext = str(pargs[1])
        self.markid = ext

        if not self.datas:
            self.itemget()
        
        items = self.datas.get(ext, {})
        if not items:
            self.purge(0)
            return
        
        self.title = f'{ext} files'
        self.items = items


class mort_linkeduser(mort_base):
    def __init__(self, marktype='users', title='Linked Users', link='/filter/userl:{}/1', icon=ii(25)):
        super().__init__(marktype, title, link, icon)
    
    def gimme_idc(self):
        self.datas = xlink.get('descuserback', {})
        self.items = list(self.datas)


class mort_scout(mort_base):
    def __init__(self, marktype='users', title='Scout', link='/user/{}/1', icon=ii(32)):
        super().__init__(marktype, title, link, icon)
        self.headtext[0] = '<a href="/scout/!@passed !@gone/1">Available & not Passed</a><br>'
    
    def gimme_idc(self):
        self.datas = users
        self.items = {
            x: get_subs(x) - len(y)
            for x, y in self.datas.items()}
        
        self.items = sorted(self.items.items(), key=itemgetter(1))


class mort_favey(mort_base):
    def __init__(self, marktype='users', title='Favey', link='/user/{}/1', icon=ii(32)):
        super().__init__(marktype, title, link, icon)
    
    def uget(self, user):
        g = ustat.dget(user, {})
        if 'posts' in g and 'faves' in g:
            return g['faves'] / max(g['posts'], 1)
        
        return -1
    
    def gimme_idc(self):
        self.datas = users
        self.items = {
            x: self.uget(x)
            for x, y in self.datas.items()}
        
        self.items = sorted(self.items.items(), key=itemgetter(1))

class mort_percgot(mort_base):
    def __init__(self, marktype='users', title='Percent Got', link='/user/{}/1', icon=ii(95)):
        super().__init__(marktype, title, link, icon)
        self.headtext[0] = '<a href="/percgot/reversed !@gone !@passed/1">Available & not Passed</a><br>'
    
    def gimme_idc(self):
        self.datas = users
        self.items = {}
        
        for user, posts in users.items():
            al = get_subs(user)
            if user.startswith('@') or al == .1:
                continue
            
            self.items[user] = len(posts) / max(al, .1)
        
        self.items = sorted(self.items.items(), key=itemgetter(1))


def select_thumb(posts, do_ext=True):
    i = None
    for i in posts:
        if cfg['docats'] and i in ent['_marked']:
            continue
        
        break
    
    if not i:
        return 'parrot.svg'
    
    d = apdfa.dget(i, {'ext': 'error'})
    if file_category(d.get('ext', '')) == 'image':
        if do_ext:
            i += '.' + d['ext']
        
        return i
    
    return 'parrot.svg'


def choose_thumb(marktype, thing, level=0, do_ext=True):
    
    if marktype == 'posts':
        return select_thumb([thing], do_ext=do_ext)
    
    if marktype == 'users':
        posts = users.get(thing, [])
        return select_thumb(posts, do_ext=do_ext)
    
    if marktype == 'tags':
        posts = kwd.get(thing, [])
        return select_thumb(posts, do_ext=do_ext)
    
    if marktype == 'folders':
        posts = apdfafol.dget(thing, {}).get('items', [])
        return select_thumb(posts, do_ext=do_ext)
    
    if apdmm.get(marktype):
        posts = apdm.get(marktype, {})
        posts = posts.get(thing, {}).get('items', [])
        
        marktype = apdmm[marktype].get('for', 'posts')
        if not posts:
            return 'parrot.png'
        
        elif marktype == 'posts':
            return select_thumb(posts, do_ext=do_ext)
        
        elif level < cfg.get('thumbnail_recursion_limit', 5):
            posts = choose_thumb(
                marktype, posts[0], level=level+1, do_ext=do_ext)
            
            if posts == 'icons.svg':
                logging.debug(f'Recursion limit reached: {level} {marktype} {thing}')
            
            return posts
        
        return 'icons.svg'
    
    return 'parrot.png'


class builtin_search(builtin_base):

    def __init__(self, title='Search', link='/search', icon=20):
        super().__init__(title, icon)
    
    def page(self, handle, path):
        
        handle.wfile.write(b'<div class="head" onload="search()">')
        nav = template_nav('Search', 1, 1)
        handle.wfile.write(nav + b'</div>\n')
        
        pagehtml = '<select id="searchOF" class="niceinp" onchange="search(true)">\n'
        col = [d.get('name_plural', f) for f, d in apdmm.items() if d.get('type') == 'collection']
        for label in ['Users', 'Titles', 'Tags', 'Folders'] + col:
            pagehtml += f'<option value="{label}">{label}</option>\n'
        
        pagehtml += '</select>\n'
        pagehtml += strings['search_bar']
        
        pagehtml += mark_button().ez(
            '', '',
            'search(true)',
            'Search', ii(20), '')
        
        pagehtml += '<div class="container list"></div>\n'
        pagehtml += f'<script>var page = 1;var listCount = {cfg["list_count"]};</script>'
        handle.wfile.write(bytes(pagehtml, cfg['encoding_serve']))
        
        handle.wfile.write(b'\n</div><div class="foot">' + nav + b'</div><div class="foot">\n<br>')


def do_general_stat(items, data=None, fallback=100):
    # ah see, much nicer
    by_day = {}
    days = set()
    prev = 0
    pday = ''
    val = 1
    
    for item, datestamp in items.items():
        if type(datestamp) == str and not datestamp.isdigit():
            continue
        
        datestamp = int(datestamp)
        datestamp -= cfg['sec_offset'] * 1000# doesn't reset midnight utc0
        
        if 1800000 > prev - datestamp > -1800000:
            date = pday
        else:
            date = jsdate(datestamp).isoformat()[:10]
            prev = datestamp
            pday = date
        
        if data != None:
            val = data.get(item, fallback)
        
        if date in days:
            by_day[date] += val
        else:
            by_day[date] = val
            days.add(date)
    
    return by_day


def trtd(things):
    ret = '<tr>'
    for t in things:
        ret += f'\n\t<td>{t}</td>'
    
    return f'{ret}\n</tr>\n'


class builtin_info(builtin_base):

    def __init__(self, title='Info', link='/stats', icon=51):
        super().__init__(title, icon)
    
    def page(self, handle, path):
        srvname = cfg['server_name']
        if not isinstance(srvname, str) or not srvname:
            srvname = 'FADSRV'
        
        doc = f'<div class="head"><h2 class="pagetitle">{srvname} Info</h2></div>\n'
        doc += '<div class="container list">\n'
        
        doc += '<p>Heck.</p>\n'
        doc += f'<p>You\'re running version {ent["version"]}</p>\n'
        if '#' in ent['version']:
            doc += 'Note: <i>This is a developer build.</i> &gt;.&lt;<br>\n'

        doc += f'''<br><br>
Last rebuilt at:<br>
{ent['generated'].isoformat()}<br>
<br>
Server time now:<br>
{datetime.now().isoformat()}<br><br>
{isdocats()}
<br><br>
'''
        handle.wfile.write(bytes(doc, cfg['encoding_serve']))
        
        doc = f'''<br>
apdfa: {len(apdfa):,}<br>
apdfafol: {len(apdfafol):,}<br><br>
'''
        handle.wfile.write(bytes(doc, cfg['encoding_serve']))


class builtin_stats(builtin_base):

    def __init__(self, title='Stats', link='/stats', icon=ii(2)):
        super().__init__(title, icon)
        self.pagetype = 'builtin_stats'
    
    @staticmethod
    def perc_builder(label, out):
        doc = f'<div class="markinfobox"><h3>{label}</h3>'
        for l, v in out:
            if type(l) == int:
                l, v = out[l][1], out[v][1]
                v = max(1, max(l, v))
                doc += f'{l/v:.02%}<br>\n'
                continue
            
            doc += f'{l}: {v:,}<br>\n'
        
        return doc + '</div>\n'
    
    def do_percent(self, mark):
        
        data = apdmm[mark]
        
        tx = ''
        out = [
            ['Total', 0],
            ['Marked', 0],
            [1, 0],
            ]
        
        dfor = data.get('for', 'posts')
        label = data.get("label", mark.title())
        
        if dfor == 'posts':
            out[0][1] = len(apdfa)
            out[1][1] = len(apdm.get(mark, []))
        
        elif dfor == 'posts_unav':
            out[0][1] = len(xlink.get('descpostback', {}))
            out[1][1] = len(apdm.get(mark, []))
        
        elif dfor == 'users':
            m = set(apdm.get(mark, []))

            tx = self.perc_builder(
                label + ' (Users)', [
                ['Users', len(users)],
                ['Marked', len(m)],
                [1, 0]
                ])
            label += ' (Posts)'
            
            for user, posts in users.items():
                if user not in m:
                    continue
                
                posts = len(posts)
                out[1][1] += posts
                
                k = get_subs(user)
                out[0][1] += max(posts, k)
        
        elif dfor == 'folders':
            m = set(apdm.get(mark, []))
            
            for user in apdfafol:
                data = apdfafol.dget(user)
                posts = len(data.get('items', []))
                out[0][1] += posts
                
                if user in m:
                    out[1][1] += posts
        
        return tx + self.perc_builder(label, out)
    
    def do_breakdown(self, mark):
        data = apdmm[mark]
        
        count = 0
        dfor = data.get('for', 'posts')
        if dfor == 'posts':
            count = len(apdfa)
        
        elif dfor == 'posts_unav':
            count = len(xlink.get('descpostback', {}))
        
        elif dfor == 'users':
            count = len(users)
        
        elif dfor == 'folders':
            count = len(apdfafol)
        
        subtr = 0
        if len(data.get('values', [])) < 2:
            return ''
        
        doc = '<div class="markinfobox">'
        label = data.get("label", mark.title())
        doc += f'<h3>{label}</h3>\n'
        doc += strings['stripeytablehead'].format(3, '')
        doc += trtd(['Type', 'Count', 'Perecent'])
        vals = []
        
        for value in data.get('values', []):
            qty = len(dpref.get(value, []))
            subtr -= qty
            vals.append((value, qty))
        
        if not vals:
            return ''
        
        subtr += count
        if subtr < 0:
            count -= subtr
            subtr = 0
        
        vals.append(('remaining', subtr))
        
        c = 0
        cla = [' class="odd"', '']
        for label, qty in vals:
            doc += f'<tr{cla[c%2]}>\n\t'
            doc += f'<td>{label}</td>\n\t'
            doc += f'<td>{qty:,}</td>\n\t'
            minc = max(count, 1)
            doc += f'<td>{qty/minc:.02%}\n</tr>\n'
            c += 1
        
        doc += '</table></div>\n'
        return doc
    
    def page(self, handle, path):
        
        doc = '<div class="head"><h2 class="pagetitle">Stats</h2></div>\n'
        doc += '<div class="container list">\n'
        
        self.write(handle, doc)

        know = 0
        for user, posts in users.items():
            posts = len(posts)
            
            k = get_subs(user)
            k = max(posts, k)
            if k:
                know += k
        
        doc = ''
        
        out = [['Known', know], ['Faved', len(apdfa)], [1, 0]]
        doc += self.perc_builder('All', out)
        
        sorty = sorted([(d.get('for', 'posts'), k, d.get('stats'))
                       for k, d in apdmm.items()], reverse=True)
        
        for t, k, d in sorty:
            if d and 'percent' in d:
                doc += self.do_percent(k)
        
        self.write(handle, doc + '<br>\n')
        
        doc = ''
        for t, k, d in sorty:
            if d and 'breakdown' in d:
                doc += self.do_breakdown(k)
        
        doc += '</div>'
        self.write(handle, doc)


def table_odd(c):
    return ['', 'odd'][c%2]


def table_template(i, f):
    return f'\n\t<td>{wrapme(i, f=f)}</td>'


def do_stat_seesion(items, data=None, fallback=100):
    # ah see, much nicer
    sep = {}
    sess = set()
    prev = 0
    sesc = ''
    val = 1
    
    for item, datestamp in items.items():
        if type(datestamp) == str and not datestamp.isdigit():
            continue
        
        datestamp = int(datestamp)
        datestamp -= cfg['sec_offset'] * 1000# doesn't reset midnight utc0
        
        if not (7200000 > prev - datestamp > -7200000):
            sesc = datestamp
            prev = datestamp
        
        if data != None:
            val = data.get(item, fallback)
        
        if sesc in sess:
            sep[sesc] += val
        
        else:
            sep[sesc] = val
            sess.add(sesc)
    
    return sep


class stats_base(builtin_base):
    
    def __init__(self, title='', link='', icon=ii(99)):
        super().__init__(title, icon)
        self.table_name = 'Add a name silly!'
        self.cluster = True
        self.charte = '<canvas id="{}" style="width:100%;max-width:700px"></canvas>\n'
        self.chartc = '''new Chart("##name##", {
  type: "##TYPE##",
  data: {
    labels: chart_labels,
    datasets: [{
      fill: false,
      lineTension: 0,
      backgroundColor: "hsl(0deg 0% 62%)",
      borderColor: "hsl(0deg 0% 62% / 50%)",
      data: chart_##data##
    }]
  },
  options: {
    legend: {display: false},
    plugins: {
            title: {
                display: true,
                text: '##name##'
            }
        }
  }
});
'''.replace('##name##', 'chart_##data##')
        self.mode_default = 'simple'
        self.modes = {
            'simple': 'Simplified',
            'hour': 'Hourly',
            'day': 'Daily',
            'week': 'Weekly',
            'month': 'Monthly',
            'quart': 'Quarterly',
            'year': 'Yearly'
            }
        self.pagetype = 'builtin_stats'
    
    @staticmethod
    def fromiso(d):
        try:
            return datetime.strptime(d, '%Y-%m-%dT%H:%M:%S.%f')
        
        except:
            return datetime.strptime(d, '%Y-%m-%dT%H:%M:%S')
    
    def process_date(self, d, mode):
        if isinstance(d, int):
            d = jsdate(d).isoformat()
        
        if mode == 'simple':    return d[:7]
        elif mode == 'day':     return d[:10]
        elif mode == 'month':   return d[:7]
        elif mode == 'year':    return d[:4]
        elif mode == 'hour':    return d[:13]
        elif mode == 'quart':
            m = int(d[5:7])
            return f'{d[:4]} q{math.ceil(m/3)}'
        
        elif mode == 'week':
            d = self.fromiso(d).isocalendar()
            return f'{d[0]} w{d[1]}'
    
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
        
        return target, ' - '.join(doc) + '<br><br>\n'
    
    def data(self):
        return do_stat_seesion({
            k: v[1]
            for k, v in apdm['marka'].items()
            if v[0] != 'n/a'})
    
    def data_prep(self, path, mode):
        doc =  self.charte.format('chart_new')
        doc += self.charte.format('chart_tot')
        
        stat = self.data()
        dat = {}
        per = set()
        
        hi = 0
        for k, v in stat.items():
            w = self.process_date(k, mode)
            if w not in per:
                dat[w] = 0
                per.add(w)
            
            dat[w] += v
            
            if dat[w] > hi:
                hi = dat[w]
        
        chart_labels = []
        chart_new = []
        tot = 0
        chart_tot = []
        for k, v in sorted(dat.items()):
            chart_labels.append(k)
            chart_new.append(v)
            tot += v
            chart_tot.append(tot)
        
        doc += '<script>\n'
        doc += f'var chart_labels = {json.dumps(chart_labels)};\n'
        doc += f'var chart_new = {json.dumps(chart_new)};\n'
        doc += f'var chart_tot = {json.dumps(chart_tot)};\n'
        
        doc += self.chartc.replace('##data##', 'new').replace('##TYPE##', 'bar')
        doc += self.chartc.replace('##data##', 'tot').replace('##TYPE##', 'line')
        doc += '</script>\n<br>'
        
        if mode == 'simple':
            dat = stat
        
        return doc, dat, hi
    
    def stat_table(self, mode, dat, hi):
        doc = strings['stripeytablehead'].format(3, 'Stats')
        doc += trtd(['Date', 'Count', 'High%'])
        c = 1
        iscluster = mode == 'simple'
        carry = 0
        
        for k, v in sorted(dat.items(), reverse=True):
            if iscluster:
                if v < 5:
                    carry += v
                    continue
                
                k = self.process_date(k, 'hour')
                v += carry
            
            doc += f'<tr class="{table_odd(c)}">'
            for i, f in [
                (k, '{}'),
                (v, '{:,}'),
                (v / hi, '{:.02%}')
                ]:
                doc += table_template(i, f)
            
            carry = 0
            doc += '\n</tr>\n'
            c += 1
        
        doc += '</table>\n<br>\n<br>\n'
        return doc
    
    def page(self, handle, path):
        doc = f'<div class="head"><h2 class="pagetitle">{self.title}</h2></div>\n'
        doc += '<div class="container list">\n'
        
        doc += '<script src="chart.js"></script>\n'
        
        mode, pickmode = self.build_picker(path, self.modes, self.mode_default)
        modename = self.modes.get(mode, mode)
        doc += pickmode
        
        handle.wfile.write(bytes(doc, cfg['encoding_serve']))
        
        doc, dat, hi = self.data_prep(path, mode)
        doc += self.stat_table(mode, dat, hi)
        
        handle.wfile.write(bytes(doc, cfg['encoding_serve']))


class builtin_statsmark(stats_base):
    
    def __init__(self, mark):
        self.meta = apdmm[mark]
        icon = self.meta.get('icon', None)
        super().__init__(mark, icon)
        self.mark = mark
    
    def data(self):
        return do_stat_seesion({
            k: v[1]
            for k, v in apdm.get(self.mark, {}).items()
            if v[0] != 'n/a'})


class builtin_statadd(stats_base):

    def __init__(self, title='Stats Add', link='/statsess', icon=2):
        super().__init__(title, icon)
        #self.cluster = False
        self.field = 'filedate'
        self.table_name = 'Add'
    
    def data(self):
        d = {}
        for k in apdfa:
            v = apdfa.dget(k)
            if self.field in v and type(v[self.field]) == float:
                d[k + 'T00:00:00'] = v[self.field] * 1000
        
        return do_general_stat(d)


class builtin_statupl(builtin_statadd):

    def __init__(self, title='Stats Upload', link='/statsess', icon=2):
        super().__init__(title, icon)
        self.field = 'date'
        self.table_name = 'Upload'


class builtin_markedit(builtin_base):

    def __init__(self, title='Mark Edit', link='/markedit', icon=24):
        super().__init__(title, icon)
    
    def icobar(self, xy, s=-24):
        return f'icon: <i class="iconsheet teenyicon" {markicon(xy[0], xy[1], s)} vertical-align: middle;"></i> {xy}<br>\n'
    
    def listprop(self, data, k, v):
        # write out properties nicely
        if k == 'icon':return self.icobar(v)
        elif k == 'values' or k == 'valueicon':return ''
        else:return f'{k}: {data[k]}<br>\n'
    
    def listvalue(self, data, n, i):
        # dispay values, sometimes with icons
        body = ''
        if not n:body += '<br>\n'
        
        body += f'value {n}: {i}<br>\n'
        
        if len(data.get('valueicon', [])) > n:
            xy, ch = valueicon(
                i, data['valueicon'], data['icon'], data['values'])
            
            body += self.icobar(xy)
        
        return body
    
    def markinfo(self, name, data):
        # display everything for a mark file
        body = '<div class="markinfobox">\n'
        body += f'\n<h3>ds_{name}</h3>\n'
        
        data['for'] = data.get('for', 'posts')
        data['icon'] = data.get('icon', [-1, -1])
        
        for k, v in data.items():
            body += self.listprop(data, k, v)
        
        for n, i in enumerate(data.get('values', [])):
            body += self.listvalue(data, n, i)
        
        return body + '</div>\n'
    
    def page(self, handle, path):
        # display all mark files
        handle.wfile.write(b'<div class="head">')
        nav = template_nav('Mark Files', 1, 1)
        handle.wfile.write(nav + b'</div>\n')
        
        handle.wfile.write(b'<div class="container list">\n')
        
        body = ''
        for name in ent['mark_buttons']:
            body += self.markinfo(name, apdmm[name])
        
        handle.wfile.write(bytes(body, cfg['encoding_serve']))
        handle.wfile.write(b'</div>\n')


class builtin_quest(builtin_base):

    def __init__(self, title='Quest', link='/quest/1', icon=21):
        super().__init__(title, icon)
        self.pagetype = 'remort'
    
    def stat_block(self, stat_marka):
        score = 0
        level = 1
        req = 500
        preq = 0
        
        recent = list(stat_marka.keys())[-1]
        markpts = stat_marka[recent]
        
        score = markpts * 100
        while score+preq >= req:
            level += 1
            preq -= req
            req += 300
        
        recent = jsdate(recent).isoformat()[:13]
    
        disp = f'Showing stats from session starting {recent}<br>\n'
        disp += f'<h2 style="display: inline; margin-right: 15px;">Level {level}</h2>\n'
        disp += f'<progress value="{score+preq}" max="{req}"></progress>\n'
        disp += f'\n<p>{req-(score+preq):,} xp needed to level up</i></p>\n'
        return disp
    
    def page(self, handle, path):
        read = dpref.get('read', {})
        
        stat_marka = do_stat_seesion({k: v[1] for k, v in apdm['marka'].items()})
        
        if stat_marka:
            handle.wfile.write(
                bytes(self.stat_block(stat_marka), cfg['encoding_serve']))
        
        if 'users' in ent['_lists']:# follows user activity
            path = ['list', 'users', path[-1]]
        
        else:# inital state
            page = choice(['users', 'passed', 'queue', 'partial'])
            path = [page, path[-1]]
        
        ent['builtin'][path[0]].page(handle, path)


class builtin_menu_mark(builtin_menu):

    def __init__(self, which, aaa):
        icon = apdmm[which].get('icon', [8, 8])
        link = '/' + apdmm[which].get('values', [which])[0]
        super().__init__(which, icon, which)
    
    def page(self, handle, path):
        minfo = {
            "title": apdmm[self.which].get('title', self.which),
            "mode": "narrow-icons-flat",
            "icon": self.icon
            }
        
        eles = []
        for url, d in apdm[self.which].items():
            if d[0] == 'n/a':continue
            for s, v in [('%20', ' '),
                         ('%64', '@'),
                         ('%3E', '>'),
                         ('%3C', '<')]:
                url = url.replace(s, v)
            
            label = url.replace(' ', '<br>')
            
            for n, i in enumerate(list(label.split('/'))):
                if i and not label.startswith('<'):
                    label = f'<b>{i}</b>'
                
                elif i != '1':
                    label += f'<br>\n{i}'
            
            eles.append({'label': label, 'href': url})
        
        self.build_menu(handle, self.which, minfo, eles)


class mort_postmarks(mort_base, builtin_menu):

    def __init__(self, marktype='postmarks', title='Post Marks', link='/postmark/{}/1', icon=ii(3)):
        which = 'dummy'
        super().__init__(which, '/'+which, icon, False, which)
        self.title = title
        self.link = link
        self.icon = icon
        self.pagetype = 'remort'
        self.marktype = marktype
        self.page_options = ['reversed']
    
    def page(self, handle, path):
        minfo = {
            "title": self.title,
            "mode": "narrow-icons-flat",
            "icon": self.icon
            }
        
        eles = []
        for m, d  in apdmm.items():
            if compare_for(d, 'posts', sw=True):
                for n, v in enumerate(d.get('values', [])):
                    if v not in eles:
                        label = f'<b>{v}</b><br>\n'
                        label += f'{len(dpref.get(v, {})):,}'
                        
                        icon = d.get('icon', ii(45))
                        if len(d.get('valueicon', [])) > n:
                            icon = d['valueicon'][n]
                        
                        if not isinstance(icon, list):
                            icon = ii(45)
                        
                        url = self.link.format(v)
                        
                        eles.append({'label': label,
                                     'icon': icon,
                                     'href': url})
        
        if 'reversed' in path[1:]:
            eles = self.reverse(eles)
        
        self.build_menu(handle, self.which, minfo, eles)


class builtin_rebuild(builtin_base):
    def __init__(self,
                 title='Rebuild',
                 icon=60):
        super().__init__(title, icon)
    
    def page(self, handle, pathe):
        build_entries()
        htmlout = '<div class="head">\n<h2 class="pagetitle">Rebuild'
        htmlout += '</h2>\n</div>\n<div class="container list">\n'
        htmlout += 'Should be done!<br>\n<br>\n'
        handle.wfile.write(bytes(htmlout, cfg['encoding_serve']))


def desc_fol(item):
    data = apdfa.dget(item, {})
    user = data.get('uploader')
    
    block = user
    
    if not block:
        logging.warning(f'Can\'t find block for {item} by {user}')
        return '9999'
    
    return block


def post_path(fp):
    if cfg.get('post_split'):
        fid = fp.split('.')[0].zfill(2)
        
        if fid.isdigit():
            fp = f'{int(fid[-2:]):02d}/{fp}'
    
    return cfg['image_dir'] + fp


def serve_image(handle, path, head=True):
    if '.' not in path:path += '.'
    ext = path.split('.')[-1]
    
    fp = post_path(path.split('/')[-1])
    if '/pageimg/' in path:
        fp = path
    
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
        serve_resource(handle, 'parrot.svg', code=404, forever=False)


class builtin_reader(builtin_base):

    def __init__(self, title='Reader', icon=33):
        super().__init__(title, icon)
        self.pagetype = 'eyde'
    
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


class builtin_textattach(builtin_reader):

    def __init__(self, title='Text Attach', icon=99):
        super().__init__(title, icon)
        self.pagetype = 'eyde'
    
    def post_path(self, path):
        return 'im/_ta/' + path
    
    def page(self, handle, path):
        name = None
        if len(path) > 1:
            name = path[1].split('.')[0]
        
        if not name:
            name = 'No Data'
        
        self.title = name
        
        if name.isdigit():
            self.write(handle,
                       mark_for('posts', name, wrap=True))
        
        super().page(handle, path)


class builtin_config(builtin_config):
    def __init__(self, title='Configure', icon=12):
        super().__init__(title, icon)
        self.subpages.update({
            'test': [self.testsub, 'Test', 60],
            'menus': [self.edit_menus, 'Menus', 59],
            'marks': [self.edit_marks, 'Marks', 3],
            'profiles': [self.edit_profiles, 'Profiles', 65],
            })
    
    def testsub(self, handle, path):
        self.write(handle, 'Success')
    
    def edit_menu(self, handle, menu):
        self.write(handle, f'<h2>{menu}</h2>\n')
    
    def edit_menus(self, handle, path):
        pages = menus.get('pages', {})
        if len(path) > 2 and path[2] in pages:
            return self.edit_menu(handle, path[2])
        
        eles = [{
            'label': v.get('name', k),
            'icon': v.get('icon', 99),
            'href': f'/config/menus/{k}'}
            for k, v in pages.items()
            ]
        
        self.ez_menu(
            handle, path, 'Edit Menus', self.icon, eles)
        
        doc = '<button onclick="">Create New</button>'
        self.write(handle, doc)
    
    def edit_mark(self, handle, mark):
        doc = '<div class="container list">\n'

        inlineicn = '<i class="iconsheet teenyicon" {} vertical-align: middle;"></i> {}'
        data = apdmm[mark]
        doc += f'\n<h1>ds_{mark}</h1>\n'
        
        data['for'] = data.get('for', 'posts')
        data['icon'] = data.get('icon', [-1, -1])
        
        for k, v in data.items():
            if k == 'icon':
                v = inlineicn.format(markicon(v[0], v[1], -24), v)
                doc += f'<p>{k}: {v}</p>\n'
                continue
            
            elif k == 'values' or k == 'valueicon':
                continue
            
            doc += self.configure_item('apdmm', k, v)
            
        
        self.write(handle, doc)
        doc = ''
        
        values = data.get('values', [])
        if values:
            doc += '<h2>Values</h2>\n'
        
        for n, i in enumerate(values):
            line = f'{i}'
            
            if len(data.get('valueicon', [])) > n:
                xy, ch = valueicon(
                    i, data['valueicon'], data['icon'], data['values'])
                
                line += ': '
                line += inlineicn.format(markicon(xy[0], xy[1], -24), xy)
            
            doc += f'<p>{line}</p>\n'
        
        doc += '</div>'
        self.write(handle, doc)
    
    def edit_marks(self, handle, path):
        marks = {k: apdmm[k] for k in ent['mark_buttons']}
        if len(path) > 2 and path[2] in marks:
            return self.edit_mark(handle, path[2])
        
        eles = [{
            'label': v.get('name', k),
            'icon': v.get('icon', 99),
            'href': f'/config/marks/{k}'}
            for k, v in marks.items()
            ]
        
        self.ez_menu(
            handle, path, 'Edit Marks', self.icon, eles)
        
        doc = '<button onclick="">Create New</button>'
        self.write(handle, doc)
    
    def edit_profiles(self, handle, path):
        h = '<p>Menus:</p>'
        s = '\n<script>\nvar menuPages = {'
        butt = {}
        for k, d in menus['pages'].items():
            h += '\n<div class="btn" onclick="editMenuDisplay(\'{}\')">{}</div>'.format(k , d.get('title', k))
            s += '\n\t"{}": {},'.format(k, json.dumps(d))
            n = d.get('buttons')
            if n in menus:
                butt[n] = menus[n]
        
        s = s[:-1] + '\n};\n'
        s += '\nvar menuButtons = {'
        for k, d in butt.items():
            s += '\n\t"{}": {},'.format(k, json.dumps(d))
        
        s = s[:-1] + '\n};\n</script>'
        h += '\n<br>\n'
        handle.wfile.write(bytes(s + h, 'utf8'))
        
        h = '<input class="niceinp" name="title">\n'
        h += '<input class="niceinp" name="item-style">\n'
        h += '<div id="items"></div>'
        handle.wfile.write(bytes(h, 'utf8'))


class post_search(post_base):
    
    def search_of(self, query, kind, items, useval=None):
        mo = ent['builtin'][kind]
        mo.gimme(['', 1])
        ret = {'items': [], 'result': []}
        for item in items:
            if item is None:
                continue
            
            check = item.lower()
            if useval != None:
                check = items[item].get(useval, '@UNTITLED').lower()
            
            if query in check:
                ret['items'].append(item)
                ret['result'].append(mo.ez_build_item(item))
        
        return ret
    
    def post_logic(self, handle, pargs, data):
        mode = data.get('of', 'user').lower()
        query = data.get('query')
        
        if mode == 'users':
            ret = self.search_of(query, 'users', ent['usersort'])
        
        elif mode == 'titles':
            ret = self.search_of(query, 'view', apdfa, useval='title')
        
        elif mode == 'tags':
            ret = self.search_of(query, 'tags', kwd)
        
        elif mode == 'folders':
            ret = self.search_of(query, 'folders', apdfafol, useval='title')
        
        elif mode in apdm:
            ret = self.search_of(query, mode, apdm[mode])
        
        else:
            ret = {'result': [f'Sorry, nothing.<br><br>How do i handle {mode}?']}
        
        ret['result'] = sorted(ret['result'])
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
            apdm[flag].write(ch_apdm)
        
        return ret


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
        
        if pargs[1] == 'postdata':
            datsrc = apdfa
            
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
        handle.wfile.write(bytes(json.dumps(ret), cfg['encoding_serve']))


class post_profiles(post_base):
    
    def head(self, handle, status=200):
        path = handle.path[1:].split('/')
        if len(path) == 2:
            rd = self.page_logic(handle, path, path[1])
            if rd:
                handle.send_response(307)
                handle.send_header('Location', rd)
                handle.end_headers()
                return
        
        super().head(handle, status=status)
    
    def post_logic(self, handle, pargs, data):
        global cfg
        
        if data.get('set') in ent['profiles']:
            for k, v in ent['profiles'][data['set']].items():
                if k.startswith('_'):continue
                cfg[k] = v
            
            save_config()
            
            return {'status': 'success', 'href': '/' + cfg['dropdown_menu']}
        
        return {'error': 'unhandled request'}
    
    @staticmethod
    def validate_icon(icon):
        if isinstance(icon, list):
            return icon
        
        if isinstance(icon, int):
            return ii(icon)
        
        return [9, 9]
    
    def page_logic(self, handle, path, selected):
        js = self.post_logic(handle, [], {'set': selected})
        return js.get('href')
    
    def page(self, handle, path):
        self.title = 'Profiles'
        
        nav = template_nav(self.title, 1, 1, enc=False)
        doc = f'<div class="head">\n{nav}</div>\n'
        if not ent['profiles']:
            doc += 'No profiles created.<br><br>\n'
            self.write(handle, doc)
            return
        
        for idx, data in ent['profiles'].items():
            label = data.get('_label', idx)
            icon = self.validate_icon(data.get('_icon'))
            
            doc += strings['menubtn-narrow-icons-flat'].format(
                href=f'/profiles/{idx}',
                alt=idx, x=icon[0]*-100, y=icon[1]*-100,
                label=label
                )
        
        doc += '<br><br>\n'
        self.write(handle, doc)


class fa_req_handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        path_long = self.path[1:].lower()
        path_nice = urllib.parse.unquote(self.path)[1:]
        path_split = path_nice.lower().split('/')
        
        if path_split[0] == 'pageimg':# hack
            path_long = 'i/pages/' + path_long
        
        if path_split[-1] in ent['resources']:
            serve_resource(self, path_split[-1])
            return
        
        elif (path_long.startswith('i/') or
              path_long.startswith('t/')):
            serve_image(self, urllib.parse.unquote(self.path[3:]))
            return
        
        b = builtin_base()
        target = ent['builtin'].get(path_split[0])
        
        if target and target.pages is False:
            target.serve(self, path_split)
            return
        
        elif path_split == ['']:
            home = ent['builtin'].get(cfg['homepage_menu'])
            
            if home is None:
                home = ent['builtin']['users']
            
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
            ripdata = json.loads(post_data.decode(cfg['encoding_serve']))
        
        except:
            ripdata  = {}
        
        #logging.debug(json.dumps(ripdata))
        
        if path_split[0] in ent['builtin_post']:
            ent['builtin_post'][path_split[0]].serve_post(self, path_split, ripdata)
            return
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        ret = {}
        
        if path_split[0] == 'reshuffle':
            ent['builtin']['shuffle'].purge(2)
            ret['status'] = 'success'
        
        elif path_split[0] == 'rebuild':
            level = 0
            if len(path_split) > 1:level = path_split[1]
            build_entries(reload=level)
            ret['status'] = 'success'
        
        elif path_split[0] == 'findnew':
            level = 2
            if path_split[-1] == 'user_stats':
                level = 1
            
            elif not (cfg.get('skip_bigdata') or cfg.get('skip_findnew')):
                ent['added_content'] = apd_findnew()
            
            build_entries(reload=level)
            ret['status'] = 'success'
        
        self.wfile.write(bytes(json.dumps(ret), cfg['encoding_serve']))
        return


def get_cfg_resources(k):
    v = cfg.get(k)
    
    if type(v) == str:
        return [v]
    
    if type(v) == list:
        return v
    
    return None


def load_user_config():
    global ent
    load_global('cfg', ent['config_file'])
    load_global('menus', ent['menu_file'])
    ent['profiles'] = load_global('profiles', 'fadprofiles.json')
    
    if 'all_pages' not in menus['pages']:
        menus['pages']['all_pages'] = {
            "title": "All Pages",
            "mode": "wide-icons-flat",
            "buttons": "all_pages_buttons",
            "icon": [9, 9]
            }
    
    if 'pages' not in menus['pages']:
        menus['pages']['pages'] = {
            'title': 'Pages',
            'mode': 'wide-icons-flat',
            'buttons': 'page_buttons',
            "icon": [8, 4]
            }
    
    for k in ['resources', 'style_doc', 'script_doc']:
        v = get_cfg_resources(k)
        if v == None:continue# No files
        for i in v:
            if i.lower() not in ent['resources']:
                ent['resources'].append(i.lower())
    
    st = safe_readfile(cfg['apd_dir'] + 'strings.txt')
    if not st:return# empty
    
    for line in st.split('\n')[1:]:
        line = line.split('\t')
        if len(line) == 2:
            line[1] = line[1].replace('\\n', '\n')
            if line[0].startswith('b.'):
                line[1] = bytes(line[1][2:-1], cfg['encoding_serve'])
            
            strings[line[0]] = line[1]
    
    logging.info('Loaded strings')


def load_wp(fn):
    global wp, wpm
    
    data = wp.get(fn, appender())
    data.read(cfg['mark_dir'] + 'wp_' + fn)
    if '//' in data:
        wpm[fn] = data['//']
        del data['//']
    
    wp[fn] = data


def load_apx(path, pre, fn):
    global xlink
    
    data = xlink.get(fn, appender())
    data.read(path + pre + fn)
    
    prop = data.get('//', {})
    if '//' in data:
        prop = data['//']
    
    xlink[fn] = data
    
    if not prop.get('linkback', True):
        return# skip doing reverse linking
    
    back = {}
    exists = set()
    
    for k, v in data.items():
        if k == '//':continue
        for i in v:
            if i not in exists:
                back[i] = []
                exists.add(i)
            
            back[i].append(k)
    
    xlink[fn + 'back'] = back


def load_bigapd(load=True):
    global apdfa, apdfadesc, apdfafol

    data_files = ['apdfa', 'apdfafol']
    if not cfg['desc_split']:
        data_files.append('apdfadesc')
    
    for k in data_files:
        if k not in globals():
            globals()[k] = appender_sharedkeys()
    
    gc.collect()
    
    if cfg.get('skip_bigdata') or not load:
        return False
    
    logging.info('Reading Big APD files...')
    
    for k in data_files:
        globals()[k].read(
            cfg['apd_dir'] + k,
            encoding='iso-8859-1', dotime=True)
    
    return True


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
    global ent, apdmm, apdm, dpref, dprefm, xlink, wp, wpm
    
    logging.info('Reading Mark files')
    
    for k in ['wp', 'wpm', 'dprefm', 'dpref', 'xlink']:
        if k not in globals():
            globals()[k] = {}

    apdmark = {}
    apxlink = {}
    wpfile = {}
    
    scandir = cfg['mark_dir']
    
    for f in os.listdir(scandir):
        if '.' in f or f[-1].isdigit():
            continue
        
        if f.startswith('ds_'):
            apdmark[f[3:]] = 0
        elif f.startswith('apx_'):
            apxlink[f[4:]] = 0
        elif f.startswith('wp_'):
            wpfile[f[3:]] = 0
    
    datas  = {}
    ent['apxlink'] = apxlink
    
    order = []
    for apdfile in apdmark:
        order.append(
            load_apdmfile(scandir, 'ds_', apdfile))
    
    ent['apdmark'] = [y for x, y in sorted(order)]
    
    ent['loaded_apd'] = True
    
    for apdfile in wpfile:
        load_wp(apdfile)
    
    logging.info('Reading APX files')
    for apdfile in apxlink:
        load_apx(scandir, 'apx_', apdfile)
    
    ent['loaded_apx'] = True


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


def init_apd():
    
    if not os.path.isdir(cfg['apd_dir']):
        os.mkdir(cfg['apd_dir'])
    
    if not os.path.isdir(cfg['mark_dir']):
        os.mkdir(cfg['mark_dir'])
    
    make_apd('apdfa', {'//': {}}, origin=cfg['apd_dir'])
    if not os.path.isdir(cfg['apd_dir'] + 'descb'):
        os.mkdir(cfg['apd_dir'] + 'descb')
    
    make_apd('apdfafol', {'//': {}}, origin=cfg['apd_dir'])
    
    make_apd('apx_descpost', {'//': {
        'type': 'xlink',
        'for': 'posts'
    }})

    make_apd('apx_descuser', {'//': {
        'type': 'xlink',
        'for': 'users'
    }})
    
    make_apd('ds_passed', {'//': {
        'icon':  ii(40),
        'type': "multibutt",
        'values': ["passed"],
        'for': "users",
        'order': 0
    }})
    
    make_apd('ds_queue', {'//': {
        'icon':  ii(11),
        'type': "multibutt",
        'values': ["queue"],
        'for': "users",
        'order': 20
    }})
    
    make_apd('ds_marka', {'//': {
        'icon':  ii(60),
        'type': "multibutt",
        'values': ["seen", "ref", "rem"],
        'valueicon': [ii(3), ii(13), ii(23)],
        'order': 20
    }})
    
    make_apd('ds_sets', {'//': {
        'icon':  ii(70),
        'name': "Set",
        'type': "collection",
        'for': "posts",
        'doReadCount': True,
        "excludeMarked": False,
        'order': 90
    }})


def stop():
    logging.info('Stopping server')
    time.sleep(2)
    httpd.shutdown()


if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    init_logger('fadsrv', disp=':' in code_path)
    
    os.chdir(code_path)
    
    load_global('strings',{# todo migrate more from code and clean up
'responsive': '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n',
'thumb': '<span class="thumb{2}"><a class="thumba" href="{0}"><span>{1}</span></a></span>\n',
'nb': '<a class="btn{2}" href="{1}">{0}</a>\n',
'setlogic': '<div id="sets-man" class="hidden">\n<div class="ctrl">\n<input class="niceinp" id="setsName" oninput="setSearch()">\n<button class="mbutton" onclick="setsNew()">+</button>\n<button class="mbutton" onclick="setsClose()">X</button>\n</div>\n<div class="list" id="sets-list">\n</div>\n</div>\n',

'cfg.docats.name': 'Do Categories ^-.-^',
'cfg.docats.label': 'Hide posts you\'ve already marked from user pages.',
'cfg.image_dir.name': 'Post Image Directory',
'cfg.image_dir.label': 'Where the server should look for the images',
'cfg.data_dir.name': 'Post Data Directory',
'cfg.data_dir.label': 'Where the server should look for the post data',
'cfg.list_count.name': 'List Count',
'cfg.list_count.label': 'Used on list pages, how many elements per page.',
'cfg.post_count.name': 'Post Count',
'cfg.post_count.label': 'USed on post pages, how many posts per page.',
'cfg.over.name': 'List Overflow Limit',
'cfg.over.label': 'Includes more items on the last page if fewer than this value.',
'cfg.post_split.name': 'Split Directory Structure',
'cfg.post_split.label': 'Store and retrieve files from many subfolders for performance',
'cfg.purge.name': 'Purge Remort',
'cfg.purge.label': 'Purge old data from mort and eyde pages when rebuilding.\nMay reduce RAM usage, tbh haven\'t tested, this is so I can disable it quick',
'cfg.apd_dir.name': 'Append Data Directory',
'cfg.apd_dir.label': 'Path to core server files',
'cfg.mark_dir.name': 'Mark Data Directory',
'cfg.mark_dir.label': 'Path to user marks',
'cfg.res_dir.name': 'Resource Directory',
'cfg.res_dir.label': 'Path to server resources',
'cfg.collapse_desclength.name': 'Collapse Long Descriptions',
'cfg.collapse_desclength.label': 'Descriptions longer than this value will be collapsed until expanded',
'cfg.collapse_linkylength.name': 'Collapse Long Link Lists',
'cfg.collapse_linkylength.label': 'When a post is linked to, or by many posts, how many at most before collpased',
'cfg.allow_data.name': 'Allow /data/*',
'cfg.allow_data.label': 'Enable data access over http, used for tools',
'cfg.show_unparsed.name': 'Show Unparsed',
'cfg.show_unparsed.label': 'Display raw JSON alongside where it is used.',
'cfg.static.name': 'Static',
'cfg.static.label': 'Disable changing marks, updating sets, etc.',
'cfg.static_cfg.name': 'Static Config',
'cfg.static_cfg.label': 'Disable changing this config from the web',
'cfg.allow_pages.name': 'Allow Pages',
'cfg.allow_pages.label': 'Load custom pages from your pages folder',
'cfg.sec_offset.name': 'Seconds Offset',
'cfg.sec_offset.label': 'Used as an offset from midnight when dividing up stats',
'cfg.server_name.name': 'Server Name',
'cfg.server_name.label': 'Changes some text from FADSRV to a name of your choice',
'cfg.server_addr.name': 'Server Address',
'cfg.server_addr.label': 'IP Address, Changes will not be reflected until restart!',
'cfg.server_port.name': 'Server Port',
'cfg.server_port.label': 'Port Number, Changes will not be reflected until restart!',
'cfg.remote_images.name': 'Remote Images',
'cfg.remote_images.label': 'Used to denote a remote image server\nLeave blank to use internal server',
'cfg.homepage_menu.name': 'Homepage Menu',
'cfg.homepage_menu.label': 'Choose which menu should be displayed as home',
'cfg.dropdown_menu.name': 'Dropdown Menu',
'cfg.dropdown_menu.label': 'Choose which menu should drop down\nLeave blank for no dropdown',
'cfg.do_button_align.name': 'Do Mark Button Align',
'cfg.do_button_align.label': 'Show little alignment bars',
'cfg.mark_button_align.name': 'Mark Button Alignment',
'cfg.mark_button_align.label': 'Valid: left, center, right',
'cfg.modify_button_align.name': 'Save Mark Button Alignment',
'cfg.modify_button_align.label': 'Allow chaning settings via those alignment bars',
'cfg.encoding_serve.name': 'Serve Encoding',
'cfg.encoding_serve.label': 'Nerdy, may fix crashes and display issues, partly unresolved.',
'cfg.encoding_write.name': 'Write Encoding',
'cfg.encoding_write.label': 'Nerdy, may fix crashes and display issues, partly unresolved.',
'cfg.all_marks_visible.name': 'All Marks Visible',
'cfg.all_marks_visible.label': 'Show all marks for posts, whether unavailable or not',
'cfg.show_visited_recently.name': 'Show Visited Recently',
'cfg.show_visited_recently.label': 'Adds a temporary mark to things you visited since the last rebuild',
'cfg.ent.building_entries.name': 'Building Entries',
'cfg.ent.building_entries.label': 'Set while the server is busy, prevents some pages loading during that time.',
'cfg.ent.butt_state.name': 'Butt State',
'cfg.ent.butt_state.label': 'Joke option, set to your preference I guess',

'eyde_post_title': '<a class="title" href="/view/{0}/1"><h2>{1}</h2></a>\n<a href="https://www.furaffinity.net/view/{0}/">view fa</a><br>\n',
'stripeytablehead': '<table class="stripy">\n<tr>\n\t<td colspan={}>{}</td>\n</tr>\n',
'pt_items': '<div class="desc tags"><details><summary>{} ({:,} items)</summary>\n{}</details>\n</div><br>\n',
'search_bar': '<input id="searchbar" class="niceinp widebar" placeholder="Search..." oninput="search(false)" />\n',
'error': '<div class="errorpage">\n<div>\n<h2>{}</h2>{}</div><img src="/parrot.svg" alt="Got his fibre, on his way." /></span>\n<br>'
    })
    
    load_global('cfg', {
        'docats': False,# only includes in cats rather than keeping order
        
        'list_count': 15,# users/kewords per page
        'post_count': 25,# posts per page
        'over': 5,# how many posts over the limit a page may extend
        'collapse_desclength': 250,# collapse descriptions longer than this
        "collapse_linkylength": 10,
        
        'allow_data': True,# external data access
        'show_unparsed': False,
        'static': False,# disable changing values
        'static_cfg': False,# disab;e changing cfg with server
        'allow_pages': True,# enable custom pages
        'purge': True,# purge old data from mort and eyde to free up ram
        'sec_offset': 0,
        'lister_buttons': True,
        
        'apd_dir': 'data/',# prepend data files
        'mark_dir': 'data_mark/',
        'res_dir': 'res/',# prepend resource files
        'post_split': True,# better file op performance
        'desc_split': False,
        'image_dir': 'im/',
        'data_dir': 'pm/',
        'server_port': 6970,
        'server_name': 'FADSRV',
        'remote_images': '',
        'encoding_serve': 'utf8',
        'encoding_write': 'utf8',
        'all_marks_visible': False,
        'show_visited_recently': True,
        'skip_bigdata': False,
        'skip_findnew': False,
        
        'homepage_menu': 'menu',
        'dropdown_menu': 'menu',
        'do_button_align': False,
        'mark_button_align': 'center',
        'modify_button_align': True,
        'show_hidden_marks': False,
        'eyde_default_mode': 'full',
        
        'altlinks': {
            'users': [['https://www.furaffinity.net/user/{}/', 'FA Userpage']],
            'folders': [['https//www.furaffinity.net{}', 'FA Folder']]
            },
        
        'altdatsrv': []
        })
    
    load_global('menus', {
        'pages': {
            "menu": {
                "title": "Main Menu",
                "mode": "narrow-icons-flat",
                "buttons": "menu_buttons",
                "icon": [0, 5]
                },
            "browse": {
                "title": "Browse",
                "mode": "narrow-icons-flat",
                "buttons": "mobile_buttons"
                }
            },
        'menu_buttons': [
            { "label": "by User", "href": "users" },
            { "label": "by Tag", "href": "tags" },
            { "label": "Search", "href": "/search" },
            { "label": "Shuffled Users", "href": "shuffle" },
            { "label": "Passed Users", "href": "passed" },
            { "label": "Partially Seen", "href": "partial" },
            { "label": "Queue", "href": "queue" },
            { "label": "Quest", "href": "quest"},
            { "label": "Deactivated", "href": "gone" },
            { "label": "Review", "href": "review" },
            { "label": "Scout", "href": "/scout" },
            { "label": "Sets", "href": "sets" },
            { "label": "Folders", "href": "folders" },
            { "label": "Stats", "href": "/stats" },
            { "label": "Info", "href": "/info" },
            { "label": "Configure", "href": "/config" },
            { "label": "Pages", "href": "/pages" },
            { "label": "All Pages", "href": "/all_pages" }
            ],
        "mobile_buttons": [ 
            { "label": "by User", "href": "users" },
            { "label": "Unread", "href": "unread" },
            { "label": "Quest Browse", "href": "quest" },
            { "label": "Partially Seen", "href": "partial" },
            { "label": "Queue", "href": "queue" },
            { "label": "Passed Users", "href": "passed" },
            { "label": "Shuffled Users", "href": "shuffle" },
            { "label": "Sets", "href": "sets" },
            { "label": "Search", "href": "/search" },
            { "label": "Stats", "href": "/stats" },
            { "label": "Configure", "href": "/config" },
            { "label": "all_pages", "href": "/all_pages" }
            ]
        })
    
    load_global('ent', {
        'building_entries': False,
        
        'built_markedposts': False,
        'built_users': False,
        
        'added_content': False,
        'loaded_apd': False,
        'loaded_apx': False,
        'visited_rebuild': [],
        
        'config_file': 'fadoptions.json',
        'menu_file': 'fadmenus.json',
        'strings_file': 'fadstrings.txt',
        
        'force_datasort': True,
        'resources': [
            'style.css',
            'parrot.svg',
            'icons.svg',
            'mark.js',
            'client.js',
            'chart.js'
            ],
        
        '_kwd': {},
        '_lists': {},
        '_collections': {},
        'reentry_buttons': [
            (' rebuild', 'rebuild', 'Rebuild'),
            ('', 'findnew', 'F'),
            ('', 'rebuild/99', 'D')
            ],
        
        'link_to': {
            'users': '/user/{}/1',
            'tags': '/tag/{}/1',
            'folders': '/folder/{}/1',
            'list': '/list/{}/1',
            'posts': '/view/{}/1',
            'url': '{}'
           },
        
        'builtin': {
            'data': post_data(),
            'profiles': post_profiles()
            },
        'builtin_post': {
            'search': post_search(),
            'collections': post_collections(),
            '_apref': post_apref(),
            '_flag': post__flag(),
            'data': post_data(),
            'profiles': post_profiles()
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
    
    fadcfg = {}
    if os.path.isfile('fadcfg.json'):
        fadcfg = read_json('fadcfg.json')
    
    mobile_path = fadcfg.get('content_path', '.')
    os.chdir(mobile_path)
    
    logging.info(isdocats())
    
    build_entries(reload=3)
    
    logging.info(f'Starting serivce on {cfg["server_addr"]}:{cfg["server_port"]}')
    httpd = ThreadedHTTPServer(
        (cfg['server_addr'], cfg['server_port']),
        fa_req_handler)
    
    x = threading.Thread(target=build_entries, args=(9,))
    x.start()
    
    httpd.serve_forever()
