import os
from append_handler import appender

for fn in os.listdir('data_markold/'):
    print(fn)
    src = appender()
    src.read('data_markold/' + fn)
    
    v = 25000
    if fn.startswith('apx_'):
        v = 100000
    
    out = appender()
    out.write(src, filename='data_mark/' + fn, volsize=v)
