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
let hoverId=null, ripples=[], moshAmt=0;
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
/* Canvas cannot read CSS variables, so resolve the THEME palette once here. Without
   this the engine hardcodes colours and the "edit THEME to restyle" contract is a lie. */
const VOID=CSSV('--void'), INK=CSSV('--ink'), ACCENT=CSSV('--accent'),
      GRID=CSSV('--grid'), HEAT=CSSV('--heat');
let MCMAX=1,USDMAX=1;
D.nodes.forEach(n=>{MCMAX=Math.max(MCMAX,...n.mc);USDMAX=Math.max(USDMAX,...n.usd);});
const rRing=v=>v<=0?0:CONFIG.ringMin+(CONFIG.ringMax-CONFIG.ringMin)*Math.sqrt(v/MCMAX);
const rCore=v=>v<=0?0:CONFIG.coreMin+(CONFIG.coreMax-CONFIG.coreMin)*Math.sqrt(v/USDMAX);

/* ---- camera ---- */
const BASE=()=>Math.min(W,H)*0.38;
const wx=x=>W/2+(x*BASE()+view.x)*view.k;      // world -> screen
const wy=y=>H/2+(y*BASE()+view.y)*view.k;
const sx=n=>wx(n.x);
const sy=n=>wy(n.y);
function resize(){dpr=Math.min(devicePixelRatio||1,2);W=innerWidth;H=innerHeight;
  cv.width=W*dpr;cv.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);}
/* Fit every node inside the *visible* area — the right rail covers part of the
   canvas, so the usable box is inset on that side and the camera centres on it. */
const MOBILE=()=>matchMedia('(max-width:860px)').matches;
/* horizontal extent of canvas the rail does not sit on top of */
const railOpen=()=>!rail.classList.contains('hidden');
let VIEWL=0, VIEWR=0;
function viewBox(){
  VIEWL=0;
  VIEWR=W-((railOpen()&&!MOBILE())?rail.offsetWidth:0);
}
function fit(animate){
  /* The rail eats width on desktop and height on mobile — inset whichever axis it
     actually covers, or the map centres itself underneath the panel. */
  const mob=MOBILE(), open=!rail.classList.contains('hidden');
  const railW = (open&&!mob) ? rail.offsetWidth  : 0;
  const railH = (open&&mob)  ? rail.offsetHeight : 0;
  const padL=34, padR=railW+34, padT=mob?152:118, padB=railH+(mob?28:104);
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
const LABELS=[];                       // placed label boxes, one frame's worth
/* measureText is hot enough to matter at 60fps; symbol widths never change for a
   given size, and there are only a handful of sizes. */
const _tw=new Map();
function textW(txt,fs){
  const key=fs+'|'+txt;
  let w=_tw.get(key);
  if(w===undefined){w=ctx.measureText(txt).width;_tw.set(key,w);}
  return w;
}
function rebuildOrder(){ORDER=D.nodes.filter(shown).sort((a,b)=>b.rank-a.rank);rebuildHulls();}

/* ---- chain territories ------------------------------------------------------
   Node positions are frozen, so each chain's hull is solved once in world space
   and only projected per frame. The hull is what makes a cluster read as a place
   rather than as a coincidence, and it labels the colours where they are used —
   the legend says which hue is which chain, the hull says which region is. */
const HULLS={};
function convexHull(pts){
  if(pts.length<3)return pts.slice();
  const p=pts.slice().sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
  const cr=(o,a,b)=>(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]);
  const lo=[],up=[];
  for(const q of p){while(lo.length>=2&&cr(lo[lo.length-2],lo[lo.length-1],q)<=0)lo.pop();lo.push(q);}
  for(let i=p.length-1;i>=0;i--){const q=p[i];
    while(up.length>=2&&cr(up[up.length-2],up[up.length-1],q)<=0)up.pop();up.push(q);}
  lo.pop();up.pop();
  return lo.concat(up);
}
function rebuildHulls(){
  for(const k in HULLS)delete HULLS[k];
  for(const c of D.chains){
    if(!chainOn[c])continue;
    const ns=D.nodes.filter(n=>n.chain===c);
    if(!ns.length)continue;
    HULLS[c]={hull:convexHull(ns.map(n=>[n.x,n.y])),n:ns.length,
              cx:ns.reduce((a,n)=>a+n.x,0)/ns.length,
              cy:ns.reduce((a,n)=>a+n.y,0)/ns.length};
  }
}
function drawHulls(){
  const pad=CONFIG.hullPad*Math.min(1.5,view.k);
  ctx.save();ctx.lineJoin='round';
  for(const c in HULLS){
    const h=HULLS[c], col=cc(c).hot, cx=wx(h.cx), cy=wy(h.cy);
    /* push each vertex out from the centroid so the boundary clears the bubbles */
    const pts=h.hull.map(p=>{
      const x=wx(p[0]),y=wy(p[1]),dx=x-cx,dy=y-cy,d=Math.hypot(dx,dy)||1;
      return [x+dx/d*pad,y+dy/d*pad];});
    ctx.beginPath();
    if(pts.length<3){ctx.arc(cx,cy,pad*1.7,0,7);}
    else{
      const mid=(a,b)=>[(a[0]+b[0])/2,(a[1]+b[1])/2];
      const st=mid(pts[pts.length-1],pts[0]);
      ctx.moveTo(st[0],st[1]);
      for(let i=0;i<pts.length;i++){
        const cur=pts[i],nx=pts[(i+1)%pts.length],m=mid(cur,nx);
        ctx.quadraticCurveTo(cur[0],cur[1],m[0],m[1]);   // round the corners off
      }
      ctx.closePath();
    }
    ctx.globalAlpha=CONFIG.hullFill;ctx.fillStyle=col;ctx.fill();
    ctx.globalAlpha=CONFIG.hullLine;ctx.strokeStyle=col;ctx.lineWidth=1;
    ctx.setLineDash([3,6]);ctx.stroke();ctx.setLineDash([]);
    /* Anchor the label on the far side of the cluster from the map centre. The
       topmost vertex is often the side facing a neighbour, and the label then
       reads as belonging to the wrong territory. */
    const mx0=wx(0),my0=wy(0);
    let ox=cx-mx0, oy=cy-my0, om=Math.hypot(ox,oy)||1;
    ox/=om; oy/=om;
    let far=pts[0],fd=-1;
    for(const q of pts){const d=(q[0]-cx)*ox+(q[1]-cy)*oy;if(d>fd){fd=d;far=q;}}
    const fs=clamp(10*Math.min(1.3,view.k),9,13);
    ctx.font=`700 ${fs}px "JetBrains Mono",monospace`;
    const txt=`${c.toUpperCase()}  ${h.n}`, tw=textW(txt,fs);
    const align=ox>0.35?'left':ox<-0.35?'right':'center';
    let lx=far[0]+ox*9, ly=far[1]+oy*9+(oy<0?-4:11);
    /* keep it inside the area the rail does not cover, or it is clipped away */
    const left=align==='left'?lx:align==='right'?lx-tw:lx-tw/2;
    lx+=clamp(left,VIEWL+6,VIEWR-tw-6)-left;
    ly=clamp(ly,fs+6,H-10);
    ctx.globalAlpha=.6;ctx.fillStyle=col;ctx.textAlign=align;
    ctx.fillText(txt,lx,ly);
    const l0=align==='left'?lx:align==='right'?lx-tw:lx-tw/2;
    LABELS.push([l0-3,ly-fs-2,l0+tw+3,ly+5]);
  }
  ctx.restore();
}
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
  ctx.fillStyle=VOID;ctx.fillRect(0,0,W,H);
  viewBox();
  const now=performance.now(), k=view.k;
  const settled=(now-lastInteract)>MOTION.idleMs;
  GLOW+=((settled?1:0)-GLOW)*(settled?0.10:0.45);
  const blur=(base,mult)=>GLOW<0.03?0:base*(mult===undefined?1:mult)*GLOW;
  /* grid drifts with the camera so panning feels anchored */
  ctx.save();ctx.strokeStyle=GRID;ctx.lineWidth=1;
  const gs=54*k, ox=(view.x*k)%gs, oy=(view.y*k)%gs;
  for(let x=ox%gs;x<W;x+=gs){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();}
  for(let y=oy%gs;y<H;y+=gs){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
  ctx.restore();

  LABELS.length=0;          // hull labels claim their boxes before any node label
  drawHulls();

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
      /* a ripple marks a rotation landing — that one is informative, so it stays */
      if(p>0.97)ripples.push({x:x2,y:y2,c:cc(b.chain).hot,t0:now,r:rRing(sample(b.mc,t))*k});
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
  /* A phone shows the same map in a fraction of the area, so the same label count
     collides. Both thresholds tighten rather than shrinking the type below legible. */
  const mob=MOBILE();
  const budget=Math.round(CONFIG.labelBudget(k)*(mob?0.5:1));
  const labelMinPx=CONFIG.labelMinPx*(mob?1.7:1);
  /* Label type size is a function of zoom alone, so the font is set once per frame
     rather than per node. Setting ctx.font and calling measureText are both costly,
     and clustering puts far more labels on screen at high zoom than the old
     scatter did — enough to cost ~6ms/frame while zooming before this. */
  const labelFs=clamp(10*Math.min(1.35,k),9,14);
  ctx.font=`600 ${labelFs}px "Chakra Petch",sans-serif`;
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
    const core=heat>0.72?mix(cc(n.chain).hot,ACCENT,(heat-0.72)/0.28):col;
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
    if(hot||n.rank<budget||R>=labelMinPx){
      const fs=labelFs;
      const txt=n.sym.slice(0,14);
      const ly=(n.sym.charCodeAt(0)%2)?y+R+13:y-R-6;
      /* Clustering packs tokens tight, so unplaced labels used to stack into an
         unreadable pile. Highest-ranked wins the spot; the rest are dropped and
         are still reachable by hover, search, or zooming in. */
      const hw=textW(txt,fs)/2+3, box=[x-hw,ly-fs-2,x+hw,ly+5];
      let clash=false;
      if(!hot)for(const b of LABELS){
        if(box[0]<b[2]&&box[2]>b[0]&&box[1]<b[3]&&box[3]>b[1]){clash=true;break;}
      }
      if(!clash){
        LABELS.push(box);
        ctx.globalAlpha=Math.min(1,born*dim(n.id)*(hot?1:.5+heat*.5));
        ctx.shadowBlur=blur(7);ctx.shadowColor=VOID;ctx.fillStyle=hot?ACCENT:INK;
        ctx.textAlign='center';
        ctx.fillText(txt,x,ly);
      }
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
  /* The scanline tear that used to fire here displaced whatever it cut through —
     token labels, chain labels, bubbles — at random moments, which made the map
     look mis-rendered and made screenshots non-deterministic. Rotations landing
     are already marked by the ripples above, which move nothing.
  */
  paintHUD(t);
  paintRail(t);
}
/* ===========================================================================
   DERIVED NARRATIVE — the one sentence a non-specialist came for.
   Every clause is computed from the payload; none of it is written by hand.
   Wording tracks the primitive exactly: `usd` is the cohort's value_usd, which
   carries price drift, so this says "cohort capital", never "bought".
   ========================================================================= */
const WINDOW=7;
const credsEl=document.getElementById('creds'), narrEl=document.getElementById('narrative');
/* The masthead states the claim, not a mood. Both lines are read from the payload
   so they cannot drift from research/claims.json. */
document.getElementById('eyebrow').textContent=
  `Nansen · ${D.stats.cohort.toLocaleString()} repeat winners · ${D.chains.length} chains`;
/* The headline sentence lives with the number in claims.json, so its scope cannot
   drift from what was measured — an unscoped "78% of winners" would read as a
   cross-chain result, which is not what the run says. */
document.getElementById('tag').textContent = D.claims.oot.headline ||
  `${D.claims.oot.value}% of the next month's winners were already on this map`;
credsEl.innerHTML=Object.keys(D.claims||{}).map(k=>{
  const c=D.claims[k];
  return `<div class="c" title="${c.scope.replace(/"/g,'&quot;')}${c.detail?' ('+c.detail+')':''}">`+
         `<span class="v">${c.value}${c.unit==='x'?'×':c.unit==='days'?'d':c.unit}</span>`+
         `<span class="k">${c.label}</span></div>`;}).join('');

let narrCache={t:-99,html:''};
function narrativeAt(t){
  const back=Math.max(0,t-WINDOW);
  const byChain={};
  for(const n of D.nodes){
    if(!shown(n))continue;
    byChain[n.chain]=(byChain[n.chain]||0)+(sample(n.usd,t)-sample(n.usd,back));
  }
  const moves=Object.entries(byChain).sort((a,b)=>b[1]-a[1]);
  if(!moves.length)return '';
  const [gC,gV]=moves[0], [lC,lV]=moves[moves.length-1];

  /* a position is "new" only if the cohort first took it inside this window */
  const fresh=D.nodes.filter(n=>shown(n)&&n.first>back&&n.first<=t&&sample(n.usd,t)>0)
                     .sort((a,b)=>sample(b.usd,t)-sample(a.usd,t))[0];

  let head;
  if(moves.length>1&&gV>0&&lV<0)
    head=`cohort capital in <b>${gC}</b> <span class="up">+${fmt(gV)}</span>, `+
         `<b>${lC}</b> <span class="dn">−${fmt(-lV)}</span>`;
  else if(gV>0)
    head=`cohort capital in <b>${gC}</b> <span class="up">+${fmt(gV)}</span>`;
  else
    head=`cohort capital in <b>${lC}</b> <span class="dn">−${fmt(-lV)}</span>`;

  let tail='';
  if(fresh){
    tail=` · largest new position <b>${fresh.sym}</b> `+
         `${fmt(sample(fresh.usd,t))} across ${Math.round(sample(fresh.wal,t))} wallets`;
  }else{
    const top=edgesFor(t)[0];
    if(top)tail=` · biggest rotation <b>${NODE[top.e.a].sym}</b> → `+
                `<b>${NODE[top.e.b].sym}</b>, ${Math.round(top.w)} shared wallets`;
  }
  const d=D.days[clamp(Math.round(t),0,LAST)];
  return `<em>${WINDOW} days to ${d}</em> — ${head}${tail}`;
}
function paintNarrative(t){
  if(Math.abs(narrCache.t-t)<0.35)return;
  narrCache.t=t;
  const html=narrativeAt(t);
  if(html!==narrCache.html){narrCache.html=html;narrEl.innerHTML=html;}
}

function paintHUD(t){
  const i=clamp(Math.round(t),0,LAST);
  document.getElementById('date').textContent=D.days[i];
  document.getElementById('status').textContent=
    `${D.stats.cohort} wallets · ${D.nodes.length} tokens · frame ${i+1}/${N}`+
    `${D.stats.built?` · built ${D.stats.built}`:''}`;
  paintNarrative(t);
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
/* Touch needs two things a mouse gets for free: pinch (there is no wheel) and
   tap-to-inspect (there is no hover). Pointer events cover both without a
   separate touch path — PTRS tracks how many are down. */
const PTRS=new Map(); let pinchD=0;
const twoPts=()=>{const a=[...PTRS.values()];return a.length>=2?[a[0],a[1]]:null;};
function pinchMove(){
  const p=twoPts(); if(!p)return;
  const d=Math.hypot(p[1].x-p[0].x,p[1].y-p[0].y);
  if(!pinchD||!d){pinchD=d;return;}
  const k0=view.tk, k1=clamp(k0*(d/pinchD),CONFIG.zoomMin,CONFIG.zoomMax);
  const mx=(p[0].x+p[1].x)/2-W/2, my=(p[0].y+p[1].y)/2-H/2;
  view.tx-=mx*(1/k0-1/k1); view.ty-=my*(1/k0-1/k1);
  view.tk=k1; pinchD=d; poke(); hideCard();
}
cv.addEventListener('pointerdown',e=>{
  PTRS.set(e.pointerId,{x:e.clientX,y:e.clientY});
  cv.setPointerCapture(e.pointerId);
  if(PTRS.size>=2){                       // second finger down: pan becomes pinch
    dragging=false;cv.classList.remove('drag');
    const p=twoPts(); pinchD=p?Math.hypot(p[1].x-p[0].x,p[1].y-p[0].y):0;
    return;
  }
  dragging=true;moved=0;poke();px0=e.clientX;py0=e.clientY;
  view.vx=view.vy=0;cv.classList.add('drag');});
cv.addEventListener('pointermove',e=>{
  if(PTRS.has(e.pointerId))PTRS.set(e.pointerId,{x:e.clientX,y:e.clientY});
  if(PTRS.size>=2){pinchMove();return;}
  if(dragging){
    const dx=(e.clientX-px0)/view.k, dy=(e.clientY-py0)/view.k;
    view.tx+=dx;view.ty+=dy;view.x+=dx;view.y+=dy;
    view.vx=dx*0.85;view.vy=dy*0.85;moved+=Math.abs(dx)+Math.abs(dy);poke();
    px0=e.clientX;py0=e.clientY;hideCard();return;
  }
  hoverTest(e.clientX,e.clientY);
});
function endPointer(e){
  const wasDragging=dragging, tapped=PTRS.size===1&&moved<6;
  PTRS.delete(e.pointerId);
  if(PTRS.size<2)pinchD=0;
  if(PTRS.size===0){
    dragging=false;cv.classList.remove('drag');
    /* a tap that did not pan is an inspect gesture — the touch stand-in for hover */
    if(wasDragging&&tapped&&e.clientX!=null)hoverTest(e.clientX,e.clientY);
  }
}
addEventListener('pointerup',endPointer);
addEventListener('pointercancel',endPointer);
cv.addEventListener('pointerleave',e=>{if(e.pointerType==='mouse'){hoverId=null;hideCard();}});
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
/* Single-key shortcuts must not fire while the user is typing: searching for
   HOOKR would otherwise hide the panel on the H and reframe the map on the R.
   Escape leaves the field so the shortcuts come back without reaching for the mouse. */
const typing=el=>!!el&&(el.tagName==='INPUT'||el.tagName==='TEXTAREA'||el.isContentEditable);
addEventListener('keydown',e=>{
  if(typing(e.target)){
    if(e.key==='Escape'){e.target.blur();}
    return;
  }
  if(e.metaKey||e.ctrlKey||e.altKey)return;      // leave browser shortcuts alone
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

/* Chain key, which doubles as the filter. Rendered as buttons so it is reachable by
   keyboard, and carries each chain's token count — the 40x spread across chains is the
   finding, so it belongs where the colours are explained. */
const legend=document.getElementById('legend');
const chainCount={}; D.nodes.forEach(n=>chainCount[n.chain]=(chainCount[n.chain]||0)+1);
/* Repeat-winner rate per chain is the ceiling on whether a cohort can work there at
   all, and it is the finding that explains why one territory carries the map. It
   rides the chip rather than a panel of its own — the colour and its caveat in the
   same place, costing no screen. */
const PERSIST={}; (D.persistence||[]).forEach(r=>PERSIST[r.chain]=r);
const chainTitle=c=>{
  const r=PERSIST[c]; if(!r)return `${c}: ${chainCount[c]||0} tokens`;
  return `${c} — ${r.rate}% repeat-winner rate (${r.repeat} of ${r.traders.toLocaleString()} `+
         `winning traders won more than once)`+
         (r.covtot?`. Out-of-time coverage ${r.cov}/${r.covtot}.`:'.')+
         (r.rate<4?' Below the ~4% floor, a cohort has no headroom here.':'');
};
legend.innerHTML=D.chains.map(c=>
  `<button type="button" class="row on" data-c="${c}" aria-pressed="true" `+
  `title="${chainTitle(c).replace(/"/g,'&quot;')}">`+
  `<i style="background:${cc(c).hot};color:${cc(c).hot}"></i>`+
  `<span>${c}</span><b style="font-weight:400;opacity:.6">${chainCount[c]||0}</b></button>`).join('');
legend.querySelectorAll('.row').forEach(r=>r.addEventListener('click',()=>{
  const c=r.dataset.c;
  /* never let the last chain be switched off — an empty map looks like a crash */
  if(chainOn[c]&&D.chains.filter(x=>chainOn[x]).length<=1)return;
  chainOn[c]=!chainOn[c];
  r.classList.toggle('on',chainOn[c]); r.classList.toggle('off',!chainOn[c]);
  r.setAttribute('aria-pressed',String(chainOn[c]));
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
      g.fillStyle=`rgba(${HEAT},${0.2+0.7*tot[i]/mx})`;
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
