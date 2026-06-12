# Swiss Watch Movement — 3D Model

An interactive, animated 3D model of a mechanical Swiss lever watch movement,
built as a single self-contained HTML file using [Three.js](https://threejs.org/)
(loaded from a CDN — no build step, no install).

## Run it

Just open the file in any modern browser:

```bash
# from the repo root
open watch-movement/index.html        # macOS
xdg-open watch-movement/index.html    # Linux
start watch-movement/index.html       # Windows
```

> The page pulls Three.js from `unpkg.com` at runtime, so the first load needs
> an internet connection. Everything else (geometry, animation) is generated
> procedurally in the file itself.

## Controls

- **Drag** — orbit the camera
- **Scroll** — zoom
- **Exploded view** — separate the parts vertically to see the stack-up
- **Running / Stopped** — start or freeze the animation
- **Bridges** — hide the top plates to reveal the going train underneath

## What's modeled

The model reproduces the functional architecture of a real caliber:

| Part | Role |
| --- | --- |
| **Mainspring barrel** | Stored energy; a coiled blued-steel spring drives the train |
| **Center / third / fourth wheels** | The *going train* — a gear reduction transmitting power |
| **Escape wheel** | Club-tooth wheel that the lever locks and releases ("tick") |
| **Pallet fork (lever)** | Rocks back and forth, gating the escape wheel one tooth per beat |
| **Balance wheel + hairspring** | The oscillator that regulates timekeeping (~4 Hz) |
| **Ruby jewels** | Low-friction pivot bearings at the wheel pivots |
| **Bridges & balance cock** | Top plates holding the upper pivots |
| **Crown & winding stem** | Winds the mainspring |

Meshing wheels rotate in opposite directions, the lever rocks in anti-phase with
the balance, and the escape wheel advances one tooth on every beat — the same
chain of motion that makes a mechanical watch keep time.

## Notes

This is a *stylized, illustrative* model — proportions and gear counts are chosen
for clarity and visual appeal rather than to match a specific commercial caliber.
Gears use an approximated involute tooth profile generated in code, so the
geometry is fully parametric: tweak the `makeGear({...})` calls near the bottom of
`index.html` to change tooth counts, sizes, and layout.
