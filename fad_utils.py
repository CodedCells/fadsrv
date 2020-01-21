'''
general purpse utility functions and variables
'''

import json, os, datetime

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


def get_prop(p, i, t='"'):
    # split string by start and stop
    return i.split(p)[1].split(t)[0]


def is_safe_path(path):
    # prevent reading files outside of root directory
    # returns True if file is safe to serve
    return os.path.abspath(path).startswith(os.getcwd())


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
    "ico": "image/x-icon",
    "css": "text/css",
    "txt": "text/plain",
    "html": "text/html",
    "htm": "text/html",
    "rtf": "application/rtf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "bmp": "image/bmp",
    "svg": "image/svg+xml",
    "webp": "image/webp",
    "gif": "image/gif",
    "mp4": "video/mp4",
    "webm": "video/webm",
    "mkv": "video/x-matroska",
    "mov": "video/quicktime",
    "avi": "video/x-msvideo",
    "wav": "audio/wav",
    "flac": "audio/flac",
    "mp3": "audio/mpeg",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "swf": "application/x-shockwave-flash"
    }
