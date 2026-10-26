"""Редакция сайта Королёва Р. В. по переписке заказчика. Flask / SQLite."""
import json, logging, os, re, secrets, time, hashlib
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image, ImageOps
from sqlalchemy import Column, Integer, String, Float
from data.db_session import global_init, create_session
from data.models import Base, Setting
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except ImportError:
    pass  # Environment variables still work; install requirements for .env support.
BASE=Path(__file__).resolve().parent
STORAGE=Path(os.getenv('STORAGE_DIR', BASE/'storage')).resolve();STORAGE.mkdir(mode=0o700,parents=True,exist_ok=True)
DB=Path(os.getenv('SITE_DB',STORAGE/'site.db')).resolve()
PASSWORD=Path(os.getenv('PASSWORD_FILE',STORAGE/'password_hash.txt')).resolve()
DEFAULTS=json.loads((BASE/'defaults.json').read_text())
CONTENT=Path(os.getenv('CONTENT_FILE',STORAGE/'content.json')).resolve()
UPLOADS=BASE/'static'/'img'/'uploads';UPLOADS.mkdir(parents=True,exist_ok=True)
PUBLIC_SETTINGS={'name','role','hero_title','hero_text','phone','email','telegram','whatsapp','site_url','experience_years','experience_caption','credentials_text','show_reviews','brand_variant'}
class LoginAttempt(Base):
    __tablename__='login_attempts'
    id=Column(Integer,primary_key=True)
    client=Column(String(64),index=True,nullable=False)
    created=Column(Float,index=True,nullable=False)

def settings():
    data=dict(DEFAULTS)
    with create_session() as db:
        for row in db.query(Setting).all():
            if row.key in DEFAULTS:data[row.key]=row.value
    return data

def contents():
    p=CONTENT if CONTENT.exists() else BASE/'content.json'
    return json.loads(p.read_text(encoding='utf8'))

def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(data,encoding='utf8');temp.chmod(0o600);temp.replace(path)

def csrf():
    if not session.get('csrf_token'):session['csrf_token']=secrets.token_hex(32)
    return session['csrf_token']

def validate_csrf():
    a=session.get('csrf_token');b=request.form.get('csrf_token')
    if not isinstance(a,str) or not isinstance(b,str) or not secrets.compare_digest(a,b):abort(403)

def admin_required():
    if not session.get('logged_in'):abort(403)
    validate_csrf()

def image_upload(file):
    if not file or not file.filename:raise ValueError('Выберите изображение')
    try:
        with Image.open(file.stream) as source:
            if source.width*source.height>40_000_000:raise ValueError('Изображение слишком большое')
            source.load();im=ImageOps.exif_transpose(source)
            if 'A' in im.getbands():
                rgba=im.convert('RGBA');background=Image.new('RGBA',rgba.size,(246,243,239,255));background.alpha_composite(rgba);im=background.convert('RGB')
            else:im=im.convert('RGB')
            im.thumbnail((2200,2600));name=secrets.token_hex(14)+'.webp';im.save(UPLOADS/name,'WEBP',quality=91)
        return 'img/uploads/'+name
    except (OSError,Image.DecompressionBombError):raise ValueError('Нужен корректный JPG, PNG или WebP')

def normalize_logo(image,left_align=False):
    path=BASE/'static'/image
    with Image.open(path) as source:
        rgba=source.convert('RGBA');background=Image.new('RGBA',rgba.size,'white');background.alpha_composite(rgba)
        alpha=ImageOps.invert(ImageOps.grayscale(background.convert('RGB'))).point(lambda v:min(255,round(v*1.25)))
        box=alpha.point(lambda a:255 if a>22 else 0).getbbox()
        if box:alpha=alpha.crop(box)
        scale=min(440/alpha.width,148/alpha.height);alpha=alpha.resize((round(alpha.width*scale),round(alpha.height*scale)),Image.Resampling.LANCZOS)
        logo=Image.new('RGBA',alpha.size,(75,69,63,255));logo.putalpha(alpha)
        canvas=Image.new('RGBA',(520,200),(0,0,0,0));canvas.alpha_composite(logo,(0 if left_align else (520-logo.width)//2,(200-logo.height)//2))
        canvas.save(path,'WEBP',lossless=True)
    return image

def validate_content(data):
    required=['services','practices','clients','experience','partners','guarantees','documents','reviews']
    if not isinstance(data,dict) or set(data)!=set(required):raise ValueError('Сохраните все разделы JSON без изменения названий')
    if any(not isinstance(data[k],list) for k in required):raise ValueError('Разделы должны быть списками')
    if len(json.dumps(data,ensure_ascii=False))>300_000:raise ValueError('Слишком большой объём текста')
    for group in required:
        for item in data[group]:
            if not isinstance(item,dict):raise ValueError('Каждая запись должна быть объектом')
            if not isinstance(item.get('title'),str) or not item['title'].strip():raise ValueError('У каждой записи должно быть название title')
    for group in ['services','practices']:
        slugs=[]
        for item in data[group]:
            if not re.fullmatch(r'[a-z0-9-]{1,80}',str(item.get('slug',''))):raise ValueError('Недопустимый slug')
            slugs.append(item['slug'])
            if not isinstance(item.get('sections'),list) or not isinstance(item.get('lead'),str):raise ValueError('Нужны lead и sections для страниц')
            for sec in item['sections']:
                if not isinstance(sec,dict) or not isinstance(sec.get('title'),str):raise ValueError('У секции нужен title')
                if 'bullets' in sec and (not isinstance(sec['bullets'],list) or any(not isinstance(x,str) for x in sec['bullets'])):raise ValueError('bullets должен содержать строки')
        if len(slugs)!=len(set(slugs)):raise ValueError('slug не должен повторяться')
    for group in ['documents','experience','partners']:
        for item in data[group]:
            for key in ['image','logo','thumbnail']:
                if item.get(key):
                    val=item[key]
                    if not isinstance(val,str) or not re.fullmatch(r'img/[\w./-]+\.(?:webp|png|jpg|jpeg)',val) or '..' in val:raise ValueError('Используйте локальные изображения img/...')
            for h in item.get('highlights',[]):
                if not isinstance(h,list) or len(h)!=4 or any(not isinstance(x,(int,float)) or x<0 or x>100 for x in h) or h[0]+h[2]>100 or h[1]+h[3]>100:raise ValueError('Область выделения — четыре числа от 0 до 100')
    return data

def create_app():
    global_init(str(DB))
    secret=os.getenv('SECRET_KEY','')
    if len(secret)<32 or secret.startswith('change-me'):raise RuntimeError('Задайте случайный SECRET_KEY длиной от 32 символов. См. README.md и manage.py')
    app=Flask(__name__)
    local=os.getenv('LOCAL_PREVIEW')=='1'
    app.config.update(SECRET_KEY=secret,MAX_CONTENT_LENGTH=16*1024*1024,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SECURE=not local,SESSION_COOKIE_SAMESITE='Strict',PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    if os.getenv('ADMIN_PASSWORD') and not PASSWORD.exists():
        pw=os.environ['ADMIN_PASSWORD']
        if len(pw)<16:raise RuntimeError('ADMIN_PASSWORD должен содержать минимум 16 символов')
        atomic(PASSWORD,generate_password_hash(pw))
    @app.context_processor
    def globals_():
        s=settings();data=contents()
        contacts=[]
        if s.get('phone'):contacts.append({'label':s['phone'],'href':'tel:'+re.sub(r'[^+0-9]','',s['phone'])})
        if s.get('email'):contacts.append({'label':s['email'],'href':'mailto:'+s['email']})
        if re.fullmatch(r'[A-Za-z0-9_]{5,32}',s.get('telegram','').lstrip('@')):contacts.append({'label':'Telegram','href':'https://t.me/'+s['telegram'].lstrip('@')})
        if s.get('whatsapp'):contacts.append({'label':'WhatsApp','href':'https://wa.me/'+re.sub(r'\D','',s['whatsapp'])})
        base=s['site_url'].rstrip('/')
        public=request.endpoint not in {'admin_entry','admin_panel','login','logout','save_settings','save_content','upload','delete_document','add_partner','delete_partner'}
        structured={'@context':'https://schema.org','@type':'Person','name':s['name'],'jobTitle':s['role'],'url':base,'image':base+url_for('static',filename=s['hero_image']),'email':s['email'],'telephone':s['phone']}
        return dict(s=s,data=data,contacts=contacts,current_year=datetime.now().year,csrf_token=csrf if not public else lambda:'',public=public,canonical=base+request.path,structured=structured,preview=local)
    @app.get('/')
    def index():return render_template('index.html')
    @app.get('/services/<slug>')
    def service_page(slug):
        if slug=='court-examination':return redirect(url_for('service_page',slug='expert-opinion'),301)
        item=next((x for x in contents()['services'] if x['slug']==slug),None)
        if not item:abort(404)
        return render_template('detail.html',item=item,kind='service')
    @app.get('/practice/<slug>')
    def practice_page(slug):
        item=next((x for x in contents()['practices'] if x['slug']==slug),None)
        if not item:abort(404)
        return render_template('detail.html',item=item,kind='practice')
    @app.get('/expertise/<slug>')
    def old_expertise(slug):
        if slug not in [x['slug'] for x in contents()['practices']]:abort(404)
        return redirect(url_for('practice_page',slug=slug),301)
    @app.get('/expert')
    def expert_page():return render_template('expert.html')
    @app.get('/attestats.html')
    def credentials_page():return render_template('credentials.html')
    @app.route('/contact',methods=['GET','POST'])
    @app.route('/consent.html')
    def removed_form():return render_template('gone.html'),410
    @app.get('/privacy.html')
    def privacy():return render_template('privacy.html')
    @app.get('/healthz')
    def health():return {'status':'ok'}
    @app.get('/robots.txt')
    def robots():
        base=settings()['site_url'].rstrip('/')
        text='User-agent: *\nDisallow: /\n' if local else f'User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /login\nSitemap: {base}/sitemap.xml\n'
        return text,200,{'Content-Type':'text/plain; charset=utf-8'}
    @app.get('/sitemap.xml')
    def sitemap():
        from xml.sax.saxutils import escape
        c=contents();paths=['/','/expert','/attestats.html']+['/services/'+x['slug'] for x in c['services']]+['/practice/'+x['slug'] for x in c['practices']]
        base=settings()['site_url'].rstrip('/')
        return '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+escape(base+p)+'</loc></url>' for p in paths)+'</urlset>',200,{'Content-Type':'application/xml; charset=utf-8'}
    @app.get('/favicon.ico')
    def favicon():return redirect(url_for('static',filename='brand/favicon.svg'),302)
    @app.get('/admin')
    def admin_entry():
        if session.get('logged_in'):return redirect(url_for('admin_panel'))
        csrf();return render_template('login.html',configured=PASSWORD.exists())
    @app.post('/login')
    def login():
        validate_csrf()
        key=hashlib.sha256((request.remote_addr or 'local').encode()).hexdigest();now=time.time()
        with create_session() as db:
            db.query(LoginAttempt).filter(LoginAttempt.created<now-900).delete()
            count=db.query(LoginAttempt).filter(LoginAttempt.client==key).count();db.commit()
            if count>=6:return render_template('login.html',configured=PASSWORD.exists(),error='Слишком много попыток. Повторите через 15 минут.'),429
        pw=request.form.get('password','')
        good=PASSWORD.exists() and len(pw)<=1024 and check_password_hash(PASSWORD.read_text().strip(),pw)
        if not good:
            with create_session() as db:db.add(LoginAttempt(client=key,created=now));db.commit()
            return render_template('login.html',configured=PASSWORD.exists(),error='Неверный пароль'),401
        session.clear();session['logged_in']=True;session.permanent=True;csrf()
        return redirect(url_for('admin_panel'))
    @app.post('/submit_password')
    def no_public_setup():abort(404)
    @app.post('/logout')
    def logout():admin_required();session.clear();return redirect(url_for('index'))
    @app.get('/admin_panel')
    def admin_panel():
        if not session.get('logged_in'):return redirect(url_for('admin_entry'))
        return render_template('admin.html',content_json=json.dumps(contents(),ensure_ascii=False,indent=2))
    @app.post('/admin/save_settings')
    def save_settings():
        admin_required();updates={}
        for key in PUBLIC_SETTINGS:
            val=request.form.get(key,'').strip()
            if len(val)>4000:abort(400)
            updates[key]='1' if key=='show_reviews' and request.form.get(key)=='on' else '0' if key=='show_reviews' else val
        try:
            if not all(updates[k] for k in ['name','role','hero_title','hero_text']):raise ValueError('Заполните имя и основные тексты')
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',updates['email']):raise ValueError('Проверьте email')
            u=urlsplit(updates['site_url'])
            if u.scheme!='https' or not u.netloc or u.path not in ['','/'] or u.query or u.fragment or u.username:raise ValueError('Домен должен быть HTTPS-адресом без пути')
            if updates['brand_variant'] not in ['approved']:raise ValueError('Выберите вариант логотипа')
            if not re.fullmatch(r'\d{1,2}',updates['experience_years']):raise ValueError('Стаж — число лет')
            with create_session() as db:
                for key,val in updates.items():
                    row=db.query(Setting).filter_by(key=key).first()
                    if row:row.value=val
                    else:db.add(Setting(key=key,value=val))
                db.commit()
            flash('Настройки сохранены','success')
        except ValueError as e:flash(str(e),'error')
        return redirect(url_for('admin_panel'))
    @app.post('/admin/save_content')
    def save_content():
        admin_required()
        try:
            data=validate_content(json.loads(request.form.get('content_json','')))
            atomic(CONTENT,json.dumps(data,ensure_ascii=False,indent=2));flash('Тексты и разделы сохранены','success')
        except (ValueError,TypeError) as e:flash('Не сохранено: '+str(e),'error')
        return redirect(url_for('admin_panel')+'#content-editor')
    @app.post('/admin/upload')
    def upload():
        admin_required()
        try:
            target=request.form.get('target');image=image_upload(request.files.get('image'));title=request.form.get('title','').strip()[:200]
            if target=='portrait':
                with create_session() as db:
                    row=db.query(Setting).filter_by(key='hero_image').first()
                    if row:row.value=image
                    else:db.add(Setting(key='hero_image',value=image))
                    db.commit()
            elif target=='document':
                if not title:raise ValueError('Укажите название документа')
                data=contents();data['documents'].append({'title':title,'image':image,'category':request.form.get('category','Аттестат'),'text':request.form.get('caption','')[:1500],'highlights':[]});atomic(CONTENT,json.dumps(data,ensure_ascii=False,indent=2))
            elif target in ['experience','partners']:
                data=contents();index=int(request.form.get('item_index','-1'))
                if not 0<=index<len(data[target]):raise ValueError('Выберите организацию')
                data[target][index]['logo']=normalize_logo(image,left_align=target=='experience' and 'ИНКОМБАНК' not in data[target][index]['title']);atomic(CONTENT,json.dumps(data,ensure_ascii=False,indent=2))
            else:raise ValueError('Неизвестный тип загрузки')
            flash('Изображение добавлено','success')
        except (ValueError,TypeError) as e:flash(str(e),'error')
        return redirect(url_for('admin_panel'))
    @app.post('/admin/partner/add')
    def add_partner():
        admin_required()
        try:
            title=request.form.get('title','').strip()
            text=request.form.get('text','').strip()
            if not title or len(title)>200 or len(text)>1500:raise ValueError('Укажите название до 200 символов и описание до 1500 символов')
            logo='';file=request.files.get('image')
            if file and file.filename:logo=normalize_logo(image_upload(file))
            data=contents();data['partners'].append({'title':title,'text':text,'logo':logo})
            validate_content(data);atomic(CONTENT,json.dumps(data,ensure_ascii=False,indent=2))
            flash('Партнёр добавлен','success')
        except (ValueError,TypeError) as e:flash(str(e),'error')
        return redirect(url_for('admin_panel')+'#partners-editor')
    @app.post('/admin/partner/<int:index>/delete')
    def delete_partner(index):
        admin_required();data=contents()
        if not 0<=index<len(data['partners']):abort(404)
        data['partners'].pop(index);atomic(CONTENT,json.dumps(data,ensure_ascii=False,indent=2))
        flash('Партнёр убран с сайта. Файл логотипа остаётся на диске до ручной очистки.','success')
        return redirect(url_for('admin_panel')+'#partners-editor')
    @app.post('/admin/document/<int:index>/delete')
    def delete_document(index):
        admin_required();data=contents()
        if not 0<=index<len(data['documents']):abort(404)
        data['documents'].pop(index);atomic(CONTENT,json.dumps(data,ensure_ascii=False,indent=2));flash('Документ убран с сайта. Исходный файл остаётся на диске до ручной очистки.','success');return redirect(url_for('admin_panel'))
    @app.errorhandler(404)
    def missing(e):return render_template('404.html'),404
    @app.errorhandler(403)
    def forbidden(e):return render_template('403.html'),403
    @app.errorhandler(500)
    def internal(e):logging.exception('Ошибка приложения');return render_template('500.html'),500
    @app.after_request
    def security(response):
        response.headers['X-Content-Type-Options']='nosniff';response.headers['X-Frame-Options']='DENY';response.headers['Referrer-Policy']='strict-origin-when-cross-origin';response.headers['Permissions-Policy']='camera=(),microphone=(),geolocation=()'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.path.startswith(('/admin','/login','/logout')):response.headers['Cache-Control']='no-store';response.headers['X-Robots-Tag']='noindex, nofollow'
        if local:response.headers['X-Robots-Tag']='noindex, nofollow'
        else:response.headers['Strict-Transport-Security']='max-age=31536000'
        return response
    return app
app=create_app()
if __name__=='__main__':app.run(host='127.0.0.1',port=int(os.getenv('PORT','5001')),debug=False)
