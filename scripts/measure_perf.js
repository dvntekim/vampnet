/* Frame-time measurement for the rendered map.
 *
 * Numbers in SUBMISSION.md have to come from a real browser on real hardware —
 * a headless container rasterises in software and reports times several times
 * worse than a GPU-backed display, so they are not comparable.
 *
 * HOW TO RUN
 *   1. Open the site (https://dvnykim.github.io/cavitation/ or docs/index.html).
 *   2. Open DevTools -> Console.  (Cmd+Opt+J on macOS, Ctrl+Shift+J on Windows/Linux.)
 *   3. Paste this whole file in, press Enter.
 *   4. Do not touch the mouse or keyboard for ~10 seconds.
 *   5. A table prints. Copy the p90 column into the table in SUBMISSION.md.
 *
 * A display is capped at 60fps, so 16.7ms is the floor: a reading of 16.7 means
 * "not the bottleneck", not "slow". Anything consistently above ~16.7 is real
 * frame cost and worth investigating.
 */
(async () => {
  const sample = (ms = 2500) => new Promise(resolve => {
    const frames = [];
    let prev = performance.now(), stop = false;
    const tick = () => {
      const now = performance.now();
      frames.push(now - prev);
      prev = now;
      if (!stop) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
    setTimeout(() => {
      stop = true;
      const a = frames.slice(10).sort((x, y) => x - y);   // drop warm-up frames
      resolve({
        p50: +a[(a.length * 0.5) | 0].toFixed(1),
        p90: +a[(a.length * 0.9) | 0].toFixed(1),
        frames: a.length,
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
  reframe();

  console.table(out);
  console.log('p90 is the column that goes in SUBMISSION.md');
})();
