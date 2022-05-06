import os
import shutil
import logging
import threading
import json
import math
import urllib
import html
import re
import time
import zipfile

from http.server import BaseHTTPRequestHandler, HTTPServer
from random import choice, shuffle, random
from datetime import datetime, timedelta
from operator import itemgetter
from sys import stdout
from datetime import datetime
from socketserver import ThreadingMixIn

## logging utils

def filename_date(d):
    # make it safe for path
    return d.isoformat().replace(':', '-')


def init_logger(prog,
                level=logging.DEBUG,
                disp=False):
    # configure logging
    # make it easier for other programs to find it
    
    now = datetime.now()
    fn = f'log/{prog}/'
    if not os.path.isdir(fn):os.makedirs(fn)
    fn += f'{filename_date(now)}.txt'
    
    #'name'
    fmt = ['asctime', 'levelname', 'message']
    fmt = '\t'.join(f'%({x})s' for x in fmt)
    logging.basicConfig(filename=fn,
                        encoding='utf-8',
                        level=level,
                        format=fmt)
    
    if disp:
        logging.getLogger().addHandler(logging.StreamHandler(stdout))
    
    logging.info(f'Logging Started')
    logging.info(f'Program ID: {prog}')


## apd stuff

cfg = {}
ent = {}
menus = {'pages': {}}
strings = {}

def load_global(gn, val, src={}):
    if type(val) == str:
        if not os.path.isfile(cfg['apd_dir'] + val):
            return
        
        val = read_json(cfg['apd_dir'] + val)
    
    go = globals().get(gn, src.copy())
    for k, v in val.items():
        go[k] = v
    
    return go


def crude_json(d):
    if d.isdigit():return int(d)
    elif '\\' in d:pass
    elif d.startswith('"') and d.endswith('"'):return d[1:-1]
    elif d == '[]':return []
    elif d == '{}':return {}
    
    return json.loads(d)


def prepare_apd(filename, encoding='utf8'):
    
    if not os.path.isfile(filename):
        with open(filename, 'w', encoding=encoding) as fh:
            fh.write('# apdfile ' + filename)
            fh.close()
        
        return True
    
    return False


def bigapd_reader_block(
    filename, block, do_time=False, encoding='utf8'):
    
    if block > 0:
        filename += '_{:02d}'.format(block)
    
    raw = []
    if os.path.isfile(filename):
        if do_time or os.stat(filename).st_size > 4000000:# >4mb
            logging.debug(f'Reading {filename}')
            saidname = True
        
        try:
            with open(filename, 'r', encoding=encoding) as fh:
                raw = [x.strip() for x in fh.readlines()[1:]]
                fh.close()
        
        except UnicodeDecodeError as e:
            logging.warning(f'Fucking Unicode', exc_info=True)
            with open(filename, 'rb') as fh:
                raw = [unicode_stripper(x)
                       for x in fh.readlines()[1:]]
                
                logging.debug(raw[:1])
                fh.close()
    
    return raw


def apc_read(
    filename, do_time=False, encoding='utf8', parse=True):
    
    saidname = False
    nraw = None
    
    raw = []
    block = 0
    while True:
        add = bigapd_reader_block(
            filename, block, do_time=True, encoding=encoding)
        
        if add == []:
            break
        
        raw += add
        block += 1
    
    if raw == []:
        return {}
    
    if do_time:
        t = datetime.now()
    
    out = {}
    outs = set()
    try:
        for line in raw:
            depth = line.count('\t')
            
            if depth == 2:
                pd, kd, kv = line.split('\t')
                if parse:
                    kv = json.loads(kv)
                
                if pd in outs:
                    out[pd][kd] = kv
                else:
                    outs.add(pd)
                    out[pd] = {kd: kv}
        
            elif depth == 1:
                pd, kv = line.split('\t')
                if parse:
                    kv = json.loads(kv)
                
                out[pd] = kv
            
            elif depth == 0:
                out[line] = 0
    
    except Exception as e:
        logging.error("SERIUS DATA PARSE ERROR", exc_info=True)
        logging.error(f'While reading {filename}')
        logging.error(line)
    
    if do_time:
        logging.debug((datetime.now() - t).total_seconds())
    
    return out


def bigapd_writer_block(
    filename, line, fileno, out, volsize, encoding='utf8'):
    
    filenonew = ''
    
    if volsize and line >= volsize:
        filenonew = '_{:02d}'.format(line//volsize)
        if fileno != filenonew:
            fileno = filenonew
            prepare_apd(filename+fileno)
    
    #print(line, filename.split('/')[-1]+fileno)# debug which file
    
    with open(filename + fileno, 'a', encoding=encoding) as fh:
        fh.write(out)
        fh.close()
    
    return fileno


def apc_write(
    filename, newdata, existing, depth, volsize=100000, encoding='utf8'):
    
    if existing != None:
        pass
    
    elif prepare_apd(filename):# no file
        existing = {}
    
    else:
        existing = apc_read(filename, encoding=encoding)
    
    line = len(existing)
    fileno = ''
    out = ''
    
    if depth < 1 or 2 < depth:
        logging.error(f'Unsupported depth speicified in {filename} is {depth}')
        logger.error('I Saving it as json to save your skin hopefully')
        save_json(filename+'-error.json', newdata)
        return
    
    for k, i in newdata.items():
        line += 1
        if depth == 1:
            if k not in existing:
                out += '\n{}\t{}'.format(
                    k,
                    json.dumps(i, ensure_ascii=False))
        
        elif depth == 2:
            any_post = k in existing
            for t, v in i.items():
                #if any_post and t in has[k]:continue
                out += '\n{}\t{}\t{}'.format(
                    k, t,
                    json.dumps(v, ensure_ascii=False))
        
        if line % 1000 == 0 and len(out) > 0:
            fileno = bigapd_writer_block(filename, line, fileno, out,
                                volsize=volsize, encoding=encoding)
            
            out = ''
        
    fileno = bigapd_writer_block(
        filename, line, fileno, out, volsize=volsize, encoding=encoding)


## supporting functions

def check_login(d, label):
    if 'The owner of this page' in d:
        logging.error(f'Not logged in {label}')
    
    elif 'The submission you' in d:
        logging.debug(f'404! {label}')
        return None
    
    elif 'This user cannot be found' in d:
        logging.debug(f'404! {label}')
        return None
    
    elif 'DDoS protection' in d:
        logging.warning('Cloudflare DDoS Protection')
    
    else:
        return True
    
    logging.debug('Program must HALT!')
    return False

def unicode_stripper(x):
    x = str(x)[2:-1]
    for r, w in [('\\r', '\r'),('\\n', '\n'), ('\\t', '\t'), ('\\\\', '\\'), ('\\\'', '\'')]:
        x = x.replace(r, w)
    
    return x.strip()


def get_prop(p, i, t='"', o=1, u=0):
    # split string by start and stop
    return i.split(p)[o].split(t)[u]


def is_safe_path(path):
    # prevent reading files outside of root directory
    # returns True if file is safe to serve
    return os.path.abspath(path).startswith(os.getcwd())


def plu(v, e='s'):# pluralise
    return [e, ''][v == 1]


def read_filesafe(fn, mode='r', encoding='utf8', important=True):
    try:
        data = read_file(fn, mode=mode, encoding=encoding)
    
    except FileNotFoundError:
        if important:
            logging.error('FileNotFound!\t', fn)
        
        data = ''
    
    return data

def read_file(fn, mode='r', encoding='utf8'):
    # read a file on a single line
    if mode == 'rb':
        encoding = None# saves writing it a few times
    
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


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def ii(i, w=10):# convert 1d pos to 2d pos
    return [i//10, i%10]


def wrapme(i, f='{:,}'):# wrap strings safely
    if isinstance(i, int) or isinstance(i, float):
        return f.format(i)
    
    return f.replace(':,', ':').format(i)


def readfile(fn, mode='r', encoding='utf8'):
    # read a file on a single line
    if mode == 'rb':
        encoding = None# saves writing it a few times
    
    with open(fn, mode, encoding=encoding) as file:
        data = file.read()
        file.close()
    
    return data


def safe_readfile(fn, mode='r', encoding='utf8'):
    if not os.path.isfile(fn):# no file
        return
    
    try:
        return readfile(fn, mode=mode, encoding=encoding)
    
    except Exception as e:
        logging.error(f"Failed to read {fn}", exc_info=True)
        return


def divy(di, nth=0):# separate by nth value
    out = {}
    k = set()
    
    for i, v in di.items():
        if v[nth] not in k:
            k.add(v[nth])
            out[v[nth]] = {}
        
        out[v[nth]][i] = v[1]
    
    return out


def jsdate(i):# javascript notated dates are 1000x bigger
    return datetime.utcfromtimestamp(i/1000)


def trim_date(i, t=19):
    return jsdate(i).isoformat()[:t]


def very_pretty_json(name, data, ignore_keys=[]):
    return f'''<details><summary>{name} data</summary>
<pre style="text-align: initial;">
{user_friendly_dict_formatter(data, ignore_keys=ignore_keys)}
</pre></details><br>'''


def user_firendly_line_parse(k, v):
    t = type(v)
    
    if t == str:
        return f'"{k}": "{v}"'
    
    elif t == bool:
        return f'"{k}": {str(v).lower()}'
    
    elif t == int or t == float:
        return f'"{k}": {v}'
    
    elif t == list:
        out = f'"{k}": ['
        for i in v:
            i = json.dumps(i, indent=0, ensure_ascii=False).replace('\n', ' ')
            out += f'\n {i},'
        
        if v:
            return out[:-1] + '\n]'
        return out + ']'
    
    elif t == dict:
        out = f'"{k}": {{'
        for i, j in v.items():
            out += f'\n "{i}": '
            out += json.dumps(j, indent=0, ensure_ascii=False).replace('\n', ' ') + ','
        
        if v:
            return out[:-1] + '\n}'
        return out + '}'
    
    elif v is None:
        return f'"{k}": null'
    
    else:
        logging.warn(f'Unsupported save format: {k} {t}')
        return f'{k}: null'


def user_friendly_dict_formatter(data, ignore_keys=[]):
    out = '{\n'
    line = 1
    
    for k, v in data.items():
        if k in ignore_keys:
            continue
        
        if line > 1:
            out += ',\n'
        
        out += user_firendly_line_parse(k, v)
        
        line += 1
    
    return out + '\n}'


def user_friendly_dict_saver(fn, data, ignore_keys=[]):
    out = user_friendly_dict_formatter(data, ignore_keys=ignore_keys)
    
    with open(fn, 'w') as fh:
        fh.write(out)
        fh.close()


def fa_datebox(line):
    if 'ago"' in line:# date visible
        return get_prop('popup_date">', line, t='</')
    
    # date not visible
    return get_prop('title="', line, t='"')


def strdate(indate):# only used when parsing fa pages
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    ids = indate.split(' ')
    year = int(ids[2])
    month = months.index(ids[0].lower()) + 1
    day = ids[1]
    while not day.isdigit():day = day[:-1]
    if len(day) == 0:print('DAY ERROR', ids)
    day = int(day)
    hour, minute = [int(x) for x in ids[3].split(':')]
    if len(ids) == 5:
        if ids[4].lower() == 'pm':
            hour += 12
    
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
    'docx': 'application/msword',
    'js': 'application/javascript'
    }

def ext_content(fn):
    return ctl.get(fn.split('.')[-1].lower())


def compress(zip_name, files, compression=zipfile.ZIP_DEFLATED):
     # Select the compression mode ZIP_DEFLATED for compression
     # or zipfile.ZIP_STORED to just store the file
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
