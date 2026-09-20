import json
SITE  = "https://dvnykim.github.io/vampnet/"
BLURB = ("Where proven onchain capital moves next. 741 wallets that each won four or more "
         "separate memecoins, mapped across 80 tokens and 141 days — built entirely on the "
         "Nansen API.")

HEAD = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Vampnet — the onchain attention map</title>
<meta name="description" content="__BLURB__">
<meta name="author" content="Vampnet">
<link rel="canonical" href="__SITE__">

<!-- Social cards. The product is visual, so the preview image is the pitch. -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="Vampnet">
<meta property="og:url" content="__SITE__">
<meta property="og:title" content="Vampnet — the onchain attention map">
<meta property="og:description" content="__BLURB__">
<meta property="og:image" content="__SITE__og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="A dark network map of memecoin tokens clustered by chain, sized by market cap, with capital rotations drawn as glowing links between them.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Vampnet — the onchain attention map">
<meta name="twitter:description" content="__BLURB__">
<meta name="twitter:image" content="__SITE__og.png">
<meta name="theme-color" content="#0A0C11">

<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap">
<style>
/* ===========================================================================
   1. THEME — every colour and surface. Edit freely; no data/logic depends on it.
   ========================================================================= */
:root{
  /* Off-black, not pure black. The map's whole job is dormant-vs-active contrast,
     and #000 leaves no room below the dimmest signal. */
  --void:#0A0C11; --panel:rgba(14,17,24,.86); --panel-solid:#0E1118;
  --line:#1E2430; --line-hot:#35425C;
  --grid:rgba(124,144,178,.05);        /* camera-anchored grid */
  --heat:124,144,178;                  /* timeline activity strip (r,g,b) */
  --cyan:#3DD6D0; --magenta:#FF4D6A; --yellow:#E8B33C; --violet:#8B7FE8; --green:#4FD98A;
  --accent:#F2F7FF;                    /* RESERVED: capital moving right now */
  --ink:#DDE4EF; --muted:#8290A8; --faint:#4A5568;
  --in:#4FD98A;                        /* inbound  / fed by   */
  --out:#FF4D6A;                       /* outbound / feeding  */
  --hover:#161C27; --field:#0C0F16; --tab-on:#151B27;
  --hair:rgba(30,36,48,.75);           /* list separators */
  /* HUD chrome: panels are cut, not rounded, and framed by corner marks rather
     than full borders. Structure borrowed, palette unchanged. */
  --notch:11px;                        /* corner cut on panels */
  --notch-sm:6px;                      /* corner cut on controls */
  --bracket:rgba(61,214,208,.30);      /* viewport corner marks */
}
/* one cut corner, opposite corners, used on every panel and control */
.cut{clip-path:polygon(var(--notch) 0,100% 0,100% calc(100% - var(--notch)),
     calc(100% - var(--notch)) 100%,0 100%,0 var(--notch))}
.cut-sm{clip-path:polygon(var(--notch-sm) 0,100% 0,100% calc(100% - var(--notch-sm)),
     calc(100% - var(--notch-sm)) 100%,0 100%,0 var(--notch-sm))}
*{box-sizing:border-box}
html,body{height:100%;margin:0;overflow:hidden;background:var(--void)}
body{font-family:"Chakra Petch",system-ui,sans-serif;color:var(--ink);
     -webkit-font-smoothing:antialiased;line-height:1.45}
canvas{display:block;position:fixed;inset:0;width:100%;height:100%;touch-action:none;cursor:grab}
canvas.drag{cursor:grabbing}
/* Vignette only. The scanline overlay that used to sit here cost contrast on a
   canvas whose entire signal is dormant-vs-active brightness, and it read as a
   filter rather than as an instrument. */
#fx{position:fixed;inset:0;pointer-events:none;z-index:4;
  background:radial-gradient(ellipse at 50% 45%,transparent 62%,rgba(6,8,12,.55) 100%)}
/* Corner marks on the viewport itself. Four short rules state the frame without
   boxing the map in, which is the whole trick of a HUD: imply the edge. */
#hud{position:fixed;inset:10px;pointer-events:none;z-index:5}
#hud i{position:absolute;width:26px;height:26px;border:1px solid var(--bracket)}
#hud i:nth-child(1){top:0;left:0;border-right:0;border-bottom:0}
#hud i:nth-child(2){top:0;right:0;border-left:0;border-bottom:0}
#hud i:nth-child(3){bottom:0;right:0;border-left:0;border-top:0}
#hud i:nth-child(4){bottom:0;left:0;border-right:0;border-top:0}
/* a thin tick rule down the left gutter — reads as an instrument scale */
#hud u{position:absolute;left:0;top:64px;bottom:64px;width:7px;
  background:repeating-linear-gradient(180deg,var(--bracket) 0 1px,transparent 1px 13px);
  opacity:.5}
.mono{font-family:"JetBrains Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}

/* ---- overlays ---- */
.ov{position:fixed;z-index:6}
#brand{top:18px;left:20px}
#brand .eyebrow{font-family:"JetBrains Mono",monospace;font-size:9.5px;letter-spacing:.3em;
  text-transform:uppercase;color:var(--cyan);opacity:.8;display:flex;align-items:center;gap:7px}
#brand .eyebrow::before{content:"[";color:var(--line-hot);font-size:13px;line-height:1}
#brand .eyebrow::after{content:"]";color:var(--line-hot);font-size:13px;line-height:1}
/* No chromatic aberration on the wordmark — at a glance it read as a rendering
   fault rather than a choice. The accent letterform carries the identity instead. */
#brand h1{font-size:38px;font-weight:700;letter-spacing:.012em;margin:1px 0 0;line-height:1;
  color:var(--ink)}
#brand h1 .d{color:var(--magenta)}
#brand .tag{font-family:"JetBrains Mono",monospace;font-size:9.5px;letter-spacing:.2em;
  text-transform:uppercase;color:var(--muted);margin-top:6px;padding:4px 9px;
  border-left:2px solid var(--magenta);background:linear-gradient(90deg,
  rgba(255,77,106,.10),transparent 70%);max-width:330px;line-height:1.7}
#brand .date{font-family:"JetBrains Mono",monospace;font-size:19px;margin-top:9px;color:var(--ink);
  display:inline-flex;align-items:center;gap:9px}
#brand .date::before{content:"";width:16px;height:1px;background:var(--line-hot)}
/* Chain key + filter. Lives inside #brand so it is never occluded by the rail and
   survives the panel being hidden — it is the only key to what the colours mean. */
#legend{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;max-width:320px}
#legend .row{display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none;
  font-family:"JetBrains Mono",monospace;font-size:9.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted);background:var(--panel);
  border:1px solid var(--line);padding:4px 8px;transition:.15s;clip-path:polygon(5px 0,100% 0,100% calc(100% - 5px),calc(100% - 5px) 100%,0 100%,0 5px)}
#legend .row:hover{border-color:var(--line-hot);color:var(--ink)}
#legend .row.off{opacity:.38}
#legend .row.off i{background:transparent!important;box-shadow:none!important}
#legend .row.on{color:var(--ink)}
#legend .row:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
#legend i{width:7px;height:7px;border-radius:50%;flex:none;border:1px solid currentColor}
/* ---- derived narrative: the sentence a non-specialist came for ----
   Regenerated from the payload on every frame; never written by hand. */
#narrative{top:20px;left:372px;right:452px;text-align:center;pointer-events:none;
  font-size:13px;color:var(--muted);line-height:1.5;transition:opacity .2s}
#narrative b{color:var(--ink);font-weight:600}
#narrative .up{color:var(--in)} #narrative .dn{color:var(--out)}
#narrative em{font-style:normal;color:var(--faint)}

/* ---- credibility strip: what the map is worth, stated permanently ---- */
#creds{bottom:44px;left:20px;display:flex;gap:20px;align-items:flex-end}
#creds .c{display:flex;flex-direction:column;gap:2px;cursor:help;padding-left:9px;border-left:1px solid var(--line-hot)}
#creds .v{font-family:"JetBrains Mono",monospace;font-size:19px;color:var(--accent);
  line-height:1;font-variant-numeric:tabular-nums}
#creds .k{font-family:"JetBrains Mono",monospace;font-size:8px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--faint);max-width:92px;line-height:1.35}
#status{bottom:16px;left:20px;font-family:"JetBrains Mono",monospace;font-size:9.5px;
  letter-spacing:.14em;color:var(--faint);text-transform:uppercase}
#hint{bottom:16px;right:20px;font-family:"JetBrains Mono",monospace;font-size:9px;
  letter-spacing:.12em;color:var(--faint);text-align:right;line-height:1.7}
#hint b{color:var(--muted);font-weight:400}

/* ---- right rail ---- */
#rail{top:0;right:0;bottom:0;width:302px;background:var(--panel);backdrop-filter:blur(9px);
  border-left:1px solid var(--line);padding:70px 0 118px;display:flex;flex-direction:column;
  transition:transform .32s cubic-bezier(.4,0,.2,1);
  clip-path:polygon(22px 0,100% 0,100% 100%,0 100%,0 22px)}
/* device stamp in the rail's head gutter — the panel has 70px of clear space
   above the tabs, so it costs nothing and names the surface */
#rail::before{content:"ROTATION FEED";position:absolute;top:28px;left:16px;
  font-family:"JetBrains Mono",monospace;font-size:8.5px;letter-spacing:.34em;
  color:var(--faint);pointer-events:none}
#rail::after{content:"";position:absolute;top:46px;left:16px;right:16px;height:1px;
  background:linear-gradient(90deg,var(--line-hot),transparent);pointer-events:none}
#rail.hidden{transform:translateX(302px)}
#rail h2{font-family:"JetBrains Mono",monospace;font-size:9.5px;letter-spacing:.22em;
  text-transform:uppercase;color:var(--cyan);margin:0 0 3px;padding:0 16px;font-weight:400}
#rail .note{font-size:11px;color:var(--faint);padding:0 16px 10px;margin:0}
#tabs{display:flex;gap:1px;background:var(--line);margin:0 0 12px;border-block:1px solid var(--line)}
#tabs button{flex:1;background:var(--panel-solid);border:0;color:var(--faint);cursor:pointer;
  font-family:"JetBrains Mono",monospace;font-size:8.5px;letter-spacing:.06em;
  text-transform:uppercase;padding:9px 1px;transition:.15s;white-space:nowrap}
#tabs button:hover{color:var(--muted)}
#tabs button.on{color:var(--cyan);background:var(--tab-on);box-shadow:inset 0 -2px 0 var(--cyan)}
#tabs button:focus-visible{outline:1px solid var(--cyan);outline-offset:-2px}
#search{margin:0 12px 10px;display:none}
#search input{width:100%;background:var(--field);border:1px solid var(--line-hot);color:var(--ink);
  font-family:"JetBrains Mono",monospace;font-size:12px;padding:8px 10px;outline:none}
#search input:focus{border-color:var(--cyan);box-shadow:0 0 12px rgba(61,214,208,.18)}
#search input::placeholder{color:var(--faint)}
.pane{display:none;flex:1;overflow-y:auto;overflow-x:hidden}
.pane.on{display:block}
#board{position:relative;height:100%}
.fl2{padding:7px 14px;border-bottom:1px solid var(--hair);font-family:"JetBrains Mono",monospace;
  font-size:11px;cursor:pointer}
.fl2:hover{background:var(--hover)}
.fl2 .p{display:flex;align-items:center;gap:6px;color:var(--ink)}
.fl2 .p em{font-style:normal;color:var(--faint)}
.fl2 .m{display:flex;justify-content:space-between;color:var(--faint);margin-top:2px;font-size:10px}
.fl2 .m b{color:var(--cyan);font-weight:400}
.mv{display:flex;align-items:center;gap:8px;padding:6px 14px;font-family:"JetBrains Mono",monospace;
  font-size:11px;border-bottom:1px solid var(--hair)}
.mv .sy{flex:1;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mv .dl{flex:none}
.up{color:var(--in)} .dn{color:var(--out)}
/* ---- fresh inflow: new tokens taking capital from established names ---- */
.fr{padding:8px 14px;border-bottom:1px solid var(--hair);font-family:"JetBrains Mono",monospace;
  font-size:11px;cursor:pointer}
.fr:hover{background:var(--hover)}
.fr .t{display:flex;align-items:center;gap:7px}
.fr .t .sy{color:var(--accent);font-weight:700;flex:1;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.fr .age{font-size:9px;letter-spacing:.1em;color:var(--void);background:var(--accent);
  padding:1px 5px;flex:none;
  clip-path:polygon(3px 0,100% 0,100% calc(100% - 3px),calc(100% - 3px) 100%,0 100%,0 3px)}
.fr .m{display:flex;justify-content:space-between;gap:8px;color:var(--faint);
  margin-top:3px;font-size:10px}
.fr .m b{color:var(--muted);font-weight:400}
.fr .src{color:var(--in)}
#sres{padding:0 0 10px}
#sres .det{padding:10px 14px;font-family:"JetBrains Mono",monospace;font-size:11px}
#sres .det .h{font-size:14px;color:var(--accent);font-weight:700}
#sres .det .ch{color:var(--faint);font-size:9px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px}
#sres .det .r{display:flex;justify-content:space-between;color:var(--muted);margin-top:2px}
#sres .det .r b{color:var(--ink);font-weight:400}
#sres .det .lbl{font-size:8.5px;letter-spacing:.16em;text-transform:uppercase;margin:10px 0 3px}
#sres .det .lbl.i{color:var(--in)} #sres .det .lbl.o{color:var(--out)}
#sres .hit{padding:7px 14px;cursor:pointer;color:var(--muted);border-bottom:1px solid var(--hair);
  font-family:"JetBrains Mono",monospace;font-size:11.5px}
#sres .hit:hover{background:var(--hover);color:var(--ink)}
#speed{background:transparent;border:1px solid var(--line-hot);clip-path:polygon(var(--notch-sm) 0,100% 0,100% calc(100% - var(--notch-sm)),calc(100% - var(--notch-sm)) 100%,0 100%,0 var(--notch-sm));color:var(--muted);
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
  border:1px solid var(--line-hot);
  clip-path:polygon(var(--notch-sm) 0,100% 0,100% calc(100% - var(--notch-sm)),
    calc(100% - var(--notch-sm)) 100%,0 100%,0 var(--notch-sm));color:var(--cyan);font-family:"JetBrains Mono",monospace;
  font-size:10px;letter-spacing:.14em;padding:6px 11px;cursor:pointer;text-transform:uppercase;
  transition:right .32s cubic-bezier(.4,0,.2,1),background .15s}
#railToggle.out{right:20px}
#railToggle:hover{background:var(--line)}
#railToggle:focus-visible{outline:2px solid var(--cyan);outline-offset:2px}

/* ---- transport ---- */
#transport{bottom:44px;left:50%;transform:translateX(-50%);width:min(640px,calc(100vw - 420px));
  display:flex;align-items:center;gap:12px;background:var(--panel);backdrop-filter:blur(9px);
  border:1px solid var(--line);padding:10px 14px;transition:width .32s;
  clip-path:polygon(var(--notch) 0,100% 0,100% calc(100% - var(--notch)),
    calc(100% - var(--notch)) 100%,0 100%,0 var(--notch))}
#transport.wide{width:min(760px,calc(100vw - 80px))}
#play{background:transparent;border:1px solid var(--line-hot);clip-path:polygon(var(--notch-sm) 0,100% 0,100% calc(100% - var(--notch-sm)),calc(100% - var(--notch-sm)) 100%,0 100%,0 var(--notch-sm));color:var(--cyan);
  font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.18em;padding:7px 12px;
  cursor:pointer;text-transform:uppercase;flex:none;transition:.15s}
#play:hover{background:var(--line);box-shadow:0 0 16px rgba(61,214,208,.22)}
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
  background:rgba(10,13,19,.97);border:1px solid var(--line-hot);padding:11px 13px;min-width:206px;
  clip-path:polygon(var(--notch-sm) 0,100% 0,100% calc(100% - var(--notch-sm)),
    calc(100% - var(--notch-sm)) 100%,0 100%,0 var(--notch-sm));
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

/* ---------------------------------------------------------------------------
   Narrow screens. The rail becomes a bottom sheet rather than a side panel, and
   the map keeps the upper half of the viewport. Keyboard hints are dropped
   because there is no keyboard; everything they describe has a touch gesture.
   ------------------------------------------------------------------------- */
@media (max-width:860px){
  #brand{top:12px;left:14px;right:14px}
  #brand h1{font-size:30px}
  #brand .eyebrow,#brand .tag{font-size:8.5px;letter-spacing:.18em}
  #brand .date{font-size:16px;margin-top:5px}
  #legend{max-width:none;margin-top:9px}
  #hint{display:none}

  #rail{top:auto;left:0;right:0;bottom:0;width:auto;height:46vh;
    border-left:0;border-top:1px solid var(--line);padding:0 0 8px;
    transform:translateY(0)}
  #rail.hidden{transform:translateY(100%)}
  #board{height:560px;overflow:visible}
  .pane{overflow-y:auto;-webkit-overflow-scrolling:touch}

  #railToggle{top:auto;right:14px;bottom:calc(46vh + 10px);
    transition:bottom .32s cubic-bezier(.4,0,.2,1),background .15s}
  #railToggle.out{right:14px;bottom:14px}

  #transport{left:14px;right:14px;width:auto;transform:none;
    bottom:calc(46vh + 52px);transition:bottom .32s cubic-bezier(.4,0,.2,1)}
  #transport.wide{width:auto;bottom:56px}

  /* the sheet covers the bottom-left corner, and the run stats are repeated in
     the credibility strip — drop the duplicate rather than stack it underneath */
  #status{display:none}
  #card{max-width:min(250px,calc(100vw - 28px))}
  #tabs button{font-size:10px;letter-spacing:.1em;padding:12px 2px}
  /* the narrative and the numbers are the point — they stay, stacked under the
     brand where there is width for them, rather than floating over the map */
  #narrative{position:static;margin:11px 0 0;text-align:left;font-size:12px}
  #creds{position:static;margin:12px 0 0;gap:16px}
  #creds .v{font-size:16px}
  #creds .k{font-size:7.5px;max-width:78px}
}
@media (max-width:420px){
  #brand h1{font-size:25px}
  #rail,#railToggle,#transport{--sheet:52vh}
  #rail{height:52vh}
  #railToggle{bottom:calc(52vh + 10px)}
  #transport{bottom:calc(52vh + 52px);gap:8px}
  #play,#speed{padding:7px 9px;font-size:9px}
}
</style>
</head>
<body>'''

BODY = r'''
<canvas id="cv"></canvas>
<div id="fx"></div>
<div id="hud"><i></i><i></i><i></i><i></i><u></u></div>

<div class="ov" id="brand">
  <div class="eyebrow" id="eyebrow"></div>
  <h1>Vamp<span class="d">net</span></h1>
  <div class="tag" id="tag"></div>
  <div class="date mono" id="date">—</div>
  <div id="legend" role="group" aria-label="Filter by chain"></div>
  <div class="ov" id="narrative"></div>
  <div class="ov" id="creds"></div>
</div>

<button id="railToggle" aria-expanded="true">Hide panel</button>
<aside class="ov" id="rail">
  <div id="tabs">
    <button data-p="rank" class="on">Rank</button>
    <button data-p="flow">Flows</button>
    <button data-p="fresh">Fresh</button>
    <button data-p="move">Movers</button>
    <button data-p="find">Search</button>
  </div>
  <div id="search"><input id="q" type="text" placeholder="search token…" autocomplete="off"></div>
  <p class="note" id="paneNote">Cohort capital, reordering as you scrub.</p>
  <div class="pane on" id="p-rank"><div id="board"></div></div>
  <div class="pane" id="p-flow"></div>
  <div class="pane" id="p-fresh"></div>
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
  railHold    :0.6,    // day-indices of pending scrub above which the board holds
                       // still (drags only — playback is exempt). DOM relayout of
                       // the reordering rows is the one thing in the app that drops
                       // frames; raise for a calmer board, lower to keep it live
                       // deeper into a drag.
  moshGain    :0.9,    // RGB-split strength per unit of scrub velocity
  moshMax     :3,      // px cap — scrubbing is the money shot, it must stay legible
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
  fitFill:1.00,           // 1.0 = everything visible on load; the judge never pans
  glowMinPx:7,            // nodes smaller than this get no glow (cheap + cleaner)
  /* A token the cohort has only just taken a position in is the highest-value
     thing on the map, and its inflow is usually small in absolute terms — so it
     loses to the top-N edge cap exactly when it matters. These are drawn whether
     or not they win that contest. */
  newDays:14,              // how long a token counts as newly entered
  freshSourceRank:20,      // the feeder must be a top-N name — a proven winner
  freshMinShared:3,        // shared wallets before an inflow is worth drawing
  freshEdges:6,            // fresh inflows guaranteed a line, over the cap
  groupPad:26, groupArm:16,                    // rotation-neighbourhood frame
  groupFill:0.028, groupLine:0.42,
  speeds:[0.5,1,2],       // play-rate options
  chain:{                 // rest = identity, hot = saturated; accent takes over at full activity
    /* rest sits close to the background so the CHANGE carries the signal, not raw
       brightness; hot is the chain's identity at full activity. */
    robinhood:{rest:'#5A2733', hot:'#FF4D6A'},
    bnb      :{rest:'#514520', hot:'#E8B33C'},
    base     :{rest:'#1E4C55', hot:'#3DD6D0'},
    solana   :{rest:'#26503B', hot:'#4FD98A'},
    ethereum :{rest:'#3A3356', hot:'#8B7FE8'},
    hyperevm :{rest:'#553524', hot:'#F0844A'}
  },
  fallback:{rest:'#2E3646', hot:'#8290A8'}
};
const D = __PAYLOAD__;
__ENGINE__
</script>
</body>
</html>'''

ENGINE = open("engine.js").read()
payload = open("data/bubbles80.json").read()
out = (HEAD.replace("__SITE__", SITE).replace("__BLURB__", BLURB)
       + BODY.replace("__ENGINE__", ENGINE).replace("__PAYLOAD__", payload))
import pathlib; pathlib.Path("docs").mkdir(exist_ok=True)
open("docs/index.html","w",encoding="utf-8").write(out)
import os; print("site written", f"{os.path.getsize('docs/index.html'):,}", "bytes")
