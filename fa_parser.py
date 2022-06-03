import logging
import requests
import html
import re
import json
from datetime import datetime

## scroll to bottom for example

def get_prop(p, i, t='"', o=1, u=0):
    # split string by start and stop
    return i.split(p)[o].split(t)[u]


def fa_datebox(line):
    if 'ago"' in line:# date visible
        return get_prop('popup_date">', line, t='</')
    
    # date not visible
    return get_prop('title="', line, t='"')


def strdate(indate):# only used when parsing fa pages
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
              'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    
    ids = indate.split(' ')
    year = int(ids[2])
    month = months.index(ids[0].lower()) + 1
    day = ids[1]
    while not day.isdigit():
        day = day[:-1]
    
    if len(day) == 0:
        print('DAY ERROR', ids)
    
    day = int(day)
    hour, minute = [int(x) for x in ids[3].split(':')]
    
    if len(ids) == 5:
        if ids[4].lower() == 'pm':
            hour += 12
    
    if hour >= 24:
        hour = 0
    
    date = datetime(year, month, day, hour, minute)
    return date


class parse_basic(object):
    # base class for parsers
    def __init__(self):
        self.text = ''
        self.origin = None
        self.items = {}
        self.funcs = {
            '_online_users': self.item_online_users,
            '_status': self.item_deactive
            }
    
    def load(self, fn):# from file
        self.origin = 'file'
        self.items = {}
        try:
            with open(fn, 'r', encoding='utf8') as fh:
                self.text = fh.read()
                fh.close()
        
        except UnicodeDecodeError:
            logging.warning(f'UnicodeError {fn}')
            with open(fn, 'rb') as fh:
                self.text = str(fh.read())
                fh.close()
    
    def loads(self, text):# from string
        self.origin = 'string'
        self.items = {}
        self.text = text
    
    def loadw(self, url):# from web
        self.origin = 'web'
        self.items = {}
        self.text = requests.get(url).text
    
    def get(self, item):# get single value
        if item not in self.funcs:
            logging.error(f'Don\'t know how to parse {item}')
        
        if item not in self.items:
            self.items[item] = self.funcs[item](item)
        
        return self.items[item]
    
    def get_all(self):# get all values
        for item, func in self.funcs.items():
            v = self.items.get(item)
            if not v:
                v = func(item)
            
            if item not in self.items:
                self.items[item] = v
            
            if item == '_status' and v:
                break
        
        return {x: v for x, v in self.items.items() if v is not None}
    
    def item_online_users(self, prop):
        if self.origin != 'web':
            return
        
        user_count = get_prop('<strong>registered',
                              self.text, t='>,', o=0, u=-1).strip()
        
        if user_count.isdigit():
            user_count = int(user_count)
        
        else:
            user_count = -1
        
        return user_count
    
    def item_deactive(self, prop):
        state = None
        if '<h2>System Message</h2>' in self.text:
            if 'available to registered users only' in self.text:
                state = 'registered_only'
            
            elif 'enable the Mature or Adult content' in self.text:
                state = 'rated_content'
        
        elif ('">Click here to go back' in self.text or
            '">Continue &raquo;</a>' in self.text):
            state = 'dactive'
        
        elif ('<title>System Error</title>' in self.text and
              'This user cannot be found.' in selx.text):
            state = 'not_found'
        
        return state


class parse_user_common(parse_basic):
    def __init__(self):
        super().__init__()
        self.funcs.update({
            'username': self.item_username,
            'user_status': self.item_username,
            'user_title': self.item_username,
            'registered_date': self.item_username
            })
    
    def item_username(self, prop):
        tmp = get_prop('userpage-flex-item username">', self.text, t='</div')
        
        username = tmp.split('</')[0].split('>')[-1].strip()
        self.items['username'] = username[1:]
        statuses = {'!': 'suspended', '-': 'banned', '@': 'admin'}
        self.items['user_status'] = statuses.get(username[0], 'regular')

        user_title = None
        if '"hideonmobile">' in tmp:
            user_title = get_prop('font-small">', tmp, t='<span ').strip()

        if user_title:
            self.items['user_title'] = html.unescape(user_title)
        
        tmp = get_prop('Member Since:', tmp, t='</').strip()
        self.items['registered_date'] = strdate(tmp).timestamp()
        
        return self.items.get(prop)


class parse_userpage(parse_user_common):
    # class for parsing user pages, /user/username
    def __init__(self):
        super().__init__()
        self.funcs.update({
            'submissions': self.item_stats,
            'views': self.item_stats,
            'favs': self.item_stats,
            'comments_earned': self.item_stats,
            'comments_made': self.item_stats,
            'journals': self.item_stats,
            'accepting_trades': self.item_trades,
            'accepting_commissions': self.item_trades,
            'featured_post': self.item_featured_post,
            'recent_posts': self.item_posts,
            'recent_faved_posts': self.item_posts,
            })
    
    def item_stats(self, prop):
        for tmp in self.text.split('<span class="highlight">')[1:]:
            thing, value = tmp[:40].lower().split('</span>')
            if thing.endswith(':'):
                thing = thing[:-1]
            
            value = value.split('<br')[0].strip()
            if value.isdigit():
                value = int(value)
            
            thing = thing.replace(' ', '_')
            self.items[thing] = value
        
        return self.items.get(prop)
    
    def item_trades(self, prop):
        for tmp in self.text.split('userpage-profile-question"><strong class="highlight">')[1:]:
            thing, value = tmp[:90].lower().split('</strong></div>')
            value = value.split('<')[0].strip()
            value = value == 'yes'
            thing = thing.replace(' ', '_')
            self.items[thing] = value
        
        return self.items.get(prop)
    
    def item_posts(self, prop):
        js = get_prop('var submission_data = ', self.text, t=';\n')
        js = dict(json.loads(js))
        
        out = {}
        for postid, data in js.items():
            if (self.get('username') == data['username']) != (prop == 'recent_posts'):
                continue
            
            upload = fa_datebox(data['html_date'])
            thumb = get_prop(f'id="sid-{postid}"', self.text, t='data-width')
            out[postid] = {
                'title': html.unescape(data['title']),
                'upload_date': strdate(upload).timestamp(),
                'rating': data['icon_rating'],
                'thumb': get_prop('src="', thumb)
                }
            if prop != 'recent_posts':
                out[postid]['uploader'] = data['lower']
        
        if out:
            return out
    
    def item_featured_post(self, prop):
        fs = '<h2>Featured Submission</h2>'
        if fs not in self.text:
            return

        text = get_prop(fs, self.text, t='</section>')
        data = {
            'id': get_prop('/view/', text, t='/'),
            'title': get_prop('/">', text, t='</a>', o=2),
            'rating': get_prop('<a class="r-', text),
            'thumb': get_prop('src="', text),
            }
        
        return data


class parse_gallery(parse_user_common):
    # class for parsing user pages, /user/username
    def __init__(self):
        super().__init__()
        self.funcs.update({
            'gallery_posts': self.item_gallery_posts
            })
    
    def item_gallery_posts(self, prop):
        if 'id="gallery-gallery"' not in self.text:
            return
        
        text = get_prop('id="gallery-gallery"', self.text, t='</section')
        posts = {}
        for line in text.split('\n'):
            if '/view/' not in line:
                continue
            
            sid = get_prop('/view/', line, t='/')
            posts[sid] = {
                'title': get_prop(' title="', line, o=2),
                'rating': get_prop('class="r-', line),
                'thumb': get_prop('src="', line),
                'uploader': self.get('username')
                }
        
        return posts


class parse_postpage(parse_basic):
    # class for parsing post pages, /view/postid
    def __init__(self):
        super().__init__()
        self.funcs.update({
            'id': self.item_id,
            'upload_date': self.item_upload_date,
            'title': self.item_title,
            'full': self.item_ext,
            'ext': self.item_ext,
            'resolution': self.item_resolution,
            'uploader': self.item_uploader,
            'rating': self.item_rating,
            'tags': self.item_tags,
            'folders': self.item_folders,
            'desc': self.item_desc,
            'descwc': self.item_desc,
            'see_more': self.item_see_more
            })
    
    def item_id(self, prop):
        return get_prop('view/',
                        self.text, t='/')
    
    def item_ext(self, prop):
        full = None

        for container in [
            'class="download"><a href="',
            'class="download fullsize"><a href="'
            ]:
            if container in self.text:
                full = get_prop(container, self.text)
                break
        
        if not full:
            return
        
        self.items['full'] = full
        
        ext = full.split('.')[-1].lower()
        if len(ext) > 5:
            ext = None
        
        self.items['ext'] = ext
        
        return self.items.get(prop)
    
    def item_rating(self, prop):
        return get_prop('"twitter:data2" content="', self.text).lower()
    
    def item_uploader(self, prop):
        return get_prop(
            'property="og:title" content="', self.text).split(' ')[-1].lower()
    
    def item_title(self, prop):
        title = None
        for container, start, end in [
            ('<div class="submission-title">', '<p>', '</p>'),
            ('"classic-submission-title information">', '<h2>', '</h2>'),
            ('<table cellpadding="0" cellspacing="0" border="0" width="100%">',
             'class="cat">', '</th>')
            ]:
            if container in self.text:
                title = get_prop(container, self.text, t=end).split(start)[1]
                break
        
        if not title:
            return
            
        title = html.unescape(title).strip()
        if not title:
            title = 'Untitled'
        
        return title
    
    def item_upload_date(self, prop):
        datesplit = '<span class="hideonmobile">posted'
        oldatesplit = '<b>Posted:</b> <span'
        if datesplit in self.text:
            date = fa_datebox(get_prop(datesplit, self.text, t='</strong>'))
        
        elif oldatesplit in self.text:
            date = fa_datebox(get_prop(oldatesplit, self.text, t='</span>'))
        
        else:
            return
        
        # MMM DDth, CCYY hh:mm AM
        return strdate(date).timestamp()
    
    def item_tags(self, prop):
        ks = '@keywords _untagged"'
        
        if '"/search/@keywords' not in self.text:# no tags
            return
        
        elif '<div id="keywords">' in self.text:# old theme
            ks = get_prop('<div id="keywords">', self.text, t='</div>')
        
        elif '<section class="tags-row">' in self.text:# new theme
            ks = get_prop('<section class="tags-row">',
                          self.text, t='</section>')
        
        else:
            return
        
        return [x.split('"')[0].lower()
                for x in ks.split('@keywords ')[1:]]
    
    def item_resolution(self, prop):
        if 'Size</strong> <span>' in self.text:
            rat = get_prop('Size</strong> <span>', self.text,
                           t='</span').split(' x ')
        
        elif '<b>Resolution:</b> ' in self.text:
            rat = get_prop('<b>Resolution:</b> ', self.text,
                           t='<br>').split('x')
        
        else:
            return
        
        return [int(rat[0]), int(rat[1])]
    
    def item_folders(self, prop):
        fol = {}
        if 'Listed in Folders' not in self.text:
            return
        
        for f in get_prop('Listed in Folders</h3>',
                          self.text, t='</section').split('</div>')[:-1]:
            fpath = get_prop('href="', f)
            folid = fpath.split('/')[4]
            
            fol[folid] = {
                'path': fpath,
                'title': html.unescape(get_prop('span>', f, t='</')),
                'count': int(get_prop('title="', f, t=' '))
                }
        
        return fol
    
    def item_desc(self, prop):
        desc = None

        for container, end in [
            ('<div class="submission-description user-submitted-links">', '</div>'),
            ('<div class="submission-description">', '</div>'),
            ('<td valign="top" align="left" width="70%" class="alt1" style="padding:8px">', '</td>')
            ]:
            if container in self.text:
                desc = get_prop(container, self.text, t=end).strip()
                break
        
        if not desc:
            return
        
        desc = '"https://www.furaffinity.net/gallery/'.join(desc.split('"/user/'))
        desc = '\n'.join([x.strip() for x in desc.split('\\n')])
        desc = '\n'.join([x.strip() for x in desc.split('\n')])
        
        self.items['desc'] = desc
        self.items['descwc'] = len(re.findall(r'\w+', desc))
        
        return self.items.get(prop)
    
    def item_see_more(self, prop):
        if not '<h3>See more from <a href="' in self.text:
            return
        
        uploader = self.items.get('uploader', self.item_uploader(None))
        posts = {}
        for post in get_prop('<h3>See more from <a href="',
                             self.text, t='</section>').split(
                                 '<a href="/view/')[1:]:
            posts[post.split('/')[0]] = {
                'title': get_prop('title="', post),
                'thumb': get_prop('src="', post),
                'uploader': uploader
                }
        
        return posts


if __name__ == '__main__':
    ## example
    user = parse_userpage()
    user.loadw('https://www.furaffinity.net/user/codedcells/')
    print('\nUser Parse:')
    for k, v in user.get_all().items():
        if type(v) == dict:continue
        print(k, v)
    
    recent = user.items.get('recent_posts')
    if recent:
        print('\nIncluded Post:')
        most_recent = sorted(recent.keys(), reverse=True)[0]
        print(recent[most_recent])
        
        print('\nPost Parse:')
        post = parse_postpage()
        post.loadw(f'https://www.furaffinity.net/view/{most_recent}/')
        for k, v in post.get_all().items():
            if k == 'desc':continue
            print(k, v)
