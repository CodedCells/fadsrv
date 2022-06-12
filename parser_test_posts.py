from fa_parser import *
import os

c = 0
location = f'pm/01/'
for fn in os.listdir(location):
    x = parse_postpsge()
    x.load(location + fn)
    v = x.get_all()
    c += 1
    if c % 500 == 0:
        print(c)
