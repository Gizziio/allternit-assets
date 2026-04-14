# allternit-assets — Agent Guide

> Brand assets, logos, and design resources for the Allternit ecosystem.

## What this repo contains

This is a **static asset repository**. There is no build system, no package manager, and no tests.

## Directory Map

| File / Path | Description |
|-------------|-------------|
| `gizzi-mascot.svg` | Vector mascot |
| `gizzi-mascot.png` | Transparent PNG mascot |
| `gizzi-animation.gif` | Animated mascot |
| `gizzi-mascot-ascii.svg` | ASCII-style variant |
| `matrix-logo.svg` | Matrix / grid logo |
| `GizziMascot.tsx` | React component |
| `GIZZI_MASCOT_HANDOFF.md` | Design handoff notes |

## Conventions

- Add new assets to the root directory.
- Prefer SVG for vector graphics, PNG for raster previews.
- Keep filenames lowercase with hyphens.

## Warnings

- Do not run `npm install` or any build commands here — there is no `package.json`.
- Large binary files (GIF, PNG) are tracked directly in Git.

## Related Repos

- [`allternit-platform`](https://github.com/Gizziio/allternit-platform) — Uses these assets in the UI
- [`allternit-docs`](https://github.com/Gizziio/allternit-docs) — Documentation site
