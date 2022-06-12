from fa_parser import *
import os

if os.path.isfile('dumpusers.json'):
    with open('dumpusers.json', 'r') as fh:
        users = json.load(fh)
        fh.close()

else:
    users = requests.get('http://copi:6970/data/users').json().keys()
    with open('dumpusers.json', 'w') as fh:
        json.dump(list(users), fh)
        fh.close()


x = parse_userpsge()
x.load('userstats/h/user_endium.html')
v = x.get_all()
print(v)

x = parse_userpsge()
x.load('endium.txt')
v = x.get_all()
print(v)
input()

c = 0
buff = {}
for user in users:
    x = parse_userpsge()
    fn = f'userstats/h/user_{user}.html'
    if os.path.isfile(fn):
        x.load(fn)
        try:
            buff[user] = x.get_all()
        except Exception as e:
            print(user, e)
    
    c += 1
    if c % 500 == 0:
        print(c)
        apc_write('testusers', buff, {}, 1)
        buff = {}
