'''
general purpse utility functions and variables
'''

import json
import os
from datetime import datetime
import zipfile

def check_login(d, label):
    if 'The owner of this page' in d:
        print('Not logged in', label)
    
    elif 'The submission you' in d:
        print('404!', label)
        return None
    
    elif 'DDoS protection' in d:
        print('Cloudflare DDoS')
    
    else:
        return True
    
    input()
    exit()

def jsdate(i):
    return datetime.utcfromtimestamp(i/1000)

def divy(di):
    out = {}
    k = set()
    
    for i, vd in di.items():
        v = list(vd.keys())[0]
        
        if v not in k:
            k.add(v)
            out[v] = {}
        
        out[v][i] = vd[v]
    
    return out

def read_filesafe(fn, mode='r', encoding='utf8'):
    try:
        data = read_file(fn, mode=mode, encoding=encoding)
    except FileNotFoundError:
        print('FileNotFound!\t', fn)
        data = ''
    
    return data

def safe_perc(a, b):
    return min(
    	max(a, 1) / max(b, 1),
    	1)

def wrapme(i, f='{:,}'):
    if type(i) == int:
        return f.format(i)
    else:
        return f.replace(':,', ':').format(i)

def compress(zip_name, files):
     # Select the compression mode ZIP_DEFLATED for compression
     # or zipfile.ZIP_STORED to just store the file
     compression = zipfile.ZIP_DEFLATED
     errorlevel = []
     # create the zip file first parameter path/name, second mode
     zf = zipfile.ZipFile(zip_name, mode="w")
     
     for fn in files:
         try:
             # Add file to the zip file
             # first parameter file to zip, second filename in zip
             zf.write(fn, fn.split('/')[-1], compress_type=compression)
     
         except FileNotFoundError:
             print("couldn\'t add", fn)
             errorlevel.append(fn)
     
     # Don't forget to close the file!
     zf.close()
     return errorlevel

def write_apd(fn, d, has, depth):

    if has != None:
        pass
    
    elif os.path.isfile(fn):
        has = read_apd(fn)
    
    else:
        has = {}
        with open(fn, 'w') as fh:
            fh.write('# apdfile' + fn)
            fh.close()
    
    c = 0
    o = ''

    if depth < 1 or 2 < depth:
        print('caution bad depth speicified', depth)
        dasdsa
    
    for k, i in d.items():
        c += 1
        if depth == 1:
            if k not in has:
                o += '\n{}\t{}'.format(k, json.dumps(i))
        
        elif depth == 2:
            any_post = k in has
            for t, v in i.items():
                #if any_post and t in has[k]:continue
                o += '\n{}\t{}\t{}'.format(k, t, json.dumps(v))
        
        if c % 1000 == 0 and len(o) > 0:
            print(c)
            with open(fn, 'a') as fh:
                fh.write(o)
                fh.close()
            o = ''
    
    with open(fn, 'a') as fh:
        fh.write(o)
        fh.close()


def crude_json(d):
    if d.isdigit():return int(d)
    elif '\\' in d:pass
    elif d.startswith('"') and d.endswith('"'):return d[1:-1]
    elif d == '[]':return []
    
    return json.loads(d)


def read_apd(fn, out={}, do_time=False):
    print('Reading', fn)
    if os.path.isfile(fn):
        try:
            with open(fn, 'r', encoding='utf8') as fh:
                raw = [x.strip() for x in fh.readlines()[1:]]
                fh.close()
        except UnicodeDecodeError as e:
            print('Fucking Unicode', e)
            with open(fn, 'rb') as fh:
                raw = []
                for x in fh.readlines()[1:]:
                    x = str(x)[2:-1]
                    for r, w in [('\\r', '\r'),('\\n', '\n'), ('\\t', '\t'), ('\\\\', '\\'), ('\\\'', '\'')]:
                        x = x.replace(r, w)
                    
                    raw.append(x.strip())
                print(raw[:1])
                fh.close()
    else:
        return out
    
    if do_time:t = datetime.now()
    
    out = {}
    

    outs = set()
    for line in raw:
        depth = line.count('\t')
        
        if depth == 2:
            pd, kd, kv = line.split('\t')
            if pd in outs:
                out[pd][kd] = crude_json(kv)
            else:
                outs.add(pd)
                out[pd] = {kd: crude_json(kv)}
    
        elif depth == 1:
            pd, kv = line.split('\t')
            out[pd] = json.loads(kv)
        
        elif depth == 0:
            out[line] = 0
    
    if do_time:print((datetime.now() - t).total_seconds())
    return out


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


def save_json(fn, d, indent=None):
    with open(fn, 'w') as file:
        if indent == None:json.dump(d, file)
        else:json.dump(d, file,indent=indent)
        file.close()
    return


def get_prop(p, i, t='"', o=1):
    # split string by start and stop
    return i.split(p)[o].split(t)[0]


def is_safe_path(path):
    # prevent reading files outside of root directory
    # returns True if file is safe to serve
    return os.path.abspath(path).startswith(os.getcwd())

def plu(v, e='s'):
    return [e, ''][v == 1]

def strdate(indate):
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    ids = indate.split(' ')
    year = int(ids[2])
    month = months.index(ids[0].lower()) + 1
    day = ids[1]
    while not day.isdigit():day = day[:-1]
    if len(day) == 0:print('DAY ERROR', ids)
    day = int(day)
    hour, minute = [int(x) for x in ids[3].split(':')]
    if ids[4].lower() == 'pm':hour += 12
    if hour >= 24:hour = 0
    
    date = datetime(year, month, day, hour, minute)
    return date


def file_category(fn):
    # identify the file category
    ext = fn.lower().split('.')[-1]
    if ext in ["mp4", "webm", "mkv", "mov", "avi"]:return 'video'
    elif ext in ["wav", "flac", "mp3", "aac", "ogg"]:return 'audio'
    elif ext in ["png", "jpg", "jpeg", "bmp", "svg", "webp", "gif"]:return 'image'
    elif ext == 'swf':return 'flash'
    elif ext in ["txt", "html", "htm", "rtf"]:return 'text'
    
    return 'unknown'

def fn2id(fn):
    return fn.split('.')[0].split('_')[-1] + '.' + fn.split('.')[-1]


ctl = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'swf': 'application/x-shockwave-flash',
    'pdf': 'application/pdf',
    'ico': 'image/x-icon',
    'css': 'text/css',
    'txt': 'text/plain',
    'html': 'text/html',
    'htm': 'text/html',
    'rtf': 'application/rtf',
    'bmp': 'image/bmp',
    'svg': 'image/svg+xml',
    'webp': 'image/webp',
    'mp4': 'video/mp4',
    'webm': 'video/webm',
    'mkv': 'video/x-matroska',
    'mov': 'video/quicktime',
    'avi': 'video/x-msvideo',
    'wav': 'audio/wav',
    'flac': 'audio/flac',
    'mp3': 'audio/mpeg',
    'aac': 'audio/aac',
    'ogg': 'audio/ogg',
    'doc': 'application/msword',
    'docx': 'application/msword'
    }
