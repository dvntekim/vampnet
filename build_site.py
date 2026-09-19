import json
HEAD = r'''<title>Cavitation</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap">
<style>
/* ===========================================================================
   1. THEME — every colour and surface. Edit freely; no data/logic depends on it.
   ========================================================================= */
:root{
  --void:#05030B; --panel:rgba(10,7,22,.82); --panel-solid:#0A0716;
  --line:#241A45; --line-hot:#4B2F7A;
  --cyan:#2DE2E6; --magenta:#FF3864; --yellow:#F9C80E; --violet:#9D4EDD; --green:#57E389;
  --accent:#EAFBFF;                    /* RESERVED: capital moving right now */
  --ink:#E9E4FF; --muted:#8A7FB8; --faint:#4E4472;
  --in:#57E389;                        /* inbound  / fed by   */
  --out:#FF3864;                       /* outbound / feeding  */
}
*{box-sizing:border-box}
html,body{height:100%;margin:0;overflow:hidden;background:var(--void)}
body{font-family:"Chakra Petch",system-ui,sans-serif;color:var(--ink);
     -webkit-font-smoothing:antialiased;line-height:1.45}
canvas{display:block;position:fixed;inset:0;width:100%;height:100%;touch-action:none;cursor:grab}
canvas.drag{cursor:grabbing}
/* scanline + vignette — decoration only */
#fx{position:fixed;inset:0;pointer-events:none;z-index:4;
  background:repeating-linear-gradient(0deg,rgba(45,226,230,.018) 0 1px,transparent 1px 3px),
             radial-gradient(ellipse at 50% 45%,transparent 52%,rgba(5,3,11,.82) 100%)}
.mono{font-family:"JetBrains Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}

/* ---- overlays ---- */
.ov{position:fixed;z-index:6}
#brand{top:18px;left:20px}
#brand .eyebrow{font-family:"JetBrains Mono",monospace;font-size:9.5px;letter-spacing:.3em;
  text-transform:uppercase;color:var(--cyan);opacity:.8}
#brand h1{font-size:38px;font-weight:700;letter-spacing:.012em;margin:1px 0 0;line-height:1;
  text-shadow:-1.5px 0 var(--magenta),1.5px 0 var(--cyan)}
#brand h1 .d{color:var(--violet)}
#brand .tag{font-family:"JetBrains Mono",monospace;font-size:9.5px;letter-spacing:.2em;
  text-transform:uppercase;color:var(--faint);margin-top:5px}
#brand .date{font-family:"JetBrains Mono",monospace;font-size:19px;margin-top:7px;color:var(--ink);
  text-shadow:0 0 16px rgba(157,78,221,.55)}
#legend{top:18px;right:20px;display:flex;flex-direction:column;gap:5px;align-items:flex-end;
  font-family:"JetBrains Mono",monospace;font-size:9.5px;color:var(--muted)}
#legend .row{display:flex;align-items:center;gap:7px;cursor:pointer;user-select:none;opacity:.55;
  transition:opacity .15s}
#legend .row.on{opacity:1;color:var(--ink)}
#legend i{width:8px;height:8px;border-radius:50%}
#status{bottom:16px;left:20px;font-family:"JetBrains Mono",monospace;font-size:9.5px;
  letter-spacing:.14em;color:var(--faint);text-transform:uppercase}
#hint{bottom:16px;right:20px;font-family:"JetBrains Mono",monospace;font-size:9px;
  letter-spacing:.12em;color:var(--faint);text-align:right;line-height:1.7}
#hint b{color:var(--muted);font-weight:400}

/* ---- right rail ---- */
#rail{top:0;right:0;bottom:0;width:302px;background:var(--panel);backdrop-filter:blur(9px);
  border-left:1px solid var(--line);padding:70px 0 118px;display:flex;flex-direction:column;
  transition:transform .32s cubic-bezier(.4,0,.2,1)}
#rail.hidden{transform:translateX(302px)}
#rail h2{font-family:"JetBrains Mono",monospace;font-size:9.5px;letter-spacing:.22em;
  text-transform:uppercase;color:var(--cyan);margin:0 0 3px;padding:0 16px;font-weight:400}
#rail .note{font-size:11px;color:var(--faint);padding:0 16px 10px;margin:0}
#tabs{display:flex;gap:1px;background:var(--line);margin:0 0 12px;border-block:1px solid var(--line)}
#tabs button{flex:1;background:var(--panel-solid);border:0;color:var(--faint);cursor:pointer;
  font-family:"JetBrains Mono",monospace;font-size:9px;letter-spacing:.14em;text-transform:uppercase;
  padding:9px 2px;transition:.15s}
#tabs button:hover{color:var(--muted)}
#tabs button.on{color:var(--cyan);background:#150F2B;box-shadow:inset 0 -2px 0 var(--cyan)}
#tabs button:focus-visible{outline:1px solid var(--cyan);outline-offset:-2px}
#search{margin:0 12px 10px;display:none}
#search input{width:100%;background:#0B0819;border:1px solid var(--line-hot);color:var(--ink);
  font-family:"JetBrains Mono",monospace;font-size:12px;padding:8px 10px;outline:none}
#search input:focus{border-color:var(--cyan);box-shadow:0 0 12px rgba(45,226,230,.2)}
#search input::placeholder{color:var(--faint)}
.pane{display:none;flex:1;overflow-y:auto;overflow-x:hidden}
.pane.on{display:block}
#board{position:relative;height:100%}
.fl2{padding:7px 14px;border-bottom:1px solid rgba(36,26,69,.6);font-family:"JetBrains Mono",monospace;
  font-size:11px;cursor:pointer}
.fl2:hover{background:#130E28}
.fl2 .p{display:flex;align-items:center;gap:6px;color:var(--ink)}
.fl2 .p em{font-style:normal;color:var(--faint)}
.fl2 .m{display:flex;justify-content:space-between;color:var(--faint);margin-top:2px;font-size:10px}
.fl2 .m b{color:var(--cyan);font-weight:400}
.mv{display:flex;align-items:center;gap:8px;padding:6px 14px;font-family:"JetBrains Mono",monospace;
  font-size:11px;border-bottom:1px solid rgba(36,26,69,.5)}
.mv .sy{flex:1;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mv .dl{flex:none}
.up{color:var(--in)} .dn{color:var(--out)}
#sres{padding:0 0 10px}
#sres .det{padding:10px 14px;font-family:"JetBrains Mono",monospace;font-size:11px}
#sres .det .h{font-size:14px;color:var(--accent);font-weight:700}
#sres .det .ch{color:var(--faint);font-size:9px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px}
#sres .det .r{display:flex;justify-content:space-between;color:var(--muted);margin-top:2px}
#sres .det .r b{color:var(--ink);font-weight:400}
#sres .det .lbl{font-size:8.5px;letter-spacing:.16em;text-transform:uppercase;margin:10px 0 3px}
#sres .det .lbl.i{color:var(--in)} #sres .det .lbl.o{color:var(--out)}
#sres .hit{padding:7px 14px;cursor:pointer;color:var(--muted);border-bottom:1px solid rgba(36,26,69,.5);
  font-family:"JetBrains Mono",monospace;font-size:11.5px}
#sres .hit:hover{background:#130E28;color:var(--ink)}
#speed{background:transparent;border:1px solid var(--line-hot);color:var(--muted);
  font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.1em;padding:7px 9px;
  cursor:pointer;flex:none;transition:.15s;min-width:42px}
#speed:hover{background:var(--line);color:var(--cyan)}
#speed:focus-visible{outline:2px solid var(--cyan);outline-offset:2px}
#date.paused::after{content:" ❚❚";font-size:11px;color:var(--accent);letter-spacing:.1em}
#board{position:relative;flex:1;overflow:hidden;margin:0 6px}
.rw{position:absolute;left:0;right:0;height:34px;display:flex;align-items:center;gap:8px;
  padding:0 10px;font-family:"JetBrains Mono",monospace;font-size:11.5px;
  transition:transform .55s cubic-bezier(.4,0,.2,1),opacity .3s;will-change:transform}
.rw .rk{width:20px;color:var(--faint);font-size:10px;text-align:right;flex:none}
.rw .dt{width:7px;height:7px;border-radius:50%;flex:none}
.rw .sy{flex:1;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rw .vl{color:var(--muted);flex:none}
.rw .ar{width:12px;font-size:9px;flex:none;text-align:center}
.rw.hot .sy{color:var(--accent);text-shadow:0 0 10px rgba(234,251,255,.5)}
#railToggle{position:fixed;z-index:7;top:18px;right:318px;background:var(--panel-solid);
  border:1px solid var(--line-hot);color:var(--cyan);font-family:"JetBrains Mono",monospace;
  font-size:10px;letter-spacing:.14em;padding:6px 11px;cursor:pointer;text-transform:uppercase;
  transition:right .32s cubic-bezier(.4,0,.2,1),background .15s}
#railToggle.out{right:20px}
#railToggle:hover{background:var(--line)}
#railToggle:focus-visible{outline:2px solid var(--cyan);outline-offset:2px}

/* ---- transport ---- */
#transport{bottom:44px;left:50%;transform:translateX(-50%);width:min(640px,calc(100vw - 420px));
  display:flex;align-items:center;gap:12px;background:var(--panel);backdrop-filter:blur(9px);
  border:1px solid var(--line);padding:10px 14px;transition:width .32s}
#transport.wide{width:min(760px,calc(100vw - 80px))}
#play{background:transparent;border:1px solid var(--line-hot);color:var(--cyan);
  font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.18em;padding:7px 12px;
  cursor:pointer;text-transform:uppercase;flex:none;transition:.15s}
#play:hover{background:var(--line);box-shadow:0 0 16px rgba(45,226,230,.25)}
#play:focus-visible{outline:2px solid var(--cyan);outline-offset:2px}
#track{flex:1;position:relative;height:34px;cursor:grab;touch-action:none}
#track:active{cursor:grabbing}
#heat{position:absolute;top:6px;left:0;right:0;height:14px;opacity:.55}
#rail2{position:absolute;top:20px;left:0;right:0;height:2px;background:var(--line-hot)}
#fillbar{position:absolute;top:20px;left:0;height:2px;background:var(--cyan);box-shadow:0 0 10px var(--cyan)}
#headbar{position:absolute;top:12px;width:2px;height:18px;background:var(--accent);
  box-shadow:0 0 12px var(--accent);transform:translateX(-1px)}
#ticks{position:absolute;top:24px;left:0;right:0;height:12px}
#ticks b{position:absolute;font-family:"JetBrains Mono",monospace;font-size:8.5px;color:var(--faint);
  font-weight:400;transform:translateX(-50%);white-space:nowrap}

/* ---- hover card ---- */
#card{position:fixed;z-index:8;pointer-events:none;opacity:0;transition:opacity .11s;
  background:rgba(8,5,18,.96);border:1px solid var(--line-hot);padding:11px 13px;min-width:206px;
  max-width:250px;font-family:"JetBrains Mono",monospace;font-size:11px}
#card .h{font-size:13px;color:var(--accent);font-weight:700;letter-spacing:.05em}
#card .ch{color:var(--faint);font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:7px}
#card .r{display:flex;justify-content:space-between;gap:14px;color:var(--muted);margin-top:2px}
#card .r b{color:var(--ink);font-weight:400}
#card .sec{margin-top:9px;padding-top:7px;border-top:1px solid var(--line)}
#card .lbl{font-size:8.5px;letter-spacing:.16em;text-transform:uppercase;margin-bottom:3px}
#card .lbl.i{color:var(--in)} #card .lbl.o{color:var(--out)}
#card .fl{display:flex;justify-content:space-between;gap:10px;color:var(--muted);font-size:10.5px}
#card .fl b{color:var(--ink);font-weight:400}

/* ---- boot ---- */
#boot{position:fixed;inset:0;z-index:20;background:var(--void);display:flex;align-items:center;
  justify-content:center;transition:opacity .45s}
#boot.done{opacity:0;pointer-events:none}
#bootlines{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--cyan);
  line-height:2;min-width:330px}
#bootlines div{opacity:0}
#bootlines div.on{opacity:1}
#bootlines span{color:var(--faint)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>'''

BODY = r'''
<canvas id="cv"></canvas>
<div id="fx"></div>

<div class="ov" id="brand">
  <div class="eyebrow">Nansen · 741 repeat winners · 4 chains</div>
  <h1>Cavit<span class="d">ation</span></h1>
      <div class="tag">the collapse is where the damage happens</div>
  <div class="date mono" id="date">—</div>
</div>

<div class="ov" id="legend"></div>

<button id="railToggle" aria-expanded="true">Hide panel</button>
<aside class="ov" id="rail">
  <div id="tabs">
    <button data-p="rank" class="on">Rank</button>
    <button data-p="flow">Flows</button>
    <button data-p="move">Movers</button>
    <button data-p="find">Search</button>
  </div>
  <div id="search"><input id="q" type="text" placeholder="search token…" autocomplete="off"></div>
  <p class="note" id="paneNote">Cohort capital, reordering as you scrub.</p>
  <div class="pane on" id="p-rank"><div id="board"></div></div>
  <div class="pane" id="p-flow"></div>
  <div class="pane" id="p-move"></div>
  <div class="pane" id="p-find"><div id="sres"></div></div>
</aside>

<div class="ov" id="transport">
  <button id="play">▶ Play</button>
  <button id="speed" title="Playback speed">1×</button>
  <div id="track" role="slider" aria-label="Timeline" aria-valuemin="0" aria-valuemax="100"
       aria-valuenow="100" tabindex="0">
    <canvas id="heat"></canvas><div id="rail2"></div><div id="fillbar"></div>
    <div id="headbar"></div><div id="ticks"></div>
  </div>
</div>

<div class="ov mono" id="status">—</div>
<div class="ov" id="hint"><b>drag</b> pan · <b>scroll</b> zoom · <b>space</b> play<br>
<b>R</b> reframe · <b>H</b> hide panel</div>
<div id="card"></div>

<div id="boot"><div id="bootlines"></div></div>

<script>
/* ===========================================================================
   2. MOTION — feel. Every easing/timing constant lives here.
   ========================================================================= */
const MOTION={
  scrubEase   :0.14,   // lower = heavier scrubber
  playSpeed   :0.16,   // day-indices per frame while playing (multiplied by speed toggle)
  scrubGain   :0.55,   // <1 = finer scrubber control; drag distance -> time travelled
  panFriction :0.90,   // inertia decay after a drag
  zoomEase    :0.20,   // how fast zoom settles
  particleRate:0.00040,
  rippleMs    :850,
  boardHz     :8,      // ranking-panel refresh (Hz) — DOM work, keep low
  moshGain    :3.4,    // RGB-split strength per unit of scrub velocity
  moshMax     :14,     // px cap on the split
  glitchMs    :260,    // scanline tear duration on a big rotation
  idleMs      :140,    // how long after interaction before full glow returns
};
/* ===========================================================================
   3. CONFIG — visual mapping + what counts as "active". Safe to edit.
   ========================================================================= */
const CONFIG={
  ringMin:3, ringMax:54, coreMin:1.5, coreMax:38,
  edgeWindow:1, edgeMinShared:2, maxEdges:10, edgeMaxAlpha:0.62,
  dormantAlpha:0.085, activeBoost:1.9, activeGamma:0.55,
  glow:{ring:14, core:22},
  labelBudget:k=>Math.round(10+34*Math.min(1,(k-0.55)/1.5)), // labels revealed as you zoom
  labelMinPx:11,          // …or any node at least this big on screen
  focusDim:0.06,
  zoomMin:0.42, zoomMax:4.2,
  fitFill:1.18,           // >1 fills the frame rather than fitting exactly
  glitchShared:6,         // shared wallets needed to trigger a tear
  glowMinPx:7,            // nodes smaller than this get no glow (cheap + cleaner)
  speeds:[0.5,1,2],       // play-rate options
  chain:{                 // rest = identity, hot = saturated; accent takes over at full activity
    robinhood:{rest:'#8E2340', hot:'#FF3864'},
    bnb      :{rest:'#7A6508', hot:'#F9C80E'},
    base     :{rest:'#177074', hot:'#2DE2E6'},
    solana   :{rest:'#2C7047', hot:'#57E389'},
    ethereum :{rest:'#4F2A70', hot:'#9D4EDD'},
    hyperevm :{rest:'#7F4520', hot:'#FF8A3D'}
  },
  fallback:{rest:'#3A3355', hot:'#8A7FB8'}
};
const D = __PAYLOAD__;
__ENGINE__
</script>'''

ENGINE = open("engine.js").read()
payload = open("data/bubbles80.json").read()
out = HEAD + BODY.replace("__ENGINE__", ENGINE).replace("__PAYLOAD__", payload)
import pathlib; pathlib.Path("docs").mkdir(exist_ok=True)
open("docs/index.html","w",encoding="utf-8").write(out)
import os; print("site written", f"{os.path.getsize('docs/index.html'):,}", "bytes")
