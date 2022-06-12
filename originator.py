from onefad import *
from fa_parser import *
import os

has = apc_master().read('data/sideposts')
print(f'total: {len(has):,}')

for i in range(35, 100):
    c = 0
    known = {}
    origin = {}
    location = f'pm/{i:02d}/'
    print(location, end=' working')
    for fn in os.listdir(location):
        c += 1
        if c % 200 == 0:
            print('.', end='')
        
        x = parse_postpsge()
        x.load(location + fn)
        try:
            v = x.get_all()
        except Exception:
            print('\tfailed', fn)
            continue
        
        origin[v['id']] = {k: v
                           for k, v in v.items()
                           if k in ['title', 'full', 'uploader']}
        
        for post, info in v.get('see_more', {}).items():
            known[post] = info
    
    print(f'\norigins:    {len(origin):,}')
    print(f'discovered: {len(known):,}')
    
    apc_write('data/sideposts', known, has, 1)
    has = {*has, *known}
    print(f'total:      {len(has):,}')
