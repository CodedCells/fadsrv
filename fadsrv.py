from http.server import BaseHTTPRequestHandler, HTTPServer
import os, json, random, datetime, time, math, urllib, json, operator
from io import BytesIO

version = '15'

mobile_path = '/storage/emulated/0/download/takeout/fad/'
is_mobile = os.path.isdir(mobile_path)
if is_mobile:os.chdir(mobile_path)

def read_file(fn, mode='r', encoding='utf-8'):
    # read a file on a single line
    if mode == 'rb':encoding = None# saves writing it a few times
    with open(fn, mode, encoding=encoding) as file:
        data = file.read()
        file.close()
    
    return data


def read_json(fn):
    with open(fn, 'r') as file:
        return json.load(file)


def save_json(fn, d):
    with open(fn, 'w') as file:
        json.dump(d, file)
        file.close()
    return

pref = {}
for file in ['passed', 'seen', 'ref', 'rem', 'l8r']:
    if os.path.isfile(file + '.json'):
        pref[file] = read_json(file + '.json')
    else:
        pref[file] = {}


def get_prop(p, i, t='"'):
    # split string by start and stop
    return i.split(p)[1].split(t)[0]


def strdate(indate):
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    ids = indate.split(' ')
    year = int(ids[2])
    month = months.index(ids[0].lower()) + 1
    day = int(ids[1][:-3])
    hour, minute = [int(x) for x in ids[3].split(':')]
    if ids[4].lower() == 'pm':hour += 12
    if hour >= 24:hour = 0
    date = datetime.datetime(year, month, day, hour, minute)
    return date


def artistsort(postfn, docats=is_mobile):
    # sort posts to artists
    artdata = entries['_fadata']['postdata']
    artists = {}
    for post in postfn:
        k = artdata.get(post, {'artist': '_badart'}).get('artist')
        if not docats:pass
        elif post in pref['seen'].keys():k = '_seen'
        elif post in pref['ref'].keys():k = '_ref'
        elif post in pref['rem'].keys():k = '_rem'
        
        if k in artists:artists[k].append(post)
        else:artists[k] = [post]
    
    for artist in artists.keys():
        tmpid = {}
        posts = []
        for post in artists[artist]:
            mp = '_'.join(post.split('_')[1:])
            tmpid[mp] = post.split('_')[0]
            posts.append(mp)
        
        artists[artist] = []
        posts = sorted(set(posts))
        for post in posts:
            artists[artist].append(tmpid[post]+'_'+post)
    
    return artists


def is_safe_path(path):
    # prevent reading files outside of root directory
    # returns True if file is safe to serve
    return os.path.abspath(path).startswith(os.getcwd())


entries = {
    '_css': read_file('style.css', mode='rb'),
    '_parrot': read_file('parrot.svg', mode='rb'),
    '_searchjs': read_file('search.js', mode='rb'),
    '_markjs': read_file('mark.js', mode='rb'),
    '_cyoajs': read_file('cyoa.js', mode='rb'),
    '_kwdata': {}
}


def fadata_findnew():
    fadata = entries['_fadata']
    
    if 'artists' in fadata:del fadata['artists']
    
    processed = list(fadata['postdata'].keys())
    new = []
    for file in os.listdir('i/'):
        if file not in processed:
            if file.count('.') >= 2:
                new.append(file)
            else:
                print('bugged file', file)
    
    print(len(new), 'new files')
    if len(new) > 0:
        if 'pagefn' not in fadata:
            print('Loading all page files')
            fadata['pagefn'] = []
        else:
            print('Loading new page files')

        dataf = {}
        print('Loading pagefiles')
        for x in os.listdir('p/'):
            if x not in fadata['pagefn']:
                fadata['pagefn'].append(x)
            
            dataf['_'.join(x.split('_')[1:])] = 'p/'+x
        
        c = 0
        keywords = fadata['keywords']
        for file in new:
            postfn = '.'.join(file.split('.')[:-1]) + '_desc.html'
            postfn = dataf.get('_'.join(postfn.split('_')[1:]), None)
            if postfn == None:
                print('Missing data for', file)
                continue
            
            else:
                c += 1
                if c % 500 == 0:print('\t', c)
                postdf = read_file(postfn)
                fadata['postdata'][file] = {}
                pd = fadata['postdata'][file]
                
                if '@keywords' in postdf:
                    ks = get_prop('<div id="keywords">', postdf, t='</div>')
                    pd['keywords'] = [x.split('"')[0].lower() for x in ks.split('@keywords ')[1:]]
                else:
                    pd['keywords'] = ['_untagged']
                
                for k in pd['keywords']:
                    if k in keywords:keywords[k].append(file)
                    else:keywords[k] = [file]
                
                date = get_prop('popup_date">', postdf, t='</')# Nov 19th, 2015 02:34 AM
                try:pd['date'] = strdate(date).isoformat()
                except Exception as e:
                    print(date)
                    input(e)
                pd['title'] = get_prop('property="og:title" content="', postdf)
                pd['artist'] = get_prop('property="og:title" content="', postdf).split(' ')[-1].lower()
                desc = get_prop('<td valign="top" align="left" width="70%" class="alt1" style="padding:8px">', postdf, t='</td>')
                pd['description'] = '"http://www.furaffinity.net/gallery/'.join(desc.split('"/user/'))
                pd['description'] = '\n'.join([x.strip() for x in pd['description'].split('\\n')])
                pd['description'] = [x.strip() for x in pd['description'].split('\n')]
                pd['url'] = get_prop('"og:url" content="', postdf)
        
        print('\t', c)
        
        print('Saving')
        with open('fadata.json', 'w') as file:
            json.dump(fadata, file)
            file.close()


if os.path.isfile('fadata.json'):entries['_fadata'] = read_json('fadata.json')
else:entries['_fadata'] = {'artists': {}, 'postdata': {}, 'keywords': {}}
if not is_mobile:fadata_findnew()

prog = read_json('prog.json')
fmt = prog['formats']
fmt['all'] = []
for k in fmt.keys():fmt['all'] += fmt[k]
ctl = prog['content']
del prog

s = {
    'thb': '<span class="thumb{3}"><a href="{1}"><img loading="lazy" src="{2}" /><br>{0}</a></span>\n',
    'thmb': '<span class="thumb {3}"><a href="/s{4}/{0}/1"><img loading="lazy" src="/t/i/{2}" /><br>{0} - {1}</a></span>\n',
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
    'all': '<h2>Sorry, but...</h2><br>\nThat\'s all I\'ve got on record. Just {} {}{}.',
    'noby': 'Sorry, but no works by <b>{}</b> are in my database.'
}


def build_entries():
    global entries
    
    entries['generated'] = datetime.datetime.now()
    print('Building artist entries', entries['generated'])
    
    if entries['_fadata'] != {} and entries['_kwdata'] == {}:
        print('Building KWS')
        entries['_all'] = os.listdir('i/')
        entries['_kws'] = {}
        
        c = 0
        r = 0
        for key in list(entries['_fadata']['keywords'].keys()):
            #entries['_kwdata'][key] = [x for x in entries['_fadata']['keywords'][key] if x in entries['_all']]
            entries['_kwdata'][key] = entries['_fadata']['keywords'][key]
            entries['_kws'][key] = len(entries['_kwdata'][key])
            
            if entries['_kws'][key] < 2:# delete any keywords representing fewer than 2 posts
                del entries['_kws'][key]
                del entries['_kwdata'][key]
                r += 1
            
            c += 1
            if c % 1000 == 0:print('\t', c)
        
        print('\t', c, 'removed', r)
        
        entries['_kws'] = sorted(entries['_kws'].items(), key=operator.itemgetter(1))
        print('Finised', c-r, 'keywords')

    files = os.listdir('i/')
    entries['artists'] = artistsort(files)
    entries['idfn'] = {x.split('.')[0].split('_')[-1]: x for x in files}
    
    entries['featured'] = random.choice(list(entries['artists'].keys()))
    
    # merged pages
    for n in range(1, 6):
        name = '_merge{}'.format(n)
        entries['artists'][name] = []
        for artist in list(entries['artists'].keys()):
            if not artist in pref['passed'] and len(entries['artists'][artist]) == n:
                entries['artists'][name] += entries['artists'][artist]
    
    entries['artistsort'] = sorted(entries['artists'], key=lambda k: len(entries['artists'][k]))
    print('Completed {} entries'.format(len(entries['artistsort'])))


def serve_image(handle, path):
    if path[1] == 'i':path[2] = entries['idfn'].get(path[2].split('.')[0], path[2])
    spath = '/'.join(path[1:])
    ext = spath.split('.')[-1].lower()
    
    if len(spath) > 2 and os.path.isfile(spath) and is_safe_path(spath):
        handle.send_response(200)
        handle.send_header('Content-type', ctl[ext])
        handle.end_headers()
        handle.wfile.write(read_file(spath, mode='rb', encoding=None))
    
    else:
        handle.send_response(404)
        handle.send_header('Content-type', 'image/svg+xml')
        handle.end_headers()
        handle.wfile.write(entries['_parrot'])


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
    handle.wfile.write(b'<script src="/mark.js"></script>\n')
    nav = b''
    handle.wfile.write(b'<div class="head">\n')
    
    if do_prev:
        nav += bytes(s['nb'].format('Previous', index_id-1, ''), 'utf8')
    
    nav += bytes('<h1 class="btn">{0}</h1>\n'.format(name + ' ' + str(index_id)), 'utf8')
    
    if do_next:
        nav += bytes(s['nb'].format('Next', index_id+1, ''), 'utf8')
    
    return nav


def serve_keyword(handle, index_id):
    keyword = handle.path[4:].lower().split('/')[0]
    keywords = keyword.split('%20')
    if sum([1 for kw in keywords if kw in entries['_kwdata'].keys()]) == 0:
        serve_error(handle, keyword, bytes(s['noby'].format(keyword), 'utf8'))
        return
    
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    
    files = entries['_kwdata'].get(keywords[0], [])
    for kw in keywords[1:]:
        files = [f for f in files if f in entries['_kwdata'].get(kw, [])]
    
    do_nav = len(files) > 25
    nav = build_nav(handle, keyword, index_id, do_nav and index_id > 1, do_nav and index_id < math.ceil(len(files) / 25))
    handle.wfile.write(nav)
    
    handle.wfile.write(b'</div><div class="container">\n')
    if not is_mobile:
        handle.wfile.write(bytes('<a href="http://www.furaffinity.net/search/@keywords%20{}">Search FA</a><br>'.format(keyword), 'utf8'))
    
    handle.wfile.write(b'<p>' + bytes(str(len(files))+' file'+['s', ''][len(files) == 1], 'utf8') + b'</p>')
    count = write_imagedefs(files[(index_id-1)*25:index_id*25], handle)

    if count < 25:
        handle.wfile.write(bytes(s['all'].format(len(files), 'file', ['s', ''][len(files) == 1]), 'utf8'))
        handle.wfile.write(s['parrot'])
    
    handle.wfile.write(b'\n</div><div class="foot">' + nav)

def serve_artist(handle, index_id):
    artist = handle.path[4:].lower().split('/')[0]
    if artist not in entries['artists']:
        serve_error(handle, artist, bytes(s['noby'].format(artist), 'utf8'))
        handle.wfile.write(b'<script src="/mark.js"></script>\n')
        passed = ['', 'on'][artist in pref['passed']]
        handle.wfile.write(bytes(s['markt'].format(artist, 'passed', 'P', passed), 'utf8'))
        return
    
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()

    files = entries['artists'][artist]
    do_nav = len(files) > 25
    nav = build_nav(handle, artist, index_id, do_nav and index_id > 1, do_nav and index_id < math.ceil(len(files) / 25))
    handle.wfile.write(nav)
    
    handle.wfile.write(b'</div><div class="container">\n')
    if not artist.startswith('_'):
        aurl = artist
        for r in ['_']:aurl = aurl.replace(r, '')
        if not is_mobile:
            handle.wfile.write(bytes('<a href="http://www.furaffinity.net/user/{}/">Userpage</a><br>'.format(aurl), 'utf8'))
        passed = ['', 'on'][artist in pref['passed']]
        handle.wfile.write(bytes(s['markt'].format(artist, 'passed', 'P', passed), 'utf8'))
    
    handle.wfile.write(b'<p>' + bytes(str(len(files))+' file'+['s', ''][len(files) == 1], 'utf8') + b'</p>')
    count = write_imagedefs(files[(index_id-1)*25:index_id*25], handle, artist)

    if count < 25:
        handle.wfile.write(bytes(s['all'].format(len(files), 'file', ['s', ''][len(files) == 1]), 'utf8'))
        handle.wfile.write(s['parrot'])
    
    handle.wfile.write(b'\n</div><div class="foot">' + nav)


def write_imagedefs(files, handle, name=''):
    count = 0
    for file in files:
        ext = file.lower().split('.')[-1]
        post_html = ''
        fnid = file.split('.')[0].split('_')[-1] + '.' + ext
        if ext in fmt['image']:
            post_html += '<img loading="lazy" src="/i/i/{}" /><br>\n'.format(fnid)
        elif ext in fmt['text']:post_html += '<p>'+read_file('i/'+file)+'</p>\n'
        elif ext in fmt['flash']:post_html += '<embed src="/i/i/{}" /><br>\n'.format(fnid)
        else:
            post_html += s['uft'].format(ext, file)
            continue
        
        data = entries['_fadata']['postdata'].get(file, None)
        if data != None:
            post_html = '<h2>{}</h2>\n'.format(data['title']) + post_html
            desc = '\n'.join(data['description'])
            desc_word_count = len(desc.split(' '))
            if desc_word_count > 250:
                post_html += s['ewc'].format(desc_word_count, desc)
            else:
                post_html += '<div class="desc">{}</div>\n'.format(desc)
            if not is_mobile:
                post_html += '<a href="{}">View post on FA</a>\n'.format(data['url'])
            if len(data['keywords']) > 0:
                post_html += '<div class="tags">\n'
                for key in data['keywords']:
                    post_html += '\t<a href="/sk/{0}/1">{0}</a>\n'.format(key)
                post_html += '</div>\n'
        else:
            print('Missing data for', file)
            post_html += 'Error: Missing data'
        
        handle.wfile.write(bytes(post_html, 'utf8'))
        
        marks = ''
        marks += s['markt'].format(file, 'seen', 'o.o', ['', 'on'][file in pref['seen']])
        marks += s['markt'].format(file, 'ref', '++', ['', 'on'][file in pref['ref']])
        marks += s['markt'].format(file, 'rem', '--', ['', 'on'][file in pref['rem']])
        if name.startswith('_'):
            real_artist = file.split('.')[1].split('_')[0]
            marks += s['markt'].format(real_artist, 'passed', 'P', ['', 'on'][real_artist in pref['passed']])
        handle.wfile.write(bytes(marks, 'utf8'))
        
        count += 1
    
    return count


def serve_list_keyword(handle, index_id):
    
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    
    keywords = entries['_kws']
    last_file = len(keywords)
    last_page = math.ceil(last_file / 15)
    
    nav = build_nav(handle, 'keywords', index_id, index_id > -last_page, index_id < last_page)
    handle.wfile.write(nav)
    handle.wfile.write(b'</div><div class="container">\n')
    
    count = 0
    for line in range(15*(index_id-1), 15*index_id):
        if line >= last_file or -line >= last_file:
            break
        count += 1
        kw, kc = keywords[line]
        handle.wfile.write(bytes(s['thmb'].format(kw, kc, entries['_kwdata'][kw][0], '', 'k'), 'utf8'))
    
    if count == 0:
        handle.wfile.write(bytes('\n<br>'+s['oor'].format(last_page), 'utf8'))
        handle.wfile.write(s['parrot'])
    
    elif count < 14:
        handle.wfile.write(bytes(s['all'].format(last_file, 'keyword', 's'), 'utf8'))
        handle.wfile.write(s['parrot'])
    
    handle.wfile.write(b'\n</div><div class="foot">' + nav)


def serve_list_artist(handle, index_id):
    
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    
    artists = entries['artistsort']
    last_file = len(artists)
    last_page = math.ceil(last_file / 14)
    
    nav = build_nav(handle, 'artists', index_id, index_id > -last_page, index_id < last_page)
    handle.wfile.write(nav)
    handle.wfile.write(b'</div><div class="container">\n')
    
    artist = entries['featured']
    
    filec = len(entries['artists'][artist])
    handle.wfile.write(bytes(s['thmbf'].format(artist, filec, thmb_finder(artist), 'a'), 'utf8'))
    
    count = 0
    for line in range(14*(index_id-1), 14*index_id):
        if line >= last_file or -line >= last_file:
            break
        count += 1
        artist = artists[line]
        handle.wfile.write(bytes(s['thmb'].format(artist, len(entries['artists'][artist]), thmb_finder(artist), ['', 'passed'][artist in pref['passed']], 'a'), 'utf8'))
    
    if count == 0:
        handle.wfile.write(bytes('\n<br>'+s['oor'].format(entries['last']), 'utf8'))
        handle.wfile.write(s['parrot'])
    
    elif count < 14:
        handle.wfile.write(bytes(s['all'].format(str(len(entries['html'])), 'artist', 's'), 'utf8'))
        handle.wfile.write(s['parrot'])
    
    handle.wfile.write(b'\n</div><div class="foot">' + nav)


def serve_list_shuffle_artist(handle, index_id):
    
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    
    artists = list(entries['artistsort'])
    random.shuffle(artists)
    last_file = len(artists)
    last_page = math.ceil(last_file / 14)
    
    nav = build_nav(handle, 'shuffle', index_id, index_id > -last_page, index_id < last_page)
    handle.wfile.write(nav)
    handle.wfile.write(b'</div><div class="container">\n')
    
    count = 0
    for line in range(12*(index_id-1), 12*index_id):
        if line >= last_file or -line >= last_file:
            break
        count += 1
        artist = artists[line]
        if artist not in entries['artists']:
            print('bug!', artist)
            continue
        
        handle.wfile.write(bytes(s['thmb'].format(artist, len(entries['artists'][artist]), thmb_finder(artist), ['', 'passed'][artist in pref['passed']], 'a'), 'utf8'))
    
    handle.wfile.write(b'\n</div><div class="foot">' + nav)

def serve_list_recent(handle, index_id):
    
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    
    posts = sorted(os.listdir('i/'), reverse=True)
    artists = []
    for post in posts:
        artist = post.split('.')[1].split('_')[0]
        if artist not in artists:
            artists.append(artist)
    
    last_file = len(artists)
    last_page = math.ceil(last_file / 14)
    
    nav = build_nav(handle, 'recent', index_id, index_id > -last_page, index_id < last_page)
    handle.wfile.write(nav)
    handle.wfile.write(b'</div><div class="container">\n')
    
    count = 0
    for line in range(60*(index_id-1), 60*index_id):
        if line >= last_file or -line >= last_file:
            break
        count += 1
        artist = artists[line]
        if artist not in entries['artists']:
            print('bug!', artist)
            continue
        
        handle.wfile.write(bytes(s['thmb'].format(artist, len(entries['artists'][artist]), thmb_finder(artist), ['', 'passed'][artist in pref['passed']], 'a'), 'utf8'))
    
    handle.wfile.write(b'\n</div><div class="foot">' + nav)


def serve_list_passed(handle, index_id):
    
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    
    artists = sorted(pref['passed'].items(), key=operator.itemgetter(1))
    
    last_file = len(artists)
    last_page = math.ceil(last_file / 14)
    
    nav = build_nav(handle, 'passed', index_id, index_id > -last_page, index_id < last_page)
    handle.wfile.write(nav)
    handle.wfile.write(b'</div><div class="container">\n')
    
    count = 0
    prev = ''
    for line in range(15*(index_id-1), 15*index_id):
        if line >= last_file or -line >= last_file:
            break
        count += 1
        artist, datestamp = artists[line]
        
        if artist not in entries['artists']:
            print('bug!', artist)
            continue
        datestamp = int(str(datestamp)[:-3])# correct js being funky
        date = datetime.datetime.utcfromtimestamp(datestamp).isoformat()[:10]
        if date != prev:
            handle.wfile.write(bytes(s['wrap'].format('h1', '', date), 'utf8'))
            prev = str(date)
        
        handle.wfile.write(bytes(s['thmb'].format(artist, len(entries['artists'][artist]), thmb_finder(artist), '', 'a'), 'utf8'))
    
    handle.wfile.write(b'\n</div><div class="foot">' + nav)


def thmb_finder(artist):
    thmb = 'parrot.svg'
    filc = len(entries['artists'][artist])
    for t in entries['artists'][artist]:
        if t.lower().split('.')[-1] in fmt['image']:
            thmb = t.split('.')[0].split('_')[-1] + '.' + t.split('.')[-1]
            break
    
    return thmb


def serve_cyoa(handle):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    
    artists = entries['artistsort']
    handle.wfile.write(b'<script src="mark.js"></script>\n<script src="cyoa.js" onload="getNew()"></script>\n')
    nav = build_nav(handle, 'Choose your own adventure', '', False, False)
    handle.wfile.write(nav)
    handle.wfile.write(b'</div><div class="container">\n</div>\n')
    
    score = {}
    for artist in list(pref['l8r'].keys()):
        if artist in pref['passed'].keys() or artist not in entries['artists']:
            del pref['l8r'][artist]
            continue
        score[artist] = pref['l8r'][artist] - len(entries['artists'][artist])
    
    handle.wfile.write(b'<h2>By Available/Got (' + bytes(str(len(score.keys())), 'utf8') + b')</h2>\n<div class="container">\n')
    
    score = sorted(score.items(), key=operator.itemgetter(1))
    for artist, value in score[:15]:
        handle.wfile.write(bytes(s['thmb'].format(artist, str(len(entries['artists'][artist])) + ' (' + str(pref['l8r'][artist]) + ')', thmb_finder(artist), '', 'a'), 'utf8'))
    
    handle.wfile.write(b'<h2>By Available/Got (' + bytes(str(len(score)), 'utf8') + b')</h2>\n<div class="container">\n')
    for artist, value in score[-15:]:
        handle.wfile.write(bytes(s['thmb'].format(artist, str(len(entries['artists'][artist])) + ' (' + str(pref['l8r'][artist]) + ')', thmb_finder(artist), '', 'a'), 'utf8'))
    
    score = {}
    for artist in list(pref['l8r'].keys()):
        if artist in pref['passed'].keys():
            del pref['l8r'][artist]
            continue
        score[artist] = pref['l8r'][artist] / len(entries['artists'][artist])
    
    handle.wfile.write(b'<h2>By Available/Got (' + bytes(str(len(score.keys())), 'utf8') + b')</h2>\n<div class="container">\n')
    
    score = sorted(score.items(), key=operator.itemgetter(1))[:15]
    for artist, value in score:
        handle.wfile.write(bytes(s['thmb'].format(artist, str(len(entries['artists'][artist])) + ' (' + str(pref['l8r'][artist]) + ')', thmb_finder(artist), '', 'a'), 'utf8'))
    
    handle.wfile.write(b'\n</div>')


def serve_list_part(handle, index_id):
    
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    
    artistc = {}
    for file in pref['seen']:
        if file not in entries['_fadata']['postdata']:continue
        artist = entries['_fadata']['postdata'][file].get('artist', '_badart')
        if artist in artistc.keys():artistc[artist] += 1
        else:artistc[artist] = 1
    
    artistp = {}
    for artist in artistc.keys():
        if artist not in entries['artists']:print(artist, 'error');continue
        perc = artistc[artist] / len(entries['artists'][artist])
        if perc < 1:artistp[artist] = perc
    
    artists = sorted(artistp.items(), key=operator.itemgetter(1), reverse=True)
    
    last_file = len(artists)
    last_page = math.ceil(last_file / 15)
    
    nav = build_nav(handle, 'part', index_id, index_id > -last_page, index_id < last_page)
    handle.wfile.write(nav)
    handle.wfile.write(b'</div><div class="container">\n')
    
    count = 0
    for line in range(15*(index_id-1), 15*index_id):
        if line >= last_file or -line >= last_file:
            break
        count += 1
        artist, perc = artists[line]
        handle.wfile.write(bytes(s['thmb'].format(artist, str(len(entries['artists'][artist]))+' - {:.02f}%'.format(perc*100), thmb_finder(artist), ['', 'passed'][artist in pref['passed']], 'a'), 'utf8'))
    
    handle.wfile.write(b'\n</div><div class="foot">' + nav)


def serve_cached(handle, ct, file):
    handle.send_response(200)
    handle.send_header('Content-type', ct)
    handle.end_headers()
    if file == '_css':
        handle.wfile.write(read_file('style.css', mode='rb'))
        return
    
    handle.wfile.write(entries[file])


def serve_search(handle):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format('Search'), 'utf8'))
    handle.wfile.write(b'<script src="search.js"></script>\n')
    handle.wfile.write(b'''<div class="head" onload="search()">
                     <input placeholder="Search Artists..." oninput="search()" />
                     </div><div class="container"></div>\n''')


def serve_stats(handle):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format('Statistics'), 'utf8'))
    handle.wfile.write(b'<h1>Statistics</h1>\n')
    
    handle.wfile.write(b'<h2>Mark Passed</h2>\n<div class="perc">')
    perc_pass = (len(pref['passed'].keys())+8) / len(entries['artists']) * 100
    handle.wfile.write(bytes('<div class="perce" style="background:#5E485A;width:{0:.2f}%">{0:.2f}%</div>'.format(perc_pass), 'utf8'))
    perc_l8r = len(pref['l8r'].keys()) / len(entries['artists']) * 100
    handle.wfile.write(bytes('<div class="perce" style="background:#2E7A3C;width:{0:.2f}%">{0:.2f}%</div>'.format(perc_l8r), 'utf8'))
    perc = 100 - (perc_pass + perc_l8r)
    handle.wfile.write(bytes('<div class="perce" style="background:#2E282A;width:{0:.2f}%">{0:.2f}%</div></div>'.format(perc), 'utf8'))
    
    handle.wfile.write(b'\n<h2>Borked Passed Artists</h2>\n')
    for artist in pref['passed']:
        if artist not in entries['artists']:
            handle.wfile.write(bytes(artist, 'utf8') + b'<br>\n')

    handle.wfile.write(b'<style>td, th {text-align:center;}tr.odd {background: #424242;}</style>')
    handle.wfile.write(b'\n<h2>Seen Stats</h2>\n<table style="min-width:20%;display:inline-block;margin:0 auto;">\n')
    handle.wfile.write(b'<tr>\n\t<th>Date</th>\n\t<th>Count</th>\n\t<th>Total %</th>\n</tr>\n')
    seen = pref['seen']
    by_day = {}

    for file in seen.keys():
        datestamp = str(seen[file])
        if not datestamp.isdigit():continue
        datestamp = int(str(datestamp)[:-3]) -21600# correct js being funky
        date = (datetime.datetime.utcfromtimestamp(datestamp)).isoformat()[:10]
        if date in by_day:by_day[date] += 1
        else:by_day[date] = 1
    
    tot = 0#sum([by_day[k] for k in by_day.keys()])
    #high = 0
    for k, c in by_day.items():
        tot += c
        #if c > high:high = c

    c = 0
    for k in sorted(by_day.keys()):
        handle.wfile.write(bytes('<tr class="{3}">\n\t<td>{0}</td>\n\t<td>{1}</td>\n\t<td>{2:.02f}%</td>\n</tr>\n'.format(k, by_day[k], by_day[k]/tot*100, ['', 'odd'][c%2]), 'utf8'))
        c += 1
        #print(k, by_day[k], '%BEST {:.02f}%'.format(by_day[k]/high*100), '%ALL '.format(), sep='\t')

def serve_menu(handle):
    handle.send_response(200)
    handle.send_header('Content-type', 'text/html')
    handle.end_headers()
    handle.wfile.write(s['utf8'])
    handle.wfile.write(bytes(s['head'].format('Navigation'), 'utf8'))
    handle.wfile.write(b'<h2 style="font-family:Brush Script MT, Brush Script Std, cursive;">Data Management Panel</h2>\n<div class="container">\n')
    pages = [('la', 'artist list'),
            ('lk', 'keyword list'),
            ('part', 'partially seen'),
            ('search', 'artist search'),
            ('shuffle', 'artist shuffle'),
            ('recent', 'artist recent'),
            ('passed', 'artist passed'),
            ('cyoa', 'cyoa finder'),
            ('stats', 'statistics')]
    for path, name in pages:
        handle.wfile.write(bytes(s['thb'].format(name, path, 'parrot.svg', ''), 'utf8'))

class fa_req_handler(BaseHTTPRequestHandler):
    def do_GET(self):
        dur = datetime.datetime.now()
        path = urllib.parse.unquote(self.path)[1:].lower().split('/')
        if '' in path and len(path) > 1:path.remove('')
        
        if path[-1] == 'parrot.svg':serve_cached(self, 'image/svg+xml', '_parrot');return
        elif path[0] == 'i' or path[0] == 't':serve_image(self, path);return
        if self.path == '/style.css':serve_cached(self, 'text/css', '_css');return
        elif self.path == '/search.js':serve_cached(self, 'application/javascript', '_searchjs');return
        elif self.path == '/mark.js':serve_cached(self, 'application/javascript', '_markjs');return
        elif self.path == '/cyoa.js':serve_cached(self, 'application/javascript', '_cyoajs');return
        
        elif self.path == '/search':serve_search(self);return
        elif self.path == '/cyoa':serve_cyoa(self);return
        elif self.path == '/stats':serve_stats(self);return
        
        if path == ['']:
            serve_menu(self)
            return
        
        elif path[-1].isdigit():
            index_id = int(path[-1])
        
        elif path[-1][1:].isdigit() and path[-1][:1] == '-':
            index_id = int(path[-1])
        
        else:
            self.send_response(307)
            if self.path == '/':self.send_header('Location', 'la/1')
            else:self.send_header('Location', self.path + '/1')
            self.end_headers()
            return
        
        if path[0] == 'sa':serve_artist(self, index_id)
        elif path[0] == 'sk':serve_keyword(self, index_id)
        elif path[0] == 'la':serve_list_artist(self, index_id)
        elif path[0] == 'lk':serve_list_keyword(self, index_id)
        elif path[0] == 'shuffle':
            serve_list_shuffle_artist(self, index_id)
        elif path[0] == 'recent':
            serve_list_recent(self, index_id)
        elif path[0] == 'passed':
            serve_list_passed(self, index_id)
        elif path[0] == 'part':
            serve_list_part(self, index_id)
        
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(s['head'].format('ERROR'), 'utf8'))
            self.wfile.write(bytes('<br><h1>Error?</h1>I couldn\'t find what you\'re looking for: ' + self.path + ' ..?<br>', 'utf8'))
            self.wfile.write(s['parrot'])
        
        dur = int((datetime.datetime.now() - dur).total_seconds() * 1000)
        self.wfile.write(b'<a class="btn on" onclick="rebuild()">Rebuild</a>')
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
            for artist in entries['artistsort']:
                if artist.startswith(ripdata['query']):
                    filc = len(entries['artists'][artist])
                    ret[artist] = s['thmb'].format(artist, filc, thmb_finder(artist), ['', 'passed'][artist in pref['passed']], 'a')
    
        elif self.path.startswith('/_flag/'):
            flag = self.path[7:]
            for file in ripdata.keys():
                ret[file] = [flag, file not in pref[flag]]
                if file in pref[flag]:del pref[flag][file]
                else:pref[flag][file] = ripdata[file]
            
            save_json(flag+'.json', pref[flag])
        
        elif self.path.startswith('/cyoa'):
            artists = list(entries['artistsort'])
            random.shuffle(artists)
            tries = 0
            while len(ret.keys()) < 3 and tries < 9999:
                if len(artists) == 0:
                    print('OUT OF ARTISTS')
                    break
                artist = artists.pop()
                filc = len(entries['artists'][artist])
                if artist not in pref['l8r'] and artist not in pref['passed'] and not artist.startswith('_'):
                    ret[artist] = s['thmb'].format(artist, filc, thmb_finder(artist), '', 'a')
                    tries = 0
        
        elif self.path == '/rebuild':
            try:
                build_entries()
                ret['status'] = 'success'
            except:
                ret['status'] = 'error'
        
        self.wfile.write(bytes(json.dumps(ret), 'utf8'))

if __name__ == '__main__':
    build_entries()
    httpd = HTTPServer(('127.0.0.1', 6970), fa_req_handler)
    httpd.serve_forever()
