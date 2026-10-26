'use strict';
(()=>{
 const root=new URL('../../',document.currentScript.src);
 const routes={"/":"index.html","/expert":"expert/index.html","/attestats.html":"attestats.html","/privacy.html":"privacy.html","/services/expert-opinion":"services/expert-opinion/index.html","/services/expert-review":"services/expert-review/index.html","/services/court-representation":"services/court-representation/index.html","/services/consulting":"services/consulting/index.html","/practice/criminal":"practice/criminal/index.html","/practice/civil":"practice/civil/index.html","/practice/arbitration":"practice/arbitration/index.html"};
 if(location.hash.startsWith('#!')){
  const [path,anchor='']=location.hash.slice(2).split('#');
  if(routes[path]){const next=new URL(routes[path],root);next.hash=anchor;location.replace(next.href);return;}
 }
 const actual=new URL(location.href);actual.hash='';actual.search='';
 const canonical=document.querySelector('link[rel="canonical"]');if(canonical)canonical.href=actual.href;
 const ogUrl=document.querySelector('meta[property="og:url"]');if(ogUrl)ogUrl.content=actual.href;
 const ogImage=document.querySelector('meta[property="og:image"]');if(ogImage)ogImage.content=new URL(ogImage.content,document.baseURI).href;
 const schema=document.querySelector('script[type="application/ld+json"]');
 if(schema){try{const data=JSON.parse(schema.textContent);data.url=root.href;if(ogImage)data.image=ogImage.content;schema.textContent=JSON.stringify(data);}catch{}}
})();
