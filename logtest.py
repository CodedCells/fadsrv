from onefad import *
import random

if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    if code_path:
        os.chdir(code_path)
    
    user_control = ':' in code_path
    init_logger('logtest', disp=user_control)

    c = 0
    while True:
        fizz = c % 3 == 0
        buzz = c % 5 == 0
        
        if fizz and buzz:
            logging.error(f'{c} Fizzbuzz')
        
        elif fizz:
            logging.info(f'{c} Fizz')
        
        elif buzz:
            logging.warning(f'{c} Buzz')
        
        else:
            logging.debug(c)
        
        c += 1
        time.sleep(random.random() * 6)
