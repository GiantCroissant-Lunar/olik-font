# v2 style sweep

- Command: `olik style --all-verified --styles ink-brush --seeds 1 --out styled-output/v2-sweep/`
- Run date: 2026-04-23
- Verified glyphs available from the host Task G extraction state: `632`
- Result: localhost ComfyUI accepted the batch and the CLI staged `632` base renders under `styled-output/v2-sweep/.base-render/`, but it still produced `0` styled PNG outputs.
- Runtime note: after multiple minutes with zero completed images, the host run was stopped; the sweep remains partial because single-worker localhost ComfyUI did not finish even the early prompts in reasonable time.
