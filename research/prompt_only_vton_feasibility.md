# Prompt-Only Virtual Try-On — Feasibility Assessment

**Question:** Can the person and garment images be converted into a sufficiently
precise text prompt, then passed to a stronger open-weight text-to-image model instead
of using direct image-conditioned editing?

## Verdict

**Prompt-only generation is feasible for outfit-inspired synthesis, but not for
high-fidelity virtual try-on.** It can reproduce broad garment attributes—category,
color, material, silhouette, neckline, sleeve length, and common patterns—but it
cannot reliably reconstruct a specific garment or preserve the exact person, pose,
camera, hands, background, logos, seams, and print placement from text alone.

The prompt is a lossy semantic bottleneck. Once two images are reduced to words,
details that were not named or that the generator does not bind precisely cannot be
recovered. A more capable text-to-image backbone may improve realism, but realism is
not the same as correspondence to the two source images.

The recommended experiment is a **hybrid generator**, not a prompt-only replacement:

```text
person image ──► pose/layout + identity/appearance embedding ─┐
garment image ─► structured fashion description              ├─► strong T2I model
garment image ─► compact garment image embedding ─────────────┘
```

This preserves the advantages of stronger text-to-image priors while retaining the
visual information that prose cannot encode.

## Why text alone loses fidelity

### 1. Descriptions encode classes, not instances

Text can say “black cropped leather biker jacket with silver asymmetric zipper,” but
it does not uniquely specify the exact lapel geometry, stitching, leather grain,
zipper placement, folds, logo, wear marks, or proportions in the reference image.
Many visually different jackets satisfy the same description.

Fashion captioning is itself a fine-grained research problem. FACAD was created
because ordinary captions do not cover the rich attributes needed for clothing;
newer fashion-captioning work still reports that general VLMs omit or hallucinate
fine-grained attributes. A longer prompt improves attribute coverage but does not
make the representation invertible.

### 2. Text does not identify an unknown person

A prose description of a face or body is not a unique identity representation. It
also cannot precisely encode pose keypoints, occlusion, camera geometry, hair strands,
or the original background. Subject-personalization research exists specifically
because ordinary prompts cannot preserve an unseen subject. Even learned pseudo-word
approaches such as Textual Inversion and DreamBooth require optimization or extra
visual examples and still trade identity fidelity against editability.

### 3. T2I strength solves plausibility, not correspondence

Modern text-to-image models are trained to produce a plausible image matching a text
distribution. Virtual try-on requires a different objective: preserve one image while
transferring a specific object from another. Stronger generation can make a more
attractive photograph while silently replacing the person or approximating the
garment.

The VTO literature consistently retains visual conditioning. IP-Adapter was created
because desired visual concepts are difficult to communicate through text alone.
Garment-driven methods such as Magic Clothing, IDM-VTON, TryOn-Adapter, and recent
multimodal VTO systems encode garment pixels/features, person structure, or both.
This convergence is strong evidence that text is useful as control but insufficient
as the sole carrier of garment and identity information.

## What prompt-only can and cannot preserve

| Requirement | Prompt only | Structured prompt + visual controls |
|---|---:|---:|
| Garment category and general style | Strong | Strong |
| Common color/material/pattern | Moderate–strong | Strong |
| Exact cut and proportions | Weak–moderate | Moderate–strong |
| Exact print, logo, text, and seam layout | Weak | Moderate–strong |
| Same person identity | Weak | Strong with identity conditioning |
| Same pose and framing | Weak | Strong with pose/depth/layout control |
| Pixel-level background preservation | Very weak | Strongest via edit/composite path |
| Novel photorealistic composition | Strong | Strong |

## Three architectures worth testing

### A. Pure prompt-only baseline

Use a vision-language model to convert both images into a constrained JSON record and
render it into a prompt for an open T2I model.

```json
{
  "person": {
    "presentation": "adult woman",
    "appearance": "...",
    "pose": "...",
    "camera": "..."
  },
  "garment": {
    "category": "jacket",
    "silhouette": "cropped fitted biker",
    "material": "black leather",
    "construction": ["asymmetric silver zipper", "wide notched lapels"],
    "surface": ["plain", "subtle leather grain"],
    "branding": "none visible"
  },
  "scene": {
    "background": "...",
    "lighting": "...",
    "composition": "..."
  }
}
```

**Use:** establish the upper bound of prose-only reconstruction.

**Expected result:** realistic, semantically similar outfit images with low instance,
identity, and background fidelity. This is better framed as “recreate this look” than
“try on this exact item.”

### B. Prompt + deterministic structure

Add pose keypoints, person segmentation, depth/edges, aspect ratio, and spatial layout
to the T2I generation. Keep the detailed garment prompt but do not pass garment image
features.

**Use:** determine how much of the person/scene failure comes from missing geometry
rather than missing appearance.

**Expected result:** better pose and composition, but the garment remains an
approximation and identity remains weak without a face/subject representation.

### C. Prompt + compact image adapters (recommended)

Use the structured prompt for semantic control, a garment image encoder/adapter for
instance details, and pose/identity controls for the person. This still exploits the
strong T2I backbone; it simply avoids forcing all information through language.

Candidates include IP-Adapter-style image prompting, a garment-specific extractor,
ControlNet or native pose conditioning, and an identity adapter or deterministic
identity restoration stage. The image input may be reduced to embeddings rather than
fed through a full general image-edit pipeline.

**Expected result:** the best chance of combining T2I realism with VTO fidelity.

## Proposed experiment

Run all three architectures on the same V2 dev pairs and the same T2I backbone where
possible. This isolates the value of each conditioning channel.

| Arm | Text | Pose/layout | Person visual signal | Garment visual signal |
|---|---:|---:|---:|---:|
| A: prompt only | Yes | Text only | No | No |
| B: structured | Yes | Keypoints/depth | No | No |
| C: hybrid | Yes | Keypoints/depth | Identity embedding | Garment embedding |
| D: existing VTO/editor | Instruction | Native/current | Person image | Garment image |

Use the existing held-out metrics:

- garment DINO/region similarity;
- identity cosine;
- pose-keypoint difference;
- background PSNR or protected-region perceptual difference;
- human/VLM garment-detail and realism judgments.

Add attribute-level garment scoring for category, silhouette, neckline, sleeves,
material, color, pattern, closures, logos/text, and distinctive details. This reveals
whether prompt-only preserves semantic attributes while losing instance details.

### Decision rule

Prompt-only should replace direct image conditioning only if it is non-inferior on
garment, identity, pose, and scene fidelity—not merely realism. That outcome is
unlikely. A more realistic decision is:

- use prompt-only for creative “inspired by this outfit” generation;
- use the hybrid arm if it matches the editor/VTO arm on fidelity;
- retain direct image-conditioned VTO for exact product transfer.

## Practical recommendation for V2

Do not redirect V2 to a pure prompt-only pipeline. Add it as a cheap, informative
ablation and prioritize the hybrid architecture:

1. Generate a structured fashion description from the garment image.
2. Extract person pose/layout deterministically.
3. Feed both to the strongest license-compatible open T2I backbone.
4. Add the smallest garment visual adapter needed to recover instance detail.
5. Add identity conditioning or the V2 fidelity guardrail for the person/background.
6. Compare every stage against the raw editor/VTO baseline.

This tests the user's core hypothesis fairly: the T2I model supplies the stronger
image prior, while visual embeddings preserve information that language necessarily
throws away.

## Primary references

- [IP-Adapter: Text Compatible Image Prompt Adapter](https://ip-adapter.github.io/)
- [Magic Clothing: Controllable Garment-Driven Image Synthesis](https://arxiv.org/abs/2404.09512)
- [IDM-VTON: Improving Diffusion Models for Authentic Virtual Try-on in the Wild](https://arxiv.org/abs/2403.05139)
- [TryOn-Adapter: Fine-Grained Clothing Identity Adaptation](https://arxiv.org/abs/2404.00878)
- [PromptDresser: Improving Virtual Try-On via Prompt Engineering](https://openaccess.thecvf.com/content/ICCV2025/papers/Kim_PromptDresser_Improving_the_Quality_and_Controllability_of_Virtual_Try-On_via_ICCV_2025_paper.pdf)
- [Fashion Captioning and the FACAD dataset](https://arxiv.org/abs/2008.02693)
- [RA-CoA: Retrieval-Augmented Chain-of-Attributes](https://openreview.net/forum?id=PpkOrVUpJ6)
- [Image Reference-Guided Fashion Design](https://openaccess.thecvf.com/content/CVPR2023W/CVFAD/html/Cao_Image_Reference-Guided_Fashion_Design_With_Structure-Aware_Transfer_by_Diffusion_Models_CVPRW_2023_paper.html)

