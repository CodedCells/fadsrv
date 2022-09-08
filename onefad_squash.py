from onefad import *
import shutil, os

from PIL import Image
from io import BytesIO

load_global('cfg', 'grabpostoptions.json')
smb = cfg.get('squash_server')

if smb:
    try:
        os.listdir(smb)
    except FileNotFoundError:
        logging.warning('!!!!Cannot connect to remote!!!!')
        smb = ''

if not smb:
    logging.debug('Squash server path not set')


def prepsys(fol, file):
    if not smb:
        return False
    
    rext = file.split('.')[-1]
    
    do, fol, file = what_to_do_with(fol, file, rext)
    
    if do in ['copy', 'compress']:
        shutil.copyfile(fol + file, smb + 'add/' + file)
        if fol == 'ncomp/':
            os.remove(fol + file)
        return True
    
    return False


def what_to_do_with(fol, file, rext):
    
    if rext.lower() in ['swf', 'mid', 'txt']:
        return 'copy', fol, file
    
    if rext.lower() in ['png', 'jpg', 'jpeg', 'bmp', 'jfif']:
        try:
            src_size = os.path.getsize(fol + file)
        
        except FileNotFoundError:
            logging.warning(f'Can\'t get size of {fol}{file}')
            return 'fuck', 'idk', 'haha'
        
        if src_size < 51200:# fuke us snakk, it'll do
            return 'copy', fol, file
        
        try:
            img = Image.open(fol + file)
        
        except Exception as e:
            logging.error(f"Error while opening image {fol}{file}", exc_info=True)
            return 'fuck', 'idk', 'haha'

        try:        
            if img.mode == 'RGBA':
                po = Image.new('RGBA', img.size, color='#303030')
                img = Image.alpha_composite(po, img)
            
            img = img.convert('RGB')
        
        except OSError as e:
            logging.error(f"'Something went terribly wrong!\n{fol}{file}", exc_info=True)
            return 'fuck', 'idk', 'haha'
        
        ratio = img.size[1] / img.size[0]
        if img.size[0] > 2000 and img.size[1] > 2000:
            if ratio > 1:# tall >1
                img = img.resize((2000, int(2000*ratio)), Image.ANTIALIAS)
            
            else:# wide <1
                img = img.resize((int(2000/ratio), 2000), Image.ANTIALIAS)
        
        test_file = BytesIO()
        img.save(test_file, 'jpeg')
        
        if test_file.tell() < src_size:
            file = file.replace(rext, 'jpg')
            img.save('ncomp/' + file)
            return 'compress', 'ncomp/', file
    
    return 'copy', fol, file
