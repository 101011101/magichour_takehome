# PROD — ticket template and past examples

Saved verbatim from Ray, 2026-09-11. The format `TICKET.md` follows. Not edited.

## Template

```text
Colab:
[ADD LINK]

GPU:
[ADD GPU TYPE]

Model:
Krea 2

Modes:
- Text to Image
- Image to Image / Image Editing
- [ADD ANY OTHER SUPPORTED MODE]

Inputs:
- Prompt
- Input image(s), if applicable
- Width
- Height
- [Mask / reference images / other inputs, if applicable]

Outputs:
- Generated image(s)
- [Any additional output details]

Generation time:
[ADD APPROXIMATE TIME]

Resolution:
[ADD SUPPORTED RESOLUTIONS]

Cost:
[ADD COST PER IMAGE OR CREDITS]

Notes:
- [Any important implementation notes]
- [Whether this will be used in AI Image Generator, AI Image Editor, or both]
- [Existing script/model setup to reuse, if any]
```

## Past script examples

```text
web: add Qwen Edit to AI Image Editor
Script: https://colab.research.google.com/drive/1CVDSm1_nRiRffX6lPljYYzztlX9XCbA5?usp=sharing
GPU: A100
Generation time at 752x1024 (on A100):
1 input image = 5.17s
2 input images = 8.09s
3 input images = 11.73s
Credit cost: 10 per image
Notes:
Accepts 3 images max
First run takes 60s
MAINTAIN_ASPECT_RATIO_IMG1 = True will preserve the aspect ratio of image 1, and use the max of MAX_WIDTH and MAX_HEIGHT to determine the maximum dimension. By default we should set MAINTAIN_ASPECT_RATIO_IMG1 = True, similar to the other AI Image Editor models.
We can cap max aspect ratio at 1080p (1920x max)
It'd be good to A/B test setting this the default vs. NB (NB beat Seedream in A/B test). It's lower quality but less restrictive and way cheaper and faster, so could win.
```

```text
aie: build flux klein script

Colab: https://colab.research.google.com/drive/12qIADWLGUZ4mCbRDlCqiP3INEmQG64qH?usp=sharing
This model will be used in both AI Image Generator and Editor.
We have a few options for GPU. On G4, 18.3GB of VRAM are used at all resolutions, so we could use a partitioned GPU. RTX seems it can do 4 partitions with some room leftover just in case.
Generation times at 1024x1024:
GPU
t2i
i2i
Notes
NVIDIA L4
2.27s
4.48s
Requires enable_model_cpu_offload()
NVIDIA A100
0.6s
1.2s


NVIDIA RTX PRO 6000 Blackwell (G4)
0.41s (2.8s at 1920x1920)
0.75s
First run ~9s warmup

A100 is also viable, but we can only partition in half. With L4, we'd run the whole GPU (and it's a bit slower). The goal is to see if retention is better than Z-Image and Qwen 2511, respectively, and if so, we may make this the default in either mode.
Credits: same as Qwen Edit
Max resolution: 1080p (or, 2K)
Input image limit: 6
To pass in resolution, you can just change MAX_RES, and it'll use the aspect ratio of the first input image. You can override by entering an override w+h directly.
MAX_RES    = 1024   # set None for no limit
OVERRIDE_W = None   # e.g. 1920
OVERRIDE_H = None   # e.g. 1080
```

```text
web: build Wan 2.2 script
Colab: https://colab.research.google.com/drive/1dAVf7znvi4MqJwq4dniQr3MPC4kIiR-2?usp=sharing
Modes:
Image to Video (including FFLF)
Text to Video
GPU: use RTX 6000 directly - I'm confident it will be faster than A100
Notes:
In this Colab, mode selects whether we're doing I2V, T2V, or FFLF
For I2V/FFLF, max_resolution determines the dimensions of the longer dimension and preserves aspect ratio of the input image
For T2V, resolution is specified via T2V_Width and T2V_Height
Always keep USE_GEMINI_PROMPT on - it helps
Keep FPS at 16
Use Num_Frames to change length (so 48 frames = 3s)
We're going to turn all the loras in the 3 lora fields into templates. So just FYI that these will be adjusted. The UI for this will be similar to Higgsfield where we have an Effects section at the top of the creation flow.
Let's constrain the max resolution to 1080p
On a100, the generation time is 1.2min for a 448x832, 48 frames T2V video. But this is just for reference - RTX should be sub one minute.
We can charge 1 frame = 1 credit
```
