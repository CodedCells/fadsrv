from logging_grab_userstats import *


def check_user(user, data, when):
    checked = data.get('_meta')
    if not checked:
        return 9999
    
    checked = datetime.fromtimestamp(checked)
    
    if data.get('error') == 'not_found':
        return
    
    new_post = data.get('new_post')
    days = (when - checked).days
    days = min(days, 48)
    if days < 14:
        return
    
    return days
    
    diff = 56
    if new_post:
        new_post = datetime.fromtimestamp(new_post)
        diff = abs(new_post - checked).days
    
    if diff > days:
        return diff - days
    

def should_check(users, when):
    check = []
    for user in users:
        data = userstats.get(user, {})
        priority = check_user(user, data, when)
        if priority is not None:
            check.append((priority, user))
    
    return {user: priority for priority, user in sorted(check, reverse=True)}


def main():
    global userstats
    
    session_create()
    
    userstats = appender()
    userstats.read(cfg['apd_dir'] + 'userstats')
    
    users = load_users()
    update = should_check(users, datetime.now())
    
    if not update:
        logging.info('No users to update')
        return
    
    work = len(update)
    logging.info(f'Updating {work:,} users')
    
    c = 0
    for user in update:
        if c:
            time.sleep(cfg['speed'] * 2)
        
        c += 1
        get_user_save(user, userstats)
        
        if c % 500 == 0:
            logging.info(f'Updated {c:,} of {work:,} userstats')
            if ent['online'] > 10000:
                logging.info(f'Halting, {ent["online"]:,} registerd users')
                break
    
    logging.info('Finished updating user stats')


if __name__ == '__main__':
    code_path = os.path.dirname(__file__)
    if code_path:
        os.chdir(code_path)
    
    user_control = ':' in code_path
    init_logger('refrssh_userstats', disp=user_control)
    configgy("userstats")
    
    try:
        main()
    
    except Exception as e:
        logging.error("Exception occurred", exc_info=True)
    
    logging.info('Done')
    
    poke_servers(cfg['poke_servers'])
