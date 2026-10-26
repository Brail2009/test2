"""Локальная настройка. Пароль вводится скрыто, не через аргументы команды."""
from pathlib import Path
import os, secrets, getpass, sys, re
from werkzeug.security import generate_password_hash
BASE=Path(__file__).resolve().parent
if len(sys.argv)!=2 or sys.argv[1]!='init-admin':
    print('Использование: python manage.py init-admin');raise SystemExit(1)
env=BASE/'.env'
if not env.exists():
    env.write_text('SECRET_KEY='+secrets.token_urlsafe(48)+'\nLOCAL_PREVIEW=1\nPORT=5001\n',encoding='utf8');env.chmod(0o600)
else:
    values=env.read_text(encoding='utf8')
    match=re.search(r'^SECRET_KEY=(.*)$',values,re.M)
    current=match.group(1).strip().strip('"').strip("'") if match else ''
    if len(current)<32 or current.startswith('change-me'):
        line='SECRET_KEY='+secrets.token_urlsafe(48)
        values=re.sub(r'^SECRET_KEY=.*$',line,values,flags=re.M) if match else line+'\n'+values
        env.write_text(values,encoding='utf8');env.chmod(0o600)
try:
    from dotenv import load_dotenv
    load_dotenv(env)
except ImportError:
    pass
pw=getpass.getpass('Новый пароль администратора (от 16 символов): ')
if len(pw)<16 or pw!=getpass.getpass('Повторите пароль: '):
    print('Пароли не совпадают или слишком короткие');raise SystemExit(1)
storage=Path(os.getenv('STORAGE_DIR',BASE/'storage'));storage.mkdir(mode=0o700,parents=True,exist_ok=True)
p=Path(os.getenv('PASSWORD_FILE',storage/'password_hash.txt'));p.write_text(generate_password_hash(pw),encoding='utf8');p.chmod(0o600)
print('Пароль сохранён. Для локального запуска: python main.py. Перед публикацией установите LOCAL_PREVIEW=0 и HTTPS.')
