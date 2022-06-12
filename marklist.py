from onefad import *

data = {}


bu = apc_master().read('ds_tgfaved')
print('load')

data['tgffaved'] = {
    'modified': 0,
    'items': list(bu.keys())[1:],
    'lock': True
    }

del bu
'''
bu = apc_master().read('data_mark/ds_BadUnicode')
print('load')

data['badunicode'] = {
    'modified': 0,
    'items': list(bu.keys())[1:],
    'lock': True
    }

del bu

bu = apc_master().read('data_mark/ds_favedbyusers')
print('load')

data['favedbyusers'] = {
    'modified': 0,
    'items': list(bu.keys())[1:],
    'pos': True,
    'lock': True
    }
'''
print('writing')
apc_write('data_mark/ds_wdyt', data, {}, 1)
