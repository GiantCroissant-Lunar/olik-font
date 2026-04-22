# ComfyUI workflow templates

These templates style the already-composed base glyph PNG. They do not
do any CJK placement or category-based layout work; geometry stays in
the glyph record and the base renderer.

Each workflow JSON contains three top-level sections:

- `prompt`: the ComfyUI API payload to submit to `POST /prompt`
- `nodes` and `links`: a graph view for editing in the ComfyUI UI

All three templates use the same node ids so the batch runner can patch
them predictably:

- node `4`: `LoadImage.image` for the base PNG staged into ComfyUI's
  input directory
- node `8`: `KSampler.seed`
- node `10`: `SaveImage.filename_prefix`

The checked-in default image is `example.png` because a stock ComfyUI
install already ships it in the input directory. Task 4 should replace
that value at runtime with the rendered glyph base PNG filename.

## Style matrix

| Style | Base checkpoint | ControlNet | Source |
| --- | --- | --- | --- |
| `ink-brush` | `sd_xl_base_1.0.safetensors` | `controlnet-scribble-sdxl-xinsir.safetensors` | Stability AI SDXL base: <https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0> ; xinsir scribble ControlNet: <https://huggingface.co/xinsir/controlnet-scribble-sdxl-1.0> |
| `aged-print` | `sd_xl_base_1.0.safetensors` | `controlnet-canny-sdxl-xinsir.safetensors` | Stability AI SDXL base: <https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0> ; xinsir canny ControlNet: <https://huggingface.co/xinsir/controlnet-canny-sdxl-1.0> |
| `soft-watercolor` | `sd_xl_base_1.0.safetensors` | `controlnet-scribble-sdxl-xinsir.safetensors` | Stability AI SDXL base: <https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0> ; xinsir scribble ControlNet: <https://huggingface.co/xinsir/controlnet-scribble-sdxl-1.0> |

## Local availability on this machine

Queried from `http://127.0.0.1:8188/object_info` while authoring:

- checkpoints present: `sd_xl_base_1.0.safetensors`,
  `sd_xl_base_1.0_0.9vae.safetensors`
- ControlNet models present:
  `controlnet-canny-sdxl-xinsir.safetensors`,
  `controlnet-depth-sdxl-xinsir.safetensors`,
  `controlnet-scribble-sdxl-xinsir.safetensors`

If a later machine is missing one of those files, install it into the
matching ComfyUI model directory and keep the workflow JSON unchanged.
The verdict task can skip styles whose required checkpoints are not
installed locally.
