# v2 style sweep

- Command: `olik style --all-verified --styles ink-brush --seeds 1 --out styled-output/v2-sweep/`
- Run date: 2026-04-23
- Verified glyphs available from the clean host Task G extraction run: `632`
- Result: localhost ComfyUI accepted prompts but produced `0` styled PNGs before the sweep was interrupted.
- Constraint: single-worker host ComfyUI did not complete even the early prompts in reasonable time, so the sweep remained partial.
