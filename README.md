# VRM Platform Preflight — Documentation

Check your avatar against cluster's VRM 1.0 upload limits **inside Blender, before you export** — with polygon counts done the way upload sites count them: as triangles.

## Why this exists

Blender shows you polygon counts. Upload platforms count **triangles after triangulation**. A model that looks fine in Blender (say, 45,000 polygons shown) can silently be over a platform limit once quads and n-gons are converted to triangles (the same model can be 84,000+ triangles). This add-on counts the way the platform counts, and checks every published numeric limit in one click.

## Installation

1. Download the add-on `.py` file (or `.zip`).
2. In Blender: **Edit → Preferences → Add-ons → Install…**, select the file.
3. Enable **Object: VRM Platform Preflight** in the add-on list.
4. Open the **N panel** in the 3D Viewport and select the **VRM Preflight** tab.

Requires Blender 4.2 LTS.

## How to use

1. Open your avatar `.blend`.
2. In the **VRM Preflight** tab, click **Run Preflight (cluster VRM 1.0)**.
3. Read the results list. Each row shows the measured value and the limit:
   - **PASS** (checkmark) — within the limit.
   - **FAIL** (✕) — over a hard upload limit. Your upload will be rejected or the item will not load.
   - **WARN** — not an upload blocker, but worth knowing (see below).

## What is checked (cluster VRM 1.0 profile)

Limits are taken from cluster's official help (Japanese edition), verified 2026-11-06.

| Check | Limit | Type |
|---|---|---|
| Triangles (triangulated count, modifiers applied) | 72,000 | FAIL |
| Materials | 25 | FAIL |
| Mesh objects (submeshes) | 25 | FAIL |
| Objects (nodes) | 1,000 | FAIL |
| Texture max side | 8,192 px | FAIL |
| Texture formats (file-based images) | PNG / JPEG only | FAIL |
| Texture pixels, total | 12,000,000 | WARN — display-compression trigger in cluster, not an upload limit |
| Bones (total) | 200 | WARN — reference value (listed in cluster's English help) |

The panel also shows the plain Blender polygon count for comparison, so you can see the triangulation gap on your own model.

## Notes on counting

- Triangle counts use the evaluated mesh (modifiers applied), matching what an exporter would produce.
- Texture totals count each unique image once, even if several materials use it.
- Images generated inside Blender (no source file) are counted for size but not judged on format, since their delivery format is decided at export time.
- The saved `.blend` file size is shown for reference against the 100 MB platform limit; note the uploaded VRM file size will differ.

## FAQ

**Does it fix my model automatically?**
No. This is a preflight checker: it tells you exactly which limit you are over and by how much, so you can fix the right thing instead of guessing after a rejected upload.

**Does it work without the VRM add-on?**
Yes. The checks run on any scene. Spring-bone, collider, and constraint counts are planned for a future version and will use VRM add-on data when present.

**Which Blender versions are supported?**
Blender 4.2 LTS. Updates are covered for 12 months from purchase (Support Period).

**What license is the add-on under?**
GPL, as required for Blender add-ons sold on Superhive. You receive the full source code.

**Was AI used to make this?**
Yes — the code was written with AI assistance and then verified by an automated test suite (21 checks, including fixtures with deliberately over-limit geometry) run against Blender 4.2 in headless mode. Every limit in the profile is sourced from the platform's official documentation.

## Support

Bug reports are welcome via the Superhive product page. Please include your Blender version and, if possible, a minimal `.blend` that reproduces the issue. Support covers defects in the add-on; it does not include avatar modeling or retopology advice.

## Repository contents

- `vrm_preflight.py` — the add-on (single file, Blender 4.2 LTS)
- `test_vrm_preflight.py` — automated test suite, run headless against Blender 4.2.3 LTS: 21 checks, all passing, including fixtures with deliberately over-limit geometry to verify FAIL/WARN behaviour
- `demo_pass.blend` — sample scene that passes every check
- `demo_fail.blend` — sample scene that correctly fails the triangle limit (80,000 triangles vs the 72,000 limit)
- `LICENSE` — GPL v3, as required for Blender add-ons

## About Preflight Lab

Preflight Lab builds small, single-purpose verification tools. Other published digital products by the same developer:

- EA Kensho Lab (BOOTH): https://ea-kensho-lab.booth.pm/ — spreadsheet analysis template for trading statement data
- TRPG Sozai Lab (BOOTH): https://trpg-sozai-lab.booth.pm/ — background illustration packs for tabletop RPG sessions
