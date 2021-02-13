from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading
import os
import json
from random import choice, shuffle
from datetime import datetime, timedelta
import math
import urllib
from operator import itemgetter
import html
import re

###############################################################################
# pep8 non-compliant :(

from fad_utils import *

version = '31#2021-02-11'

def loadpages():
    global ent
    
    pages = []
    
    if cfg['allowPages'] and os.path.isdir('pages/'):
        for f in os.listdir('pages/'):
            fn = f.split('.')[0]
            pages.append(fn)
            if f in ent['pagedata'] and not cfg['developer']:
                continue
            
            with open('pages/'+f, 'rb') as fh:
                ent['pagedata'][fn] = fh.read()
                fh.close()
    
    ent['pages'] = pages


def setget(con, postid, retcount=False, onlyin=False):
    ret = []
    add = []
    for d, k, n in setsort(con):
        if k not in ent[con]:continue
        i = ent[con][k]
        r = (
            k,
            len(i['items']),
            postid in i['items'],
            i.get('lock', False)
            )
        if r[2]:add.append(r)
        else:ret.append(r)
    
    if retcount:return len(add)
    if onlyin:return add
    
    return (ret + add)[::-1]


def setsort(con, ret=True, rebuild=False):
    consort = con + 'sort'
    if  ent.get(consort, 0) == 0 or rebuild:
        ent[consort] = sorted(
            [(ent[con][x].get('modified', 0), x, n)
             for n, x in enumerate(ent.get(con, {}).keys())
             if x != '//'])
    
    if ret:
        return ent[consort]


def markedposts():
    mark = set()
    exclude = [x for x in prefm.keys()
               if prefm[x].get('for', 'posts') == 'posts'
               and prefm[x].get('excludeMarked', True)]
    
    for x in exclude:
        mark.update(set(pref[x].keys()))
    
    exclude = [x for x in apdmm.keys()
               if apdmm[x].get('for', 'posts') == 'posts'
               and apdmm[x].get('excludeMarked', True)]
    
    for x in exclude:
        print(x)
        if apdmm[x].get('type', 'unknown') == 'collection':
            mark.update(set(dpref[x].keys()))
        else:
            mark.update(set(apdm[x].keys()))

    ent['_marked'] = mark
    return mark


def usersort(docats):
    global ent
    # sort posts to users
    
    users = {}
    allusers = {}
    
    mark = markedposts()
    
    for post in list(apdfa.keys()):
        if post == '' or post == None:continue
        d = apdfa.get(post, {'user': '@badart', 'descwc': -1})
        
        k = d.get('user')
        if k == None:k = '@badart'
        k = k.replace('_', '')
        
        if not k in users:users[k] = []
        users[k].append(post)
    
    for user in list(users.keys()):
        if type(user) != str:
            del user
            continue
        
        sa = [str(x) for x in sorted([int(x) for x in users[user]])]
        if docats:allusers[user] = sa
        users[user] = [x for x in sa if not (docats and x in mark)]
        
        ent['_kwd']['a:'+user] = sa
    
    for m in dprefm:
        if dprefm[m].get('for', 'posts') == 'posts':
            users['@' + m] = list(dpref.get(m, {}).keys())
    
    ent['users'] = users
    if docats:
        ent['_allusers'] = allusers
    else:
        ent['_allusers'] = ent['users']


def kwsort():
    kwd = {}
    kws = set()
    
    for post, data in apdfa.items():
        if len(data['keywords']) == 0:
            data['keywords'] = ['_untagged']
        
        for kw in data['keywords']:
            if kw in kws:
                kwd[kw].append(post)
            else:
                kws.add(kw)
                kwd[kw] = [post]
    
    ent['_kws'] = list(kws)
    return kwd


def make_apd(fn, data):
    if not os.path.isfile(cfg['pp'] + fn):
        print('Creating', fn)
        write_apd(cfg['pp'] + fn, data, {}, 2)


def apd_findnew():
    print('Finding posts to include...')
    made_changes = 0
    fields = ['ext', 'keywords', 'date',
              'title', 'user', 'desclen',
              'descwc', 'folders', 'srcbytes']
    
    if os.path.isdir('put/'):
        for fn in os.listdir('put/'):
            if os.path.isfile('p/'+fn):
                os.remove('p/' + fn)
            
            os.rename('put/'+fn, 'p/'+fn)
            fi = fn.split('_')[0]
            if fi in apdfa:
                del apdfa[fi]
            if fi in apdfadesc:
                del apdfadesc[fi]
    
    c = 0
    descset = set(apdfadesc.keys())
    
    ch_apdfa = {}
    ch_apdfadesc = {}
    ch_apdfafol = {}
    
    output = '\t{:>5,} posts'

    if cfg['doPostSplit']:
        files = []
        for i in range(100):
            i = cfg['image_dir'] + '{:02d}/'.format(i)
            if os.path.isdir(i):
                files += os.listdir(i)
    else:
        files = []
        if os.path.isdir(cfg['image_dir']):
            files = os.listdir(cfg['image_dir'])
    
    for file in files:
        if '.' not in file:
            #print('No ext', file)
            file += '.'
            #continue
        
        postid, postext = file.split('.')
        pd = {**apdfa.get(postid, {})}
        
        add = [x for x in fields
               if not x in pd
               or (x in ['title', 'user'] and pd[x].strip() == '')]
        if not postid in descset:add.append('desc')
        
        if add == []:continue
        c += 1
        if c % 200 == 0:
            print(output.format(c))
        
        made_changes += 1
        if 'ext' in add:
            pd['ext'] = postext
            if add == ['ext']:
                ch_apdfa[postid] = pd
                continue
        
        datafn = cfg['data_dir'] + '{}_desc.html'.format(postid)
        try:
            data = read_filesafe(datafn)
        except UnicodeDecodeError:# prevent strange files messing up
            data = str(read_filesafe(datafn, mode='rb', encoding=None))
        
        if data == '':
            made_changes -= 1
            continue
        
        if 'srcbytes' in add:
            if cfg['doPostSplit']:
            
                pd['srcbytes'] = os.path.getsize(
                    cfg['image_dir'] + '{:02d}/{}'.format(
                        int(postid[-2:]), file))
            else:
                pd['srcbytes'] = os.path.getsize(cfg['image_dir'] + file)
        
        if 'keywords' in add:
            if '@keywords' in data:
                if '<div id="keywords">' in data:# old theme
                    ks = get_prop('<div id="keywords">', data, t='</div>')
                elif '<section class="tags-row">' in data:# new theme
                    ks = get_prop('<section class="tags-row">',
                                  data, t='</section>')
                else:
                    print('Unknown Keywork container', file)
                    made_changes -= 1
                    continue
                
                pd['keywords'] = [x.split('"')[0].lower()
                                  for x in ks.split('@keywords ')[1:]]
            else:
                pd['keywords'] = ['_untagged']
        
        if 'date' in add:
            if 'popup_date">' in data:
                # MMM DDth, CCYY hh:mm AM
                date = get_prop('popup_date">', data, t='</')
                pd['date'] = strdate(date).isoformat()
            else:
                print('Missing date', file)
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
                        ch_apdfafol[folid] = apdfafol[folid]
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
            pd['title'] = html.unescape(get_prop(
                'property="og:title" content="', data))
        
        if 'user' in add:
            pd['user'] = get_prop('property="og:title" content="',
                                  data).split(' ')[-1].lower()
        
        # modern theme
        if '<div class="submission-description user-submitted-links">' in data:
            desc = get_prop(
                '<div class="submission-description user-submitted-links">',
                data, t='</div>').strip()
        
        # pre-2020 theme modern theme?
        elif '<div class="submission-description">' in data:
            desc = get_prop('<div class="submission-description">',
                            data, t='</div>').strip()
        
        # pre-2020 classic theme?
        elif '<td valign="top" align="left" width="70%" class="alt1" style="padding:8px">' in data:
            desc = get_prop('<td valign="top" align="left" width="70%" class="alt1" style="padding:8px">', data, t='</td>')
        
        else:
            print('Unknown description container', file)
            made_changes -= 1
            continue
        
        desc = '"https://www.furaffinity.net/gallery/'.join(
            desc.split('"/user/'))
        desc = '\n'.join([x.strip() for x in desc.split('\\n')])
        desc = '\n'.join([x.strip() for x in desc.split('\n')])
        pd['desclen'] = len(desc)
        pd['descwc'] = len(desc.split(' '))
        
        url = get_prop('"og:url" content="', data)
        urlid = url.split('/')[-2]
        if urlid != postid:
            print(postid, 'doesn\'t match', url)
        
        ch_apdfa[postid] = pd
        ch_apdfadesc[postid] = desc
    
    if made_changes == 0:
        print('No changes found, skipping...')
    
    if c > 0:
        print(output.format(len(ch_apdfa)))
        
        print('Writing apd')
        
        write_apd(cfg['pp'] + 'apdfa', ch_apdfa, {}, 1)
        write_apd(cfg['pp'] + 'apdfadesc', ch_apdfadesc, {}, 1)
        write_apd(cfg['pp'] + 'apdfafol', ch_apdfafol, {}, 1)
        
        for post in ch_apdfa:
            if post in apdfa:
                for key in ch_apdfa[post]:
                    apdfa[post][key] = ch_apdfa[post][key]
            else:
                apdfa[post] = ch_apdfa[post]
        
        for post in ch_apdfadesc:
            apdfadesc[post] = ch_apdfadesc[post]
        
        for fol in ch_apdfafol:
            apdfafol[fol] = ch_apdfafol[fol]
        
        print('Done!')

    if 'descpost' not in xlink:
        make_apd('apx_descpost', {'//': {'type': 'xlink', 'for': 'posts'}})
        load_apx('apx_descpost')
    
    descpost = set(xlink['descpost'])
    
    if 'descuser' not in xlink:
        make_apd('apx_descuser', {'//': {'type': 'xlink', 'for': 'users'}})
        load_apx('apx_descuser')
    
    descuser = set(xlink['descuser'])
    ch_descpost = {}
    ch_descuser = {}
    for postid, desc in apdfadesc.items():
        thispostids = set()
        
        if postid not in descpost:
            if type(desc) != str:continue
            for linky in ['view/', 'full/']:
                if linky in desc:
                    for x in desc.split(linky)[1:]:
                        ogi = ''
                        for c in x.split('"')[0].strip():
                            if c.isdigit():ogi += c
                            else:break
                        
                        thispostids.add(ogi)
            
            ch_descpost[postid] = list(thispostids)
        
        thispostids = set()
        if postid not in descuser:
            me = apdfa.get(postid, {}).get('ext', '@badart')
            if me == 'swf' and cfg['docats']:
                pref['flash'][postid] = 0
            
            # get a string error sometimes idk why
            me = apdfa.get(postid, {}).get('user', '@badart')
            
            for linky in ['user/', 'gallery/', 'scraps/']:
                if linky in desc:
                    for x in desc.split(linky)[1:]:
                        og = x.split('"')[0].lower()
                        
                        if '/' in og:og = og.split('/')[0]
                        if og == me:continue
                        
                        thispostids.add(og)
            
            ch_descuser[postid] = list(thispostids)
    
    if len(ch_descpost) > 0:
        print('Writing descpost')
        write_apd(cfg['pp'] + 'apx_descpost',
                  ch_descpost, xlink['descpost'], 1)
        for post in ch_descpost:
            xlink['descpost'][post] = ch_descpost[post]
    
    if len(ch_descuser) > 0:
        print('Writing descuser')
        write_apd(cfg['pp'] + 'apx_descuser',
                  ch_descuser, xlink['descuser'], 1)
        for post in ch_descuser:
            xlink['descuser'][post] = ch_descuser[post]
    
    return made_changes


def loadts():
    global ent, apdmm, apdm
    
    apdmm['ts'] = {
        "icon": [3, 5],
        "type": "multibutt",
        "values": ["ts"],
        "excludeMarked": False,
        "order": 200,
        "apdm": "ts",
        "disabled": True,
        "hidden": True
        }
    apdm['ts'] = {}
    
    if not os.path.isdir(cfg['image_dir'] + 'ts'):
        print('No ts dir')
        ts = {}
    
    elif os.path.isfile(cfg['image_dir'] + 'ts/apdts'):
        print('Checking ts')
        ts = read_apd(cfg['image_dir'] + 'ts/apdts')
        ch_ts = {}
        for fn in os.listdir(cfg['image_dir'] + 'ts'):
            if not fn.endswith('.txt'): continue
            postid = fn.split('.')[0]
            if postid in ts:continue
            with open(cfg['image_dir'] + 'ts/' + fn, 'rb') as fh:
                words = len(fh.read().split(b' '))
                fh.close()
            
            ch_ts[postid] = {'filename': fn, 'words': words}
        
        if len(ch_ts) > 0:
            print('Adding', len(ch_ts))
            write_apd(cfg['image_dir'] + 'ts/apdts', ch_ts, ts, 2)
            for postid in ch_ts:
                ts[postid] = ch_ts[postid]
    
    else:
        print('Building ts')
        ts = {}
        for fn in os.listdir(cfg['image_dir'] + 'ts'):
            postid = fn.split('.')[0]
            if not postid.isdigit(): continue
            with open(cfg['image_dir'] + 'ts/' + fn, 'rb') as fh:
                words = len(fh.read().split(b' '))
                fh.close()
            
            ts[postid] = {'filename': fn, 'words': words}

        write_apd(cfg['image_dir'] + 'ts/apdts', ts, {}, 2)
    
    ent['_tsinfo'] = ts
    apdm['ts'] = {x: {'ts': 0} for x in ent['_tsinfo']}


def build_entries(rebuild=False):
    global ent, dpref
    global apdfa, apdfadesc, apdfafol
    docats = cfg['docats']
    if ent['building_entries']:
        print('Already building entries! goto /unstuck if this is an error')
        return
    
    ent['building_entries'] = True
    if (ent['built_state'] == 0) == is_mobile:
        load_apd(ent['built_state'] < 1 == is_mobile)
    
    loadpages()
    loadts()
    
    # clear cached data
    for x in ['_lperc', 'setsort', 'by_day'] + ['user'+x for x in pref.keys()]:
        if x in ent:del ent[x]
    
    ent['generated'] = datetime.now()
    print('\nStarted building entries')
    
    cfgload()
    
    ent['_bart'] = {}
    for m in prefm:
        if prefm[m].get('for', 'posts') == 'posts':
            ent['remort'][m] = mort_postmark(m)
        else:
            ent['remort'][m] = mort_mark(m)
    
    for m in apdmm:
        if apdmm[m].get('for', 'posts') == 'posts':
            #print(m, 'posts')
            for v in apdmm[m].get('values', []):
                if v not in ent['remort']:
                    ent['remort'][v] = mort_postamark(m, v)
        else:
            #print(m, 'other')
            for v in apdmm[m].get('values', []):
                if v not in ent['remort']:
                    ent['remort'][v] = mort_amark(m, v)
    
    cfg['remort_buttons'] = []
    for m, v in ent['remort'].items():
        icn = {'label': '<b>{}</b><br><i>{}</i>'.format(m, v.marktype), 'href': m}
        if cfg['purge']:v.purge(rebuild)
        cfg['remort_buttons'].append(icn)
    
    for m, v in ent['eyde'].items():
        icn = {'label': m, 'href': m}
        if cfg['purge']:v.purge(rebuild)
        cfg['remort_buttons'].append(icn)
    
    if rebuild:
        if not cfg['developer']:
            loadpages()
        
        ent['_kwd'] = kwsort()
        
        if cfg['docats']:
            pref['flash'] = {}
        
        print('Processing links')
        
        for user, sa in xlink['descuserback'].items():
            ent['_kwd']['al:'+user] = sa
        
        for post, sa in xlink['descpost'].items():
            ent['_kwd']['linkto:'+post] = sa
        
        for post, sa in xlink['descpostback'].items():
            ent['_kwd']['linkfrom:'+post] = sa
    
    usersort(docats)
    
    ent['ustats'] = {}
    ent['artup'] = {}
    
    ustats = read_apd(cfg['pp'] + 'apduserstats')
    if len(ustats) == 0:
        print('User statistics unavilable')
    
    for k in ustats:
        if k.startswith('@'):continue
        j = k.replace('_', '')
        ent['artup'][j] = ustats.get(k, {}).get('lastPostDate', '2000-01-01')
        ent['ustats'][j] = ustats.get(k, {}).get('posts', .1)

    '''
    # merged pages
    for n in range(1, 6):
        name = '@merge{}'.format(n)
        ent['users'][name] = []
        for user in list(ent['users'].keys()):
            if not user in apdm['passed'] and len(ent['users'][user]) == n:
                ent['users'][name] += ent['users'][user]
    '''
    ent['usersort'] = sorted(ent['users'], key=lambda k: len(ent['users'][k]))
    
    print('{:,} users'.format(len(ent['usersort'])))
    ent['building_entries'] = False
    ent['built_state'] = 2
    print('Ready.')


def serve_image(handle, path):
    spath = '/'.join(path[1:])
    if '?' in spath:
        spath, arg = spath.split('?')
    else:
        arg = ''
    ext = spath.split('.')[-1].lower()
    mode = 'image'
    if ext == 'txt':mode = 'text'
    
    if cfg['doPostSplit']:
        if spath.startswith(cfg['image_dir']):
            if 'ts/' in spath:
                mode = 'text'
            else:
                fid = get_prop('/', spath, '.', -1)
                if fid.isdigit():
                    fol = int(fid[-2:])
                    spath = spath.replace(cfg['image_dir'], cfg['image_dir'] + '{:02d}/'.format(fol))
    
    if len(spath) > 2 and os.path.isfile(spath) and is_safe_path(spath):
        handle.send_response(200)
        if mode == 'text':
            fd = read_file(spath, mode='r', encoding='utf8')
            if 'nl' in arg:
                fd = fd.replace('\n', ' ').replace('  ', ' ')
                fd = fd.replace('. ', '.\n')
            
            if 'noesc' not in arg:
                fd = html.escape(fd)
            
            handle.send_header('Content-type', 'text/plain')
            handle.end_headers()
            handle.wfile.write(s['utf8'])
            
            for line in fd.split('\n'):
                handle.wfile.write(bytes(line+'\n', 'utf8'))
        
        else:
            handle.send_header('Content-type', ctl.get(ext, 'text/plain'))
            handle.end_headers()
            handle.wfile.write(read_file(spath, mode='rb', encoding=None))
    
    elif ext != 'jpg':
        path[-1] = path[-1].replace(spath.split('.')[-1], 'jpg')
        serve_image(handle, path)
    
    else:
        handle.send_response(404)
        handle.send_header('Content-type', 'image/svg+xml')
        handle.end_headers()
        handle.wfile.write(ent['_parrot.svg'])


def serve_error(handle, title, message, head=True):
    if head:
        handle.send_response(404)
        handle.send_header('Content-type', 'text/html')
        handle.end_headers()
    page = s['head'].format(title) + '<div class="errorpage"><div>'
    page += '<h1>{}</h1>{}</div>'.format(title, message)
    page += '<img src="/parrot.svg" alt="Got his fibre, on his way." /></span>\n<br>'
    
    if head:
        handle.wfile.write(bytes(page, 'utf8'))
    else:
        return page


def sequence_items(kind):
    si = ent['_lists'].get(kind, {})
    q = []
    if 'pref' in si:
        q = list(pref[si['pref']].keys())
    
    elif 'ent' in si:
        q = ent.get(si['ent'], [])
    elif 'items' in si:
        q = si['items']
    
    if type(q) == dict:
        q = list(q.keys())
    else:
        if 'i' in si:
            q = [i[si['i']] for i in q]#aye aye aye
        else:
            q = list(q)
    
    return q


def sequence_linker(kind):
    return cfg['link_to'].get(kind, '/{}/1')


def sequence_get(name, kind='users'):
    # overwrite queue nav buttons
    qpos = -1
    
    si = ent['_lists'].get(kind, {})
    
    q = sequence_items(kind)
    hd = sequence_linker(kind)
    
    prev, next = b'', b''
    
    icon = si.get('icon', '?')
    if type(icon) == list:
        ogm = 'iconsheet' + markicon(*icon, m=-24)
        ogm = '<i class="teenyicon {}"></i>'.format(ogm)
    else:
        ogm = icon
    
    if name in q:
        qpos = q.index(name)
        prev = bytes(s['nb'].format('&lt; '+ogm, hd.format(q[qpos-1]), ''), 'utf8')
        
        next = bytes(s['nb'].format(ogm+' &gt;', hd.format(q[(qpos+1)%len(q)]), ''), 'utf8')
    
    return (prev, next)


def page_count(flen, index_id, pc=''):
    if type(pc) != int:pc = cfg['postcount']
    last_page = max(math.ceil(flen / pc), 1)
    
    sa = (index_id - 1) * pc
    ea = index_id * pc
    if 0 < flen % pc <= cfg['over']:
        last_page = max(last_page - 1, 1)
        if index_id == last_page:ea = flen
    
    if index_id < 1:
        index_id += last_page
        if index_id == last_page:ea = flen
    
    return last_page, sa, ea


def listmodepicker(path):
    
    out = ''
    list_mode = 'Full'
    target = 'Thumb'
    
    lm_text = '<a href="/{}">{} mode</a><br>\n'
    if 'full' in path[2:]:
        path[path[2:].index('full')+2] = 'thumb'
    
    elif 'thumb' in path[2:]:
        path[path[2:].index('thumb')+2] = 'full'
        list_mode, target = target, list_mode
    
    else:
        index_id = path[-1]
        path[-1] = target
        path.append(index_id)
    
    return [list_mode.lower(), lm_text.format('/'.join(path), target)]


def user_has_local_percent(user):
    got = len(ent['_allusers'].get(user, ''))
    know = max(ent['ustats'].get(user, 1), got)
    return safe_perc(got, know), got


def markicon(x, y, m=-60):
    return '" style="background-position: {}px {}px;'.format(x*m, y*m)


def amarkt(p, n, b='diy', a=' on', action='aprefMagic(this)', m=-60):
    btnd = apdmm[p]
    btype = btnd.get('type', '?')
    cla = ''
    if btnd.get('hidden'):return ''
    if btnd.get('disabled'):
        action = ''
        cla = 'disabled '
    
    icon = btnd.get('icon', p)
    
    if b == 'diy':
        if btype == 'collection':
            # todo dont't be lazy
            b = [[],[True]][setget(p, n, retcount=True) > 0]
        elif btnd.get('list'):
            b = [[], [p]][apdm[p].get(n) == 0]
        else:
            b = list(apdm[p].get(n, {}).keys())
    
    if len(b) == 0 or (len(b) == 1 and b[0] == 'n/a'):
        b = ''
        pressed = ''
    else:
        b = b[0]
        pressed = 'on '
    
    if b in btnd.get('values', []):
        bp = btnd['values'].index(b)
        if len(btnd.get('valueicon', [])) > bp:
            icon = btnd['valueicon'][bp]

    if btype == 'collection':
        action = 'setsGet(\'{}\', \'{}\')'.format(n, p)
    
    if type(icon) == list:
        c = '<i class="iconsheet ico{} {}" onclick="{}"></i>'.format(m, markicon(*icon, m=m), action)
    
    else:
        c = '<span onclick="{}">{}</span>'.format(action, str(icon))
    
    mt = '<div name="{0}@{1}" class="mbutton {3}">{2}</div>\n'
    
    if btype == 'int':
        c += '<input type="number" class="niceinp" size="1" value="{}">'.format(b)
    
    elif btype == 'list' and 'values' in btnd:
        c += '<select class="niceinp" onchange="{action}">\n'.format(action=action)
        for v in [''] + btnd['values']:
            c += '<option value="{0}" {1}>{0}</option>\n'.format(v, ['', 'selected'][v == b])
        
        c += '</select>'
    
    elif btype == 'multibutt':
        o = '<span name="{0}@{1}">\n'
        for i, v in enumerate(btnd['values']):
            if len(btnd.get('valueicon', [])) > i:
                icon = btnd['valueicon'][i]
            c = '<i class="iconsheet ico{} {}" onclick="{}"></i>'.format(m, markicon(*icon, m=m), action)
            o += mt.format(n, v+'@'+p, c, cla+['', ' on'][v == b])
        
        mt = o + '</span>'
    
    elif btype == 'collection':
        pass
    
    else:
        c += '<input type="text" class="niceinp" size="1" value="{}">'.format(b)
    
    return mt.format(n, p, c, pressed)


def mark_for(kind, thing, wrap=False, m=-60, inset=None):
    out = ''
    
    for p in prefm:
        if prefm[p].get('for', 'posts') != kind:continue
        out += markt(p, thing, m=m)
    
    for p in apdmm:
        if apdmm[p].get('for', 'posts') != kind:continue
        out += amarkt(p, thing, m=m)
    
    if wrap and len(out) > 0:
        out = '<div class="btn abox">\nMarks for <b>{}</b><br>\n{}</div>\n'.format(thing, out)
    else:
        out = '<div class="abox">\n{}</div>\n'.format(out)
    
    return out

def markt(p, n, b='diy', a=' on', action='mark(\'{0}\', \'{1}\')', m=-60):
    c = ''
    
    if prefm[p].get('hidden'):return ''
    if prefm[p].get('disabled'):
        action = ''
        c = 'disabled '
    
    mt = s['markt'].replace('{action}', action)
    icon = prefm[p].get('icon', p)
    if b == 'diy':
        b = n in pref[p]
    
    if type(icon) == list:
        c += 'iconsheet' + ['', a][b] + markicon(*icon, m=m)
        return mt.format(n, p, '', c)
    
    else:
        return mt.format(n, p, icon, c+['', a][b])


def post_things(label, items, itype, me=None, op=None):
    # cleaner link builder for posts
    out = ''
    do_op = False
    if op != None and me != None:
        if me in op:
            pos = op.index(me)
            do_op = True
    
    if not (len(items) < 1 or (len(items) == 1 and me in items)):
        out = '<div class="tags">\n' + label + '<br>\n'
        for i in items:
            ipos = int(i == me)
            if ipos != 1 and do_op and i in op:
                ipos = [2, 3][op.index(i) > pos]
            
            out += create_linktodathing(itype, i, onpage=ipos) + '\n'
        
        out += '</div>\n'
    
    return out


class eyde_base(object):

    def __init__(self, items=[], marktype='', domodes=True):
        self.items = items
        self.marktype = marktype
        self.domodes = domodes
        self.name = ''
        self.title = 'EYDE'
        self.markid = 'MARKIDEORROR'
        self.clear_threshold = 0
        
        self.headtext = ['', '']
    
    def gimme(self, pargs):
        pass
    
    def build_page(self, pargs):
        si = len(self.items)
        index_id = pargs[-1]
        lse = page_count(si, pargs[-1])
        last_page, sa, ea = lse
        
        h, list_mode, nav, si = self.build_page_wrap(pargs, lse)
        
        h += self.build_page_mode(list_mode, lse)
        
        if index_id == last_page and sa < si:
            h += s['all'].format(si, 'file', plu(si))
        
        h += '\n</div><div class="foot">' + str(nav, 'utf8') + '\n<br>'
        return h
    
    def build_page_wrap(self, pargs, lse):
        index_id = pargs[-1]
        pargs = [str(x) for x in pargs]
        last_page, sa, ea = lse
        
        if index_id < 1:
            index_id += last_page
        
        h = s['head'].format(self.title)
        h += s['setlogic']
        
        si = len(self.items)
        last_page, sa, ea = lse
        if self.domodes == True:
            list_mode, wr = listmodepicker(pargs)
        else:
            list_mode, wr = self.do_modes, ''
        
        q = sequence_get(self.title)
        nav = q[0]
        nav += template_nav(self.title, index_id, last_page)
        nav += q[1]
        
        h += '<div class="head">\n' + str(nav, 'utf8') + '</div>\n<div class="container">\n'
        
        h += wr
        h += self.headtext[0]
        h += mark_for(self.marktype, self.markid) + '<br>\n'
        h += self.headtext[1]
        
        h += '{:,} item{}<br>\n'.format(si, plu(si))
        
        return h, list_mode, nav, si
    
    def build_page_mode(self, list_mode, lse):
        last_page, sa, ea = lse
        
        if list_mode == 'full':
            h = self.build_page_full(sa, ea)
        elif list_mode == 'thumb':
            h = self.build_page_thumb(sa, ea)
        else:
            h = 'Unimplemented Mode: {}'.format(list_mode)
        
        return h
    
    def build_page_full(self, sa, ea):
        out = ''
        
        for item in self.items[sa:ea]:
            out += self.build_item_full(item)
        
        return out
    
    def build_item_full(self, file):
        file = str(file)
        data = apdfa.get(file, {'got': False, 'ext': 'png', 'title': 'Unavailable: {}'.format(file), 'user': '@badart'})
        ext = data['ext']
        cat = file_category(ext)
        fnid = '{}.{}'.format(file, ext)
        post_html = ''
        
        l = '/i/{}{}'.format(cfg['image_dir'], fnid)
        if cfg['useRemoteImages'] != False:
            l = cfg['useRemoteImages'].format(fnid)
            
        if cat == 'image':
            post_html = '<img loading="lazy" src="{}" />'.format(l)
        
        elif cat == 'flash':
            post_html = '<embed src="{}" />'.format(l)
        
        elif ext == 'txt':
            post_html = 'Text File: <a href="{}" target="_blank">Click here to open in new tab</a>'.format(l)
            apwc = int(data.get('srcbytes', 0) / 6.5)
            if apwc > 1000000 or apwc < 1:apwc = 0
            post_html += ' Approx ' + wrapme(apwc) + ' words'
        
        if post_html == '':
            post_html = '<a href="{}" target="_blank">Click here to open in new tab</a>'.format(l)
        
        post_html = '<h2>{}</h2></a>\n'.format(data['title']) + post_html + '\n<br>'
        if is_mobile:
            post_html = '<a href="/view/{}/">'.format(file) + post_html
        else:
            post_html = '<a href="https://www.furaffinity.net/view/{}/">'.format(file) + post_html
        
        if data.get('got', True):
            desc = apdfadesc.get(file, '')
            desc_word_count = data['descwc']
            if desc_word_count > cfg['collapse_desclength']:
                post_html += s['ewc'].format('Description', desc_word_count, desc)
            else:
                post_html += '<div class="desc">{}</div>\n'.format(desc)
            
            post_html += post_things('Keywords:', data.get('keywords', ''), 'keywords')
            
            thispostids = xlink['descpost'].get(file, [])
            post_html += post_things('<a href="/keyword/linkto:{}/1">Linking to</a>:'.format(file), thispostids, 'posts', file, self.items)
            
            thisusers = [data['user'].replace('_', '')] + xlink['descuser'].get(file, [])
            post_html += post_things('Users mentioned:', thisusers, 'users', self.name[5:])
            
            thisfolders = data.get('folders', [])
            post_html += post_things('In folders:', thisfolders, 'folders')
        
    
        for col, cd in apdmm.items():
            if cd.get('type', False) != 'collection':continue
            if cd.get('for', 'posts') != 'posts':continue
            
            thissets = setget(col, file, onlyin=True)
            if len(thissets) > 0:
                post_html += '<div class="tags">\n{}:<br>\n'.format(cd['name_plural'])
                for linky in thissets:
                    post_html += create_linktodathing(col, linky[0], con=cd.get('name', col))
                
                post_html += '</div>\n'
        
        thispostids = sorted(xlink['descpostback'].get(file, []))
        post_html += post_things('<a href="/keyword/linkfrom:{}/1">Linked from</a>:'.format(file), thispostids, 'posts', file, self.items)
        
        if file in ent['_tsinfo']:
            ta = ent['_tsinfo'][file]
            post_html += 'Attached document: {:,} words <a href="/i/im/ts/{}" target="_blank">Click here to open in new tab</a>'.format(ta.get('words'), ta.get('filename'))
        
        post_html += '\n<br>\n' + mark_for('posts', file)
        
        if self.name.startswith('user:@'):
            post_html += mark_for('users', data['user'], wrap=True) + '<br>'
        
        return post_html
    
    def build_page_thumb(self, sa, ea):
        out = ''
        
        for item in self.items[sa:ea]:
            out += self.build_item_thumb(item)
        
        return out

    def build_item_thumb(self, file):
        data = apdfa.get(file, {'got': False, 'ext': 'png', 'title': 'Unavailable: {}'.format(file), 'user': '@badart'})
        ext = data['ext']
        cat = file_category(ext)
        fnid = '{}.{}'.format(file, ext)
        
        l = '/i/{}{}'.format(cfg['image_dir'], fnid)
        if cfg['useRemoteImages'] != False:
            l = cfg['useRemoteImages'].format(fnid)
        
        if cat == 'image':post_html = '<img loading="lazy" src="{}" />'.format(l)
        elif cat == 'flash':post_html = '<embed src="{}" />'.format(l)
        else:post_html = '<a href="{}">{} file</a>'.format(l, ext)
        if is_mobile:
            h = '<a href="/view/{}/">'
        else:
            h = 'https://furaffinity.net/view/{}/'
        
        post_html = '\n<span class="tbox"><span class="thumb">\n\t<a class="thumba" href="{}">{}<br>\n\t'.format(h.format(file), data['title']) + post_html + '\n\t</a></span><br>'
        
        post_html += mark_for('posts', file, inset=setget('sets', file, retcount=True)>0)
        post_html += '</span>\n'
        
        return post_html
    
    def purge(self, strength):
        if self.clear_threshold <= strength:
            self.items = []
            self.title = ''
            self.name = ''
            self.headtext = ['', '']

class eyde_view(eyde_base):
    
    def __init__(self, items=[], marktype='', domodes=True):
        super().__init__(items, marktype, domodes)
        self.markid = 'VIEWERROR'
    
    def gimme(self, pargs):
        if len(pargs) < 3:
            pargs.append(1)
        
        if ' ' in str(pargs[1]):
            self.items = pargs[1].split(' ')
        else:
            self.items = [str(pargs[1])]
        
        self.items = [x.split('.')[0] for x in self.items]
        
        si = len(self.items)
        if si == 1:
            self.title = self.items[0]
        else:
            self.title = 'View ({} items)'.format(si)

class eyde_user(eyde_base):

    def __init__(self, items=[], marktype='users', domodes=True):
        super().__init__(items, marktype, domodes)
    
    def gimme(self, pargs):
        if len(pargs) > 1:
            user = str(pargs[1])
        else:
            user = ''
        
        self.name = 'user:' + user
        self.title = user
        self.markid = user
        self.items = ent['users'].get(user, [])
        
        if user.startswith('@'):
            self.marktype = 'users_mark'
            self.headtext = ['', '']
        
        else:
            self.marktype = 'users'
            h = ''
            perc, count = user_has_local_percent(user)
            
            for path, name in cfg['altsrv']:
                path = path.format(user)
                h += '<a href="{}">{}</a><br>'.format(path, name)
            
            if cfg['docats']:
                h += 'Try <a href="/keyword/a:{0}/1">Search keywords: a:{0}</a><br>\n'.format(user)
            
            self.headtext[0] = h +'<br>\n'
            h = ''
            
            h += '<div class="userinfo">\n'
            mr = ent['artup'].get(user, None)
            if mr != None:
                h += 'Last post: {}<br>\n'.format(mr)
            
            if user in dpref.get('passed', {}):
                passdate = dpref['passed'][user]
                h += 'Passed: {}<br>\n'.format(jsdate(passdate).isoformat()[:19])
            
            if user in ent['ustats']:
                h += 'Got {:,} of {:,} posts ({:.02%})'.format(count, ent['ustats'][user], perc)
            
            h += '\n</div>'
            self.headtext[1] = h
        
class eyde_folder(eyde_base):
    
    def __init__(self, items=[], marktype='folders', domodes=True):
        super().__init__(items, marktype, domodes)
    
    def gimme(self, pargs):
        folid = str(pargs[1])
        
        if folid not in apdfafol:
            self.purge(0)
            return
        
        f = apdfafol[folid]
        self.title = f['title']
        self.markid = folid
        self.name = 'folder:' + folid
        self.items = f['items']
        if 'sortid' in pargs:
            self.items = sorted([int(x) for x in self.items])
            self.items = [str(x) for x in self.items]
        
        got = len(self.items)
        know = max(got, f['count'])
        
        h = '<script>\nvar defaultSetName = "{}";\nvar posts = [ '.format(f['title'].replace('"', '\\"'))
        for i in self.items:
            h += '\n\t"{}",'.format(i)
        
        h = h[:-1] + '\n];\n</script>\n'
        
        icn = 'iconsheet' + markicon(1, 3, m=-60)
        h += s['markt'].replace('{action}', 'folderToSet(\'Name the new Set\')').format('create', folid, '', icn)
        
        h += '<div class="userinfo">Folder #{}<br>\n'.format(folid)
        perc = safe_perc(got, know)
        h += 'Got {:,} of {:,} posts ({:.02%})'.format(got, know, perc)
        h += '</div>\n'
        self.headtext[1] = h
        
        h = ''
        if not is_mobile:
            h += '<a href="//furaffinity.net{}">FA Folder</a><br>'.format(f['path'])
        
        self.headtext[0] = h
    
    def build_page(self, pargs):
        if self.title == '':
            return serve_error('', 'No folder id {}'.format(pargs[1]), '<a href="/folders/">&lt; Back to Folders</a>', head=False)
        else:
            if pargs[-1] == pargs[1]:pargs.append(1)
            return super().build_page(pargs)

class eyde_set(eyde_base):
    
    def __init__(self, con='sets', items=[], marktype='sets', domodes=True, lister='/sets/1'):
        super().__init__(items, marktype, domodes)
        self.con = con
        self.lister = lister
    
    def gimme(self, pargs):
        name = str(pargs[1])
        
        if  name.startswith('id.'):# if set is named something illegal
            name = name[3:]
            if name.isdigit():
                name = int(name)
                for d, k, n in setsort(self.con, rebuild=True):
                    if name == n:
                        name = k.lower()
                        break
        
        for n in ent.get(self.con, {}).keys():
            if n.lower() == name:
                name = n
                break
        else:
            self.purge(0)
            return
        
        prefr = set(dpref.get('read', {}))
        
        self.title = name
        self.markid = name
        self.name = 'set:' + name
        self.items = ent[self.con][name]['items']
        si = len(self.items)
        
        unread = 0
        for p in self.items:
            if p not in prefr:
                unread += 1
        
        lock = ['', ' on'][ent[self.con][name].get('lock', False)]
        escname = re.sub(r'\W+', '', name.lower())
        icn = 'iconsheet' + lock + markicon(5, 0, m=-60)
        h = s['markt'].replace('{action}', 'setsProp(\'{0}\', \'{1}\')').format(escname, 'lock', '', icn)
        h += s['markt'].replace('{action}', 'setDelete(\'{0}\')').format(escname, 'delete', 'Delete', 'disabled')
        
        h += '<script>\nvar posts = [ '
        for i in self.items:
            h += '\n\t"{}",'.format(i)
        
        h = h[:-1] + '\n];\nvar con = "{}";</script>\n'.format(self.con)
        
        h += '''<div name="set{}@readma" class="mbutton"><i class="iconsheet ico-60 " style="background-position: -180px -180px;" onclick="apdmAllRead(this)"></i><select class="niceinp" onchange="apdmAllRead(this)">
<option value=""></option>
<option value="no-text">no-text</option>
<option value="unread">unread</option>
<option value="read">read</option>
<option value="setur">setur</option>
</select></div>'''.format(name)
        
        h += '<br>\n'
        if unread > 0:
            h += '{:,} unread - '.format(unread)
        else:
            h += 'All read - '
        
        self.headtext[1] = h
    
    def build_page(self, pargs):
        if self.title == '':
            return serve_error('', 'No collection named {}'.format(pargs[1]), '<a href="{}">&lt; Back to {}</a>'.format(self.lister, self.con), head=False)
        else:
            return super().build_page(pargs)

class eyde_keyword(eyde_base):
    
    def __init__(self, items=[], marktype='sets', domodes=True):
        super().__init__(items, marktype, domodes)
    
    def gimme(self, pargs):
        keyword = str(pargs[1])
        
        if keyword == self.name:
            return
        
        self.name = 'kw:' + keyword
        
        if ' ' in keyword:keywords = keyword.split(' ')
        else:keywords = [keyword]
        
        args = []
        excl = []
        doerror = False
        bad = []
        two = list(keywords)
        for kw in list(keywords):
            if kw.startswith('@'):
                args.append(kw)
                keywords.remove(kw)
            
            elif kw.startswith('!'):
                if kw[1:] in ent['_kwd']:
                    excl.append(kw[1:])
                keywords.remove(kw)
            
            elif kw not in ent['_kwd']:
                doerror = True
                bad.append(kw)
                two.remove(kw)
        
        if doerror:
            self.purge(0)
            self.headtext = ['No posts tagged {}'.format(bad[0]), '<a href="/keyword/{}/1">Try {}?</a>'.format('%20'.join(two), ' '.join(two))]
            return
    
        del bad, two
        self.title = 'kw {}'.format(keyword.replace('%20', ' '))
        
        if len(keywords) == 0:self.items = list(apdfa.keys())
        else:self.items = ent['_kwd'].get(keywords[0], [])
        
        for kw in excl:
            kws = set(ent['_kwd'].get(kw, []))
            self.items = [f for f in self.items if f not in kws]
        
        for kw in keywords[1:]:
            kws = set(ent['_kwd'].get(kw, []))
            self.items = [f for f in self.items if f in kws]
        
        if '@unmarked' in args:
            seen = set()
            for k in pref:
                if '@'+k not in args:
                    seen |= set(pref[k])
            for k in apdm:
                if '@'+k not in args:
                    seen |= set(apdm[k])
            for k in dpref:
                if '@'+k not in args:
                    seen |= set(dpref[k])
            
            self.items = [f for f in self.items if f not in seen]
        
        setstrip = {}
        wdytstrip = {}
        setswithin = []
        wdytwithin = []
        
        for k in args:
            doin = not k.startswith('@!')
            k = k[2-int(doin):]
            if ':' not in k: continue

            if k.startswith('set'):
                setid = k[4:]
                if setstrip == {}:
                    for i in ent['sets']:
                        setstrip[re.sub(r"[^A-Za-z]+", '', i.lower())] = i
                
                if setid.startswith('d:'):
                    setid = setid[2:]
                    if setid.isdigit():
                        setid = int(setid)
                        for d, k, n in setsort('sets'):
                            if setid == n:
                                setswithin.append((k, doin))
                                break
                
                    del setid
                else:
                    for i in setstrip:
                        if setid == i:
                            setswithin.append((setstrip[i], doin))
                            break
            
            elif k.startswith('wdyt'):
                setid = k[5:]
                if wdytstrip == {}:
                    for i in ent['wdyt']:
                        wdytstrip[re.sub(r"[^A-Za-z]+", '', i.lower())] = i
                
                if setid.startswith('d:'):
                    setid = setid[2:]
                    if setid.isdigit():
                        setid = int(setid)
                        for d, k, n in setsort('wdyt'):
                            if setid == n:
                                wdytwithin.append((k, doin))
                                break
                
                    del setid
                else:
                    for i in wdytstrip:
                        if setid == i:
                            wdytwithin.append((wdytstrip[i], doin))
                            break
        
        for setname, doin in setswithin:
            kws = set(ent['sets'][setname]['items'])
            self.items = [f for f in self.items if (f in kws) == doin]
        
        for setname, doin in wdytwithin:
            kws = set(ent['wdyt'][setname]['items'])
            self.items = [f for f in self.items if (f in kws) == doin]
        
        for k in pref.keys():
            
            if '@'+k in args:mmode = True
            elif '@!'+k in args:mmode = False
            else:continue
            
            seen = set(pref[k].keys())
            self.items = [f for f in self.items if (f in seen) == mmode]
        
        for k in dpref.keys():
            
            if '@'+k in args:mmode = True
            elif '@!'+k in args:mmode = False
            else:continue
            
            seen = set(dpref[k].keys())
            self.items = [f for f in self.items if (f in seen) == mmode]
        
        for k in apdmm.keys():
            
            if '@'+k in args:mmode = True
            elif '@!'+k in args:mmode = False
            else:continue
            
            seen = set(apdm[k].keys())
            self.items = [f for f in self.items if (f in seen) == mmode]
        
        kwrange = []
        for k in args:
            if k.startswith('@wc:'):
                if '-' in k:
                    for p in k[4:].split('-'):
                        if p.isdigit():
                            kwrange.append(int(p))
                elif k[4:].isdigit():
                    kwrange = [int(k[4:])]
                    kwrange.append(kwrange[-1]+100)
                else:
                    break
                
                self.items = [f for f in self.items if kwrange[0] <= apdfa.get(f, {'descwc': -1})['descwc'] < kwrange[1]]
                break

        sortme = True
        if '@sort:user' in args:k, d, r = 'user', '_badart', False
        elif '@sort:new' in args:k, d, r = 'date', '0', True
        elif '@sort:title' in args:k, d, r = 'title', '_', False
        elif '@sort:wc' in args:k, d, r = 'descwc', 0, False
        elif '@sort:bytes' in args:k, d, r = 'srcbytes', 0, False
        elif '@sort:faves' in args:k, d, r = 'faves', 0, False
        elif '@sort:views' in args:k, d, r = 'views', 0, False
        elif '@nosort' in args:sortme = False
        else:k, d, r = 'date', '0', False
        
        if '@reversed' in args:r = not r
        if sortme:
            self.items = sorted([(apdfa.get(x, {k: d})[k], x) for x in self.items], reverse=r)
            self.items = [x for d, x in self.items]
        
        thing = ''
        if len(keywords) > 0:thing = keywords[0]

        h = ''
        m = ''
        for x in keywords+args:
            if x.startswith('@'):
                h += x + '<br>'
            elif x.startswith('a:') or x.startswith('al:'):
                h += mark_for('users', x.split(':')[1], wrap=True) + '<br>'
            else:
                h += '<a href="https://www.furaffinity.net/search/@keywords%20{0}">Search FA: {0}</a><br>'.format(x)
                m += mark_for('keywords', x, wrap=True)
        h += m
        del m
        
        if '@unmarked' not in args:
            h += '<br><a href="/keyword/{} @unmarked">@unmarked</a>\n'.format(pargs[1])
        
        self.headtext = [h, '<br>']


def serve_eyde(handle, path):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    
    index_id = path[-1]
    mode = path[0]
    mo = ent['eyde'][mode]
    mo.gimme(path)
    
    handle.wfile.write(bytes(mo.build_page(path), 'utf8'))


def apdmv(m, i):# hack why did i do this
    if apdmm[m].get('list', False):
        return [None, m][apdm[m].get(i) == 0]
    else:
        return (list(apdm[m].get(i, {}).keys()) + [None])[0]


def iconlist(di, thing):
    pgm = ''
    
    for name, icon, ext, cssc in di:
        if type(icon) == list:
            c = 'iconsheet' + cssc + markicon(*icon, m=-24)
            pgm += '<i name="{}@ico.{}" class="teenyicon {}"></i>'.format(thing, name, c)
        else:
            pgm += ' {}'.format(icon)

        if ext == '':continue
        pgm += '{} '.format(ext)
    
    return pgm


def create_linktodathing(kind, thing, onpage=False, retmode='full', con=None):
    pi = []
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
    for m in prefm:
        if prefm[m].get('for', 'posts') != kind:continue
        if thing not in pref[m]:continue
        dis = ['', ' disabled'][prefm[m].get('disabled', False)]
        
        di.append([m, prefm[m].get('icon', m), '', dis])
    
    for m in apdmm:
        btnd = apdmm[m]
        if btnd.get('for', 'posts') != kind:continue
        if btnd.get('type', False) == 'collection':continue
        v = apdmv(m, thing)
        if v == None:continue
        if v == 'n/a':continue
        
        dis = ['', ' disabled'][btnd.get('disabled', False)]
        
        icon = [m, btnd.get('icon', m), '{})'.format(v), dis]
        
        if v in btnd.get('values', []):
            bp = btnd['values'].index(v)
            if len(btnd.get('valueicon', [])) > bp:
                icon = [m, btnd['valueicon'][bp], '', dis]
            elif len(btnd['values']) == 1:
                icon[2] = ''
        
        di.append(icon)
    
    linkdes = thing
    if con == None:
        href = sequence_linker(kind)
    else:
        href = '/{}/'.format(con.lower()) + '{}/1'
        if ent[kind][thing].get('lock', False):
            pi.append(['locked', [5, 0], '', ''])
    
    if kind == 'users':
        if thing in ent['_allusers']:
            got = len(ent['_allusers'][thing])
            l8r = ent['ustats'].get(thing, '?')
            v = wrapme(got, f=' {:,}') + wrapme(l8r, ' ({:,})')
            if cfg['docats']:
                uns = len(ent['users'].get(thing, ''))
                if uns != got:
                    v = wrapme(uns, f=' {:,} ') + wrapme(got) + wrapme(l8r, ' ({:,})')
            linkdes += v
        
        else:
            pi.append(['notgot', [3, 4], '', ''])
    
    
    elif kind == 'posts':
        if thing not in apdfa:
            pi.append(['notgot', [3, 4], '', ''])
    
    elif kind == 'folders':
        linkdes = apdfafol.get(thing, {'title': 'Folder '+thing})['title']
    
    if href == '/{}/1':
        print('what?', kind, thing)
    
    if retmode == 'markonly':
        return iconlist(pi + di, thing)
    
    href = href.format(thing)
    return '<a href="{}">{} {} {}</a>'.format(href, iconlist(pi, thing), linkdes, iconlist(di, thing))


def template_nav(title, index, last):
    nav = ''
    #last = max(last, 1)
    if 1 < index <= last:nav += s['nb'].format('&lt;', index-1, '')
    elif index != last:nav += s['nb'].format('&gt;|', last, '')
    
    nav += '<h2 class="btn wide">' + ['{} - {}', '{}'][index==last and last==1].format(title, index) + '</h2>\n'
    
    if last <= index and index != 1:nav += s['nb'].format('|&lt;', 1, '')
    elif index != last:nav += s['nb'].format('&gt;', index+1, '')
    
    return bytes(nav, 'utf8')


def prefart(p, c):
    items = ent['_bart'].get(p, 0)
    if items == 0:
        userc = {}
        for file in c.get(p, []):
            if file not in apdfa:continue
            user = apdfa[file]['user']
            if user in userc.keys():userc[user] += 1
            else:userc[user] = 1
        
        items = list(userc.items())
        ent['_bart'][p] = items
    
    return items


class mort_base(object):

    def __init__(self, marktype='users', title='Users', link='/user/{}/1', icon=[0, 0]):
        self.marktype = marktype
        self.link = link
        if icon == None:icon = [9, 9]
        self.title = title
        self.icon = icon

        self.items = []
        self.iteminf = [None, None, None]
        self.datas = []
        self.clear_threshold = 0
        self.before_items = ''
        self.hide_empty = self.marktype == 'users'
    
    def gimme(self, pargs):
        self.items = ent['usersort']
        self.datas = ent['users']
    
    def purge(self, strength):
        if self.clear_threshold <= strength:
            self.items = []
            self.datas = []
    
    def build_page(self, pargs, head=True, text=''):
        index_id = pargs[-1]
        items = self.items
        
        if len(items) > 0 and type(items[0]) != tuple:
            items = [(i, 0) for i in items]
        
        pf = str(pargs[1]).split(' ')
        
        for m, d in prefm.items():
            if d.get('for', 'posts') != self.marktype:continue
            
            if '@' + m in pf:mm = True
            elif '@!' + m in pf:mm = False
            else:continue
            mset = set(pref[m].keys())
            items = [i for i in items if (i[0] in mset) == mm]
        
        for m, d in apdmm.items():
            if d.get('for', 'posts') != self.marktype:continue
            
            if d.get('type', 'idk') in ['multibutt', 'list']:
                for v in d.get('values'):
                    if '@' + v in pf:mm = True
                    elif '@!' + v in pf:mm = False
                    else:continue
                    mset = set(dpref[v].keys())
                    items = [i for i in items if (i[0] in mset) == mm]
        
        mincount = 'c' in pf
        i2 = []
        for i in items:
            t = i
            if type(i) in [tuple, list]:t = i[0]
            
            d = self.datas.get(t, '')
            if type(d) != int:d = len(d)
            i2.append(list(i) + [d])
        
        items = i2
        del i2
        
        cull = self.hide_empty
        for x in pf:
            if x == '0':
                cull = False
            elif x == 'c':
                cull = True
            
            elif '>' in x:
                cull = False
                x = x.split('>')
                if len(x) < 2:continue
                gt = 0
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
                
                if pr == 11:# 'l'
                    items = [i for i in items if lt > ent['ustats'].get(i[0], .1) > gt]
                else:
                    items = [i for i in items if lt > i[pr] > gt]
        
        if cull:
            items = [i for i in items if i[2] > 0]
        
        
        if 'count' in pf:
            items = sorted([[len(self.datas.get(i[0],[]))] + list(i) for i in items])
            items = [tuple(x[1:]) for x in items if x[0] >= mincount]
        
        elif 'ustats' in pf:
            items = sorted([[ent['ustats'].get(i[0], -1)] + list(i) for i in items])
            items = [tuple(x[1:]) for x in items if x[0] >= mincount]
        
        else:
            for x in range(5):
                if 'p'+str(x) in pf:
                    items = sorted([[i[x]] + list(i) for i in items])
                    items = [tuple(x[1:]) for x in items]
                    break
            
        if 'reversed' in pf:
            items = list(reversed(items))
        
        mode = pargs[0]
        if mode != 'list':# nothing good would come from that
            seq = {'query': '/'+'/'.join([str(x) for x in pargs]), 'icon': self.icon}
            seq['items'] = []
            for i in items:
                if type(i) in [tuple, list]:seq['items'].append(i[0])
                else:seq['items'].append(i)
            
            ent['_lists'][self.marktype] = seq
        
        count = len(items)
        last_page, sa, ea = page_count(count, index_id, pc=cfg['listcount'])
        if index_id < 1:
            index_id += last_page
        
        nav = template_nav(self.title, index_id, last_page)
        
        h = ''
        if head:
            h += s['head'].format(self.title)
            h += '<div class="head">\n' + str(nav, 'utf8') + '</div>\n'
        
        h += '<div class="container list">\n'
        h += text
        h += '<p>{:,} items</p>\n'.format(count)
        
        if mode == 'list':
            if self.query != None:
                h += '<p>Query: <a href="{0}">{0}</a></p>\n'.format(self.query)
            if self.message != None:
                h += '<p>{}</p>\n'.format(self.message)
        else:
            h += self.before_items
        
        for i in items[sa:ea]:
            if type(i) in [list, tuple]:
                item = i[0]
                
            else:
                item = i
            
            h += self.build_item(i, self.datas.get(item, None), mode)
        
        h += '\n</div><div class="foot">' + str(nav, 'utf8') + '\n<br>'
        
        if mode == 'shuffle':
            h += '<a class="btn wide on" onclick="postReload(\'/reshuffle\', \'\')">Shuffle</a>\n<br>'
        
        return h
    
    def build_label(self, i, data, mode):
        if type(i) in [tuple, list]:item = i[0]
        else:item = i
        
        if self.marktype == 'usersets':
            mdata = []
            for d in data:
                mdata += ent['_allusers'].get(d, [])
        else:
            mdata = data
        
        f = pick_thumb(mdata)
        l = '/t/{}{}'.format(cfg['image_dir'], f)
        if cfg['useRemoteImages'] != False:
            l = cfg['useRemoteImages'].format(f)
        
        label = '<img loading="lazy" src="{}" /><br>'.format(l)
        label = '<div class="overicn">' + create_linktodathing(self.marktype, item, retmode='markonly') + '</div>' + label
        
        if type(data) != int:data = len(data)
        labelt = [item, '-', wrapme(data)]
        
        if self.marktype == 'users':
            labelt.append(wrapme(ent['ustats'].get(item, '?'), f='({:,})'))
        
        for pos, inf in enumerate(self.iteminf):
            if inf == None or pos >= len(i):continue
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
        
        h = '<!-- {} -->\n'.format(i)
        
        if data == None:
            print(item, 'no data')
            data = []
        
        artm = []#.join([x for x in artmark if item in pref[x]])
        
        for m, d in prefm.items():
            if d.get('for', 'posts') != self.marktype:continue
            
            if item in pref[m]:
                artm.append(m)
        
        for m, d in apdmm.items():
            if d.get('for', 'posts') != self.marktype:continue
            
            if d.get('type', 'idk') in ['multibutt', 'list']:
                for v in d.get('values', []):
                    if item in dpref.get(v, []):
                        artm.append(v)
        
        artm = ' '.join(artm)
        
        if mode == 'sets' and self.readsets.get(item, 0) == 0:
            artm += ' passed'
        
        h += s['thumb'].format(self.link.format(item), self.build_label(i, data, mode), ' '+artm)
        
        return h

class mort_keywords(mort_base):
    
    def __init__(self, marktype='keywords', title='Keywords', link='/keyword/{}/1', icon=[1, 0]):
        super().__init__(marktype, title, link, icon)
    
    def gimme(self, pargs):
        self.items = ent['_kws']
        self.datas = ent['_kwd']

class mort_shuffle(mort_base):

    def __init__(self, marktype='users', title='Shuffle', link='/user/{}/1', icon=[3, 0]):
        super().__init__(marktype, title, link, icon)
        self.clear_threshold = 2
    
    def gimme(self, pargs):
        self.datas = ent['users']
        if self.items == []:
            self.items = [x for x in ent['usersort']]
            shuffle(self.items)

class mort_list(mort_base):
    
    def __init__(self, marktype='', title='List', link='/{}/1', icon=[3, 5]):
        super().__init__(marktype, title, link, icon)
    
    def gimme(self, args):
        if len(args) < 2:
            mimic = 1
        else:
            mimic = args[1]
        
        self.items = []
        self.datas = {}
        self.message = None
        self.query = None
        
        if mimic in ent['_lists']:
            self.marktype = mimic
            self.link = sequence_linker(mimic)
            self.items = sequence_items(mimic)
            if 'query' in ent['_lists'][mimic]:
                self.query = ent['_lists'][mimic]['query']
            
            if mimic == 'users':
                self.datas = ent['users']
            elif mimic == 'keywords':
                self.datas = ent['_kwd']
            else:
                self.message = 'Too much work rn, you\'ll probably find a better solution by the morning :)'
        
        elif type(mimic) == int:# probably index id idc
            #get meta
            self.marktype = 'list'
            self.message = 'bodge i may like'
            self.link = '/list/{}/1'
            self.items = list(ent['_lists'].keys())
            self.datas = {k: len(sequence_items(k)) for k in self.items}
        
        else:
            self.message = 'No sequence for {}.'.format(mimic[1])

class mort_mark(mort_base):
    
    def __init__(self, mark):
        self.mark = mark
        title = mark
        self.mdata = prefm[mark]
        marktype = self.mdata.get('for', 'posts')
        icon = self.mdata.get('icon', self.mark)
        link = sequence_linker(marktype)
        
        super().__init__(marktype, title, link, icon)
        self.iteminf[1] = ['date', '<br>{}']
    
    def gimme(self, pargs):
        if self.marktype == 'keywords':
            self.datas = ent['_kwd']
        
        elif self.marktype == 'users':
            self.datas = ent['users']
        
        elif self.marktype == 'sets':
            self.datas = {}
            for d, k, n in setsort('sets', rebuild=True):
                self.datas[k] = ent['sets'][k]['items']
        
        elif self.marktype == 'folders':
            folsort = ent.get('folsort', [])
            if folsort == []:
                folsort = sorted([int(x) for x in apdfafol.keys()])
                folsort = [str(x) for x in folsort]
                ent['folsort'] = folsort
            
            self.datas = {}
            for k in folsort:
                i = apdfafol[k]['items']
                self.datas[k] = i
        
        else:
            self.datas = {}
        
        self.items = []
        for pname, pdate in pref[self.mark].items():
            self.items.append((pname, pdate))

class mort_amark(mort_base):
    
    def __init__(self, mark, val):
        self.mark = mark
        title = mark
        self.val = val
        self.mdata = apdmm[mark]
        marktype = self.mdata.get('for', 'posts')
        icon = self.mdata.get('icon', self.mark)
        bp = self.mdata['values'].index(val)
        
        if len(self.mdata.get('valueicon', [])) > bp:
            icon = self.mdata['valueicon'][bp]
        
        link = sequence_linker(marktype)
        
        super().__init__(marktype, title, link, icon)
        
        if self.marktype == 'folders':
            self.iteminf[0] = ['str', '<br>id {}']
            self.iteminf[2] = ['replace', 0]
        
        self.iteminf[1] = ['date', '<br>{}']
    
    def gimme(self, pargs):
        if self.marktype == 'keywords':
            self.datas = ent['_kwd']
        
        elif self.marktype == 'users':
            self.datas = ent['users']
        
        elif self.marktype == 'sets':
            self.datas = {}
            for d, k, n in setsort('sets', rebuild=True):
                self.datas[k] = ent['sets'][k]['items']
        
        elif self.marktype == 'folders':
            folsort = ent.get('folsort', [])
            if folsort == []:
                folsort = sorted([int(x) for x in apdfafol.keys()])
                folsort = [str(x) for x in folsort]
                ent['folsort'] = folsort
            
            self.datas = {}
            for k in folsort:
                i = apdfafol[k]['items']
                self.datas[k] = i
        
        else:
            self.datas = {}

        if self.items == []:
            self.items = []
            for pname, pdate in dpref.get(self.val, {}).items():
                if self.marktype == 'folders':
                    d = apdfafol.get(pname, {})
                    self.items.append((
                        pname,
                        len(d.get('items', [])),
                        d.get('title', pname)))
                else:
                    self.items.append((pdate, pname))
            
            if self.marktype != 'folders':
                self.items = [(n, d) for d, n in sorted(self.items)]

class mort_postmark(mort_mark):
    
    def __init__(self, mark):
        super().__init__(mark)
        self.marktype = 'users'
        self.link = '/user/{}/1'
        self.iteminf[1] = ['int', '<br>{:,} ' + mark]
    
    def gimme(self, pargs):
        self.items = prefart(self.mark, pref)
        self.datas = ent['users']
        for i in self.items:
            if i[0] not in self.datas:
                self.datas[i[0]] = []

class mort_postamark(mort_amark):
    
    def __init__(self, mark, val):
        super().__init__(mark, val)
        self.val = val
        self.iteminf[1] = ['int', '<br>{:,} ' + val]
        self.marktype = 'users'
        self.link = '/keyword/@' + val + ' a:{}/1'
    
    def gimme(self, pargs):
        self.items = prefart(self.val, dpref)
        self.datas = ent['users']
        
        if 'user' in str(pargs[1]):
            self.link = '/user/{}/1'
        else:
            self.link = '/keyword/@' + self.val + ' a:{}/1'
        
        for i in self.items:
            if i[0] not in self.datas:
                self.datas[i[0]] = []

class mort_partial(mort_base):
    
    def __init__(self, marktype='users', title='Partial', link='/user/{}/1', icon=[0, 1]):
        super().__init__(marktype, title, link, icon)
        self.iteminf[1] = ['int', '- {:.01%}']
    
    def gimme(self, pargs):
        global pref
        self.datas = ent['users']
        if self.items == []:
            fprefs = ent['_marked']
            
            userc = {}
            for file in fprefs:
                if file not in apdfa:continue
                user = apdfa[file].get('user', '@badart')
                if user in userc.keys():userc[user] += 1
                else:userc[user] = 1
            
            userp = {}
            for user in userc.keys():
                if user not in ent['users']:continue
                perc = userc[user] / max(1, len(ent['_allusers'].get(user, '')))
                if perc < 1:userp[user] = perc
            
            self.items = sorted(userp.items(), key=itemgetter(1), reverse=True)
            #pref['part'] = {x: y for x, y in self.items}

class mort_gone(mort_base):
    
    def __init__(self, marktype='users', title='Gone', link='/user/{}/1', icon=[5, 0]):
        super().__init__(marktype, title, link, icon)
    
    def gimme(self, pargs):
        self.items = [x for x in ent['usersort'] if ent['ustats'].get(x, .1) == -1]
        self.datas = ent['users']

class mort_activity(mort_base):
    
    def __init__(self, marktype='users', title='Activity', link='/user/{}/1', icon=[2, 2]):
        super().__init__(marktype, title, link, icon)
        self.iteminf[1] = ['str', '<br>{}']
    
    def gimme(self, pargs):
        self.datas = ent['users']
        users = [(d, a) for a, d in ent['artup'].items() if d != '2000-01-01']
        self.items = [(a, d) for d, a in sorted(users)]
        print(pargs)
        try:# try and grab a date
            target = datetime.fromisoformat(pargs[1])
        except:
            target = 0
        
        if target != 0:
            for i, da in enumerate(self.items):# find where it is
                if datetime.fromisoformat(da[1]) >= target:
                    break
            self.items = self.items[i:]

class mort_review(mort_base):
    
    def __init__(self, marktype='users', title='Review', link='/user/{}/1', icon=[6, 1]):
        super().__init__(marktype, title, link, icon)
        self.iteminf[1] = ['int', '<br>{:,} days']
    
    def gimme(self, pargs):
        if True:
            self.items = {}
            for user in dpref.get('passed', {}):
                pd = jsdate(dpref['passed'][user])
                up = datetime.fromisoformat(ent['artup'].get(user, '2000-01-01'))
                if up > pd:
                    self.items[user] = (up-pd).days
            
            self.items = sorted(self.items.items(), key=itemgetter(1), reverse=True)
        
        self.datas = ent['users']

class mort_group(mort_base):
    def __init__(self, con='groups', marktype='users', title='Group', link='/user/{}/1', icon=[9, 9]):
        super().__init__(marktype, title, link, icon)        
        self.con = con
        self.hide_empty = False
    
    def gimme(self, pargs):
        self.title = ""
        self.datas = ent['users']
        name = str(pargs[1])
        
        if  name.startswith('id.'):# if set is named something illegal
            name = name[3:]
            if name.isdigit():
                name = int(name)
                for d, k, n in setsort(self.con):
                    if name == n:
                        name = k.lower()
                        break
        
        for n in ent[self.con].keys():
            if n.lower() == name:
                name = n
                break
        else:
            self.purge(0)
            return
        
        self.title = name
        self.items = [(v, n) for n, v in enumerate(ent[self.con][name]['items'])]
        
        lock = ['', ' on'][ent[self.con][name].get('lock', False)]
        escname = re.sub(r'\W+', '', name.lower())
        icn = 'iconsheet' + lock + markicon(5, 0, m=-60)
        h = s['markt'].replace('{action}', 'setsProp(\'{0}\', \'{1}\')').format(escname, 'lock', '', icn)
        h += s['markt'].replace('{action}', 'setDelete(\'{0}\')').format(escname, 'delete', 'Delete', 'disabled')
        
        h += '<script>\nvar con = "{}";\nvar posts = [ '.format(self.con)
        for i in self.items:
            h += '\n\t"{}",'.format(i[0])
        
        self.before_items = h[:-1] + '\n];\n</script><br>\n'
    
    def build_page(self, pargs, head=True, text=''):
        if self.title == '':
            return serve_error('', 'No group named {}'.format(pargs[1]), '<a href="/groups/1">&lt; Back to Groups</a>', head=False)
        else:
            return super().build_page([pargs[0]] + pargs[2:], head=True, text=text)

class mort_groups(mort_base):
    def __init__(self, con='groups', marktype='usersets', title='Groups', link='/group/{}/1', icon=[6, 5]):
        super().__init__(marktype, title, link, icon)
        self.iteminf[1] = ['date', '<br>{}']
        self.con = con
    
    def gimme(self, pargs):
        self.items = []
        self.datas = {}
        
        for d, k, n in setsort(self.con, rebuild=True):
            self.items.append((k, d, n))
            self.datas[k] = ent[self.con][k]['items']

class mort_sets(mort_groups):
    
    def __init__(self, con='sets', marktype='sets', title='Sets', link='/set/{}/1', icon=[7, 0]):
        super().__init__(con, marktype, title, link, icon)
        self.readsets = {}
        self.rebuildread = True
    
    def gimme(self, pargs):
        super().gimme(pargs)
        
        if self.readsets == [] or self.rebuildread:
            self.readsets = {}
            self.rebuildread = True
            prefr = set(dpref.get('read', {}))
        
            for d, k, n in setsort(self.con):
                self.readsets[k] = 0
                for p in self.datas[k]:
                    if p not in prefr:
                        self.readsets[k] += 1
            
            del prefr
            self.rebuildread = False

        if ' (' in self.title:
            self.title = ' '.join(self.title.split(' ')[:-1])
        
        if 'unread' in str(pargs[1]):
            self.items = [(k, d, n) for k, d, n in self.items if self.readsets.get(k, 0) > 0]
            self.title += ' (Unread)'
        
        elif 'read' in str(pargs[1]):
            self.items = [(k, d, n) for k, d, n in self.items if self.readsets.get(k, 0) == 0]
            self.title += ' (Read)'
        
        elif 'part' in str(pargs[1]):
            self.items = [(k, d, n) for k, d, n in self.items if 0 < self.readsets.get(k, 0) < len(self.datas[k])]
            self.title += ' (Partial)'
        
        self.before_items = '<div class="userinfo">'
        for m in ['Unread', 'Read', 'Part']:
            self.before_items += '<a href="/{0}/{1}/1">{1}</a><br>'.format(self.con, m)
        self.before_items += '</div><br>'
    
    def purge(self, strength):
        super().purge(strength)
        
        if self.clear_threshold <= strength:
            self.readsets = {}
            self.rebuildread = True

class mort_folders(mort_base):
    
    def __init__(self, marktype='folders', title='Folders', link='/folder/{}/1', icon=[8, 1]):
        super().__init__(marktype, title, link, icon)
        self.folsort = []
        self.iteminf[0] = ['str', '<br>id {}']
        self.iteminf[2] = ['replace', 0]
    
    def gimme(self, pargs):
        self.items = []
        self.datas = {}
        if self.folsort == []:
            self.folsort = sorted([int(x) for x in apdfafol.keys()])
            self.folsort = [str(x) for x in self.folsort]
        
        for k in self.folsort:
            i = apdfafol[k]['items']
            self.items.append((k, len(i), apdfafol[k]['title']))
            self.datas[k] = i
    
    def purge(self, strength):
        super().purge(strength)
        
        if self.clear_threshold <= strength:
            self.folsort = []

class mort_linkeduser(mort_base):
    def __init__(self, marktype='users', title='Linked Users', link='/keyword/al:{}/1', icon=[2, 5]):
        super().__init__(marktype, title, link, icon)
    
    def gimme(self, pargs):
        self.datas = xlink['descuserback']
        self.items = list(self.datas.keys())


class mort_l8ratio(mort_base):
    def __init__(self, marktype='users', title='L8Ratio', link='/user/{}/1', icon=[9, 9]):
        super().__init__(marktype, title, link, icon)
        self.before_items = '<a href="/l8ratio/reversed%20@!passed/1">Scout</a><br>'
    
    def gimme(self, pargs):
        self.datas = ent['_allusers']
        self.items = user_lperc()


class mort_l8rscout(mort_base):
    def __init__(self, marktype='users', title='L8R Scout', link='/user/{}/1', icon=[9, 9]):
        super().__init__(marktype, title, link, icon)
        self.before_items = '<a href="/l8rscout/@!passed%20l>1/1">Scout</a><br>'
    
    def gimme(self, pargs):
        self.datas = ent['_allusers']
        self.items = {x: ent['ustats'].get(x, .1) - len(y) for x, y in self.datas.items()}
        self.items = sorted(self.items.items(), key=itemgetter(1))


def serve_remort(handle, path, text='', head=True):
    if head:
        handle.send_response(200)
        handle.send_header('Content-type', 'text/html')
        handle.end_headers()
        handle.wfile.write(s['utf8'])
    
    index_id = path[-1]
    mode = path[0]
    mo = ent['remort'][mode]
    if cfg['developer']:print(type(mo))
    mo.gimme(path)
    
    handle.wfile.write(bytes(mo.build_page(path, head=head, text=text), 'utf8'))


def pick_thumb(posts):
    if type(posts) == int:posts = []#hack
    for i in posts:
        d = apdfa.get(i, {'ext': 'error'})
        if file_category(d['ext']) == 'image':
            return i + '.'+d['ext']
    
    return 'parrot.svg'


def user_lperc(overwrite=False):
    global ent
    lperc = ent.get('_lperc', {})
    if len(lperc) == 0 or overwrite:
        lperc = {}
        
        for user, posts in ent['_allusers'].items():
            al = ent['ustats'].get(user, .1)
            #if al == .1:print(user)
            if user.startswith('@') or al == -1:continue
            lperc[user] = len(posts) / max(al, .1)
        
        lperc = sorted(lperc.items(), key=itemgetter(1))
        ent['_lperc'] = lperc
    
    return lperc


def serve_scout(handle, path):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    
    index_id = path[-1]
    
    passed = set(dpref.get('passed', {}).keys())
    l8r = set(ent['ustats'].keys())
    unmarked = sum([1 for x in ent['_allusers'] if not x.startswith('@') and x not in l8r])

    items = user_lperc()

    ifilter = passed
    
    ifdir = False
    items = [x for x in items if (x[0] in ifilter) == ifdir]
    del ifilter
    
    flen = len(items)
    last_page, sa, ea = page_count(flen, index_id, pc=cfg['listcount'])
    
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format('Scout'), 'utf8'))
    
    nav = template_nav('Scout', index_id, last_page)
    handle.wfile.write(b'<div class="head">\n' + nav + b'</div>\n')
    users = ent['usersort']
    
    if ent['ustats'] == {}:
        handle.wfile.write(b'There doesn\'t seem to be any users marked to be seen at a later date.')
        return
    
    handle.wfile.write(b'<h2>By Available/Got (' + bytes(str(flen), 'utf8') + b')</h2>\n<div class="container list">\n')
    
    count = {x: ent['ustats'].get(x, .1) - len(ent['_allusers'].get(x, [])) for x, y in items}
    count = sorted(count.items(), key=itemgetter(1))

    mo = mort_base()
    for user, value in count[sa:ea]:
        handle.wfile.write(bytes(mo.build_item(user, ent['_allusers'].get(user, []), 'user'), 'utf8'))
    
    handle.wfile.write(b'<h2 id="perc">Highest percent got</h2>\n<div class="container list">\n')
    for user, value in list(reversed(items))[sa:ea]:
        handle.wfile.write(bytes(mo.build_item(user, ent['_allusers'].get(user, []), 'user'), 'utf8'))
    
    handle.wfile.write(b'\n</div>')
    handle.wfile.write(b'</div><div class="foot">' + nav.replace(b'">&', b'#perc">&') + b'\n<br>')


def serve_cached(handle, ct, file):
    if cfg['developer']:
        ent[file] = read_file(file[1:], mode='rb', encoding=None)
    handle.send_response(200)
    handle.send_header('Content-type', ct)
    handle.end_headers()
    
    handle.wfile.write(ent[file])


def serve_search(handle):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format('Search'), 'utf8'))
    handle.wfile.write(b'<div class="head" onload="search()">')
    nav = template_nav('Search', 1, 1)
    handle.wfile.write(nav + b'</div>\n')
    
    handle.wfile.write(bytes(s['setlogic'], 'utf8'))
    
    pagehtml = '<select id="searchOF" class="niceinp">\n'
    for label in ['User', 'Title', 'Keyword', 'Set', 'Folder']:
        pagehtml += '<option value="{0}">{0}</option>\n'.format(label)
    pagehtml += '</select>\n'
    pagehtml += '<input id="searchbar" class="niceinp" placeholder="Search..." oninput="search(false)" />\n'
    pagehtml += s['markt'].format('', '', 'Search', '', action='search(\'true\')')
    pagehtml += '<div class="container list"></div>\n'
    pagehtml += '<script>var page = 1;var listCount = {};</script>'.format(cfg['listcount'])
    handle.wfile.write(bytes(pagehtml, 'utf8'))
    
    handle.wfile.write(b'\n</div><div class="foot">' + nav + b'</div><div class="foot">\n<br>')


def do_stats():
    seen =  {x: v[apdmv('marka', x)] for x, v in apdm['marka'].items()}
    by_day = {}
    days = set()
    prev = 0
    pday = ''
    
    for file in seen.keys():
        datestamp = str(seen[file])
        if not datestamp.isdigit():continue
        datestamp = int(datestamp)
        datestamp -= cfg['sec_offset']*1000# doesn't reset midnight utc0
        
        if 1800000 > prev - datestamp > -1800000:
            date = pday
        else:
            date = jsdate(datestamp).isoformat()[:10]
            prev = datestamp
            pday = date
        
        if date in days:
            by_day[date] += 1
        else:
            by_day[date] = 1
            days.add(date)
    
    ent['by_day'] = by_day


def do_stats_read():
    seen = dpref.get('read', {})
    by_day = {}
    days = set()
    prev = 0
    pday = ''
    
    for file in seen.keys():
        datestamp = str(seen[file])
        if not datestamp.isdigit():continue
        datestamp = int(datestamp)
        datestamp -= cfg['sec_offset']*1000# doesn't reset midnight utc0
        
        if 1800000 > prev - datestamp > -1800000:
            date = pday
        else:
            date = jsdate(datestamp).isoformat()[:10]
            prev = datestamp
            pday = date
        
        wc = apdfa.get(file, {}).get('descwc', 100)
        
        if date in days:
            by_day[date] += wc
        else:
            by_day[date] = wc
            days.add(date)
    
    ent['by_day_read'] = by_day



def serve_stats(handle):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format('Stats'), 'utf8'))
    handle.wfile.write(b'<div class="head"><h2>Stats</h2></div>\n')
    handle.wfile.write(b'<div class="container list">\n')
    
    #dur = datetime.now()
    
    if cfg['docats']:
        allart = ent['_allusers'].keys()
    else:
        allart = ent['usersort']

    la = len(allart)
    la -= len([x for x in allart if x.startswith('@')])
    pas = set(dpref.get('passed', {}))
    lp = len(pas)
    
    out = '<div style="display: inline-block; vertical-align: top">'
    out += '<h2>Passed</h2>Users: {}<br>Passed: {}<br>{:.02%}</div>'.format(la, lp, lp/max(la, 1))
    handle.wfile.write(bytes(out, 'utf8'))
    
    handle.wfile.write(b'\n<h2>Mark</h2>\n')
    do_stats_read()
    dsr = set(ent['by_day_read'].keys())
    do_stats()
    by_day = ent['by_day']
    
    tot = 0
    high = 0
    for k, c in by_day.items():
        tot += c
        if c > high:high = c
    
    imgs = len(apdfa.keys())
    
    l8r = 0
    l8rp = 0
    imgsp = 0
    
    for k in ent['ustats']:
        v = ent['ustats'][k]
        if v == -1:v = len(ent['users'].get(k, []))
        elif v < 0:v = -v
        l8r += v
        if k in pas:
            l8rp += v
            imgsp += len(ent['_allusers'].get(k, []))
    
    handle.wfile.write(bytes('\nAll: Known: {:,}, Faved: {:,}, thats\'s {:.02%}\n<br><br>'.format(l8r, imgs, imgs/max(l8r, 1)), 'utf8'))
    handle.wfile.write(bytes('\nPassed: Known: {:,}, Faved: {:,}, thats\'s {:.02%}\n<br><br>'.format(l8rp, imgsp, imgsp/max(l8rp, 1)), 'utf8'))
    
    handle.wfile.write(bytes('\nTotal: {:,}, Marked: {:,}, that\'s {:.02%}\n<br><br>\n'.format(imgs, tot, tot/max(imgs,1)), 'utf8'))
    
    handle.wfile.write(b'<style>td, th {text-align:center;}tr.odd {background: #424242;}</style>')
    
    handle.wfile.write(b'<table style="display:inline-block;margin:0 auto;">\n')
    handle.wfile.write(b'<tr>\n\t<th>Date</th>\n\t<th>Count</th>\n\t<th>High %</th>\n\t<th>Read Words</th>\n</tr>\n')
    c = 0
    for k in sorted(by_day.keys(), reverse=True):
        phi = by_day[k]/high
        
        h = '<tr class="{}">'.format(['', 'odd'][c%2])
        for i, f in [
            (k, ''),
            (by_day[k], ','),
            (phi, '.02%'),
            (ent['by_day_read'].get(k, 0), ',')
            ]:
            h += '\n\t<td>{}</td>'.format(('{:'+f+'}').format(i))
        
        h += '\n</tr>\n'
        
        handle.wfile.write(bytes(h, 'utf8'))
        c += 1
    
    handle.wfile.write(b'</table></div>')


def serve_settings(handle):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format('Configure'), 'utf8'))
    
    handle.wfile.write(b'<div class="head">')
    nav = template_nav('Configure', 1, 1)
    handle.wfile.write(nav + b'</div>\n')
    
    handle.wfile.write(b'<div class="container">\n')
    
    body = '<br>\n<a class="btn wide on" onclick="postReload(\'/findnew\', \'\')">Find New</a>'
    body += '\n<hr>\n<h1>Options</h2>'
    btntmp = '\n<div class="setting">\n<div class="info">\n<h2>{name}</h2>\n<p>{label}</p>\n</div><div>\n<input class="niceinp" id="{id}" type="{inptype}" value="{val}">\n<button class="mbutton" onclick="{scr}">Apply</button>\n</div></div>'
    for k, name, label, inptype in [('docats', 'Do Cats', 'Filter out posts marked (Requires rebuild)', 'checkbox'),
                                    ('doPostSplit', 'Do Post Split', 'Use split folder structure for faster performance<br>(Does not set it up for you)', 'checkbox'),
                                    ('purge', 'Purge', 'Purge old data from mort and eyde pages when rebuilding.<br>May reduce RAM usage, tbh haven\'t tested, this is so I can disable it quick', 'checkbox'),
                                    ('listcount', 'List Count', 'How many groups to list on a page', 'number'),
                                    ('postcount', 'Post Count', 'How many posts to list on a page', 'number'),
                                    ('over', 'Overflow', 'Add overflow if it\'s less than this', 'number'),
                                    ('collapse_desclength', 'Collapse Long Descriptions', 'Descriptions longer than this value will be collapsed until expanded.', 'number'),
                                    ('developer', 'Developer Mode', 'Enable debugging features', 'checkbox'),
                                    ('allowData', 'Allow /data/*', 'Enable data access over http', 'checkbox'),
                                    ('static', 'Static', 'Disable changing marks, updating sets, etc.', 'checkbox'),
                                    ('allowPages', 'Allow Pages', 'Load custom pages from uour pages folder', 'checkbox')
                                    ]:
        if inptype == 'checkbox' and cfg.get(k, False):val = '" checked nul="'
        else:val = cfg.get(k, '')
        body += btntmp.format(name=name, label=label, id=k, inptype=inptype, val=val, scr='cfg(\''+k+'\')')
    
    handle.wfile.write(bytes(body, 'utf8'))
    
    body = '\n<hr>\n<h1>Buttons</h2>'
    for name, data in cfg['mark_buttons'].items():
        #"watching": {"icon": [1, 4], "for": "users", "disabled": True}
        body += '\n<p>{} - {}</p>'.format(name, data)
    
    handle.wfile.write(bytes(body, 'utf8'))
    handle.wfile.write(b'</div>\n')


def serve_quest(handle, path):
    
    do_stats()
    do_stats_read()
    
    today = (datetime.now() - timedelta(hours=6)).isoformat()[:10]
    if today in ent['by_day']:
        markpts = ent['by_day'][today]
    
    else:markpts = 0
    
    wordpts = 0
    if today in ent['by_day_read']:
        wordpts = ent['by_day_read'][today]
    
    score = wordpts + (markpts * 100)
    level = 1
    req = 500
    preq = 0
    while score+preq > req:
        level += 1
        preq -= req
        req += 300
    
    ent['drive'] = {
        'score': score,
    	'preq': preq,
    	'level': level,
    	'req': req
    	}
        
    disp = '<p>{:.2f} total session xp ({} mark, {:.2f} word)</p>\n'.format(score, markpts*100, wordpts)
    disp += '<h2 style="display: inline; margin-right: 15px;">Level {}</h2>'.format(level)
    disp += '<progress value="{}" max="{}"></progress>\n<br>\n'.format(score+preq, req)
    disp += '\n<p>{:,.2f} xp needed to reach <i>Level {}</i></p>\n'.format(req-(score+preq), level+1)

    if 'users' in ent['_lists']:# follows user activity
        path = ['list', 'users', path[-1]]
    else:# inital state
        page = choice(['users', 'passed', 'queue', 'partial'])
        path = [page, path[-1]]
    
    serve_remort(handle, path, disp)


def serve_menu(handle, which, head=True):
    if head:
        handle.send_response(200)
        handle.send_header('Content-type', 'text/html')
        handle.end_headers()
        handle.wfile.write(s['utf8'])
        handle.wfile.write(bytes(s['head'].format('Navigation'), 'utf8'))
    
    minfo = cfg['menu_pages'].get(which, {})
    htmlout = '<div class="head"><h2><a href="/{}">{}</a></h2></div>\n'
    htmlout = htmlout.format(which, minfo.get('title', 'Undefined: {}'.format(which)))
    htmlout += '<div class="container list">\n'
    
    mode = minfo.get('mode', 'list')
    btn = s['menubtn-'+mode]
    for d in cfg.get(minfo.get('buttons', '{}_buttons'.format(which)), []):
        
        i = {'href': d.get('href', ''),
             'label': d.get('label', 'Error'),
             'alt': d.get('alt', ''),
             'x': 9, 'y': 9}
        
        if len(i['href']) > 0 and '/' not in i['href']:
            i['href'] = '/{}/1'.format(i['href'])
        
        part = i['href'].split('/')
        
        if 'icon' in d:
            i['x'], i['y'] = d['icon']
        
        elif 'x' in d and 'y' in d:
            i['x'], i['y'] = d['x'], d['y']
        
        elif len(part) > 1 and part[1] in ent['remort']:
            i['x'], i['y'] = ent['remort'][part[1]].icon
        
        i['x'] *= -100
        i['y'] *= -100
        
        htmlout += btn.format(**i)
    
    handle.wfile.write(bytes(htmlout+'</div>\n', 'utf8'))


def serve_page(handle, path):
    if cfg['developer']:
        if os.path.isfile('pages/{}.html'.format(path[0])):
            with open('pages/{}.html'.format(path[0]), 'rb') as fh:
                ent['pagedata'][path[0]] = fh.read()
                fh.close()
    
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    data = ent['pagedata'][path[0]]
    fd = {}
    if b'<!--\r\nFADMETA' in data:
        fd = get_prop(b'<!--\r\nFADMETA', data, t=b'-->').decode("utf-8")
        try:
            fd = json.loads(fd)
        except Exception as e:
            if cfg['developer']:
                print('You fucked up!', e)
            else:
                print('Exception', e, 'while reading metadata', path[0])
    
    handle.wfile.write(data)
    return fd


def serve_data(handle, path):
    if not cfg['allowData']:
        serve_error(handle, 'Data Access is disabled', 'Accessing data has been disabled on this server.')
        return
    
    happy = True
    ret = ''
    if len(path) == 1:
        ret = '{"error": "no request specified"}'
        pass
    
    elif path[1] == 'pref' and len(path) >= 3:
        if path[2] in pref.keys():
            ret = json.dumps(pref[path[2]])
        else:
            happy = False
    
    elif path[1] == 'prefm':
        ret = json.dumps(prefm)
    
    elif path[1] == 'apdm' and len(path) >= 3:
        if path[2] in apdm.keys():
            ret = json.dumps(apdm[path[2]])
        else:
            happy = False
    
    elif path[1] == 'apdmm':
        ret = json.dumps(apdmm)
    
    elif path[1] == 'dpref' and len(path) >= 3:
        if path[2] in dpref.keys():
            ret = json.dumps(dpref[path[2]])
        else:
            happy = False
    
    elif path[1] == 'dprefm':
        ret = json.dumps(dprefm)
    
    elif path[1] == 'users':
        ret = json.dumps(ent['_allusers'])
    
    elif path[1] == 'posts':
        ret = json.dumps(list(apdfa.keys()))
    
    elif path[1] == 'userids':
        ret = json.dumps(ent['users'])
    
    elif path[1] == 'ent':
        if len(path) < 3:
            ret = '{"error": "no variable specified"}'
        elif path[2] in ent:
            ret = json.dumps(ent[path[2]])
        else:
            ret = '{"error": "variable does not exist"}'
    
    else:
        happy = False
    
    if happy:
        handle.send_response(200)
        handle.send_header('Content-type', 'application/json')
        handle.end_headers()
        handle.wfile.write(bytes(ret, 'utf8'))
        return
    else:
        handle.send_response(404)
        handle.end_headers()
        handle.wfile.write(b'{"error": "unhandled request"}')
        return


def cfgsave():
    out = '{\n'
    depth = 0
    line = 1
    for k, v in cfg.items():
        if line > 1:out += ',\n'
        if type(v) == str:out += '"{}": "{}"'.format(k, v)
        elif type(v) == bool:out += '"{}": {}'.format(k, str(v).lower())
        elif type(v) in [int, float]:out += '"{}": {}'.format(k, v)
        elif type(v) == list:
            out += '"{}": [ \n'.format(k)
            for i in v:
                out += ' ' + json.dumps(i, indent=0).replace('\n', ' ') + ','
                out += ['\n', ' '][type(i) == str and depth > 0]
            out = out[:-2] + '\n]'
        
        elif type(v) == dict:
            out += '"{}": '.format(k) + '{ \n'
            for i, j in v.items():
                out += ' "{}": '.format(i)
                out += json.dumps(j, indent=0).replace('\n', ' ') + ',\n'
            out = out[:-2] + '\n}'
        else:
            print('Unsupported CFG save format', k, type(k))
        
        line += 1
    
    out += '\n}'
    with open(cfg['pp']+'cfg.json', 'w') as fh:
        fh.write(out)
        fh.close()


def mobile_pack(handle):
    files = ['ap_' + x for x in ent['apdmark']]
    files = [cfg['pp'] + x for x in files]
    name = datetime.now()
    name -= timedelta(seconds=cfg['sec_offset'])
    
    name = name.strftime('js%y%m%d.zip')
    errorlevel = compress(name, files)

    title = 'Compressed'
    if len(errorlevel) == 0:
        msg = '{} files successfully packed into {}'.format(len(files), name)
    else:
        title += ' with errors'
        msg = '{} files successfully packed into {}<br>Could not pack:<br>'
        msg = msg.format(len(files) - len(errorlevel), name)
        msg += '<be>'.join(errorlevel)

    serve_error(handle, title, msg)


class fa_req_handler(BaseHTTPRequestHandler):
    def do_GET(self):
        tim = datetime.now()
        path = urllib.parse.unquote(self.path)[1:].lower().split('/')
        
        do_rebut = True
        do_time = True
        do_script = True
        do_menu = True
        
        handled = True
        if path[-1] == 'parrot.svg':
            serve_cached(self, 'image/svg+xml', '_parrot.svg')
            return
        
        elif path[0] == 'i' or path[0] == 't':
            serve_image(self, path)
            return
        
        elif path[0].startswith('style'):
            serve_cached(self, 'text/css', '_style.css')
            return
        
        elif self.path == '/mark.js':
            serve_cached(self, 'application/javascript', '_mark.js')
            return
        
        elif path[-1] == 'icons.svg':
            serve_cached(self, 'image/svg+xml', '_icons.svg')
            return
        
        elif path[0] == 'data':
            serve_data(self, path)
            return
        
        elif path[0] == 'pack':
            mobile_pack(self)
        
        elif self.path == '/search':
            serve_search(self)
        
        elif self.path == '/stats':
            serve_stats(self)
        
        elif self.path == '/config':
            serve_settings(self)
        
        elif cfg['allowPages'] and (path[0] in ent['pages']):
            fd = serve_page(self, path)
            do_time = fd.get('enableTime', True)
            do_script, do_style = fd.get('enableScript', True), fd.get('enableStyle', True)
            if do_style:
                self.wfile.write(b'<link rel="stylesheet" href="/style.css">\n')
            do_menu = fd.get('enableMenu', True) and do_script
            do_rebut = fd.get('enableRebuild', True) and do_script
        
        else:
            handled = False
        
        for x in cfg['menu_pages']:
            if self.path == '/'+x:
                serve_menu(self, x)
                self.wfile.write(b'<div class="foot">\n')
                handled = True
                break
        
        if path == ['']:
            do_menu = False
            serve_menu(self, 'menu')
            self.wfile.write(b'<div class="foot">\n')
            handled = True
        
        elif path[-1].isdigit():
            path[-1] = int(path[-1])
        
        elif path[-1][1:].isdigit() and path[-1][:1] == '-':
            path[-1] = int(path[-1])
        
        elif not handled:
            self.send_response(307)
            if self.path == '/':self.send_header('Location', '/')
            else:self.send_header('Location', self.path + '/1')
            self.end_headers()
            return
        
        if handled:
            pass
        
        elif path[0] == 'unstuck':
            ent['building_entries'] = False
            self.send_response(307)
            self.send_header('Location', '/')
            self.end_headers()
            return
        
        elif ent['building_entries']:
            serve_error(self, 'Building Entries', 'The program is busy building entries, please refresh in a few seconds.<br>If stuck <a href="/unstuck">Click Here</a>')
        
        elif path[0] in ent['remort']:
            serve_remort(self, path)
        
        elif path[0] in ent['eyde']:
            serve_eyde(self, path)
        
        elif path[0] == 'scout':
            serve_scout(self, path)
        
        elif path[0] == 'quest':
            serve_quest(self, path)
        
        else:
            serve_error(self, '{} not found'.format(self.path), 'I don\'t know what do')
        
        dur = int((datetime.now() - tim).total_seconds() * 1000)
        page_html = ''
        
        if do_rebut:
            page_html += '\n<a class="btn wide" onclick="postReload(\'/rebuild\', \'\')">Rebuild</a>'
        
        if do_script:
            page_html += '\n<script src="/mark.js"></script>'

        if do_time:
            page_html += '\n<p>FADSRV build#{} - Served in {}ms'.format(version, dur)
        
        self.wfile.write(bytes(page_html, 'utf8'))
        
        if do_menu:
            self.wfile.write(s['popdown'])
            serve_menu(self, 'menu', head=False)
            self.wfile.write(b'</div>')
        
        if ent['built_state'] < 2:
            pass
        
        return
    
    
    def do_POST(self):
        global cfg
        
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself
        
        try:
            ripdata = json.loads(post_data.decode('utf-8'))
        except:
            ripdata  = {}
        
        if cfg['developer']:
            print(ripdata)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        ret = {}
        if self.path == '/search' and 'query' in ripdata:
            mode = ripdata.get('of', 'user')
            ret['result'] = []
            ret['items'] = []
            
            if mode == 'user':
                mo = mort_base()
                for user in ent['usersort']:
                    if user == None:continue
                    if ripdata['query'] in user:
                        ret['items'].append(user)
                        ret['result'].append(mo.build_item(user, ent['users'].get(user, []), 'users'))
            
            elif mode == 'title':
                mo = eyde_base(marktype='posts')
                for post, data in apdfa.items():
                    if ripdata['query'] in data.get('title', '@UNTITLED').lower():
                        ret['items'].append(post)
                        ret['result'].append(mo.build_item_thumb(post))
            
            elif mode == 'keyword':
                mo = mort_keywords()
                for i in ent['_kws']:
                    if ripdata['query'] in i.lower():
                        ret['items'].append(i)
                        ret['result'].append(mo.build_item(i, ent['_kwd'].get(i, []), 'keywords'))
            
            elif mode == 'set':
                mo = mort_sets()
                for i, d in ent['sets'].items():
                    if ripdata['query'] in i.lower():
                        ret['items'].append(i)
                        ret['result'].append(mo.build_item([i, d['modified']], d['items'], 'sets'))
            
            elif mode == 'folder':
                mo = mort_folders()
                for i, d in apdfafol.items():
                    if ripdata['query'] in d['title'].lower():
                        ret['items'].append(i)
                        ret['result'].append(mo.build_item(i, d['items'], 'folders'))
            
            else:
                ret['result'].append('Sorry, nothing.<br><br>How do i handle {}?'.format(mode))
            
            ret['result'] = sorted(ret['result'])
        
        elif self.path == '/sets/for' and 'query' in ripdata:
            ret['sets'] = setget(ripdata['con'], ripdata['query'])
        
        elif self.path == '/sets/new' and 'name' in ripdata:
            name = ripdata['name']
            con = ripdata['con']
            ent[con][name] = {'modified': ripdata['time'], 'items': []}
            setsort(con, rebuild=True)
            ret['status'] = 'success'
            if apdmm[con].get('save', True):
                write_apd(cfg['pp'] + 'ap_' + con, {name: ent[con][name]}, {}, 2)
        
        elif self.path == '/sets/_flag' and 'file' in ripdata and 'flag' in ripdata:
            flag = ripdata['flag']
            flag = html.unescape(flag)
            con = ripdata['con']
            file = ripdata['file']
            oldv = {**ent[con][flag]}
            locked = ent[con][flag].get('lock', False)
            if not locked:
                ret['status'] = [flag, file not in ent[con][flag]['items']]
                if file in ent[con][flag]['items']:
                    ent[con][flag]['items'].remove(file)
                else:
                    ent[con][flag]['items'].append(file)
                
                ent[con][flag]['modified'] =  ripdata['time']
                if apdmm[con].get('save', True):
                    write_apd(cfg['pp'] + 'ap_' + con, {flag: ent[con][flag]}, oldv, 2)
                    #save_json(cfg['pp']+con+'.json', ent[con])
            
            if len(ret) == 0:
                ret['status'] = 'error'
                ret['message'] = 'Locked: {}'
        
        elif self.path == '/sets/prop' and 'name' in ripdata and 'prop' in ripdata:
            name = ripdata['name']
            prop = ripdata['prop']
            con = ripdata['con']
            stripset = {re.sub(r'\W+', '', x.lower()): x for x in ent[con]}
            
            if name in stripset:name = stripset[name]
            
            if name in ent[con]:
                oldv = {**ent[con][name]}
                ret[ripdata['name']] = [prop, not ent[con][name].get(prop, False)]
                ent[con][name][prop] = ret[ripdata['name']][-1]
                ent[con][name]['modified'] =  ripdata['time']
                
                if prop == 'delete':
                    del ent[con][name]
                    setsort(con, ret=False)
                
                if apdmm[con].get('save', True):
                    write_apd(cfg['pp'] + 'ap_' + con, {name: ent[con].get(name, {})}, oldv, 2)
                    #save_json(cfg['pp']+con+'.json', ent[con])
            else:
                ret['status'] = 'error'
                ret['message'] = 'WTF is {}'.format(name)
        
        elif self.path.startswith('/_flag/'):
            flag = self.path[7:]
            if cfg['developer']:print(flag, ripdata)
            if flag == 'cfg':pref['cfg'] = cfg
            
            for file in ripdata.keys():
                if ripdata[file] == None:continue
                ret[file] = [flag, file not in pref[flag]]
                if file in pref[flag] and flag != 'cfg':del pref[flag][file]
                else:pref[flag][file] = ripdata[file]
            
            if flag == 'cfg':
                cfg = pref['cfg']
                cfgsave()
                del pref['cfg']
            
            else:
                save_json(cfg['pp']+flag+'.json', pref[flag])
        
        elif self.path.startswith('/_apref/'):
            flag = self.path[8:]
            if cfg['developer']:print(flag, ripdata)
            if flag not in apdmm:
                print('Unknown apdm:', flag)
                return
            
            ch_apdm = {}
            for post, rating, dt in ripdata:
                if post in apdm[flag]:
                    c = list(apdm[flag][post].keys())
                    if len(c) > 0:
                        if c[0] == rating:
                            continue
                        elif c[0] == "n/a" and rating == None:
                            continue
                
                if rating == None:
                    ch_apdm[post] = {"n/a": dt}
                else:
                    ch_apdm[post] = {rating: dt}
                
                ret[post] = [flag, rating]

            if len(ch_apdm) > 0:
                if cfg['developer']:print(ch_apdm)
                write_apd(cfg['pp'] + 'ap_' + flag, ch_apdm, apdm[flag], 2)
                for k in ch_apdm:
                    apdm[flag][k] = ch_apdm[k]
        
        elif self.path == '/reshuffle':
            ent['remort']['shuffle'].purge(2)
            ret['status'] = 'success'
        
        elif self.path == '/rebuild':
            if True:#try:
                build_entries()
                ret['status'] = 'success'
            #except Exception as e:
            #    ret['status'] = 'error'
            #    ret['message'] = 'An error occurred while rebuilding, see console for more details'
            #    print('Ran into an error', e)
        
        elif self.path == '/findnew':
            if True:#try:
                apd_findnew()
                ent['_kwd'] = {}
                build_entries(rebuild=True)
                ret['status'] = 'success'
            #except Exception as e:
            #    ret['status'] = 'error'
            #    ret['message'] = 'An error occurred while adding new files, see console for more details'
            #    print(e)
        
        #print(json.dumps(ret)[:500])
        self.wfile.write(bytes(json.dumps(ret), 'utf8'))
        return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread.""" 


s = {# strings
    'utf8': b'<meta charset="UTF-8">\n',
    'head': '<html>\n<head><title>{}</title>\n<link rel="stylesheet" href="/style.css">\n</head>\n<body>\n<div class="pageinner">',
    
    'thumb': '<span class="thumb{2}"><a class="thumba" href="{0}"><span>{1}</span></a></span>\n',
    
    'menubtn-narrow-icons': '<span class="menubtn"><a href="{href}" alt="{alt}"><span class="iconsheet" style="background-position:{x}px {y}px;"></span>{label}</a></span>\n',
    'menubtn-wide-icons': '<span class="menubtn wide"><a href="{href}" alt="{alt}"><span class="iconsheet" style="background-position:{x}px {y}px;"></span> {label}</a></span>\n',
    'menubtn-list': '<a class="btn wide" style="font-size:initial;" href="{href}" alt="{alt}">{label}</a>\n',
    
    'ewc': '<div class="desc"><details><summary>{} (Estimated {} word count)</summary>\n{}</details>\n</div><br>\n',
    'nb': '<a class="btn{2}" href="{1}">{0}</a>\n',
    'markt': '<button name="{0}@{1}" onclick="{action}" class="mbutton {3}">{2}</button>\n',
    'all': '<br>\nThat\'s all I\'ve got on record. {} {}{}.',
    
    'popdown': b'<button class="mbutton" id="popdownbtn" onclick="popdown();">&#x1F53B;</button><div id="popdown">',
    'setlogic': '''<div id="sets-man" class="hidden">
<div class="ctrl">
<input class="niceinp item" id="setsName" oninput="setSearch()">
<button class="mbutton" onclick="setsNew()">+</button>
<button class="mbutton" onclick="setsClose()">X</button>
</div>
<div class="list" id="sets-list">\n</div>\n</div>\n'''
}


def cfgload():
    global ent, cfg
    
    if os.path.isfile(cfg['pp']+'cfg.json'):
        for k, v in read_json(cfg['pp']+'cfg.json').items():
            cfg[k] = v
        print('Loaded settings')


def load_apx(fn):
    global xlink
    apdfile = fn[4:]
    data = read_apd(cfg['pp'] + fn)
    prop = {}
    if '//' in data:
        prop = data['//']
        del data['//']

    xlink[apdfile] = data
    back = {}
    if prop.get('linkback', True):
        exists = set()

        for k, v in data.items():
            for i in v:
                if i in exists:
                    back[i].append(k)
                else:
                    back[i] = [k]
                    exists.add(i)
    
        xlink[apdfile + 'back'] = back


def load_apd(do_apx):
    global ent, prefm, pref, apdmm, apdm, dpref, dprefm, xlink
    apdm = {}
    dprefm = {}
    dpref = {}
    apdmm = {}

    apdmark = {}
    apxlink = {}
    scandir = cfg['pp']
    if scandir == '':scandir = '.'
    for f in os.listdir(scandir):
        if f.startswith('ap_'):
            apdmark[f[3:]] = 0
        elif f.startswith('apx_'):
            apxlink[f] = 0
    
    datas  = {}
    for apdfile in apdmark:
        data = read_apd(cfg['pp'] + 'ap_' + apdfile)
        prop = {}
        if '//' in data:
            prop = data['//']
        
        apdmark[apdfile] = prop.get('order', 0)
        datas[apdfile] = data
    
    apdmark = sorted([(y, x) for x, y in apdmark.items()])
    apdmark = [y for x, y in apdmark]
    
    ent['apdmark'] = apdmark
    ent['apxlink'] = apxlink
    
    for apdfile in apdmark:
        data = datas[apdfile]
        apdmm[apdfile] = {}
        
        prop = {}
        if '//' in data:
            prop = data['//']
            del data['//']
        
        for k, v in prop.items():
            apdmm[apdfile][k] = v
        
        if prop.get('type', False) == 'collection':
            if 'name_plural' not in apdmm[apdfile]:
                name = apdmm[apdfile].get('name', '')
                if name == '':name = apdfile
                else:name += 's'
                apdmm[apdfile]['name_plural'] = name
            
            ent[apdfile] = data
            
            dpref[apdfile] = set()
            for d, k, n in setsort(apdfile, rebuild=True):
                dpref[apdfile].update(set(ent[apdfile][k]['items']))
        
            dpref[apdfile] = {x: 0 for x in dpref[apdfile]}
            
        elif prop.get('list', False) != False:
            if prop.get('for', 'posts') == 'users':
                data = {x.replace('_', '').lower(): 0 for x in data}
            
            apdm[apdfile] = data
            dpref[apdfile] = data
        
        else:
            for k, v in list(data.items()):
                if len(v) > 1:
                    cr = '@error!'
                    cd = -32768
                    for r, d in v.items():
                        if type(d) != int:continue
                        if d > cd:
                            cd, cr = d, r
                    
                    del data[k]
                    
                    if cr != 'n/a':
                        data[k] = {cr: cd}
                
                elif list(v.keys()) == ['None']:
                    del data[k]
            
            apdm[apdfile] = data
            
            for k, v in divy(data).items():
                dprefm[k] = apdmm[apdfile]
                dprefm[k]['apdm'] = apdfile
                dpref[k] = v
    
    if do_apx:
        xlink = {}
        for apdfile in apxlink:
            load_apx(apdfile)
    
    pref = {}
    prefm = cfg['mark_buttons']
    for file in list(prefm.keys()):
        #print('Loading', file)
        origin = prefm[file].get('origin', 'json')
        pref[file] = {}
        if origin == 'json':
            if os.path.isfile(cfg['pp'] + file + '.json'):
                pref[file] = read_json(cfg['pp']+ file + '.json')
        
        elif os.path.isfile(cfg['pp'] + origin):
            pref[file] = {x.replace('_', ''): 0 for x in read_file(cfg['pp']+origin).lower().split('\n')}
        
        else:
            print('Unhandled origin for {}, {}'.format(file, origin))


def init_apd():
    make_apd('ap_passed', {'//': {
        'icon':  [4,0],
        'type': "multibutt",
        'values': ["passed"],
        'for': "users",
        'order': 0
    }})
    
    make_apd('ap_queue', {'//': {
        'icon':  [1,1],
        'type': "multibutt",
        'values': ["queue"],
        'for': "users",
        'order': 20
    }})
    
    make_apd('ap_marka', {'//': {
        'icon':  [6,0],
        'type': "multibutt",
        'values': ["seen", "ref", "rem"],
        'valueicon': [[0,3], [1,3], [2,3]],
        'order': 20
    }})


if __name__ == '__main__':
    print('Starting...')
    
    mobile_path = r'/storage/emulated/0/download/takeout/fad/'
    code_path = r'/storage/emulated/0/qpython/projects3//fadsrv/'
    is_mobile = os.path.isdir(mobile_path)
    if is_mobile:
        os.chdir(code_path)
    
    if os.path.isfile('doquickrename.py'):
        import doquickrename
        if is_mobile:
            os.chdir(code_path)
    
    cfg = {
        'developer': False,
        'docats': is_mobile,# only includes in cats rather than keeping order
        'image_dir': 'i/',
        'data_dir': 'p/',
        'server_addr': '127.0.0.1',
        'server_port': 6970,
        'useRemoteImages': False,
        'listcount': 15,# users/kewords per page
        'postcount': 25,# posts per page
        'over': 5,# how many posts over the limit a page may extend
        'collapse_desclength': 250,# collapse descriptions longer than this
        'doPostSplit': is_mobile,# better file op performance
        'pp': '',# prepend data files
        'allowData': True,# external data access
        'static': False,# disable changing values
        'allowPages': True,# enable custom pages
        'purge': True,# purge old data from mort and eyde to free up ram
        'sec_offset': 21600,
        'mark_buttons': {},# todo depricate
        'menu_pages': {
            "menu": { "title": "FADSRV Menu", "mode": "narrow-icons", "buttons": "menu_buttons" },
            "q": { "title": "Queries", "mode": "wide-icons", "buttons": "query_buttons" },
            "remort": { "title": "Remort Menu", "mode": "wide-icons", "buttons": "remort_buttons" }
            },
        'menu_buttons': [
            { "label": "by Users", "href": "users" },
            { "label": "by Keyword", "href": "keywords" },
            { "label": "Search", "href": "/search", "icon": [ 2, 0 ] },
            { "label": "Shuffled Users", "href": "shuffle" },
            { "label": "Passed Users", "href": "passed" },
            { "label": "Partially Seen", "href": "partial" },
            { "label": "Queue", "href": "queue" },
            { "label": "Quest Browse", "href": "quest", "icon": [ 2, 1 ] },
            { "label": "Query", "href": "/q", "icon": [ 3, 1 ] },
            { "label": "Scout", "href": "/scout", "icon": [ 3, 2 ] },
            { "label": "Stats", "href": "/stats", "icon": [ 0, 2 ] },
            { "label": "Sets", "href": "sets" },
            { "label": "Configure", "href": "/config", "icon": [ 1, 2 ] },
            { "label": "remort", "href": "/remort", "icon": [ 6, 0 ] }
            ],
        'query_buttons': [
            { "label": "Restricted Users", "href": "gone" },
            { "label": "User Activity", "href": "activity" },
            { "label": "Review Passed", "href": "review" },
            { "label": "Unread by User", "href": "unread" },
            { "label": "Folders", "href": "folders" }
            ],

        'altsrv': [
            ['https://www.furaffinity.net/user/{}/', 'FA Userpage']
            ],
        'link_to': {
            'users': '/user/{}/1',
            'keywords': '/keyword/{}/1',
            'folders': '/folder/{}/1',
            'list': '/list/{}/1',
            'posts': '/view/{}/1'
           }
        }
    
    ent = {
    	'built_state': 0,
        'building_entries': False,
        'sets': {},
        'groups': {},
        '_kwd': {},
        
        '_lists': {},
        '_bart': {},
        
        'pages': [],
        'pagedata': {},
        
        'remort': {
            'users': mort_base(),
            'keywords': mort_keywords(),
            'shuffle': mort_shuffle(),
            'partial': mort_partial(),
            'gone': mort_gone(),
            'activity': mort_activity(),
            'review': mort_review(),
            'list': mort_list(),
            'folders': mort_folders(),
            'sets': mort_sets(),
            'wdyt': mort_sets(title='WDYT', con='wdyt', link='/wdytart/{}/1', icon=[7,5]),
            'groups': mort_groups(),
            'group': mort_group(),
            'linkeduser': mort_linkeduser(),
            'l8ratio': mort_l8ratio(),
            'l8rscout': mort_l8rscout()
            },
        'eyde': {
            'user': eyde_user(),
            'keyword': eyde_keyword(),
            'view': eyde_view(),
            'folder': eyde_folder(),
            'set': eyde_set(),
            'wdytart': eyde_set(con='wdyt', lister='/wdyt/1'),
            }
    }
    
    for k in ['style.css', 'parrot.svg', 'icons.svg', 'mark.js']:
        ent['_'+k] = read_file(k, mode='rb', encoding=None)
    
    if is_mobile:os.chdir(mobile_path)
    
    if os.path.isdir('data'):
        cfg['pp'] = 'data/'
    
    cfgload()
    cfgsave()# double check before we start
    
    apdfa = read_apd(cfg['pp'] + 'apdfa', do_time=True)
    apdfadesc = read_apd(cfg['pp'] + 'apdfadesc', do_time=True)
    apdfafol = read_apd(cfg['pp'] + 'apdfafol', do_time=True)
    init_apd()
    if not is_mobile:
        load_apd(True)
        apd_findnew()
    
    print(['^-.-^ docats false', '^o,o^ docats true'][cfg['docats']])
    build_entries(rebuild=True)
    
    httpd = ThreadedHTTPServer((cfg['server_addr'], cfg['server_port']), fa_req_handler)
    httpd.serve_forever()
