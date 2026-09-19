/* ===========================================================================
   4. ENGINE — fixed layout, pannable camera, continuous time interpolation.
      Nodes never move in world space: scrubbing animates size/glow/edges only.
   ========================================================================= */
const cv=document.getElementById('cv'), ctx=cv.getContext('2d',{alpha:false});
const N=D.days.length, LAST=N-1, NODE={};
D.nodes.forEach(n=>NODE[n.id]=n);
const IN={}, OUT={};                       // adjacency for the hover card
D.edges.forEach(e=>{(OUT[e.a]=OUT[e.a]||[]).push(e);(IN[e.b]=IN[e.b]||[]).push(e);});

let W=0,H=0,dpr=1;
let targetT=LAST, curT=LAST, playing=false;
let hoverId=null, ripples=[], glitchUntil=0, moshAmt=0;
/* shadowBlur is by far the most expensive canvas op — ~300 shadowed draws/frame was
   what stalled pan/zoom. GLOW drops to 0 while the user is interacting and eases
   back once things settle, so motion stays at 60fps and stillness stays pretty. */
let lastInteract=0, GLOW=1;
const poke=()=>{lastInteract=performance.now();};
const view={x:0,y:0,k:1, tx:0,ty:0,tk:1, vx:0,vy:0};   // current + target + pan velocity
const chainOn={}; D.chains.forEach(c=>chainOn[c]=true);

const lerp=(a,b,f)=>a+(b-a)*f, smooth=f=>f*f*(3-2*f);
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
function sample(arr,t){const i=clamp(Math.floor(t),0,LAST), j=Math.min(LAST,i+1);
  return lerp(arr[i],arr[j],smooth(t-i));}
const fmt=v=>v>=1e9?'$'+(v/1e9).toFixed(2)+'B':v>=1e6?'$'+(v/1e6).toFixed(1)+'M':
             v>=1e3?'$'+Math.round(v/1e3)+'k':'$'+Math.round(v);
const cc=c=>CONFIG.chain[c]||CONFIG.fallback;
const _cssv={};
const CSSV=v=>_cssv[v]||(_cssv[v]=getComputedStyle(document.documentElement).getPropertyValue(v).trim());
function mix(a,b,f){ // hex blend — chain hue at rest -> hot -> reserved accent
  const p=x=>[parseInt(x.slice(1,3),16),parseInt(x.slice(3,5),16),parseInt(x.slice(5,7),16)];
  const A=p(a),B=p(b);
  return `rgb(${Math.round(lerp(A[0],B[0],f))},${Math.round(lerp(A[1],B[1],f))},${Math.round(lerp(A[2],B[2],f))})`;
}
let MCMAX=1,USDMAX=1;
D.nodes.forEach(n=>{MCMAX=Math.max(MCMAX,...n.mc);USDMAX=Math.max(USDMAX,...n.usd);});
const rRing=v=>v<=0?0:CONFIG.ringMin+(CONFIG.ringMax-CONFIG.ringMin)*Math.sqrt(v/MCMAX);
const rCore=v=>v<=0?0:CONFIG.coreMin+(CONFIG.coreMax-CONFIG.coreMin)*Math.sqrt(v/USDMAX);

/* ---- camera ---- */
const BASE=()=>Math.min(W,H)*0.38;
const sx=n=>W/2+(n.x*BASE()+view.x)*view.k;
const sy=n=>H/2+(n.y*BASE()+view.y)*view.k;
function resize(){dpr=Math.min(devicePixelRatio||1,2);W=innerWidth;H=innerHeight;
  cv.width=W*dpr;cv.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);}
/* Fit every node inside the *visible* area — the right rail covers part of the
   canvas, so the usable box is inset on that side and the camera centres on it. */
function fit(animate){
  const railW = rail.classList.contains('hidden') ? 0 : rail.offsetWidth;
  const padL=34, padR=railW+34, padT=118, padB=104;
  const availW=Math.max(200,W-padL-padR), availH=Math.max(200,H-padT-padB);
  /* Bound the node CENTRES and add one modest world-space margin. Reserving each
     node's largest-ever ring over-shrinks the whole map for a handful of mega-caps. */
  let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;
  for(const n of D.nodes){
    if(!shown(n))continue;
    x0=Math.min(x0,n.x);x1=Math.max(x1,n.x);
    y0=Math.min(y0,n.y);y1=Math.max(y1,n.y);
  }
  if(x0>x1)return;
  const M=CONFIG.ringMax*0.55/BASE();              // one shared margin, not per-node
  x0-=M;x1+=M;y0-=M;y1+=M;
  const k=clamp(Math.min(availW/((x1-x0)*BASE()),availH/((y1-y0)*BASE()))*CONFIG.fitFill,
                CONFIG.zoomMin,CONFIG.zoomMax);
  const cx=(x0+x1)/2*BASE(), cy=(y0+y1)/2*BASE();
  const boxCx=padL+availW/2, boxCy=padT+availH/2;
  view.tk=k;
  view.tx=(boxCx-W/2)/k-cx;
  view.ty=(boxCy-H/2)/k-cy;
  if(!animate){view.k=view.tk;view.x=view.tx;view.y=view.ty;}
}
function reframe(){fit(true);}

/* ---- edge strength within the visible time window ---- */
function edgeAt(e,t){
  let best=0;const lo=Math.max(0,Math.floor(t)-CONFIG.edgeWindow),
                 hi=Math.min(LAST,Math.ceil(t)+CONFIG.edgeWindow);
  for(let i=lo;i<=hi;i++){const w=e.w[i];if(!w)continue;
    best=Math.max(best,w*Math.max(0,1-Math.abs(i-t)/(CONFIG.edgeWindow+1)));}
  return best;
}
const shown=n=>chainOn[n.chain];
/* Draw order is by rank and never changes — sorting 80 nodes every frame was pure
   waste. Rebuilt only when a chain filter toggles. */
let ORDER=[];
function rebuildOrder(){ORDER=D.nodes.filter(shown).sort((a,b)=>b.rank-a.rank);}
/* Edge selection depends only on (time, hover) — cache it between frames. */
let EDGE_CACHE={t:-1,h:null,list:[]};
function edgesFor(t){
  if(Math.abs(EDGE_CACHE.t-t)<0.02 && EDGE_CACHE.h===hoverId) return EDGE_CACHE.list;
  const live=[];
  for(const e of D.edges){
    const w=edgeAt(e,t);
    if(w<CONFIG.edgeMinShared) continue;
    if(!shown(NODE[e.a])||!shown(NODE[e.b])) continue;
    live.push({e,w});
  }
  live.sort((p,q)=>q.w-p.w);
  const list = hoverId ? live.filter(r=>r.e.a===hoverId||r.e.b===hoverId)
                       : live.slice(0,CONFIG.maxEdges);
  EDGE_CACHE={t,h:hoverId,list};
  return list;
}

function draw(t){
  ctx.fillStyle='#05030B';ctx.fillRect(0,0,W,H);
  const now=performance.now(), k=view.k;
  const settled=(now-lastInteract)>MOTION.idleMs;
  GLOW+=((settled?1:0)-GLOW)*(settled?0.10:0.45);
  const blur=(base,mult)=>GLOW<0.03?0:base*(mult===undefined?1:mult)*GLOW;
  /* grid drifts with the camera so panning feels anchored */
  ctx.save();ctx.strokeStyle='rgba(157,78,221,.055)';ctx.lineWidth=1;
  const gs=54*k, ox=(view.x*k)%gs, oy=(view.y*k)%gs;
  for(let x=ox%gs;x<W;x+=gs){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();}
  for(let y=oy%gs;y<H;y+=gs){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
  ctx.restore();

  const rel=new Set();
  if(hoverId){rel.add(hoverId);
    (OUT[hoverId]||[]).forEach(e=>rel.add(e.b));(IN[hoverId]||[]).forEach(e=>rel.add(e.a));}
  const dim=id=>hoverId?(rel.has(id)?1:CONFIG.focusDim):1;

  /* ---------- rotations ---------- */
  const drawn=edgesFor(t);
  ctx.save();ctx.lineCap='round';
  for(const {e,w} of drawn){
    const a=NODE[e.a],b=NODE[e.b];
    const x1=sx(a),y1=sy(a),x2=sx(b),y2=sy(b);
    if(Math.max(x1,x2)<-80||Math.min(x1,x2)>W+80||Math.max(y1,y2)<-80||Math.min(y1,y2)>H+80)continue;
    const mx=(x1+x2)/2+(y2-y1)*.15, my=(y1+y2)/2-(x2-x1)*.15;
    const vis=Math.min(dim(e.a),dim(e.b));
    const alpha=Math.min(CONFIG.edgeMaxAlpha,w/7)*vis;
    /* when focused, colour by direction: green feeds in, red feeds out */
    /* While focused, direction beats chain identity: green feeds IN, red feeds OUT.
       The glow has to follow the same colour or it washes the coding out. */
    let g, glowCol=cc(b.chain).hot;
    if(hoverId===e.b){glowCol=CSSV('--in'); g=glowCol;}
    else if(hoverId===e.a){glowCol=CSSV('--out'); g=glowCol;}
    else{const lg=ctx.createLinearGradient(x1,y1,x2,y2);
      lg.addColorStop(0,cc(a.chain).hot);lg.addColorStop(1,cc(b.chain).hot);g=lg;}
    ctx.globalAlpha=alpha;ctx.strokeStyle=g;
    ctx.lineWidth=Math.min(3.2,(0.5+w*0.24))*Math.min(1.5,k)*(hoverId?1.25:1);
    ctx.shadowBlur=blur(11*Math.min(1.4,k));ctx.shadowColor=glowCol;
    ctx.beginPath();ctx.moveTo(x1,y1);ctx.quadraticCurveTo(mx,my,x2,y2);ctx.stroke();
    const nP=Math.min(4,1+Math.floor(w/3));
    for(let i=0;i<nP;i++){
      const p=((now*MOTION.particleRate*(0.7+w*0.05))+i/nP+e.a.length*0.07)%1;
      const q=1-p,bx=q*q*x1+2*q*p*mx+p*p*x2,by=q*q*y1+2*q*p*my+p*p*y2;
      ctx.globalAlpha=Math.min(1,alpha*2.5);ctx.fillStyle=glowCol;ctx.shadowBlur=0;
      ctx.beginPath();ctx.arc(bx,by,(1.7+w*.07)*Math.min(1.6,k),0,7);ctx.fill();
      if(p>0.97){ripples.push({x:x2,y:y2,c:cc(b.chain).hot,t0:now,r:rRing(sample(b.mc,t))*k});
        if(w>=CONFIG.glitchShared)glitchUntil=now+MOTION.glitchMs;}
    }
  }
  ctx.restore();
  ripples=ripples.filter(r=>now-r.t0<MOTION.rippleMs);
  ctx.save();
  for(const r of ripples){const f=(now-r.t0)/MOTION.rippleMs;
    ctx.globalAlpha=(1-f)*.45;ctx.strokeStyle=r.c;ctx.lineWidth=1.5;
    ctx.shadowBlur=blur(16);ctx.shadowColor=r.c;
    ctx.beginPath();ctx.arc(r.x,r.y,r.r+f*30,0,7);ctx.stroke();}
  ctx.restore();

  /* ---------- nodes: biggest drawn last so they read on top ---------- */
  const budget=CONFIG.labelBudget(k);
  for(const n of ORDER){
    const mc=sample(n.mc,t), usd=sample(n.usd,t), act=sample(n.act,t);
    if(mc<=0&&usd<=0)continue;
    const born=clamp((t-n.first+1.2)/1.6,0,1); if(born<=0)continue;
    const x=sx(n),y=sy(n);
    const R=rRing(mc)*born*k, C=Math.min(R*.92,rCore(usd)*born*k);
    if(x<-R-40||x>W+R+40||y<-R-40||y>H+R+40){n._sx=null;continue;}
    const heat=Math.pow(Math.min(1,act*CONFIG.activeBoost),CONFIG.activeGamma);
    const A=(CONFIG.dormantAlpha+(1-CONFIG.dormantAlpha)*heat)*born*dim(n.id);
    const hot=hoverId===n.id;
    /* hue = chain identity; heat drives it toward the reserved accent */
    const col=mix(cc(n.chain).rest,cc(n.chain).hot,Math.min(1,heat*1.25));
    const core=heat>0.72?mix(cc(n.chain).hot,'#EAFBFF',(heat-0.72)/0.28):col;
    ctx.save();
    ctx.globalAlpha=.92*A;ctx.strokeStyle=col;ctx.lineWidth=(hot?2.3:1.25)*Math.min(1.6,k);
    const bigEnough=R>=CONFIG.glowMinPx;
    ctx.shadowBlur=bigEnough?blur(CONFIG.glow.ring*(hot?1.8:heat),Math.min(1.5,k)):0;
    ctx.shadowColor=col;
    ctx.beginPath();ctx.arc(x,y,Math.max(.8,R),0,7);ctx.stroke();
    if(C>.6){
      ctx.globalAlpha=.30*A;ctx.fillStyle=core;
      ctx.shadowBlur=bigEnough?blur(CONFIG.glow.core*heat):0;
      ctx.beginPath();ctx.arc(x,y,C,0,7);ctx.fill();
      ctx.globalAlpha=.88*A;ctx.beginPath();ctx.arc(x,y,C*.42,0,7);ctx.fill();
    }
    if(hot||n.rank<budget||R>=CONFIG.labelMinPx){
      ctx.globalAlpha=Math.min(1,born*dim(n.id)*(hot?1:.5+heat*.5));
      ctx.shadowBlur=blur(7);ctx.shadowColor='#05030B';ctx.fillStyle=hot?'#EAFBFF':'#E9E4FF';
      ctx.font=`600 ${clamp(10*Math.min(1.35,k),9,14)}px "Chakra Petch",sans-serif`;
      ctx.textAlign='center';
      ctx.fillText(n.sym.slice(0,14),x,(n.sym.charCodeAt(0)%2)?y+R+13:y-R-6);
    }
    ctx.restore();
    n._sx=x;n._sy=y;n._sr=Math.max(R,10);
  }

  /* ---------- datamosh: RGB split driven by scrub velocity ---------- */
  if(moshAmt>0.4){
    const off=Math.min(MOTION.moshMax,moshAmt*MOTION.moshGain);
    ctx.save();ctx.globalCompositeOperation='lighter';ctx.globalAlpha=.30;
    ctx.drawImage(cv,-off*dpr,0,cv.width,cv.height,-off,0,W,H);
    ctx.globalAlpha=.22;
    ctx.drawImage(cv, off*dpr,0,cv.width,cv.height, off,0,W,H);
    ctx.restore();
  }
  /* scanline tear on a large rotation */
  if(now<glitchUntil){
    const f=(glitchUntil-now)/MOTION.glitchMs;
    for(let i=0;i<4;i++){
      const yy=Math.random()*H, hh=4+Math.random()*16, dx=(Math.random()-.5)*34*f;
      ctx.drawImage(cv,0,yy*dpr,cv.width,hh*dpr,dx,yy,W,hh);
    }
  }
  paintHUD(t);
  paintRail(t);
}
function paintHUD(t){
  const i=clamp(Math.round(t),0,LAST);
  document.getElementById('date').textContent=D.days[i];
  document.getElementById('status').textContent=
    `${D.stats.cohort} wallets · ${D.nodes.length} tokens · frame ${i+1}/${N} · zoom ${view.k.toFixed(2)}×`;
  const p=t/LAST*100;
  document.getElementById('headbar').style.left=p+'%';
  document.getElementById('fillbar').style.width=p+'%';
  document.getElementById('track').setAttribute('aria-valuenow',Math.round(p));
}

/* ---- main loop ---- */
let lastT=LAST;
function frame(){
  if(playing){targetT+=MOTION.playSpeed*rate();if(targetT>LAST){targetT=LAST;setPlay(false);}}
  curT+=(targetT-curT)*MOTION.scrubEase;
  if(Math.abs(targetT-curT)<0.0004)curT=targetT;
  moshAmt=moshAmt*0.82+Math.abs(curT-lastT)*0.9; lastT=curT;
  if(moshAmt>0.35||Math.abs(view.tk-view.k)>0.002||Math.abs(view.vx)+Math.abs(view.vy)>0.4)poke();
  if(!dragging){view.tx+=view.vx;view.ty+=view.vy;view.vx*=MOTION.panFriction;view.vy*=MOTION.panFriction;}
  view.x+=(view.tx-view.x)*MOTION.zoomEase;
  view.y+=(view.ty-view.y)*MOTION.zoomEase;
  view.k+=(view.tk-view.k)*MOTION.zoomEase;
  draw(curT);
  requestAnimationFrame(frame);
}

/* ===========================================================================
   5. INTERACTION — pan, zoom, hover, transport
   ========================================================================= */
let dragging=false,px0=0,py0=0,moved=0;
cv.addEventListener('pointerdown',e=>{dragging=true;moved=0;poke();px0=e.clientX;py0=e.clientY;
  view.vx=view.vy=0;cv.setPointerCapture(e.pointerId);cv.classList.add('drag');});
cv.addEventListener('pointermove',e=>{
  if(dragging){
    const dx=(e.clientX-px0)/view.k, dy=(e.clientY-py0)/view.k;
    view.tx+=dx;view.ty+=dy;view.x+=dx;view.y+=dy;
    view.vx=dx*0.85;view.vy=dy*0.85;moved+=Math.abs(dx)+Math.abs(dy);poke();
    px0=e.clientX;py0=e.clientY;hideCard();return;
  }
  hoverTest(e.clientX,e.clientY);
});
addEventListener('pointerup',()=>{dragging=false;cv.classList.remove('drag');});
cv.addEventListener('pointerleave',()=>{hoverId=null;hideCard();});
cv.addEventListener('wheel',e=>{
  e.preventDefault();poke();
  const k0=view.tk, k1=clamp(k0*(e.deltaY<0?1.14:0.877),CONFIG.zoomMin,CONFIG.zoomMax);
  /* zoom toward the cursor, not the centre */
  const mx=e.clientX-W/2, my=e.clientY-H/2;
  view.tx-=mx*(1/k0-1/k1); view.ty-=my*(1/k0-1/k1);
  view.tk=k1;
},{passive:false});

const card=document.getElementById('card');
const hideCard=()=>{card.style.opacity=0;};
function hoverTest(mx,my){
  let best=null,bd=1e9;
  for(const n of D.nodes){
    if(n._sx==null||!shown(n))continue;
    const d=Math.hypot(mx-n._sx,my-n._sy);
    if(d<n._sr&&d<bd){bd=d;best=n;}
  }
  hoverId=best?best.id:null;
  if(!best){hideCard();return;}
  const t=curT;
  const rows=(arr,key)=>(arr||[]).map(e=>({s:NODE[key==='a'?e.a:e.b],w:edgeAt(e,t)}))
    .filter(r=>r.w>=CONFIG.edgeMinShared).sort((a,b)=>b.w-a.w).slice(0,4);
  const fedBy=rows(IN[best.id],'a'), feeding=rows(OUT[best.id],'b');
  const sec=(lbl,cls,list)=>list.length?`<div class="sec"><div class="lbl ${cls}">${lbl}</div>`+
    list.map(r=>`<div class="fl"><span>${r.s.sym.slice(0,13)}</span><b>${Math.round(r.w)}w</b></div>`).join('')+
    `</div>`:'';
  card.innerHTML=`<div class="h">${best.sym}</div><div class="ch">${best.chain}</div>
    <div class="r"><span>market cap</span><b>${fmt(sample(best.mc,t))}</b></div>
    <div class="r"><span>cohort capital</span><b>${fmt(sample(best.usd,t))}</b></div>
    <div class="r"><span>wallets in</span><b>${Math.round(sample(best.wal,t))}</b></div>
    <div class="r"><span>first seen</span><b>${D.days[best.first]}</b></div>
    ${sec('Fed by','i',fedBy)}${sec('Feeding','o',feeding)}`;
  card.style.opacity=1;
  card.style.left=Math.min(W-262,mx+18)+'px';
  card.style.top=clamp(my-12,8,H-190)+'px';
}

/* transport */
const track=document.getElementById('track'), playBtn=document.getElementById('play'),
      speedBtn=document.getElementById('speed'), dateEl=document.getElementById('date');
function absT(cx){const r=track.getBoundingClientRect();
  return clamp((cx-r.left)/r.width*LAST,0,LAST);}
let sdrag=false, dragX0=0, dragT0=0;
track.addEventListener('pointerdown',e=>{
  sdrag=true;track.setPointerCapture(e.pointerId);setPlay(false);
  targetT=absT(e.clientX);            // click still jumps straight to the spot
  dragX0=e.clientX;dragT0=targetT;e.stopPropagation();});
track.addEventListener('pointermove',e=>{
  if(!sdrag)return;
  /* relative drag with gain < 1 so fine adjustment is possible */
  const r=track.getBoundingClientRect();
  targetT=clamp(dragT0+((e.clientX-dragX0)/r.width)*LAST*MOTION.scrubGain,0,LAST);
  e.stopPropagation();});
addEventListener('pointerup',()=>{if(sdrag){sdrag=false;snapDate();}});

/* ---------- (3) playback speed ---------- */
let speedIx=1;                                   // index into CONFIG.speeds
const rate=()=>CONFIG.speeds[speedIx];
speedBtn.addEventListener('click',()=>{
  speedIx=(speedIx+1)%CONFIG.speeds.length;
  speedBtn.textContent=rate()+'×';});

/* ---------- (4) land on an exact day whenever playback stops ---------- */
let everPlayed=false;
function snapDate(){targetT=clamp(Math.round(targetT),0,LAST);}
function setPlay(v){
  playing=v;playBtn.textContent=v?'❚❚ Pause':'▶ Play';
  if(v){everPlayed=true;if(targetT>=LAST)targetT=0;}
  else snapDate();
  dateEl.classList.toggle('paused',!v&&everPlayed);
}
playBtn.addEventListener('click',()=>setPlay(!playing));
addEventListener('keydown',e=>{
  if(e.key===' '){setPlay(!playing);e.preventDefault();}
  if(e.key==='ArrowRight'){setPlay(false);targetT=Math.min(LAST,Math.round(targetT)+1);}
  if(e.key==='ArrowLeft'){setPlay(false);targetT=Math.max(0,Math.round(targetT)-1);}
  if(e.key==='/'){e.preventDefault();showPane('find');document.getElementById('q').focus();}
  if(e.key==='r'||e.key==='R')reframe();
  if(e.key==='h'||e.key==='H')toggleRail();
});

/* rail */
const rail=document.getElementById('rail'), rToggle=document.getElementById('railToggle'),
      transport=document.getElementById('transport');
function toggleRail(){
  const hid=rail.classList.toggle('hidden');
  rToggle.classList.toggle('out',hid);
  transport.classList.toggle('wide',hid);
  rToggle.textContent=hid?'Show panel':'Hide panel';
  rToggle.setAttribute('aria-expanded',String(!hid));
  setTimeout(()=>fit(true),340);            // refit once the panel finishes sliding
}
rToggle.addEventListener('click',toggleRail);

/* legend doubles as a chain filter */
const legend=document.getElementById('legend');
legend.innerHTML=D.chains.map(c=>
  `<div class="row on" data-c="${c}"><span>${c}</span><i style="background:${cc(c).hot};box-shadow:0 0 8px ${cc(c).hot}"></i></div>`).join('');
legend.querySelectorAll('.row').forEach(r=>r.addEventListener('click',()=>{
  const c=r.dataset.c;chainOn[c]=!chainOn[c];r.classList.toggle('on',chainOn[c]);
  rebuildOrder();EDGE_CACHE.t=-1;fit(true);}));

/* ticks + activity heat strip */
document.getElementById('ticks').innerHTML=[0,.25,.5,.75,1]
  .map(f=>{const i=Math.round(f*LAST);
    return `<b style="left:${f*100}%">${D.days[i].slice(5)}</b>`;}).join('');
(function heat(){
  const c=document.getElementById('heat');
  function paint(){const w=track.clientWidth||520;c.width=w*2;c.height=28;c.style.width=w+'px';
    const g=c.getContext('2d');g.clearRect(0,0,c.width,c.height);
    const tot=D.days.map((_,i)=>D.nodes.reduce((a,n)=>a+(n.act[i]||0),0));
    const mx=Math.max(...tot)||1;
    for(let i=0;i<N;i++){const h=(tot[i]/mx)*28;
      g.fillStyle=`rgba(157,78,221,${0.2+0.7*tot[i]/mx})`;
      g.fillRect(i/N*c.width,28-h,Math.max(1,c.width/N-1),h);}}
  paint();addEventListener('resize',()=>setTimeout(paint,60));
})();

/* ===========================================================================
   RAIL — four panes: Rank, Flows, Movers, Search. Only the active one paints.
   ========================================================================= */
const board=document.getElementById('board'), ROWS={};
const panes={rank:document.getElementById('p-rank'),flow:document.getElementById('p-flow'),
             move:document.getElementById('p-move'),find:document.getElementById('p-find')};
const NOTES={rank:'Cohort capital, reordering as you scrub.',
             flow:'Shared wallets reducing one token while increasing another.',
             move:'7-day change in cohort capital at this frame.',
             find:'Find a token and see what it feeds, and what feeds it.'};
let pane='rank', lastPaint=0;
function showPane(p){
  pane=p;
  for(const k in panes) panes[k].classList.toggle('on',k===p);
  document.querySelectorAll('#tabs button').forEach(b=>b.classList.toggle('on',b.dataset.p===p));
  document.getElementById('search').style.display=p==='find'?'block':'none';
  document.getElementById('paneNote').textContent=NOTES[p];
  lastPaint=0; paintRail(curT);
}
document.querySelectorAll('#tabs button').forEach(b=>
  b.addEventListener('click',()=>showPane(b.dataset.p)));

/* focus a token from any list: highlight it and centre the camera on it */
function focusToken(id){
  const n=NODE[id]; if(!n)return;
  hoverId=id;
  view.tx=-n.x*BASE(); view.ty=-n.y*BASE();
  view.tk=clamp(Math.max(view.tk,1.35),CONFIG.zoomMin,CONFIG.zoomMax);
  poke();
}
function flowsAt(t){
  const live=[];
  for(const e of D.edges){
    const w=edgeAt(e,t);
    if(w>=CONFIG.edgeMinShared&&shown(NODE[e.a])&&shown(NODE[e.b])) live.push({e,w});
  }
  return live.sort((a,b)=>b.w-a.w);
}
function paintRank(t){
  const rank=D.nodes.filter(shown).map(n=>({n,usd:sample(n.usd,t),act:sample(n.act,t)}))
    .filter(r=>r.usd>1000).sort((a,b)=>b.usd-a.usd).slice(0,16);
  const seen=new Set();
  rank.forEach((r,i)=>{
    seen.add(r.n.id);
    let el=ROWS[r.n.id];
    if(!el){
      el=document.createElement('div');el.className='rw';
      el.innerHTML=`<span class="rk"></span><span class="dt" style="background:${cc(r.n.chain).hot}"></span>`+
        `<span class="sy">${r.n.sym.slice(0,15)}</span><span class="vl"></span><span class="ar"></span>`;
      el.addEventListener('click',()=>focusToken(r.n.id));
      el.style.cursor='pointer';
      board.appendChild(el);ROWS[r.n.id]=el;el._p=i;
    }
    el.style.transform=`translateY(${i*34}px)`;el.style.opacity=1;
    el.querySelector('.rk').textContent=i+1;
    el.querySelector('.vl').textContent=fmt(r.usd);
    const d=el._p-i; el._p=i;
    const ar=el.querySelector('.ar');
    ar.textContent=d>0?'▲':d<0?'▼':'';
    ar.style.color=d>0?'var(--in)':d<0?'var(--out)':'transparent';
    el.classList.toggle('hot',r.act>0.45);
  });
  for(const id in ROWS) if(!seen.has(id)){ROWS[id].style.opacity=0;ROWS[id].style.transform='translateY(600px)';}
}
function paintFlow(t){
  const live=flowsAt(t).slice(0,14);
  panes.flow.innerHTML = live.length ? live.map(({e,w})=>{
    const a=NODE[e.a],b=NODE[e.b];
    return `<div class="fl2" data-id="${e.b}">
      <div class="p"><span style="color:${cc(a.chain).hot}">${a.sym.slice(0,12)}</span>
      <em>→</em><span style="color:${cc(b.chain).hot}">${b.sym.slice(0,12)}</span></div>
      <div class="m"><span>${a.chain} → ${b.chain}</span><b>${Math.round(w)} wallets</b></div></div>`;
  }).join('') : '<div class="fl2"><div class="m">no rotations in this window</div></div>';
  panes.flow.querySelectorAll('.fl2[data-id]').forEach(el=>
    el.addEventListener('click',()=>focusToken(el.dataset.id)));
}
function paintMove(t){
  const back=Math.max(0,t-7);
  const rows=D.nodes.filter(shown).map(n=>{
    const now=sample(n.usd,t), then=sample(n.usd,back);
    return {n,now,delta:now-then,pct:then>500?(now/then-1)*100:(now>500?999:0)};
  }).filter(r=>Math.abs(r.delta)>2000).sort((a,b)=>b.delta-a.delta);
  const top=rows.slice(0,8), bot=rows.slice(-6).reverse();
  const row=r=>`<div class="mv" data-id="${r.n.id}">
    <span class="dt" style="background:${cc(r.n.chain).hot};width:7px;height:7px;border-radius:50%"></span>
    <span class="sy">${r.n.sym.slice(0,13)}</span>
    <span class="dl ${r.delta>0?'up':'dn'}">${r.delta>0?'+':''}${fmt(Math.abs(r.delta))}</span></div>`;
  panes.move.innerHTML =
    `<div class="fl2" style="cursor:default"><div class="m"><b>GAINING</b></div></div>`+top.map(row).join('')+
    `<div class="fl2" style="cursor:default;margin-top:6px"><div class="m"><b style="color:var(--out)">BLEEDING</b></div></div>`+bot.map(row).join('');
  panes.move.querySelectorAll('.mv[data-id]').forEach(el=>
    el.addEventListener('click',()=>focusToken(el.dataset.id)));
}
/* ---------- (1) search ---------- */
let query='', picked=null;
const qEl=document.getElementById('q');
qEl.addEventListener('input',()=>{query=qEl.value.trim().toLowerCase();picked=null;lastPaint=0;paintRail(curT);});
function paintFind(t){
  const host=document.getElementById('sres');
  if(picked&&NODE[picked]){
    const n=NODE[picked];
    const rows=(arr,key)=>(arr||[]).map(e=>({s:NODE[key==='a'?e.a:e.b],w:edgeAt(e,t)}))
      .filter(r=>r.w>=CONFIG.edgeMinShared).sort((a,b)=>b.w-a.w).slice(0,6);
    const sec=(lbl,cls,list)=>list.length?`<div class="lbl ${cls}">${lbl}</div>`+
      list.map(r=>`<div class="r" data-id="${r.s.id}" style="cursor:pointer"><span>${r.s.sym.slice(0,14)}</span><b>${Math.round(r.w)}w</b></div>`).join(''):
      `<div class="lbl ${cls}">${lbl}</div><div class="r"><span>none in window</span></div>`;
    host.innerHTML=`<div class="det"><div class="h">${n.sym}</div><div class="ch">${n.chain}</div>
      <div class="r"><span>market cap</span><b>${fmt(sample(n.mc,t))}</b></div>
      <div class="r"><span>cohort capital</span><b>${fmt(sample(n.usd,t))}</b></div>
      <div class="r"><span>wallets in</span><b>${Math.round(sample(n.wal,t))}</b></div>
      <div class="r"><span>first seen</span><b>${D.days[n.first]}</b></div>
      <div class="r"><span>peak cohort</span><b>${fmt(n.peak)}</b></div>
      ${sec('Fed by','i',rows(IN[n.id],'a'))}${sec('Feeding','o',rows(OUT[n.id],'b'))}</div>`;
    host.querySelectorAll('[data-id]').forEach(el=>el.addEventListener('click',()=>{
      picked=el.dataset.id;focusToken(picked);lastPaint=0;paintRail(curT);}));
    focusToken(picked);
    return;
  }
  const hits=D.nodes.filter(n=>!query||n.sym.toLowerCase().includes(query))
    .sort((a,b)=>b.peak-a.peak).slice(0,24);
  host.innerHTML=hits.length?hits.map(n=>
    `<div class="hit" data-id="${n.id}"><span style="color:${cc(n.chain).hot}">●</span> ${n.sym} <span style="color:var(--faint)">${fmt(n.peak)}</span></div>`).join('')
    :'<div class="hit">no match</div>';
  host.querySelectorAll('.hit[data-id]').forEach(el=>el.addEventListener('click',()=>{
    picked=el.dataset.id;lastPaint=0;paintRail(curT);}));
}
function paintRail(t){
  const now=performance.now();
  if(now-lastPaint<1000/MOTION.boardHz)return; lastPaint=now;
  if(pane==='rank')paintRank(t);
  else if(pane==='flow')paintFlow(t);
  else if(pane==='move')paintMove(t);
  else paintFind(t);
}

/* ===========================================================================
   6. BOOT — a short terminal sequence that sets tone and masks first layout
   ========================================================================= */
(function boot(){
  const lines=[
    ['LINKING COHORT', `${D.stats.cohort} WALLETS`],
    ['INDEXING TOKENS', `${D.nodes.length} / ${D.stats.tokens.toLocaleString()}`],
    ['RESOLVING ROTATIONS', `${D.edges.length}`],
    ['LOADING FRAMES', `${N}`],
    ['READY', '']
  ];
  const host=document.getElementById('bootlines');
  host.innerHTML=lines.map(([a,b])=>`<div>&gt; ${a} <span>${b}</span></div>`).join('');
  const els=[...host.children];
  els.forEach((el,i)=>setTimeout(()=>el.classList.add('on'),i*150));
  setTimeout(()=>document.getElementById('boot').classList.add('done'),900);
})();
addEventListener('resize',()=>{resize();fit(true);});
resize(); rebuildOrder(); fit(false); requestAnimationFrame(frame);
