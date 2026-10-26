import os,sys,secrets,re,json,base64,mimetypes
from pathlib import Path
P=Path(__file__).resolve().parent
import tempfile
_temp=tempfile.TemporaryDirectory(prefix='korolev-preview-')
os.environ['SECRET_KEY']=secrets.token_urlsafe(48);os.environ['LOCAL_PREVIEW']='1';os.environ['STORAGE_DIR']=_temp.name
sys.path.insert(0,str(P))
from main import app
client=app.test_client()
content=json.loads((P/'content.json').read_text())
paths=['/','/expert','/attestats.html','/privacy.html']+['/services/'+x['slug'] for x in content['services']]+['/practice/'+x['slug'] for x in content['practices']]
def inline_assets(text):
 def replace(m):
  attr=m.group(1);url=m.group(2)
  if not url.startswith('/static/'):return m.group(0)
  p=P/'static'/url[len('/static/'):]
  if not p.exists():raise FileNotFoundError(p)
  mime=mimetypes.guess_type(str(p))[0] or 'application/octet-stream'
  return attr+'="data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode()+'"'
 return re.sub(r'(src|href)="(/static/[^"]+\.(?:webp|png|jpe?g|svg))"',replace,text).replace('loading="lazy"','loading="eager"')
records={}
source=client.get('/').text
for route in paths:
 text=client.get(route).text
 records[route]={'body':inline_assets(re.search(r'<body[^>]*>([\s\S]*)</body>',text).group(1)),'title':re.search(r'<title>(.*?)</title>',text).group(1)}
head=source.split('<body')[0]
head=re.sub(r'<link rel="canonical"[^>]*>','',head)
head=head.replace('<script src="/static/js/site.js" defer></script>','')
head=re.sub(r'<link rel="stylesheet" href="[^"]+">','<style>'+(P/'static/css/style.css').read_text()+'</style>',head)
icon='data:image/png;base64,'+base64.b64encode((P/'static/brand/favicon.png').read_bytes()).decode()
head=head.replace('/static/brand/favicon.png',icon)
js=(P/'static/js/site.js').read_text()
preview='''const pages=RECORDS;let route='/';
function initialize(){INIT}
function show(path,anchor=''){route=pages[path]?path:'/';document.body.innerHTML=pages[route].body;document.title=pages[route].title;initialize();window.scrollTo(0,0);if(anchor)setTimeout(()=>document.getElementById(anchor)?.scrollIntoView(),0);}
document.addEventListener('click',e=>{const a=e.target.closest('a');if(!a||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;const href=a.getAttribute('href')||'';if(href.startsWith('/')){const[path,anchor='']=href.split('#');if(pages[path]){e.preventDefault();const next=path==='/'?(anchor?'#'+anchor:'#top'):'#!'+path+(anchor?'#'+anchor:'');if(location.hash===next)show(path,anchor);else location.hash=next;}}});
function restore(){const h=location.hash;if(h.startsWith('#!')){const[path,anchor='']=h.slice(2).split('#');show(path,anchor);}else{show('/',h.slice(1));}}
window.addEventListener('hashchange',restore);restore();'''.replace('INIT',js).replace('RECORDS',json.dumps(records,ensure_ascii=False).replace('<','\\u003c'))
(P/'index.html').write_text(head+'<body id="top">'+records['/']['body']+'<script>'+preview+'</script></body></html>')
print("Автономное превью создано: index.html")
