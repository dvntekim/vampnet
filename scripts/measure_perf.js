/* Frame-cost measurement for the rendered map.
 *
 * TWO NUMBERS, AND THEY ARE NOT THE SAME THING
 *
 *   draw cost       how long draw() takes to render one frame. This is the
 *                   number that reflects rendering work, and the one the table
 *                   in SUBMISSION.md reports. It has no floor.
 *
 *   frame interval  wall-clock gap between frames. Floored by the display's
 *                   refresh rate — 16.7ms on a 60Hz panel, 8.3ms at 120Hz — so
 *                   a reading at the floor means "keeping up", and no amount of
 *                   optimisation pushes it lower.
 *
 * Reporting an interval where a cost is expected makes a fast renderer look
 * slow: a p90 of 16.7ms is a perfect score on 60Hz, not a bad one. Keep the two
 * columns apart.
 *
 * HOW TO RUN
 *   1. Open the site (https://dvnykim.github.io/vampnet/ or docs/index.html).
 *   2. DevTools -> Console.  (Cmd+Opt+J on macOS, Ctrl+Shift+J elsewhere.)
 *   3. Paste this whole file, press Enter.
 *   4. Do not touch the mouse or keyboard for ~10 seconds.
 *   5. Two tables print. The draw-cost p90 column goes in SUBMISSION.md.
 */
(async () => {
  if (typeof draw !== 'function') {
    console.error('draw() not found — run this on the Vampnet page, after it has loaded.');
    return;
  }

  // Wrap draw() to time it. frame() resolves `draw` globally on every call, so
  // reassigning it here is enough; the original is restored at the end.
  const original = draw;
  let costs = [];
  // eslint-disable-next-line no-global-assign
  draw = function (t) {
    const t0 = performance.now();
    original(t);
    costs.push(performance.now() - t0);
  };

  const pct = (arr, p) => {
    const a = arr.slice().sort((x, y) => x - y);
    return a.length ? +a[Math.min(a.length - 1, (a.length * p) | 0)].toFixed(1) : NaN;
  };

  const sample = (ms = 2500) => new Promise(resolve => {
    costs = [];
    const gaps = [];
    let prev = performance.now(), stop = false;
    const tick = () => {
      const now = performance.now();
      gaps.push(now - prev);
      prev = now;
      if (!stop) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
    setTimeout(() => {
      stop = true;
      const c = costs.slice(10), g = gaps.slice(10);      // drop warm-up frames
      resolve({
        drawP50: pct(c, 0.5), drawP90: pct(c, 0.9),
        intervalP50: pct(g, 0.5), intervalP90: pct(g, 0.9),
        frames: g.length,
      });
    }, ms);
  });

  const out = {};
  console.log('measuring… do not touch the page for ~10s');

  out.idle = await sample();

  let i = 0;
  const pan = setInterval(() => {
    i++; view.tx += Math.sin(i / 6) * 22; view.ty += Math.cos(i / 7) * 16; poke();
  }, 16);
  out.panning = await sample();
  clearInterval(pan);

  let j = 0;
  const zoom = setInterval(() => {
    j++; view.tk = 1.1 + Math.sin(j / 12) * 0.6; poke();
  }, 16);
  out.zooming = await sample();
  clearInterval(zoom);

  setPlay(true);
  out.playing = await sample();
  setPlay(false);

  // eslint-disable-next-line no-global-assign
  draw = original;
  reframe();

  const refresh = +(1000 / out.idle.intervalP50).toFixed(0);
  console.log(`\nDISPLAY ≈ ${refresh}Hz  (interval floor ≈ ${(1000 / refresh).toFixed(1)}ms)`);

  console.log('\nDRAW COST — rendering work. This is the table in SUBMISSION.md.');
  console.table(Object.fromEntries(Object.entries(out)
    .map(([k, v]) => [k, { p50: v.drawP50, p90: v.drawP90 }])));

  console.log('FRAME INTERVAL — pacing. At the floor means keeping up, not slow.');
  console.table(Object.fromEntries(Object.entries(out)
    .map(([k, v]) => [k, { p50: v.intervalP50, p90: v.intervalP90, frames: v.frames }])));
})();
