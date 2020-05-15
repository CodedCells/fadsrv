from http.server import BaseHTTPRequestHandler, HTTPServer
import os, json, random, datetime, time, math, urllib, operator, html

from fad_utils import *

version = '24'

def artistsort(postfn, docats=True):
    # sort posts to artists
    artdata = fadata['postdata']
    artists = {}
    mark = []
    for x in pref.keys():mark += list(pref[x].keys())
    mark = set(mark)
    for i in range(50):
        ent['_kwdata']['wc:'+str(i*500)] = []
    
    for post in postfn:
        if post == '' or post == None:continue
        d = artdata.get(post, {'artist': '@badart', 'descwc': -1})
        k = (d.get('descwc') // 500) *500
        if k < 0:k = 500
        k = 'wc:'+str(k)
        ent['_kwdata'][k].append(post)
        
        k = d.get('artist')
        if k == None:k = '@badart'
        
        if not k in artists:artists[k] = []
        artists[k].append(post)
    
    for artist in list(artists.keys()):
        if type(artist) != str:
            del artist
            continue
        
        sa = [str(x) for x in sorted([int(x) for x in artists[artist]])]
        artists[artist] = [x for x in sa if not (docats and x in mark)]
        if len(artists[artist]) == 0:del artists[artist]
        ent['_kwdata']['a:'+artist] = {x: fadata['postdata'].get(x) for x in sa}
    
    for m in prefm:
        artists['@'+m] = list(x for x in pref[m].keys() if x in artdata)
    
    return artists


def read_filesafe(fn, mode='r', encoding='utf8'):
    try:
        data = read_file(fn, mode=mode, encoding=encoding)
    except FileNotFoundError:
        print('FILENOTFOUND!!\t', fn)
        data = ''
    
    return data


def fadata_findnew():
    made_changes = 0
    fields = ['ext', 'keywords', 'date', 'title', 'artist', 'desclen', 'descwc']
    c = 0
    keywords = fadata['keywords']
    keyset = set(keywords.keys())
    artists = fadata['artists']
    artistset = set(artists.keys())
    descset = set(fadesc.keys())
    
    #print(len(fadata['postdata']), len(descset))
    
    for file in os.listdir('i/'):
        postid, postext = file.split('.')
        pd = fadata['postdata'].get(postid, {})
        add = [x for x in fields if not x in pd or (x in ['title', 'artist'] and pd[x].strip() == '')]
        if not postid in descset:add.append('desc')
        
        if add == []:continue
        c += 1
        if c % 500 == 0:
            print('', str(c).rjust(5), '{} artists'.format(len(artistset)), '{} keywords'.format(len(keyset)), sep='\t')
        
        made_changes += 1
        if 'ext' in add:pd['ext'] = postext
        if add == ['ext']:
            fadata['postdata'][postid] = pd
            continue
        
        datafn = 'p/{}_desc.html'.format(postid)
        try:
            data = read_filesafe(datafn)
        except UnicodeDecodeError:# prevent strange files messing up
            data = str(read_filesafe(datafn, mode='rb', encoding=None))
        
        if data == '':
            made_changes -= 1
            continue
        
        if 'keywords' in add:
            if '@keywords' in data:
                if '<div id="keywords">' in data:# old theme
                    ks = get_prop('<div id="keywords">', data, t='</div>')
                elif '<section class="tags-row">' in data:# new theme
                    ks = get_prop('<section class="tags-row">', data, t='</section>')
                else:
                    print('Unknown Keywork container', file)
                    made_changes -= 1
                    continue
                
                pd['keywords'] = [x.split('"')[0].lower() for x in ks.split('@keywords ')[1:]]
            else:
                pd['keywords'] = ['_untagged']
            
            for k in pd['keywords']:
                if k in keyset:keywords[k].append(postid)
                else:
                    keywords[k] = [postid]
                    keyset.add(k)
        
        if 'date' in add:
            if 'popup_date">' in data:
                date = get_prop('popup_date">', data, t='</')# MMM DDth, CCYY hh:mm AM
                pd['date'] = strdate(date).isoformat()
            else:
                print('Missing date', file)
                made_changes -= 1
                continue
        
        if 'title' in add:pd['title'] = html.unescape(get_prop('property="og:title" content="', data))
        if 'artist' in add:
            pd['artist'] = get_prop('property="og:title" content="', data).split(' ')[-1].lower()
            if pd['artist'] in artistset:
                artists[pd['artist']].append(postid)
            else:
                artists[pd['artist']] = [postid]
                artistset.add(pd['artist'])
        
        if '<div class="submission-description user-submitted-links">' in data:# latest
            desc = get_prop('<div class="submission-description user-submitted-links">', data, t='</div>').strip()
        elif '<div class="submission-description">' in data:# pre-jan new theme
            desc = get_prop('<div class="submission-description">', data, t='</div>').strip()
        elif '<td valign="top" align="left" width="70%" class="alt1" style="padding:8px">' in data:# old theme
            desc = get_prop('<td valign="top" align="left" width="70%" class="alt1" style="padding:8px">', data, t='</td>')
        else:
            print('Unknown description container', file)
            made_changes -= 1
            continue
        
        desc = '"https://www.furaffinity.net/gallery/'.join(desc.split('"/user/'))
        desc = '\n'.join([x.strip() for x in desc.split('\\n')])
        desc = '\n'.join([x.strip() for x in desc.split('\n')])
        pd['desclen'] = len(desc)
        pd['descwc'] = len(desc.split(' '))
        
        url = get_prop('"og:url" content="', data)
        urlid = url.split('/')[-2]
        if urlid != postid:
            print(postid, 'doesn\'t match', url)
        
        fadata['postdata'][postid] = pd
        fadesc[postid] = desc
    
    print('', str(len(fadata['postdata'])).rjust(5) + ' posts', '{} artists'.format(len(artistset)), '{} keywords'.format(len(keyset)), sep='\t')
    if made_changes == 0:
        print('Unchanged')
        return 0
    
    for artist in list(fadata['artists'].keys()):
        fadata['artists'][artist] = list(set(fadata['artists'][artist]))
    
    for keyword in list(fadata['keywords'].keys()):
        fadata['keywords'][keyword] = list(set(fadata['keywords'][keyword]))
    
    if c > 0:
        print('Writing blobfa to disk... ', end='')
        with open('blobfa', 'w') as file:
            json.dump(fadata, file)
            file.close()
    print('Done!')
    
    if c > 0:
        print('Writing blobfadesc to disk... ', end='')
        with open('blobfadesc', 'w') as file:
            json.dump(fadesc, file)
            file.close()
    print('Done!')
    
    return made_changes


def build_entries(docats):
    global ent
    
    if 'artistpart' in ent:
        del ent['artistpart']
    
    ent['generated'] = datetime.datetime.now()
    print('Started building entries')
    
    if os.path.isfile('watch.txt'):
        ent['watch'] = read_file('watch.txt').lower().split('\n')
    else:
        ent['watch'] = []
    
    if fadata != {} and ent['_kwdata'] == {}:
        print('Grouping posts by keywords ^c,c^/n')
        pd = set(fadata['postdata'].keys())
        files = []
        for x in os.listdir('i/'):
            x = x.split('.')[0]
            files.append([fadata['postdata'].get(x, {}).get('date', '0'), x])
        
        files = [x for d, x in files]
        ent['_all'] = files
        ent['_kws'] = {}
        
        c = 0
        r = 0
        kwm = {}
        kwd = {}
        kwk = set(['ass'])
        for key in list(fadata['keywords'].keys()):
            ent['_kwdata'][key] = fadata['keywords'][key]
            ent['_kws'][key] = len(ent['_kwdata'][key])
            
            sk = key#clever_trim(key, kwk)
            kwk.add(sk)
            if sk in kwm:
                kwm[sk].append(key)
                kwd[sk] += ent['_kwdata'][key]
            else:
                kwm[sk] = [key]
                kwd[sk] = fadata['keywords'][key]
            
            if ent['_kws'][key] < 2:# delete any keywords representing fewer than 2 posts
                r += 1
            
            else:
                c += 1
            
            if c % 1000 == 0:print('\t', c)
        
        print('\nSifted through', c, 'important and', r, 'useless keywords')
        print(len(ent['_kws']), len(kwm))
        ent['_kwdata'] = {}
        ent['_kws'] = {}
        ent['_kwm'] = {}
        for key in kwm:
            ent['_kwm'][key] = kwm[key]
            ent['_kwdata'][key] = list(set(kwd[key]))
            ent['_kws'][key] = len(ent['_kwdata'][key])
        
        ent['_kws'] = sorted(ent['_kws'].items(), key=operator.itemgetter(1))
        print('Done with all that')
    
    files = ent['_all']
    ent['artists'] = artistsort(files, docats=docats)
    
    # merged pages
    for n in range(1, 6):
        name = '@small'#'_merge'.format(n)
        ent['artists'][name] = []
        for artist in list(ent['artists'].keys()):
            if not artist in pref['passed'] and len(ent['artists'][artist]) == n:
                ent['artists'][name] += ent['artists'][artist]
    
    ent['artistsort'] = sorted(ent['artists'], key=lambda k: len(ent['artists'][k]))
    
    print('{} artists'.format(len(ent['artistsort'])))


def clever_trim(i, l):
    i = i.lower().replace('_', '').replace('-', '')
    if i in l:return i
    elif i.endswith('es'):i = i[:-2]
    elif i.endswith('s'):i = i[:-1]
    return i


def serve_image(handle, path):
    spath = '/'.join(path[1:])
    ext = spath.split('.')[-1].lower()
    
    if len(spath) > 2 and os.path.isfile(spath) and is_safe_path(spath):
        handle.send_response(200)
        handle.send_header('Content-type', ctl[ext])
        handle.end_headers()
        handle.wfile.write(read_file(spath, mode='rb', encoding=None))
    elif ext != 'jpg':
        path[-1] = path[-1].replace(spath.split('.')[-1], 'jpg')
        serve_image(handle, path)
    else:
        handle.send_response(404)
        handle.send_header('Content-type', 'image/svg+xml')
        handle.end_headers()
        handle.wfile.write(ent['_parrot'])


def serve_error(handle, title, message):
    handle.send_response(404)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format(title), 'utf8'))
    handle.wfile.write(message)
    handle.wfile.write(s['parrot'])


def build_nav(handle, name, index_id, do_prev=True, do_next=True):
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format(name), 'utf8'))
    nav = b''
    handle.wfile.write(b'<div class="head">\n')
    
    if do_prev:
        nav += bytes(s['nb'].format('Previous', index_id-1, ' wide'), 'utf8')
    elif do_next:
        nav += bytes(s['nb'].format('-&gt;', 0, ' wide'), 'utf8')
    
    nav += bytes('<h1 class="btn wide">{0}</h1>\n'.format(name + ' ' + str(index_id)), 'utf8')
    
    if do_next:
        nav += bytes(s['nb'].format('Next', index_id+1, ' wide'), 'utf8')
    elif do_prev:
        nav += bytes(s['nb'].format('&lt;-', 1, ' wide'), 'utf8')
    
    return nav


def serve_keyword(handle, path):
    if len(path) == 3:keyword = path[1]
    else:keyword = ''
    index_id = path[-1]
    
    if ' ' in keyword:keywords = keyword.split(' ')
    else:keywords = [keyword]
    
    args = []
    doerror = False
    for kw in keywords:
        if kw.startswith('@'):
            args.append(kw)
            keywords.remove(kw)
        elif kw not in ent['_kwdata']:
            doerror = True
            break
    
    if doerror:
        serve_error(handle, keyword, bytes(s['noby'].format(keyword.replace('%20', ' ')), 'utf8'))
        return
    
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()

    if len(keywords) == 0:files = ent['_all']
    else:files = ent['_kwdata'].get(keywords[0], [])
    for kw in keywords[1:]:
        
        files = [f for f in files if f in ent['_kwdata'].get(kw, [])]
    
    if '@unmarked' in args:
        seen = set({**pref['seen'], **pref['ref'], **pref['rem']}.keys())
        files = [f for f in files if f not in seen]
    else:
        for k in prefm.keys():
            if '@'+k in args:
                seen = set(pref[k].keys())
                files = [f for f in files if f in seen]
    
    if '@sort:artist' in args:k, d, r = 'artist', '_badart', False
    elif '@sort:new' in args:k, d, r = 'date', '0', True
    elif '@sort:title' in args:k, d, r = 'title', '_', False
    else:k, d, r = 'date', '0', False
    
    files = sorted([(fadata['postdata'].get(x, {k: d})[k], x) for x in files], reverse=r)
    files = [x for d, x in files]
    pc = ent['_settings']['postcount']
    
    flen = len(files)
    ea = index_id * pc
    last_page = math.ceil(flen / pc)
    if 0 < flen % pc < 5:
        last_page -= 1
        if index_id == last_page:
            ea = flen
    
    do_nav = len(files) > pc
    nav = build_nav(handle, keyword.replace('%20', ' '), index_id, do_nav and index_id > 1, do_nav and index_id < last_page)
    handle.wfile.write(nav)
    
    handle.wfile.write(b'</div><div class="container">\n')
    if not is_mobile:
        for x in keywords:
            if x.startswith('@'):continue
            for k in ent['_kwm'].get(x, [x]):
                handle.wfile.write(bytes('<a href="https://www.furaffinity.net/search/@keywords%20{0}">Search FA: {0}</a><br>\n'.format(k), 'utf8'))
    
    if '@unmarked' not in args:
        handle.wfile.write(bytes('<a href="/sk/{} @unmarked/{}">@unmarked</a>\n'.format(path[1], path[2]), 'utf8'))
    
    handle.wfile.write(bytes('<p>{} file{}</p>\n'.format(flen, ['s', ''][flen == 1]), 'utf8'))
    count = write_imagedefs(files[(index_id-1)*pc:ea], handle)

    if index_id == last_page:
        handle.wfile.write(bytes(s['all'].format(len(files), 'file', ['s', ''][flen == 1]), 'utf8'))
    
    handle.wfile.write(b'</div><div class="foot">' + nav)

def l8r_or_count(a):
    return max(pref['l8r'].get(a.replace('_', ''), 0), len(ent['artists'][a]))

def gp(k):
    g = len(fadata['artists'][k])
    return g / l8r_or_count(k), g

def serve_artist(handle, path):
    if len(path) == 3:artist = path[1]
    else:artist = ''
    index_id = path[-1]
    
    if artist not in ent['artists']:
        serve_error(handle, artist, bytes(s['noby'].format(artist), 'utf8'))
        if not is_mobile:
            passed = ['', 'on'][artist in pref['passed']]
            handle.wfile.write(bytes(s['markt'].format(artist, 'passed', 'P', passed), 'utf8'))
        
        return
    
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()

    files = ent['artists'][artist]
    pc = ent['_settings']['postcount']
    
    flen = len(files)
    last_page = math.ceil(flen / pc)
    if index_id < 1:index_id += last_page
    
    ea = index_id * pc
    if 0 < flen % pc < 5:
        last_page -= 1
        if index_id == last_page:
            ea = flen
    
    do_nav = len(files) > pc
    nav = build_nav(handle, artist, index_id, do_nav and index_id > 1, do_nav and index_id < last_page)
    handle.wfile.write(nav)
    
    handle.wfile.write(b'</div><div class="container">\n')
    if not artist.startswith('@'):
        aclean = artist.replace('_', '')
        passed = ['', 'on'][artist in pref['passed']]
        
        perc, count = gp(artist)
        if not is_mobile:
            h = '<a href="https://www.furaffinity.net/user/{}/">Userpage</a><br>'.format(aclean)
            h += s['markt'].format(artist, 'passed', 'P', passed)
            
            mr = data = fadata['postdata'].get(files[-1], {}).get('date', 'bugged date :(')
            if artist in pref['passed']:
                pd = datetime.datetime.fromtimestamp(pref['passed'][artist]/1000).isoformat()[:19]
            else:
                pd = 'No'
            
            h += '<div style="display:inline-block; text-align: left;">\n'
            h += 'Last post: {}<br>Passed: {}<br>\n'.format(mr, pd)
            h += '\n</div>\n'
            
            h += '<input style="width: 140px;" class="niceinp" id="{0}ip" type="number" value="{1}">\n<button id="{0}l8r" onclick="l8r(\'{0}\')">l8r</button><br>\n'.format(aclean, pref['l8r'].get(aclean, ''))
            
            if perc > .8:sw = 'Yes'
            elif perc > .5:sw = 'Probably'
            elif perc > .2:sw = 'Maybe'
            else:sw = 'Probably not'
            h += 'Watching: {}, Should Watch? {}<br>'.format(artist in ent['watch'], sw)
            
            handle.wfile.write(bytes(h, 'utf8'))
            del mr, pd, h, sw
        
        if aclean in pref['l8r']:
            if perc < 0.1:com = 'oh'
            elif perc < .5:com = 'wow'
            elif perc < .9:com = 'wew'
            else:com = 'wonderful'
            handle.wfile.write(bytes('{} of {}, that\'s {:.02%}, {}.'.format(count, pref['l8r'][aclean], perc, com), 'utf8'))
    
    handle.wfile.write(b'<p>' + bytes(str(len(files))+' file'+['s', ''][len(files) == 1], 'utf8') + b'</p>')
    serveme = files[(index_id-1)*pc:ea]
    handle.wfile.write(bytes('<!-- Posts\n' + '\t\n'.join(serveme) + '\n-->\n', 'utf8'))
    count = write_imagedefs(serveme, handle, artist)
    
    if index_id == last_page:
        handle.wfile.write(bytes(s['all'].format(len(files), 'file', ['s', ''][flen == 1]), 'utf8'))
    
    handle.wfile.write(b'\n</div><div class="foot">' + nav)


def serve_view(handle, ids):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'] + b'<link rel="stylesheet" href="/style2.css">\n')
    
    ids = [x for x in ids if x in fadata['postdata']]
    
    write_imagedefs(ids, handle, name='@view')
def write_imagedefs(files, handle, name=''):
    count = 0
    
    for file in files:
        data = fadata['postdata'].get(file, {'ext': 'png', 'title': 'MISSING DATA'})
        ext = data['ext']
        cat = file_category(ext)
        fnid = '{}.{}'.format(file, ext)
        if cat == 'image':
            post_html = '<img loading="lazy" src="/i/i/{}" /><br>\n'.format(fnid)
        
        elif cat == 'flash':
            post_html = '<embed src="/i/i/{}" /><br>\n'.format(fnid)
        
        else:
            post_html = '<a href="/i/i/{0}.{1}">I don\'t do {1} files, click me to view/download.</a><br>\n'.format(file, ext)
        
        post_html = '<h2>{}</h2></a>\n'.format(data['title']) + post_html
        if not is_mobile:
            post_html = '<a href="https://furaffinity.net/view/{}/">'.format(file) + post_html
        
        if data['title'] != 'MISSING DATA':
            desc = fadesc.get(file, '')
            desc_word_count = data['descwc']
            if desc_word_count > 250:
                post_html += s['ewc'].format(desc_word_count, desc)
            else:
                post_html += '<div class="desc">{}</div>\n'.format(desc)
            if len(data['keywords']) > 0:
                post_html += '<div class="tags">\n'
                for key in data['keywords']:
                    post_html += '\t<a href="/sk/{0}/1">{0}</a>\n'.format(key)
                post_html += '</div>\n'
        
        handle.wfile.write(bytes(post_html, 'utf8'))
        
        marks = ''
        for m in prefm:
            marks += s['markt'].format(file, m, prefm[m], ['', 'on'][file in pref[m]])
        
        if name.startswith('@'):
            real_artist = data['artist']
            marks += s['markt'].format(real_artist, 'passed', 'P', ['', 'on'][real_artist in pref['passed']])
        handle.wfile.write(bytes(marks, 'utf8'))
        
        count += 1
    
    return count


def template_nav(title, index, last):
    nav = ''
    
    if 1 < index <= last:nav += s['nb'].format('&lt;', index-1, '')
    elif index != last:nav += s['nb'].format('&gt;|', last, '')
    
    nav += '<h1 class="btn wide">{} - {}</h1>\n'.format(title, index)
    
    if last <= index and index != 1:nav += s['nb'].format('|&lt;', 1, '')
    elif index != last:nav += s['nb'].format('&gt;', index+1, '')
    
    return bytes(nav, 'utf8')


def serve_mort(handle, path, head=True):
    
    if path[0] == 'lk':
        mode = 'keywords'
        items = ent['_kws']
        datas = ent['_kwdata']
        link = '/sk/{}/1'
    
    elif  path[0] == 'shuffle':
        mode = 'shuffle'
        items = ['male', 'female', 'octopus']
        datas = ent['_kwdata']
        link = '/sk/{}/1'
        
        items = ent.get('artistshuffle', 0)
        if items == 0:
            ent['artistshuffle'] = [x for x in ent['artistsort']]
            random.shuffle(ent['artistshuffle'])
            items = ent['artistshuffle']
        
        datas = ent['artists']
        link = '/sa/{}/1'
    
    elif path[0] == 'part':
        mode = 'part'
        items = ent.get('artistpart', 0)
        if items == 0:
            artistc = {}
            for file in pref['seen']:
                if file not in fadata['postdata']:continue
                artist = fadata['postdata'][file]['artist']
                if artist in artistc.keys():artistc[artist] += 1
                else:artistc[artist] = 1
            
            artistp = {}
            for artist in artistc.keys():
                if artist not in ent['artists']:continue
                perc = artistc[artist] / len(fadata['artists'][artist])
                if perc < 1:artistp[artist] = perc
            
            ent['artistpart'] = sorted(artistp.items(), key=operator.itemgetter(1), reverse=True)
            items = ent['artistpart']
        
        datas = ent['artists']
        link = '/sa/{}/1'
    
    elif path[0] == 'passed':
        mode = 'passed'
        
        aset = set(ent['artists'].keys())
        items = []
        datas = {}
        for pname, pdate in pref['passed'].items():
            if not pname in aset:continue
            items.append((pname, pdate))
            datas[pname] = ent['artists'][pname]
        
        items = sorted(items, key=operator.itemgetter(1))
        link = '/sa/{}/1'
    
    elif path[0] == 'recent':
        mode = 'recent'
        
        items = []
        datas = {}
        artists = set()
        for post in fadata['postdata']:
            artist = fadata['postdata'][post].get('artist')
            if artist not in artists:
                artists.add(artist)
                items.append((artist))
                datas[artist] = ent['artists'][artist]
        
        link = '/sa/{}/1'
    
    else:
        mode = 'artists'
        items = ent['artistsort']
        datas = ent['artists']
        link = '/sa/{}/1'
    
    index_id = path[-1]
    count = len(items)
    last_page = count // sett['listcount']
    if count % sett['listcount'] > sett['over'] or last_page == 0:
        last_page += 1
    
    if index_id < 1:
        index_id = last_page + index_id
    
    if head:
        handle.send_response(200)
        handle.send_header('Content-type', 'text/html')
        handle.end_headers()
    
    handle.wfile.write(s['utf8'] + b'<link rel="stylesheet" href="/style2.css">\n')
    nav = template_nav(mode, index_id, last_page)
    handle.wfile.write(b'<div class="head">\n' + nav + b'</div>\n<div class="container list">\n')
    
    end_at = index_id * sett['listcount']
    if index_id == last_page:
        end_at = None
    
    for i in items[(index_id-1)*sett['listcount']:end_at]:
        if type(i) == tuple:item = i[0]
        else:item = i
        if item not in datas:continue
        data = datas[item]
        html = '<span class="thumb{}">\n\t'.format(['', ' passed'][item in pref['passed']])
        html += '<a href="{}">\n\t\t'.format(link.format(item))
        html += '<img loading="lazy" src="/t/i/{}"><br>'.format(pick_thumb(data))
        label = '{} - {}'.format(item, len(data))
        if mode == 'part':
            label += ' - {:.02%}'.format(i[1])
        elif mode == 'passed':
            label += ' ({})'.format(pref['l8r'].get(item, '?'))
            label += '<br>' + datetime.datetime.utcfromtimestamp(int(str(i[1])[:-3])).isoformat()[:10]
            
        html += '\n\t\t{}\n\t</a>\n</span>\n'.format(label)
        
        handle.wfile.write(bytes(html, 'utf8'))
    
    handle.wfile.write(b'\n</div><div class="foot">' + nav)
    if path[0] == 'shuffle':
        handle.wfile.write(b'<br><a class="btn wide on" onclick="postReload(\'/reshuffle\', \'\')">Shuffle</a>')


def pick_thumb(posts):
    for i in posts:
        d = fadata['postdata'].get(i, {'ext': 'error'})
        if file_category(d['ext']) == 'image':
            return i + '.'+d['ext']
    
    return 'parrot.svg'


def serve_cyoa(handle, path):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    
    index_id = path[-1]
    
    passed = set(pref['passed'].keys())
    l8r = set(pref['l8r'].keys())
    unmarked = sum([1 for x in ent['artists'] if not x.startswith('@') and x.replace('_', '') not in l8r])
    
    score = {}
    count = []
    for artist in ent['artists']:
        aclean = artist.replace('_', '')
        if artist not in passed and aclean in l8r and pref['l8r'][aclean] > 0:
            score[artist] = pref['l8r'][aclean] - len(ent['artists'][artist])
            count.append(score[artist])
    
    l8rc = len(count)
    last_page = l8rc // sett['listcount']
    if l8rc % sett['listcount'] > sett['over'] or last_page == 0:
        last_page += 1
    
    if index_id < 1:
        index_id = last_page + index_id
    
    end_at = index_id * sett['listcount']
    if index_id == last_page:
        end_at = None
    
    handle.wfile.write(s['utf8'] + b'<link rel="stylesheet" href="/style2.css">\n')
    nav = template_nav('Choose your own adventure', index_id, last_page)
    handle.wfile.write(b'<div class="head">\n' + nav + b'</div>\n')
    handle.wfile.write(b'<body onload="getCYOA(6)">\n')
    artists = ent['artistsort']
    handle.wfile.write(b'</div>')
    
    if unmarked > 0:
        handle.wfile.write(b'<div class="container list" onload="getCYOA(6)">\n</div>\n')
        handle.wfile.write(b'<button onclick="getCYOA(6)">Refresh</button>\n')
    
    if pref['l8r'] == {}:
        handle.wfile.write(b'There doesn\'t seem to be any artists marked to be seen at a later date.')
        return
    
    count = sorted(count)
    lc = len(count)
    if lc % 2:median = count[lc//2]
    else:median = (count[lc//2] + count[(lc//2)+1]) // 2
    average = sum(count)//len(score.keys())
    handle.wfile.write(bytes('<p>Median: {}, Average: {}</p>\n'.format(median, average), 'utf8'))
    handle.wfile.write(b'<h2>By Available/Got (' + bytes(str(len(score.keys())), 'utf8') + b')</h2>\n<div class="container list">\n')
    
    score = sorted(score.items(), key=operator.itemgetter(1))
    for artist, value in score[(index_id-1)*15:end_at]:
        aclean = artist.replace('_', '')
        handle.wfile.write(bytes(s['thmb'].format(artist, str(len(ent['artists'][artist])) + ' (' + str(pref['l8r'][aclean]) + ')', pick_thumb(fadata['artists'][artist]), '', 'a'), 'utf8'))
    
    score = {}
    zero = []
    for artist in list(pref['l8r'].keys()):
        aclean = artist.replace('_', '')
        if artist in pref['passed'].keys() or artist not in ent['artists']:
            continue
        elif pref['l8r'][artist] < 0:
            zero.append(artist)
            continue
        score[artist] = pref['l8r'][artist] / len(ent['artists'][artist])
    
    handle.wfile.write(b'<h2 id="perc">Highest percent got</h2>\n<div class="container list">\n')
    score = sorted(score.items(), key=operator.itemgetter(1))[(index_id-1)*15:end_at]
    for artist, value in score:
        injectbtn = str(len(ent['artists'][artist])) + ' (' + str(pref['l8r'][artist]) + ')'
        handle.wfile.write(bytes(s['thmb'].format(artist, injectbtn, pick_thumb(fadata['artists'][artist]), '', 'a'), 'utf8'))
    
    #handle.wfile.write(bytes('<h2>Less than zero ({})</h2>\n<div class="container list">\n'.format(len(zero)), 'utf8'))
    #for artist in zero[:12]:
    #    injectbtn = str(len(ent['artists'][artist])) + ' (' + str(pref['l8r'][artist]) + ')'
    #    handle.wfile.write(bytes(s['thmb'].format(artist, injectbtn, pick_thumb(fadata['artists'][artist]), '', 'a'), 'utf8'))
    
    handle.wfile.write(b'\n</div>')
    handle.wfile.write(nav.replace(b'">&', b'#perc">&'))


def serve_cached(handle, ct, file):
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
    nav = build_nav(handle, 'Search', '', False, False)
    handle.wfile.write(nav)
    handle.wfile.write(b'<div class="head" onload="search()">')
    handle.wfile.write(b'<input class="niceinp" placeholder="Search..." oninput="search(false)" />\n')
    handle.wfile.write(b'<button onclick="search(\'true\')">Search</button>\n')
    handle.wfile.write(b'</div><div class="container list"></div>\n')


def do_stats():
    seen = {**pref['seen'], **pref['ref'], **pref['rem']}
    by_day = {}
    
    for file in seen.keys():
        datestamp = str(seen[file])
        if not datestamp.isdigit():continue
        datestamp = int(str(datestamp)[:-3]) -21600# correct js being funky
        date = (datetime.datetime.utcfromtimestamp(datestamp)).isoformat()[:10]
        if date in by_day:by_day[date] += 1
        else:by_day[date] = 1
    
    ent['by_day'] = by_day


def serve_stats(handle):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format('Statistics'), 'utf8'))
    handle.wfile.write(b'<h1>Statistics</h1>\n')
    
    handle.wfile.write(b'<h2>Mark Passed</h2>\n')
    meta = sum([1 for x in ent['artists'] if x != None and x[:1] == '_'])
    la = len(ent['artists'].keys())
    lp = len(pref['passed'])
    
    handle.wfile.write(bytes('\nTotal: {:,}, Passed: {:,}, that\'s {:.02f}%\n<br>'.format(la, lp+meta, ((lp+meta)/la)*100), 'utf8'))
    
    handle.wfile.write(b'<style>td, th {text-align:center;}tr.odd {background: #424242;}</style>')
    handle.wfile.write(b'\n<h2>Seen Stats</h2>\n')
    do_stats()
    by_day = ent['by_day']
    
    tot = 0
    high = 0
    for k, c in by_day.items():
        tot += c
        if c > high:high = c
    
    imgs = len(fadata['postdata'].keys())
    
    l8r = 0
    l8rp = 0
    for k in pref['l8r']:
        v = pref['l8r'][k]
        if v == -1:v = len(ent['artists'].get(k, []))
        elif v < 0:v = -v
        l8r += v
        if k in pref['passed']:l8rp += v
    
    handle.wfile.write(bytes('\nAll: Known: {:,}, Faved: {:,}, thats\'s {:.02%}\n<br><br>'.format(l8r, imgs, tot/l8r), 'utf8'))
    handle.wfile.write(bytes('\nPassed: Known: {:,}, Faved: {:,}, thats\'s {:.02%}\n<br><br>'.format(l8rp, imgs, tot/l8rp), 'utf8'))
    
    handle.wfile.write(bytes('\nTotal: {:,}, Marked: {:,}, that\'s {:.02%}\n<br><br>\n'.format(imgs, tot, tot/imgs), 'utf8'))
    handle.wfile.write(b'<table style="min-width:20%;display:inline-block;margin:0 auto;">\n')
    handle.wfile.write(b'<tr>\n\t<th>Date</th>\n\t<th>Count</th>\n\t<th>Total %</th>\n\t<th>High %</th>\n</tr>\n')
    c = 0
    for k in sorted(by_day.keys(), reverse=True):
        ptot = by_day[k]/imgs
        phi = by_day[k]/high
        handle.wfile.write(bytes('<tr class="{4}">\n\t<td>{0}</td>\n\t<td>{1}</td>\n\t<td>{2:.02%}</td>\n\t<td>{3:.02%}</td>\n</tr>\n'.format(k, by_day[k], ptot, phi, ['', 'odd'][c%2]), 'utf8'))
        c += 1
    
    handle.wfile.write(b'</table>')


def serve_settings(handle):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format('Settings'), 'utf8'))
    sett = ent['_settings']
    
    handle.wfile.write(b'<div class="container">\nWIP\n')
    handle.wfile.write(b'</div>\n')
    handle.wfile.write(b'<br>\n<a class="btn wide on" onclick="postReload(\'/findnew\', \'\')">Findnew</a>')


def serve_drive(handle):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format('Drive'), 'utf8'))
    
    do_stats()
    today = (datetime.datetime.now() - datetime.timedelta(hours=6)).isoformat()[:10]
    if today in ent['by_day']:
        markpts = ent['by_day'][today]
    
    else:markpts = 0
    
    wordpts = 0
    for k in reversed(list(pref['read'].keys())):
        datestamp = str(pref['read'][k])
        if not datestamp.isdigit():continue
        datestamp = int(str(datestamp)[:-3]) -21600# correct js being funky
        date = (datetime.datetime.utcfromtimestamp(datestamp)).isoformat()[:10]
        if date == today:
            if k in fadata['postdata']:
                wordpts += 50 + (fadata['postdata'][k]['descwc']*.2)
    
    score = wordpts + (markpts * 100)
    level = 1
    req = 1000
    preq = 0
    while score+preq > req:
        level += 1
        preq -= req
        #req *= 1.2
        req += 500
    
    ent['drive'] = {
    	   'score': score,
    	   'preq': preq,
    	   'level': level,
    	   'req': req
    	   }
    
    disp = '<p>{:.2f} total session xp ({} mark, {:.2f} word)</p>\n<h2>Level {}</h2>\n<p>{:,.2f} xp needed to reach Level {}</p>\n'.format(score, markpts*100, wordpts, level, req-(score+preq), level+1)
    disp += '<progress value="{}" max="{}"></progress>\n<br>\n'.format(score+preq, req)
    handle.wfile.write(bytes(disp, 'utf8'))
    
    serve_mort(handle, ['shuffle', 1], head=False)

def serve_menu(handle):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format('Navigation'), 'utf8'))
    handle.wfile.write(b'<h2 style="margin-top: 10px;">Main Menu</h2>\n')
    handle.wfile.write(b'<p>Welcome to FADSRV, viewing and organising your stuff made easy.\n')
    handle.wfile.write(b'<div class="container list">\n')
    
    for path, name in [('la', 'Artist List'),
                       ('lk', 'Keyword List'),
                       ('part', 'Partially Seen'),
                       ('search', 'Search Artists'),
                       ('shuffle', 'Shuffled Artists'),
                       ('recent', 'Recent Artists'),
                       ('passed', 'Passed Artists'),
                       ('cyoa', 'Explore'),
                       ('drive', 'Drive'),
                       ('stats', 'Statistics'),
                       ('settings', 'Settings')]:
        
        handle.wfile.write(bytes(s['menubtn'].format(name, path, path, ''), 'utf8'))


def serve_data(handle, path):
    happy = False
    ret = ''
    if len(path) == 1:pass
    elif path[1] == 'pref' and len(path) >= 3:
        if path[2] in pref.keys():
            ret = json.dumps(pref[path[2]])
            happy = True
    
    elif path[1] == 'artists':
        ret = json.dumps(ent['artistsort'])
        happy = True
    
    elif path[1] == 'posts':
        ret = json.dumps(list(fadata['postdata'].keys()))
        happy = True

    if happy:
        handle.send_response(200)
        handle.send_header('Content-type', 'application/json')
        handle.end_headers()
        handle.wfile.write(bytes(ret, 'utf8'))
        return
    else:
        handle.send_response(404)
        return


class fa_req_handler(BaseHTTPRequestHandler):
    def do_GET(self):
        dur = datetime.datetime.now()
        path = urllib.parse.unquote(self.path)[1:].lower().split('/')
        if '' in path and len(path) > 1:path.remove('')
        
        handled = True
        if path[-1] == 'parrot.svg':serve_cached(self, 'image/svg+xml', '_parrot');return
        elif path[0] == 'i' or path[0] == 't':serve_image(self, path);return
        if path[0].startswith('style'):
            if not '2' in path[0]:
                serve_cached(self, 'text/css', '_css');
            
            if not is_mobile:
                ent['_css2'] = read_file('style2.css', mode='rb')
            serve_cached(self, 'text/css', '_css2')
            
            return
        
        elif self.path == '/mark.js':serve_cached(self, 'application/javascript', '_markjs');return
        elif path[0] == 'data':serve_data(self, path);return
        
        elif self.path == '/search':serve_search(self)
        elif self.path == '/drive':serve_drive(self)   
        elif self.path == '/stats':serve_stats(self)
        elif self.path == '/settings':serve_settings(self)
        else:handled = False
        
        if path == ['']:
            serve_menu(self)
            handled = True
        
        elif path[-1].isdigit():
            path[-1] = int(path[-1])
        
        elif path[-1][1:].isdigit() and path[-1][:1] == '-':
            path[-1] = int(path[-1])
        
        elif not handled:
            self.send_response(307)
            if self.path == '/':self.send_header('Location', 'la/1')
            else:self.send_header('Location', self.path + '/1')
            self.end_headers()
            return
        
        if handled:pass
        elif path[0] in ['la', 'lk', 'shuffle', 'recent', 'passed', 'part']:
            serve_mort(self, path)
        elif path[0] == 'sa':serve_artist(self, path)
        elif path[0] == 'sk':serve_keyword(self, path)
        elif path[0] == 'la':serve_list_rtist(self, path)
        elif path[0] == 'lk':serve_list_keyword(self, path)
        elif path[0] == 'cyoa':serve_cyoa(self, path)
        elif path[0] == 'view':serve_view(self, path[1:])
        elif path[0] == 'rebuild':
            build_entries(ent['_settings']['docats'])
            serve_error(self, 'rebuild', b'rebuild success')
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(s['head'].format('ERROR'), 'utf8'))
            self.wfile.write(bytes('<br><h1>Error?</h1>I couldn\'t find what you\'re looking for: ' + self.path + ' ..?<br>', 'utf8'))
            self.wfile.write(s['parrot'])
        
        dur = int((datetime.datetime.now() - dur).total_seconds() * 1000)
        self.wfile.write(b'\n<br><hr>\n<a class="btn wide on" onclick="postReload(\'/rebuild\', \'\')">Rebuild</a>')
        self.wfile.write(b'<script src="/mark.js"></script>\n')
        self.wfile.write(bytes('<p>FADSRV build#{} - Served in {}ms</p>'.format(version, dur), 'utf8'))
        return


    def do_POST(self):
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself
        
        try:
            ripdata = json.loads(post_data.decode('utf-8'))
        except:
            ripdata  = {}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        ret = {}
        if self.path == '/search' and 'query' in ripdata:
            for artist in ent['artistsort']:
                if artist == None:continue
                if artist.startswith(ripdata['query']):
                    filc = len(ent['artists'][artist])
                    ret[artist] = s['thmb'].format(artist, filc, pick_thumb(fadata['artists'][artist]), ['', ' passed'][artist in pref['passed']], 'a')
        
        elif self.path.startswith('/_flag/'):
            flag = self.path[7:]
            for file in ripdata.keys():
                if ripdata[file] == None:continue
                ret[file] = [flag, file not in pref[flag]]
                if file in pref[flag] and flag != 'l8r':del pref[flag][file]
                else:pref[flag][file] = ripdata[file]
            
            save_json(flag+'.json', pref[flag])
        
        elif self.path.startswith('/cyoa'):
            passed = set(pref['passed'].keys())
            l8r = set(pref['l8r'].keys())
            artists = [x for x in ent['artists'] if x != None and not x in passed and x.replace('_', '') not in l8r and not x.startswith('@')]
            artists += [x for x in passed if not x.replace('_', '') in l8r and x in ent['artists']]
            ret['results'] = len(artists)
            ret['artists'] = {}
            a = ripdata.get('count', 3)
            
            for artist in artists[:a]:
                filc = str(len(ent['artists'][artist]))
                aurl = artist
                for r in ['_']:aurl = aurl.replace(r, '')
                ret['artists'][aurl] = '<a href="https://www.furaffinity.net/user/{}/">[F]</a>'.format(aurl)
                ret['artists'][aurl] += s['thmb'].format(artist, filc, pick_thumb(fadata['artists'][artist]), ['', ' passed'][artist in passed], 'a')
        
        elif self.path == '/reshuffle':
            ent['artistshuffle'] = [x for x in ent['artistsort']]
            random.shuffle(ent['artistshuffle'])
            ret['status'] = 'success'
        
        elif self.path == '/rebuild':
            try:
                build_entries(ent['_settings']['docats'])
                ret['status'] = 'success'
            except:
                ret['status'] = 'error'
                ret['message'] = 'An error occurred while rebuilding, see console for more details'
        
        elif self.path == '/findnew':
            try:
                fadata_findnew()
                ent['_kwdata'] = {}
                build_entries(ent['_settings']['docats'])
                ret['status'] = 'success'
            except:
                ret['status'] = 'error'
                ret['message'] = 'An error occurred while adding new files, see console for more details'
        
        self.wfile.write(bytes(json.dumps(ret), 'utf8'))


s = {# strings
    'thb': '<span class="thumb{3}"><a href="{1}"><img loading="lazy" src="{2}" /><br>{0}</a></span>\n',
    'thmb': '<span class="thumb{3}"><a href="/s{4}/{0}/1"><img loading="lazy" src="/t/i/{2}" /><br>{0} - {1}</a></span>\n',
    'thmbf': '<span class="thumb featured"><a href="/s{3}/{0}/1"><img loading="lazy" src="/t/i/{2}" /><br>{0} - {1}<br><b>Featured</b></a></span>\n',
    'utf8': b'<meta charset="UTF-8">\n',
    '404': 'Couldn\'t find <b>{}</b><br>\nSorry about that. :(',
    'head': '<html>\n<head><title>{}</title>\n<link rel="stylesheet" href="/style.css">\n</head>\n<body>\n',
    'uft': 'Unknown file type: <b>{}</b> on <i>{}</i>\n',
    'ewc': '<div class="desc"><details><summary>Descripton (Estimated {} word count)</summary>\n{}</details>\n</div><br>\n',
    'nb': '<a class="btn{2}" href="{1}">{0}</a>\n',
    'oor': 'Out of Range.<br><a class="back" href="/{0}">Go to last valid page. Page {0}.</a>',
    'wrap': '<{0} {1}>{2}</{0}>\n',
    'parrot': b'<br>\n<!-- I\'ve been summoned, something may be wrong. -->\n<img src="/parrot.svg" alt="Got his fibre, on his way." /><br>\n',
    
    'markt': '<button id="{0}{1}" onclick="mark(\'{0}\', \'{1}\')" class="{3}">{2}</button>\n',
    'all': '<br>\nThat\'s all I\'ve got on record. {} {}{}.',
    'noby': 'Sorry, but no works by <b>{}</b> are in my database.',
    'menubtn': '<span class="menubtn{3}"><a href="{1}"><span class="{2}"></span> {0}</a></span>\n'
}


if __name__ == '__main__':
    
    mobile_path = '/storage/emulated/0/download/takeout/fad/'
    is_mobile = os.path.isdir(mobile_path)
    if is_mobile:os.chdir(r'projects3/fadsrvb/')
    
    sett = {'docats': is_mobile, 'listcount': 15, 'postcount': 25, 'over': 5}
    
    ent = {
        '_css': read_file('style.css', mode='rb'),
        '_css2': read_file('style2.css', mode='rb'),
        '_parrot': read_file('parrot.svg', mode='rb'),
        '_markjs': read_file('mark.js', mode='rb'),
        '_kwdata': {},
        '_settings': sett
    }
    
    want_cats = ent['_settings']['docats']
    print(['^-.-^ docats false', '^o,o^ docats true'][want_cats])
    if is_mobile:os.chdir(mobile_path)
    
    pref = {}
    prefm = {'seen': 'o.o', 'ref': '++', 'rem': '--', 'read': '[~]', 'tord': '[to]'}
    for file in ['passed', 'l8r'] + list(prefm.keys()):
        if os.path.isfile(file + '.json'):
            pref[file] = read_json(file + '.json')
        else:
            pref[file] = {}
    
    if os.path.isfile('blobfa'):fadata = read_json('blobfa')
    else:fadata = {'artists': {}, 'postdata': {}, 'keywords': {}}
    if os.path.isfile('blobfadesc'):fadesc = read_json('blobfadesc')
    else:fadesc = {}
    if not is_mobile:fadata_findnew()
    
    build_entries(want_cats)
    httpd = HTTPServer(('127.0.0.1', 6970), fa_req_handler)
    httpd.serve_forever()
