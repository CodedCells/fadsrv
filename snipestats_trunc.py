from append_handler import *
from datetime import datetime

now = datetime.now()

def convert(user):
    src = appender()
    src.read(f'data_period/{user}_period')
    outd = {}
    outh = {}
    
    lasth = 255
    lastd = 0
    unchanged = 0
    
    filed = appender()
    filed.read(f'data_period/{user}_trunc', parse=False)
    
    for period, data in sorted(src.items()):

        hour = int(period.split('T')[1][:2])
        day = int(period.split('-')[2][:2])
        
        if hour == 0 or hour < lasth or lastd != day:
            if period not in filed:
                outd[period] = data
            
            ref = data
            lasth = 0
            lastd = day
            continue
        
        lasth = hour
        lastd = day
        
        if period in filed:
            continue
        if (now - datetime.fromisoformat(period)).days < 60:
            outd[period] = data
    
    if outd:
        filed.write(outd)

users = []
with open('cfg/stat_cfg.json') as fh:
    users = json.load(fh)["collect"].keys()
    fh.close()

for user in users:
    convert(user)
