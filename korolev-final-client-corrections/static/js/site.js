'use strict';
(()=>{
const menu=document.querySelector('.menu-button'),nav=document.getElementById('navigation');
const closeMenu=()=>{nav?.classList.remove('open');menu?.setAttribute('aria-expanded','false');};
menu?.addEventListener('click',()=>{const open=nav.classList.toggle('open');menu.setAttribute('aria-expanded',String(open));});
nav?.addEventListener('click',e=>{if(e.target.closest('a'))closeMenu();});
const dialog=document.getElementById('document-dialog'),image=document.getElementById('dialog-image'),highlights=document.getElementById('document-highlights'),viewport=dialog?.querySelector('.document-viewport'),zoom=dialog?.querySelector('.document-zoom');
const links=[...document.querySelectorAll('.document-open')];let opener,index=0;
function resetZoom(){dialog?.classList.remove('is-zoomed');zoom?.setAttribute('aria-pressed','false');if(zoom)zoom.textContent='Увеличить +';if(viewport){viewport.scrollTop=0;viewport.scrollLeft=0;}}
function showDocument(i){index=(i+links.length)%links.length;const a=links[index];opener=a;resetZoom();document.getElementById('dialog-title').textContent=a.dataset.title;image.src=a.href;image.alt=a.dataset.title;dialog.querySelector('.dialog-caption').textContent=a.dataset.caption||'';highlights.replaceChildren();let rectangles=[];try{rectangles=JSON.parse(a.dataset.highlights||'[]');}catch{}for(const r of rectangles){if(!Array.isArray(r)||r.length!==4)continue;const mark=document.createElement('span');mark.className='surname-highlight';[mark.style.left,mark.style.top,mark.style.width,mark.style.height]=r.map(x=>Number(x)+'%');highlights.append(mark);}}
links.forEach((a,i)=>a.addEventListener('click',e=>{if(!dialog?.showModal)return;e.preventDefault();showDocument(i);dialog.showModal();}));
function closeDialog(){dialog?.close();opener?.focus();}
dialog?.querySelector('.dialog-close').addEventListener('click',closeDialog);
dialog?.querySelector('.document-prev').addEventListener('click',()=>showDocument(index-1));
dialog?.querySelector('.document-next').addEventListener('click',()=>showDocument(index+1));
zoom?.addEventListener('click',()=>{const on=dialog.classList.toggle('is-zoomed');zoom.setAttribute('aria-pressed',String(on));zoom.textContent=on?'Уместить −':'Увеличить +';});
dialog?.addEventListener('click',e=>{if(e.target===dialog)closeDialog();});
dialog?.addEventListener('close',()=>{resetZoom();opener?.focus();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&nav?.classList.contains('open')){closeMenu();menu?.focus();}if(dialog?.open&&!dialog.classList.contains('is-zoomed')){if(e.key==='ArrowRight'){e.preventDefault();showDocument(index+1);}if(e.key==='ArrowLeft'){e.preventDefault();showDocument(index-1);}}});
document.querySelectorAll('form[data-confirm]').forEach(f=>f.addEventListener('submit',e=>{if(!confirm(f.dataset.confirm))e.preventDefault();}));
})();
