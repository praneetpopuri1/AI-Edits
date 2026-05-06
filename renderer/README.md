# AI-Edits Remotion renderer

Deterministic render pipeline for [edit_plan_schema.json](../edit_plan_schema.json). The VLM outputs an edit plan; this package turns it into an MP4.

## Prerequisites

- Node.js and npm (for `npx remotion`)
- FFmpeg on `PATH` (Remotion uses it when rendering video)

## Install

```console
npm i
```

## Props shape

`--props` is a JSON file with:

- `editPlan` — full object matching `edit_plan_schema.json` (includes `source_video`, `segments`, `captions`, optional `zooms`, `overlays`, `text_overlays`, `music`, `reframe`).
- `sourceVideoSrc` — filename under `public/`, e.g. `source.mp4` (after copying the asset there).
- `musicSrc` (optional) — filename under `public/` for background music.

Example:

```json
{
  "editPlan": { },
  "sourceVideoSrc": "source.mp4"
}
```

## Commands

**Remotion Studio (preview)**

```console
npm run dev
```

**Render MP4**

```console
npx remotion render src/index.ts EditPlanVideo out/rendered.mp4 --props=./props.json
```

**Lint / typecheck**

```console
npm run lint
```

## Composition

- **EditPlanVideo** — main composition; duration and dimensions come from `calculateMetadata` and the plan (`source_video` + optional `reframe`).

## Fixtures

See [fixtures/minimal_plan.json](fixtures/minimal_plan.json) for a minimal valid plan (use with a matching `public/source.mp4`).

## Python integration

From the repo root, after `pip install -r pipeline/render/requirements.txt`:

```console
python pipeline/render/validate_plan.py edit_plans/my_plan.json
python pipeline/render/render.py --plan edit_plans/my_plan.json --source-video path/to/video.mp4 --out out/rendered.mp4
```

`render.py` resolves overlay intent into local image assets, validates the plan, copies media into `public/`, and runs `npx remotion render`.

### Overlay resolver env vars

Set these in your shell before running `render.py`:

- `PIXABAY_API_KEY` (recommended) — first-choice stock image search.
- `OPENAI_API_KEY` (fallback) — generated image when stock search has no usable result.

Behavior:

- Resolver checks each overlay for an existing safe local `image_url` under `public/overlays/`.
- Otherwise it tries Pixabay using `search_query` / `image_query` / `visual_description`.
- If stock search fails, it calls OpenAI image generation and saves a local PNG.
- Unresolved overlays are dropped with a warning so render can continue.

### Where to put edit plans

Edit plan JSON files can live anywhere (the CLI takes a path), but this repo includes `edit_plans/`
as the convention location to store them.

### Where the rendered video goes

The output MP4 is written to the `--out` path you pass. If you omit `--out`, it defaults to
`out/rendered.mp4` (relative to the repo root when you run the Python script from there).
