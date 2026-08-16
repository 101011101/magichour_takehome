# V2 notebook source. Markers: "# %% [markdown]" = markdown cell, "# %%" = code cell.
# Generate the notebook with:
#   jupytext --to notebook --output ../virtual_tryon.ipynb notebook_cells.py
# (No generator script existed in v1/build; the percent format is jupytext-standard.)
# Structure follows execution_conventions.md: Setup / Inputs / Test set /
# Inference / Comparison grid / Eval / Verdict. No emojis, professional comments.
#
# Open integration points (owned by parallel work, do not implement here):
#   (all integration points resolved 2026-08-14: composite inlined at 6e,
#    metrics swapped in 5c, anchors recalibrated)

# %% [markdown]
# # Virtual Try-On — Open-Weights Comparison (V2)
# Person image + garment image -> the person wearing that garment, evaluated
# across open-weights arms against the **Qwen 2511** baseline. Budget ceiling:
# **\$10**.
#
# Every arm serves an open checkpoint. The fal endpoints are used for iteration
# only, per the testing exception in `execution_conventions.md`; the parity
# re-run on downloaded weights is a later wave and is not part of this notebook.
#
# Runs identically in two environments:
# - **Locally** (VS Code / Jupyter): keys come from a `.env` file in the repo
#   root (`FAL_KEY=...`, `OPENAI_API_KEY=...`); outputs go to `v2/runs/`.
# - **Colab**: keys come from Colab Secrets (`FAL_KEY`, `OPENAI_API_KEY`,
#   optional `HF_TOKEN`); the repo is cloned automatically and outputs go to
#   Drive under `DRIVE_PROJECT_DIR` (set the exact folder name in §1).
#
# ## Run flow — reproducible top-to-bottom
# 1. **Triage:** all 4 arms x 4 pairs (`RUN_TRIAGE=True`, ~\$0.61).
# 2. **Elimination (automatic):** deterministic judges score the triage
#    outputs; the top 50% of arms (`SURVIVOR_COUNT = 2`) advance, and the
#    baseline always advances for comparison. `SURVIVORS` in §1 stays empty
#    unless you want to override the automatic pick.
# 3. **Grid:** survivors x 12 pairs (`RUN_GRID=True`).
# 4. **Composite:** the `composite_v2ow` arm (§6e, built in
#    `v2/build/composite_cells.py`) enters the grid and holdout stages
#    regardless of triage rank.
# 5. **Judging:** deterministic metrics on every output (free, automatic);
#    `gpt-5.5` VLM judge as a second opinion (`RUN_VLM_JUDGE=True`,
#    ~\$0.025/output); human spot-check via §8 as insurance.
# 6. **§10 leaderboards per stage + §11 verdict.**
#
# Seeds are fixed per pair with stage offsets (triage +0, grid +100, reserve
# +200, holdout +300) and completed generations are reloaded from run packages,
# so a full re-run reproduces the same results without re-spending.
# **Paid cells never execute on "Run all"** — each is gated behind an explicit
# flag, and every paid call checks the budget ceiling before submission.
#
# Docs: `prd/` (scope) · `execution_conventions.md` (conventions).
#
# ## Quick start — "I just want to try it on two images"
# 1. Add `FAL_KEY` (Colab Secrets or `.env`) and run all cells — free; nothing
#    spends without a flag.
# 2. Go to **§12a** (single model) or **§12b** (composite) and call
#    `run_single()` / `run_composite()` — with no arguments in Colab you will
#    be prompted to upload a person image and a garment image.
# 3. **§12c** `compare_vs_baseline()` renders your inputs through the baseline,
#    the best single arm, and the composite side by side.
#
# ## Quick start — "I want to reproduce the evaluation"
# Flip the flags in §1 one stage at a time (`RUN_TRIAGE` -> survivors
# auto-select -> `RUN_GRID` -> `RUN_RESERVE` -> `RUN_COMPOSITE` ->
# `RUN_BENCHMARK`, judges via `RUN_CV_JUDGE`/`RUN_VLM_JUDGE`). Completed
# generations reload from run packages, so re-running never re-buys an image.
# Boards print in §10, verdict in §11.

# %%
#  §1 · Settings ------------------------------------------------------------
SEED_BASE = 46            # per-pair seed = SEED_BASE + stage offset + pair index
PROMPT_TEMPLATE = (
    "Replace the clothing of the person in image 1 with the garment shown in "
    "image 2. Keep the person's face, hair, pose, hands, body and the "
    "background completely unchanged. Preserve the garment's exact color, "
    "pattern, print, and cut."
)
RUN_TRIAGE    = False     # paid: arms x 4 pairs x 1 gen (~$0.61)
RUN_GRID      = False     # paid: SURVIVORS x 12 pairs x 1 gen
RUN_RESERVE   = False     # paid: TOP2 x 12 pairs x 1 extra gen (best-of-2 / seed variance)
RUN_COMPOSITE = False     # paid: composite arm on the grid pairs (§6e); holdout via RUN_BENCHMARK
RUN_BENCHMARK = False     # paid: BENCH_ARMS x 18 held-out pairs — final numbers
BENCH_ARMS    = []        # leave empty to auto-select: grid winner + composite_v2ow + baseline
RUN_CV_JUDGE  = True      # free: local CV metrics; first run downloads ~350MB of models
RUN_VLM_JUDGE = False     # paid: ~$0.025 per judged output on gpt-5.5
BASELINE = "qwen_2511"    # always advances to every stage for comparison
SURVIVOR_COUNT = 2        # elimination rule: top 50% of 4 arms advance from triage
SURVIVORS = []            # leave empty to auto-select by deterministic score
TOP2      = []            # leave empty to auto-select top 2 of the grid ranking
BUDGET_USD = 10.00        # hard ceiling; checked before every paid submission
DRIVE_PROJECT_DIR = "Side projects and shi"   # exact Drive folder name (UI truncates it);
                                              # §2 asserts it exists at mount time
ARM_EST_USD = {           # single cost source; ARM_REGISTRY (§5) references it
    "qwen_2511": 0.03,        # $0.03/MP
    "klein_4b_edit": 0.015,
    "fashn_v15": 0.075,       # confirmed on live /v1.5 endpoint 2026-08-14
    "firered_edit": 0.033,    # $0.0325/MP; ~1MP outputs assumed
}
ARMS_ENABLED = {
    "qwen_2511": True,       # baseline
    "klein_4b_edit": True,
    "fashn_v15": True,
    "firered_edit": True,
}
print(f"arms on: {[k for k, v in ARMS_ENABLED.items() if v]}")

# %%
#  §2 · Setup (free) --------------------------------------------------------
import os, subprocess, sys
try:
    import google.colab
    IN_COLAB = True
except ImportError:
    IN_COLAB = False
if IN_COLAB:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "fal-client",
                    "pillow", "pandas", "matplotlib", "jsonschema", "openai",
                    "mediapipe", "insightface", "onnxruntime",
                    "huggingface_hub"], check=True)   # composite deps (paste-back + gate)
    # metric-model deps (FashionSigLIP / AuraFace) are declared by
    # v2/build/metrics_v2.py, not here:
    # subprocess.run([sys.executable, "-m", "pip", "install", "-q", <metrics_v2 deps>])
    from google.colab import userdata
    for k in ("FAL_KEY", "OPENAI_API_KEY", "HF_TOKEN"):   # HF_TOKEN optional (gated weights)
        try:
            os.environ[k] = userdata.get(k)
        except Exception:
            pass
    REPO_DIR = "/content/tryon_repo"
    if not os.path.exists(REPO_DIR):
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/101011101/magichour_takehome.git",
                        REPO_DIR], check=True)
    try:
        from google.colab import drive
        drive.mount("/content/drive")
        _mounted = True
    except Exception:
        # Drive declined or unavailable: outputs live on the session VM
        # (discarded when the session ends) — fine for smoke tests.
        _mounted = False
        OUT_ROOT = "/content/tryon_v2_runs"
    if _mounted:
        _drive_base = os.path.join("/content/drive/MyDrive", DRIVE_PROJECT_DIR)
        assert os.path.isdir(_drive_base), (
            f"Drive project folder not found: {_drive_base}\n"
            "The Drive UI truncates long folder names — open the folder, check "
            "its exact full name, and fix DRIVE_PROJECT_DIR in §1 to match.")
        OUT_ROOT = os.path.join(_drive_base, "tryon_v2_runs")
        # HF weights cached on Drive so metric models survive session resets
        os.environ["HF_HOME"] = os.path.join(_drive_base, "hf_cache")
        os.makedirs(os.environ["HF_HOME"], exist_ok=True)
        # AuraFace (~300MB) persists to Drive too, or it re-downloads every VM
        os.environ.setdefault("AURAFACE_ROOT",
                              os.path.join(os.environ["HF_HOME"], "auraface"))
else:
    REPO_DIR = os.getcwd()
    if os.path.basename(REPO_DIR) in ("v2", "build"):   # notebook may live in v2/
        REPO_DIR = REPO_DIR[:REPO_DIR.rindex("v2")].rstrip(os.sep) or REPO_DIR
    if os.path.exists(os.path.join(REPO_DIR, ".env")):
        for line in open(os.path.join(REPO_DIR, ".env")):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    OUT_ROOT = os.path.join(REPO_DIR, "v2", "runs")
# OUT_ROOT is V2-only by construction. Never point it at V1's tryon_pilot_runs
# or v1/artifacts — the reload cell (§5b) would silently ingest V1 runs.
if not os.environ.get("FAL_KEY"):
    from getpass import getpass
    os.environ["FAL_KEY"] = getpass("fal API key (input hidden): ").strip()
assert os.environ["FAL_KEY"], "no FAL_KEY provided"   # key is never printed
os.makedirs(OUT_ROOT, exist_ok=True)
ARTIFACT_DIR = os.path.join(REPO_DIR, "v2", "artifacts")   # committed-board fallback (§10)
print(f"setup ok: colab={IN_COLAB}, repo={REPO_DIR} -> outputs: {OUT_ROOT}")

# %%
#  §3 · Test set (free) -----------------------------------------------------
import pandas as pd
TS = os.path.join(REPO_DIR, "test_set")
pairs = pd.read_csv(os.path.join(TS, "pairs.csv"))
# deterministic subsets: triage = 1 easy + 2 medium + 1 hard; grid = stratified 12
tri = pd.concat([pairs[pairs.difficulty == "easy"].head(1),
                 pairs[pairs.difficulty == "medium"].head(2),
                 pairs[pairs.difficulty == "hard"].head(1)])
gri = pd.concat([pairs[pairs.difficulty == "easy"].head(2),
                 pairs[pairs.difficulty == "medium"].head(5),
                 pairs[pairs.difficulty == "hard"].head(5)])
TRIAGE_PAIRS = list(tri.itertuples(index=False))
GRID_PAIRS   = list(gri.itertuples(index=False))
# held-out split: never touched by triage, grid, or any model decision;
# reserved for the final reported numbers
HOLDOUT_PAIRS = list(pairs.drop(index=set(tri.index) | set(gri.index))
                          .itertuples(index=False))
PAIRS_BY_STAGE = {"triage": TRIAGE_PAIRS, "grid": GRID_PAIRS, "holdout": HOLDOUT_PAIRS}
def img_path(kind, pid): return os.path.join(TS, kind, f"{pid}.jpg")
print(f"{len(pairs)} pairs loaded — triage {len(TRIAGE_PAIRS)}, "
      f"grid {len(GRID_PAIRS)}, holdout {len(HOLDOUT_PAIRS)}")

# %%
#  §4 · Preflight + cost estimate (free) ------------------------------------
import fal_client
assert os.environ.get("FAL_KEY"), "FAL_KEY missing"
for r in TRIAGE_PAIRS + GRID_PAIRS + HOLDOUT_PAIRS:
    for p in (img_path("people", r.person_id), img_path("garments", r.garment_id)):
        assert os.path.exists(p), f"missing test image: {p}"
_on = [a for a, v in ARMS_ENABLED.items() if v]
# per-arm costs; survivor-dependent stages use worst-case arm subsets
# (most expensive arms) since survivors are unknown before triage
_desc = sorted((ARM_EST_USD[a] for a in _on), reverse=True)
est = {"triage":    sum(ARM_EST_USD[a] for a in _on) * len(TRIAGE_PAIRS),
       "grid":      (sum(_desc[:SURVIVOR_COUNT]) + ARM_EST_USD[BASELINE]) * len(GRID_PAIRS),
       "reserve":   sum(_desc[:2]) * len(GRID_PAIRS),
       "benchmark": (_desc[0] + ARM_EST_USD[BASELINE]) * len(HOLDOUT_PAIRS)}
print("est. spend if all stages run (worst case, composite excluded): "
      f"${sum(est.values()):.2f} of ${BUDGET_USD:.2f} — "
      + ", ".join(f"{k} ${v:.2f}" for k, v in est.items()))
print("composite arm cost is declared by its own cells (§6e)")

# %%
#  §5 · Harness: arm registry + try_on() + run_stage() (free) ----------------
import io, json, time, hashlib, requests, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

# All four endpoints serve open-weight checkpoints (V2 constraint).
# Schemas verified against live /api pages 2026-08-14: research/fal_v2_endpoint_schemas.md
def _std(person_url, garment_url, seed):        # multi-image instruction editors
    return {"prompt": PROMPT_TEMPLATE, "image_urls": [person_url, garment_url],
            "seed": seed, "num_images": 1}
def _std_acc(person_url, garment_url, seed):    # + disable output acceleration (determinism)
    return {**_std(person_url, garment_url, seed), "acceleration": "none"}
ARM_REGISTRY = {
    "qwen_2511":     {"endpoint": "fal-ai/qwen-image-edit-2511",   # baseline
                      "args": _std_acc, "est_usd": ARM_EST_USD["qwen_2511"]},
    "klein_4b_edit": {"endpoint": "fal-ai/flux-2/klein/4b/distilled/edit",
                      # max 4 reference images; 2 used here; no negative_prompt/guidance exposed
                      "args": _std, "est_usd": ARM_EST_USD["klein_4b_edit"]},
    # v1.5 pinned: only v1.5 weights are open (Apache); fal's newer /v1.6 is FASHN's
    # closed commercial model and the bare /tryon id 404s. Do not bump this version.
    "fashn_v15":     {"endpoint": "fal-ai/fashn/tryon/v1.5",
                      "args": lambda p, g, s: {"model_image": p,
                                               "garment_image": g,
                                               "category": "auto",
                                               "mode": "quality",
                                               "garment_photo_type": "auto",
                                               "seed": s, "num_samples": 1},
                      "est_usd": ARM_EST_USD["fashn_v15"]},   # fixed 864x1296 output
    # v1.1 weights confirmed Apache 2.0 (HF FireRedTeam/FireRed-Image-Edit-1.1)
    "firered_edit":  {"endpoint": "fal-ai/firered-image-edit-v1.1",
                      "args": _std_acc, "est_usd": ARM_EST_USD["firered_edit"]},
}
_upload_cache, RUNS = {}, []
_runs_lock = threading.Lock()   # RUNS is appended from worker threads (§ paid stages)
def upload(path, max_mp=None):
    """Upload to fal, downscaling to a megapixel cap when required by the endpoint."""
    key = (path, max_mp)
    if key not in _upload_cache:   # benign race: worst case re-uploads once
        src = path
        if max_mp:
            im = Image.open(path); mp = im.width * im.height / 1e6
            if mp > max_mp:
                sc = (max_mp / mp) ** 0.5
                im = im.resize((int(im.width * sc), int(im.height * sc)))
                src = f"/tmp/{hashlib.md5(str(key).encode()).hexdigest()}.jpg"
                im.convert("RGB").save(src, quality=95)
        _upload_cache[key] = fal_client.upload_file(src)
    return _upload_cache[key]
def try_on(arm, pair, seed, stage):
    cfg = ARM_REGISTRY[arm]
    t0 = time.time()
    meta = None
    try:
        if "call" in cfg:   # multi-call pipeline arms (composite): no single endpoint
            img, meta = cfg["call"](pair, seed)
            args = {}
        else:
            rz = cfg.get("resize", {})
            args = cfg["args"](upload(img_path("people", pair.person_id), rz.get("person_mp")),
                               upload(img_path("garments", pair.garment_id), rz.get("garment_mp")),
                               seed)
            res = fal_client.subscribe(cfg["endpoint"], arguments=args)
            url = (res.get("images") or [res.get("image", {})])[0].get("url")
            img = Image.open(io.BytesIO(requests.get(url).content)).convert("RGB")
    except Exception as e:
        with _runs_lock:
            RUNS.append({"arm": arm, "pair": f"{pair.person_id}x{pair.garment_id}",
                         "stage": stage, "seed": seed, "ok": False, "err": str(e)[:200]})
        return None
    rid = f"{stage}_{arm}_{pair.person_id}x{pair.garment_id}_s{seed}"
    rdir = os.path.join(OUT_ROOT, rid); os.makedirs(rdir, exist_ok=True)
    img.save(os.path.join(rdir, "result.png"))
    rec = {"arm": arm, "pair": f"{pair.person_id}x{pair.garment_id}", "stage": stage,
           "seed": seed, "ok": True, "latency_s": round(time.time() - t0, 1),
           "est_usd": cfg["est_usd"], "endpoint": cfg["endpoint"], "dir": rdir}
    extra = {"pipeline_meta": meta} if meta is not None else {"args_keys": list(args)}
    json.dump({**rec, **extra},
              open(os.path.join(rdir, "run_config.json"), "w"), indent=2)
    with _runs_lock:
        RUNS.append(rec)
    return img
def spent(): return sum(r.get("est_usd", 0) for r in RUNS if r.get("ok"))
STAGE_SEED_OFFSET = {"triage": 0, "grid": 100, "reserve": 200, "holdout": 300}
def run_stage(arms, plist, stage, seed_off, workers=8):
    """Concurrent stage runner. fal_client.subscribe is blocking, so calls fan
    out on a thread pool. The budget ceiling is enforced at submit time via a
    committed-cost counter (spent() lags while futures are in flight); RESULTS
    is written only from this thread."""
    todo = [(a, i, p) for a in arms for i, p in enumerate(plist)
            if (stage, a, i, SEED_BASE + seed_off + i) not in RESULTS]
    if not todo:
        print(f"[{stage}] nothing to run — all outputs already present")
        return
    committed = spent()
    futs = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for a, i, pair in todo:
            c = ARM_REGISTRY[a]["est_usd"]
            if committed + c > BUDGET_USD:
                print(f"[{stage}] budget ceiling — stopped before {a} pair {i}")
                break
            committed += c
            futs[ex.submit(try_on, a, pair, SEED_BASE + seed_off + i, stage)] = (a, i)
        for f in as_completed(futs):
            a, i = futs[f]
            img = f.result()
            if img is not None:
                RESULTS[(stage, a, i, SEED_BASE + seed_off + i)] = img
    print(f"[{stage}] {len(futs)} calls done ({workers}-way) — est ${spent():.2f} spent")

# %%
#  §5b · Reload prior results from run packages (free) -----------------------
# Makes paid stages idempotent: anything already generated is never re-bought.
# Reads only OUT_ROOT, which is a V2-only path (§2) — V1 runs are never ingested.
import glob
RESULTS = globals().get("RESULTS", {})
def reload_results():
    idx = {(s, f"{p.person_id}x{p.garment_id}"): i
           for s, pl in PAIRS_BY_STAGE.items() for i, p in enumerate(pl)}
    seen = {(r["stage"], r["arm"], r["pair"], r["seed"]) for r in RUNS}
    n = 0
    for cfgp in glob.glob(os.path.join(OUT_ROOT, "*", "run_config.json")):
        rec = json.load(open(cfgp))
        f = os.path.join(os.path.dirname(cfgp), "result.png")
        i = idx.get((rec["stage"], rec["pair"]))
        if i is None or not os.path.exists(f):
            continue
        k = (rec["stage"], rec["arm"], i, rec["seed"])
        if k in RESULTS:
            continue
        RESULTS[k] = Image.open(f).convert("RGB")
        if (rec["stage"], rec["arm"], rec["pair"], rec["seed"]) not in seen:
            RUNS.append({c: rec.get(c) for c in ("arm", "pair", "stage", "seed", "ok",
                                                 "latency_s", "est_usd", "endpoint", "dir")})
        n += 1
    print(f"reloaded {n} prior results — est spend on record ${spent():.2f}")
reload_results()

# %% [markdown]
# ## §5c · Deterministic judges (free, local CPU) — the authoritative metric set
# Four metrics per output, no API calls:
# - `garment_sim` — similarity between the output's torso crop and the
#   reference garment (catches "wrong garment" and "changed nothing").
#   V1 shipped an HSV-histogram proxy; V2 replaces it with Marqo-FashionSigLIP
#   embeddings (`v2/build/metrics_v2.py`, integration point marked below).
# - `identity_cos` — face-embedding cosine, input person vs output. V1 used
#   ArcFace; V2 replaces it with AuraFace (same integration point).
# - `pose_err` — mean pose-landmark displacement, normalized by torso size
#   (lower is better)
# - `bg_psnr` — PSNR outside the person mask, input vs output (background drift)
#
# These aggregate into a per-arm matrix plus a fixed-anchor composite `score`
# that produces the authoritative ranking. Defined here, before the paid
# stages, because survivor selection (§6b) depends on them.

# %%
#  §5c · Deterministic judges: metrics + composite ranking (free) ------------
if IN_COLAB:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "numpy",
                    "opencv-python-headless", "onnxruntime", "insightface",
                    "mediapipe", "open_clip_torch", "huggingface_hub"],
                   check=True)   # torch ships with Colab
import numpy as np, cv2
import mediapipe as mp
_tls = threading.local()   # mediapipe graphs are not thread-safe; one set per thread
# identity_cos: AuraFace-v1 (Apache 2.0) replaces the NC-licensed buffalo_l
# pack. Single shared session (onnxruntime run() is thread-safe); weights
# download once to AURAFACE_ROOT (Drive-cached on Colab, set in section 2).
_models_lock = threading.Lock()
_aura = None
def _face():
    global _aura
    with _models_lock:
        if _aura is None:
            from huggingface_hub import snapshot_download
            from insightface.app import FaceAnalysis
            _aroot = os.environ.get("AURAFACE_ROOT",
                                    os.path.expanduser("~/.cache/auraface"))
            snapshot_download("fal/AuraFace-v1",
                              local_dir=os.path.join(_aroot, "models", "auraface"))
            _aura = FaceAnalysis(name="auraface", root=_aroot,
                                 providers=["CPUExecutionProvider"])
            _aura.prepare(ctx_id=-1, det_size=(640, 640))
    return _aura
def identity_cosine(person_img, result_img):
    fa = _face().get(cv2.cvtColor(_rgb(person_img), cv2.COLOR_RGB2BGR))
    fb = _face().get(cv2.cvtColor(_rgb(result_img), cv2.COLOR_RGB2BGR))
    if not fa or not fb: return None
    ea = max(fa, key=lambda f: f.bbox[2] - f.bbox[0]).normed_embedding
    eb = max(fb, key=lambda f: f.bbox[2] - f.bbox[0]).normed_embedding
    return float(np.dot(ea, eb))
def _pose_g():
    if not hasattr(_tls, "pose"):
        _tls.pose = mp.solutions.pose.Pose(static_image_mode=True)
    return _tls.pose
def _seg_g():
    if not hasattr(_tls, "seg"):
        _tls.seg = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)
    return _tls.seg
def _rgb(img): return np.array(img.convert("RGB"))
def _landmarks(img):
    res = _pose_g().process(_rgb(img))
    if not res.pose_landmarks: return None
    return np.array([[l.x, l.y, l.visibility] for l in res.pose_landmarks.landmark])
def pose_error(person_img, result_img):
    la, lb = _landmarks(person_img), _landmarks(result_img)
    if la is None or lb is None: return None
    vis = (la[:, 2] > 0.5) & (lb[:, 2] > 0.5)
    if vis.sum() < 6: return None
    torso = np.linalg.norm(la[11, :2] - la[24, :2]) + 1e-6
    return float(np.linalg.norm(la[vis, :2] - lb[vis, :2], axis=1).mean() / torso)
def background_psnr(person_img, result_img):
    a = _rgb(person_img).astype(np.float64)
    b = np.array(result_img.convert("RGB").resize(person_img.size)).astype(np.float64)
    mask = _seg_g().process(_rgb(person_img)).segmentation_mask
    bg = mask < 0.5
    if bg.sum() < 500: return None
    mse = ((a - b) ** 2)[bg].mean()
    return float(10 * np.log10(255 ** 2 / mse)) if mse > 0 else 99.0
def _torso_crop(img):
    lm = _landmarks(img); w, h = img.size
    if lm is None:
        return img.crop((int(w * .25), int(h * .2), int(w * .75), int(h * .8)))
    pts = lm[[11, 12, 23, 24], :2] * [w, h]
    x0, y0 = pts.min(0); x1, y1 = pts.max(0)
    mx, my = (x1 - x0) * 0.25, (y1 - y0) * 0.15
    return img.crop((max(0, int(x0 - mx)), max(0, int(y0 - my)),
                     min(w, int(x1 + mx)), min(h, int(y1 + my))))
# garment_sim: Marqo-FashionSigLIP embedding cosine (sees pattern and cut,
# not only color) replaces the V1 HSV-histogram proxy, which was noise:
# spearman 0.00 vs the VLM garment criterion on V1 outputs (new metric 0.51).
# See v2/build/metric_recalibration.md. _torso_crop stays as the crop source.
_siglip = None
def _fashion_clip():
    global _siglip
    with _models_lock:
        if _siglip is None:
            import torch, open_clip
            model, _, preprocess = open_clip.create_model_and_transforms(
                "hf-hub:Marqo/marqo-fashionSigLIP")
            model.eval()
            _siglip = (model, preprocess, torch)
    return _siglip
def _embed(img):
    model, preprocess, torch = _fashion_clip()
    with torch.no_grad(), _models_lock:
        return model.encode_image(preprocess(img.convert("RGB")).unsqueeze(0),
                                  normalize=True)[0].numpy()
def garment_similarity(result_img, garment_img):
    return float(np.dot(_embed(garment_img), _embed(_torso_crop(result_img))))
CV_COLS = ["garment_sim", "identity_cos", "pose_err", "bg_psnr"]
CV_CACHE = {}
def cv_scores(stage):
    """Score every output of a stage; cached per output-count so re-calls are free."""
    plist = PAIRS_BY_STAGE[stage]
    keys = sorted(k for k in RESULTS if k[0] == stage)
    ck = (stage, len(keys))
    if ck in CV_CACHE: return CV_CACHE[ck]
    def _score_one(k):
        pair = plist[k[2]]
        person = Image.open(img_path("people", pair.person_id))
        garment = Image.open(img_path("garments", pair.garment_id))
        out = RESULTS[k]
        return {"stage": stage, "arm": k[1], "pair_idx": k[2],
                "pair": f"{pair.person_id}x{pair.garment_id}",
                "garment_sim": garment_similarity(out, garment),
                "identity_cos": identity_cosine(person, out),
                "pose_err": pose_error(person, out),
                "bg_psnr": background_psnr(person, out)}
    with ThreadPoolExecutor(max_workers=3) as ex:   # 3-way: each thread holds its own models
        rows = list(ex.map(_score_one, keys))
    print(f"[{stage}] scored {len(rows)} outputs (3-way parallel)")
    CV_CACHE[ck] = pd.DataFrame(rows)
    return CV_CACHE[ck]
# garment_sim carries double weight: garment transfer is the core product
# objective. FashionSigLIP replaced the V1 color-histogram proxy, which was
# blind to warped patterns (validated in v2/build/metric_recalibration.md).
CV_WEIGHTS = {"garment_sim": 2.0, "identity_cos": 1.0, "pose_err": 1.0, "bg_psnr": 1.0}
# Fixed absolute anchors, not min-max across arms: min-max over-rewards
# compositing arms that paste original pixels back (identity/background max
# out by construction). identity saturates at the high-confidence same-person
# level — cosine above it is pixel reuse, not stronger identity.
# Recalibrated on 118 re-scored V1 outputs (v2/build/metric_recalibration.md):
# garment_sim lo = wrong-garment control median (chance floor for embedding
# cosines), hi = matched-output p95; identity_cos maps V1's buffalo anchors via
# linear fit, ceiling 0.80 stays far below paste-back saturation (~0.97).
CV_ANCHORS = {"garment_sim": (0.55, 0.85), "identity_cos": (0.42, 0.80),
              "pose_err": (0.25, 0.0), "bg_psnr": (12.0, 32.0)}
def cv_matrix(M):
    """Raw metric means per arm + composite = mean of per-OUTPUT anchored
    composites (each output scored individually, then averaged — same
    aggregation order as the VLM board)."""
    rows = M.copy()
    for c, (lo, hi) in CV_ANCHORS.items():
        rows[c + "_n"] = ((rows[c] - lo) / (hi - lo)).clip(0, 1)
    total = sum(CV_WEIGHTS.values())
    rows["comp"] = sum(rows[c + "_n"] * CV_WEIGHTS[c] for c in CV_COLS) / total
    mat = M.groupby("arm")[CV_COLS].mean()
    mat["score"] = rows.groupby("arm")["comp"].mean().round(3)
    return mat.round(3).sort_values("score", ascending=False)
print("deterministic judges loaded")

# %%
#  §6a · Triage run (paid) — executes only when RUN_TRIAGE=True -------------
if RUN_TRIAGE:
    run_stage([a for a, on in ARMS_ENABLED.items() if on],
              TRIAGE_PAIRS, "triage", STAGE_SEED_OFFSET["triage"])
    print(f"triage done — {len([k for k in RESULTS if k[0] == 'triage'])} ok")
else:
    print("triage skipped (RUN_TRIAGE=False)")

# %%
#  §6b · Survivor selection — top 50% by deterministic score + baseline ------
# Elimination rule: the SURVIVOR_COUNT best arms by triage composite advance;
# the baseline always advances for comparison. Deterministic, so a top-to-bottom
# re-run reproduces the same elimination. Set SURVIVORS in §1 to override.
if not SURVIVORS and any(k[0] == "triage" for k in RESULTS):
    tri_matrix = cv_matrix(cv_scores("triage"))
    print(tri_matrix.to_string())
    SURVIVORS = list(tri_matrix.index[:SURVIVOR_COUNT])
    if BASELINE not in SURVIVORS:
        SURVIVORS.append(BASELINE)
    print("auto-selected survivors (top "
          f"{SURVIVOR_COUNT} + baseline): {SURVIVORS}")
elif SURVIVORS:
    print("manual survivor override:", SURVIVORS)
else:
    print("no triage results yet — survivors not selected")

# %%
#  §6c · Grid run (paid) — survivors x 12 pairs; RUN_GRID=True ---------------
if RUN_GRID:
    assert SURVIVORS, "no survivors — run triage (§6a) so §6b can select them"
    run_stage(SURVIVORS, GRID_PAIRS, "grid", STAGE_SEED_OFFSET["grid"])
else:
    print("grid skipped (RUN_GRID=False)")

# %%
#  §6d · Reserve run (paid) — best-of-2 on TOP2; RUN_RESERVE=True ------------
# TOP2 auto-derives from the deterministic grid ranking (composite excluded —
# it has its own seed policy), keeping the stage zero-input and reproducible.
# Second generation per pair, seed offset 200: measures seed variance and
# enables best-of-2 selection.
if RUN_RESERVE:
    if not TOP2 and any(k[0] == "grid" for k in RESULTS):
        TOP2 = [a for a in cv_matrix(cv_scores("grid")).index
                if a != "composite_v2ow"][:2]
        print("auto-selected TOP2 from grid ranking:", TOP2)
    assert TOP2, "no grid results yet — run §6c first"
    run_stage(TOP2, GRID_PAIRS, "grid", STAGE_SEED_OFFSET["reserve"])
else:
    print("reserve skipped (RUN_RESERVE=False)")

# %%
#  §6e · Composite arm slot — COMPOSITE-V2 integration point -----------------
# The composite arm ("composite_v2ow") is developed separately in
# v2/build/composite_cells.py. Do not implement composite logic in this cell.
# Merge contract (either or both):
#   1. Register ARM_REGISTRY["composite_v2ow"] = {"endpoint": ..., "args":
#      callable(person_url, garment_url, seed) -> dict, "est_usd": ...} so the
#      shared harness (try_on / run_stage / budget ceiling) drives it.
#   2. Define composite_try_on(person_path, garment_path) -> PIL.Image for the
#      one-click path (§12b) when the pipeline is multi-call.
#  V2 composite arm (composite_v2ow) — notebook cells ------------------------
#  klein_4b gen -> geometric face paste-back -> z-image low-strength refine
#  -> AuraFace identity gate (retry seed+1000, best-of-N).
#  Geometric paste-back only: V1 prompted identity-restore pulled the original
#  clothing back or lost to baseline; do not add prompted-restore stages.
#  fal is confined to the default_* wrappers; the harness injects gen_fn /
#  refine_fn / upload_fn so pipeline logic never touches fal_client.

#  §C1 · Constants ------------------------------------------------------------
import io
import math
import os
import tempfile

import cv2
import numpy as np
from PIL import Image

ARM_NAME = "composite_v2ow"
GEN_ENDPOINT = "fal-ai/flux-2/klein/4b/distilled/edit"       # $0.014 first MP
REFINE_ENDPOINT = "fal-ai/z-image/turbo/image-to-image"      # $0.005/MP
# Schemas per research/fal_v2_endpoint_schemas.md (verified 2026-08-14):
# klein: prompt + image_urls (person first, garment second) + seed; no
# negative_prompt/guidance. z-image: single image_url string + strength.
GEN_PROMPT = (
    "Replace the clothing of the person in image 1 with the garment shown in "
    "image 2. Keep the person's face, hair, skin tone, pose, hands, body and "
    "the background completely unchanged. Preserve the garment's exact "
    "color, pattern, print, and cut."
)
REFINE_PROMPT = (
    "Enhance the photo realism of this image. Fix any artifacts in hands, "
    "skin, and fabric textures. Do not change the person's identity, face, "
    "pose, clothing, or the background."
)
REFINE_STRENGTH = 0.2
IDENTITY_THRESHOLD = 0.55        # AuraFace cosine gate; starting point, tune on data
MAX_CANDIDATES = 3
CANDIDATE_SEED_STEP = 1000
FEATHER_FRAC = 0.05              # Gaussian sigma as fraction of face size
FACE_EXPAND = 0.25               # bbox expansion for the paste crop
HEAD_EXPAND = 0.35               # bbox expansion for the garment-overlap guard
CHANGE_DIFF_FLOOR = 30           # min gray delta counted as "changed"
MIN_CHANGE_AREA_FRAC = 0.01      # smaller change regions cannot block paste
GLOBAL_CHANGE_FRAC = 0.60        # above this the change region is unlocalizable
HEAD_OVERLAP_FRAC = 0.08         # garment pixels / head area that block paste
AURAFACE_REPO = "fal/AuraFace-v1"
AURAFACE_ROOT = os.environ.get(
    "AURAFACE_ROOT", os.path.join(tempfile.gettempdir(), "auraface"))


#  §C2 · Image + fal wrappers (fal only lives here) ---------------------------
def load_image(x):
    """Path or PIL -> RGB PIL."""
    if isinstance(x, Image.Image):
        return x.convert("RGB")
    return Image.open(x).convert("RGB")


def fal_upload(img_or_path):
    """Default upload_fn. Returns a URL fal endpoints accept."""
    import fal_client
    if isinstance(img_or_path, str):
        return fal_client.upload_file(img_or_path)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        load_image(img_or_path).save(f.name)
        path = f.name
    try:
        return fal_client.upload_file(path)
    finally:
        os.unlink(path)


def _cmp_fal_image(endpoint, args):
    import fal_client
    import requests
    res = fal_client.subscribe(endpoint, arguments=args)
    url = (res.get("images") or [res.get("image", {})])[0].get("url")
    return Image.open(io.BytesIO(requests.get(url).content)).convert("RGB")


def default_gen_fn(person_url, garment_url, seed):
    """gen_fn(person_url, garment_url, seed) -> PIL. Person first, garment second."""
    return _cmp_fal_image(GEN_ENDPOINT, {
        "prompt": GEN_PROMPT, "image_urls": [person_url, garment_url],
        "seed": seed, "num_images": 1})


def default_refine_fn(img, seed):
    """refine_fn(img, seed) -> PIL. Low-strength realism pass."""
    return _cmp_fal_image(REFINE_ENDPOINT, {
        "prompt": REFINE_PROMPT, "image_url": fal_upload(img),
        "strength": REFINE_STRENGTH, "seed": seed, "num_images": 1,
        "enable_prompt_expansion": False})


#  §C3 · Face detection (mediapipe, insightface fallback) ---------------------
_MP_DETECTOR = None


def _mediapipe_detector():
    global _MP_DETECTOR
    if _MP_DETECTOR is None:
        import mediapipe as mp
        _MP_DETECTOR = mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.5)
    return _MP_DETECTOR


def detect_face(img):
    """Largest-face pixel bbox (x0, y0, x1, y1) or None."""
    rgb = np.asarray(load_image(img))
    h, w = rgb.shape[:2]
    try:
        res = _mediapipe_detector().process(rgb)
        dets = res.detections or []
        boxes = []
        for d in dets:
            r = d.location_data.relative_bounding_box
            boxes.append((r.xmin * w, r.ymin * h,
                          (r.xmin + r.width) * w, (r.ymin + r.height) * h))
    except Exception:                       # mediapipe unavailable on this host
        faces = auraface_app().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        boxes = [tuple(f.bbox) for f in faces]
    if not boxes:
        return None
    x0, y0, x1, y1 = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)


def _expand_bbox(bbox, frac, w, h):
    x0, y0, x1, y1 = bbox
    dx, dy = (x1 - x0) * frac, (y1 - y0) * frac
    return (max(0, int(x0 - dx)), max(0, int(y0 - dy)),
            min(w, int(x1 + dx)), min(h, int(y1 + dy)))


#  §C4 · Garment-overlap guard ------------------------------------------------
def garment_blocks_face(person_img, gen_img, gen_face_bbox):
    """True when the garment change region reaches the head (hoods etc.);
    also True when the change is too global to localize — in doubt, no paste."""
    gen = np.asarray(load_image(gen_img))
    h, w = gen.shape[:2]
    orig = cv2.resize(np.asarray(load_image(person_img)), (w, h))
    diff = cv2.absdiff(cv2.cvtColor(gen, cv2.COLOR_RGB2GRAY),
                       cv2.cvtColor(orig, cv2.COLOR_RGB2GRAY))
    diff = cv2.GaussianBlur(diff, (5, 5), 0)
    # Otsu separates garment-scale change from global render drift.
    otsu, _ = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = (diff > max(CHANGE_DIFF_FLOOR, otsu)).astype(np.uint8)
    if mask.mean() > GLOBAL_CHANGE_FRAC:
        return True
    fb = gen_face_bbox
    head = _expand_bbox(fb, HEAD_EXPAND, w, h)
    work = mask.copy()
    work[fb[1]:fb[3], fb[0]:fb[2]] = 0             # face re-render never counts
    work = cv2.dilate(work, np.ones((7, 7), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(work)
    head_area = max(1, (head[2] - head[0]) * (head[3] - head[1]))
    for i in range(1, n):
        if stats[i][4] < MIN_CHANGE_AREA_FRAC * w * h:
            continue
        # Hood-style coverage fills the head region; a neckline only grazes it.
        inside = int((labels[head[1]:head[3], head[0]:head[2]] == i).sum())
        if inside > HEAD_OVERLAP_FRAC * head_area:
            return True
    return False


#  §C5 · Face paste-back ------------------------------------------------------
def face_paste_back(person_img, gen_img):
    """Feathered-ellipse paste of the original face over the generated face.
    Returns (PIL, meta). Skips gracefully: missing faces, garment over head."""
    person_img, gen_img = load_image(person_img), load_image(gen_img)
    meta = {"paste_applied": False, "skip_reason": None}
    src = detect_face(person_img)
    if src is None:
        meta["skip_reason"] = "no_face_in_person"
        return gen_img, meta
    dst = detect_face(gen_img)
    if dst is None:
        meta["skip_reason"] = "no_face_in_generated"
        return gen_img, meta
    if garment_blocks_face(person_img, gen_img, dst):
        meta["skip_reason"] = "garment_overlaps_head"
        return gen_img, meta

    sw, sh = person_img.size
    gw, gh = gen_img.size
    se = _expand_bbox(src, FACE_EXPAND, sw, sh)
    de = _expand_bbox(dst, FACE_EXPAND, gw, gh)
    dw, dh = de[2] - de[0], de[3] - de[1]
    if dw < 8 or dh < 8:
        meta["skip_reason"] = "face_too_small"
        return gen_img, meta
    crop = np.asarray(person_img.crop(se), dtype=np.float32)
    crop = cv2.resize(crop, (dw, dh), interpolation=cv2.INTER_LANCZOS4)

    mask = np.zeros((dh, dw), np.float32)
    cv2.ellipse(mask, (dw // 2, dh // 2), (int(dw * 0.42), int(dh * 0.44)),
                0, 0, 360, 1.0, -1)
    sigma = max(1.0, FEATHER_FRAC * max(dst[2] - dst[0], dst[3] - dst[1]))
    mask = cv2.GaussianBlur(mask, (0, 0), sigma)[..., None]

    out = np.asarray(gen_img, dtype=np.float32)
    region = out[de[1]:de[3], de[0]:de[2]]
    out[de[1]:de[3], de[0]:de[2]] = crop * mask + region * (1.0 - mask)
    meta.update({"paste_applied": True, "src_bbox": list(src),
                 "dst_bbox": list(dst)})
    return Image.fromarray(out.clip(0, 255).astype(np.uint8)), meta


#  §C6 · AuraFace identity gate -----------------------------------------------
_AURAFACE = None


def auraface_app():
    """AuraFace-v1 (Apache-2.0) via insightface; downloads ~300MB once."""
    global _AURAFACE
    if _AURAFACE is None:
        from huggingface_hub import snapshot_download
        from insightface.app import FaceAnalysis
        snapshot_download(AURAFACE_REPO, local_dir=os.path.join(
            AURAFACE_ROOT, "models", "auraface"))
        app = FaceAnalysis(name="auraface", root=AURAFACE_ROOT,
                           providers=["CPUExecutionProvider"],
                           allowed_modules=["detection", "recognition"])
        app.prepare(ctx_id=0, det_size=(640, 640))
        _AURAFACE = app
    return _AURAFACE


def face_embedding(img):
    """Normalized AuraFace embedding of the largest face, or None."""
    bgr = cv2.cvtColor(np.asarray(load_image(img)), cv2.COLOR_RGB2BGR)
    faces = auraface_app().get(bgr)
    if not faces:
        return None
    f = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return f.normed_embedding


def face_identity_cosine(ref_emb, img):
    """Cosine(ref person, largest face in img); None when either is missing."""
    if ref_emb is None:
        return None
    emb = face_embedding(img)
    if emb is None:
        return None
    return float(np.dot(ref_emb, emb))


#  §C7 · Full arm -------------------------------------------------------------
def composite_try_on(person, garment, seed, gen_fn=None, refine_fn=None,
                     upload_fn=None):
    """Person + garment -> (PIL, meta). Meta is JSON-safe for run_config.json:
    per-candidate cosines, paste decisions, shipped candidate index."""
    gen_fn = gen_fn or default_gen_fn
    refine_fn = refine_fn or default_refine_fn
    upload_fn = upload_fn or fal_upload
    person_img = load_image(person)
    person_url = upload_fn(person if isinstance(person, str) else person_img)
    garment_url = upload_fn(garment if isinstance(garment, str)
                            else load_image(garment))
    ref_emb = face_embedding(person_img)

    images, cands = [], []
    for i in range(MAX_CANDIDATES):
        s = seed + i * CANDIDATE_SEED_STEP
        gen = gen_fn(person_url, garment_url, s)
        pasted, pmeta = face_paste_back(person_img, gen)
        cos_pre = face_identity_cosine(ref_emb, pasted)
        refined = refine_fn(pasted, s)
        cos_post = face_identity_cosine(ref_emb, refined)
        repasted = False
        # Refine drifted the face past the gate: one geometric re-paste.
        if (cos_pre is not None and cos_post is not None
                and cos_pre >= IDENTITY_THRESHOLD
                and cos_post < IDENTITY_THRESHOLD):
            repaired, rmeta = face_paste_back(person_img, refined)
            if rmeta["paste_applied"]:
                refined, repasted = repaired, True
                cos_post = face_identity_cosine(ref_emb, refined)
        images.append(refined)
        cands.append({"seed": s, "paste_applied": pmeta["paste_applied"],
                      "paste_skip_reason": pmeta["skip_reason"],
                      "cos_pre_refine": cos_pre, "cos_post_refine": cos_post,
                      "repasted": repasted})
        if ref_emb is None:                 # gate cannot run; retries are noise
            break
        if cos_post is not None and cos_post >= IDENTITY_THRESHOLD:
            break

    scores = [(-math.inf if c["cos_post_refine"] is None
               else c["cos_post_refine"]) for c in cands]
    best = int(np.argmax(scores)) if any(s > -math.inf for s in scores) else 0
    meta = {"arm": ARM_NAME, "gen_endpoint": GEN_ENDPOINT,
            "refine_endpoint": REFINE_ENDPOINT,
            "refine_strength": REFINE_STRENGTH,
            "identity_threshold": IDENTITY_THRESHOLD,
            "identity_model": AURAFACE_REPO, "seed": seed,
            "gate_active": ref_emb is not None, "candidates": cands,
            "shipped_candidate": best,
            "shipped_cos": cands[best]["cos_post_refine"],
            "paste_applied": cands[best]["paste_applied"]
            or cands[best]["repasted"]}
    return images[best], meta

# Inlined from v2/build/composite_cells.py (identity_cosine -> face_identity_cosine
# and _fal_image -> _cmp_fal_image renamed: the harness owns those names).

# %%
#  §6e (cont.) · Composite registration + grid run ---------------------------
COMPOSITE_ARM = ARM_NAME                       # "composite_v2ow"
COMPOSITE_EST_USD = 0.06   # worst case: 3 candidates x (klein 0.014 + z-image 0.005)
def _composite_call(pair, seed):
    return composite_try_on(img_path("people", pair.person_id),
                            img_path("garments", pair.garment_id), seed)
ARM_REGISTRY[COMPOSITE_ARM] = {
    "endpoint": f"{GEN_ENDPOINT} -> paste-back -> {REFINE_ENDPOINT} (AuraFace gate)",
    "call": _composite_call, "est_usd": COMPOSITE_EST_USD}
# Like V1's cascade arm, the composite enters grid + holdout regardless of
# triage rank: grid here, holdout via BENCH_ARMS in §6f.
if COMPOSITE_ARM in ARM_REGISTRY:
    if RUN_COMPOSITE:
        run_stage([COMPOSITE_ARM], GRID_PAIRS, "grid", STAGE_SEED_OFFSET["grid"])
    else:
        print("composite grid run skipped (RUN_COMPOSITE=False)")
else:
    print("composite arm not registered yet — merge v2/build/composite_cells.py "
          "into this cell (it participates in grid, holdout, boards, and §12c)")

# %%
#  §6f · Held-out benchmark (paid) — final numbers; RUN_BENCHMARK=True -------
# BENCH_ARMS auto-selects: grid winner + composite_v2ow + baseline. The 18
# held-out pairs were never seen by triage, grid, or any selection decision,
# so these are the reportable numbers.
if RUN_BENCHMARK:
    if not BENCH_ARMS:
        gboard = cv_matrix(cv_scores("grid"))
        winner = next(a for a in gboard.index if a != COMPOSITE_ARM)
        BENCH_ARMS = list(dict.fromkeys([winner, COMPOSITE_ARM, BASELINE]))
        print("benchmark arms:", BENCH_ARMS)
    runnable = [a for a in BENCH_ARMS if a in ARM_REGISTRY]
    missing = [a for a in BENCH_ARMS if a not in ARM_REGISTRY]
    if missing:
        print(f"not in ARM_REGISTRY, skipped here: {missing} — the composite "
              "runs its holdout pass via its own cells (§6e) if not registered")
    run_stage(runnable, HOLDOUT_PAIRS, "holdout", STAGE_SEED_OFFSET["holdout"])
    n_h = len([k for k in RESULTS if k[0] == "holdout"])
    print(f"benchmark done — {n_h} holdout outputs on record")
else:
    print("benchmark skipped (RUN_BENCHMARK=False)")

# %%
#  §7 · Comparison grids (free, thumbnails only) ----------------------------
import matplotlib
matplotlib.use("Agg") if not IN_COLAB and not os.environ.get("DISPLAY") else None
import matplotlib.pyplot as plt
def show_stage(stage, pairs_list, thumb=224, save=None):
    arms = sorted({k[1] for k in RESULTS if k[0] == stage})
    if not arms: print(f"no {stage} results yet"); return
    rows = len(pairs_list); cols = len(arms) + 2
    fig, ax = plt.subplots(rows, cols, figsize=(2.1 * cols, 2.4 * rows))
    for r, pair in enumerate(pairs_list):
        ins = [Image.open(img_path("people", pair.person_id)),
               Image.open(img_path("garments", pair.garment_id))]
        for c, (ttl, im) in enumerate(zip(["person", "garment"], ins)):
            t = im.copy(); t.thumbnail((thumb, thumb))
            ax[r][c].imshow(t); ax[r][c].set_title(ttl, fontsize=7)
        for c, arm in enumerate(arms, start=2):
            hit = next((v for k, v in RESULTS.items()
                        if k[0] == stage and k[1] == arm and k[2] == r), None)
            if hit:
                t = hit.copy(); t.thumbnail((thumb, thumb))
                ax[r][c].imshow(t)
            ax[r][c].set_title(arm, fontsize=7)
        for c in range(cols): ax[r][c].axis("off")
    plt.tight_layout()
    if save:
        fig.savefig(save, dpi=72); print(f"grid saved -> {save}")
    plt.show()
show_stage("triage", TRIAGE_PAIRS, save=os.path.join(OUT_ROOT, "grid_triage.png"))
show_stage("grid", GRID_PAIRS, save=os.path.join(OUT_ROOT, "grid_main.png"))
show_stage("holdout", HOLDOUT_PAIRS, save=os.path.join(OUT_ROOT, "grid_holdout.png"))

# %% [markdown]
# ---
# # §8 · Human verification (insurance)
# The deterministic judges (§5c) produce the authoritative ranking and §6b
# picks survivors automatically — no human action is required for the pipeline
# to run. This section verifies the judges:
# 1. Eyeball the §7 grids against the §10 matrices. The judge-agreement table
#    in §10 flags arms where the VLM ranking disagrees with the deterministic
#    one — check those rows first.
# 2. To quantify a disagreement, score any subset of rows in the sheet
#    (1–5 per criterion, 5 = flawless); your scores print as a third board in §10:
#    - `garment` — the output garment matches the reference (color, print, cut)
#    - `identity` — same face, hair, and body
#    - `scene` — pose and background unchanged
#    - `clean` — free of artifacts (hands, seams, textures)
#
#    Fill scores in `judging_sheet.csv` (saved next to the run outputs), then
#    run the save cell. Rows left fully blank are treated as unscored and
#    skipped.

# %%
#  §8a · Build judging sheet (free) -----------------------------------------
JUDGING_SHEET = os.path.join(OUT_ROOT, "judging_sheet.csv")   # not CWD: survives Colab resets
def _pairs_for(stage): return PAIRS_BY_STAGE[stage]
_judge_keys = sorted(RESULTS)
sheet = pd.DataFrame([{"stage": k[0], "arm": k[1], "pair_idx": k[2],
                       "pair": f"{_pairs_for(k[0])[k[2]].person_id}x"
                               f"{_pairs_for(k[0])[k[2]].garment_id}",
                       "garment": None, "identity": None, "scene": None,
                       "clean": None, "hands": None, "realism": None}
                      for k in _judge_keys],
                     columns=["stage", "arm", "pair_idx", "pair", "garment",
                              "identity", "scene", "clean", "hands", "realism"])
sheet.to_csv(JUDGING_SHEET, index=False)
print(f"{len(sheet)} outputs to judge -> {JUDGING_SHEET} (rows match judge_view index)")
def judge_view(row_i, size=380):
    """View one output at full size alongside its person and garment inputs."""
    k = _judge_keys[row_i]
    pair = _pairs_for(k[0])[k[2]]
    fig, ax = plt.subplots(1, 3, figsize=(9, 3.4))
    for a, (ttl, im) in zip(ax, [("person", Image.open(img_path("people", pair.person_id))),
                                 ("garment", Image.open(img_path("garments", pair.garment_id))),
                                 (k[1], RESULTS[k])]):
        t = im.copy(); t.thumbnail((size, size))
        a.imshow(t); a.set_title(ttl, fontsize=9); a.axis("off")
    plt.show()
# judge_view(0)  # step through rows 0..N-1 while filling the sheet

# %%
#  §8b · Save human judgments (free) -----------------------------------------
crit = ["garment", "identity", "scene", "clean", "hands", "realism"]
if not os.path.exists(JUDGING_SHEET):
    print("no judging sheet yet — run §8a first")
else:
    done = pd.read_csv(JUDGING_SHEET)
    filled = done.dropna(subset=crit, how="all")
    partial = filled[filled[crit].isna().any(axis=1)]
    assert not len(partial), f"{len(partial)} partially scored rows — fill or blank them"
    if len(filled):
        filled.to_csv(os.path.join(OUT_ROOT, "judgments.csv"), index=False)
        print(f"{len(filled)} human judgments saved -> judgments.csv (subset is fine)")
    else:
        print("no scored rows yet — fill judging_sheet.csv, then re-run")

# %% [markdown]
# ## §9 · VLM judge — `gpt-5.5` (confirmation only, zero ranking weight)
# Same rubric as §8, scored blind (the judge sees images only, never arm
# names). Its board carries no weight in the ranking — the deterministic
# composite is authoritative. §10 compares the two and flags any arm whose VLM
# rank departs from its deterministic rank (known VLM weakness: lenient on
# person swaps). Approximate cost: \$0.025 per judged output. Requires
# `OPENAI_API_KEY` (Colab Secrets or `.env`). Verdicts are schema-validated
# with up to 3 self-correct retries; a malformed reply is recorded as unscored
# rather than corrupting the board.

# %%
#  §9 · VLM judge (free to load; spends only via §9b) ------------------------
import base64
JUDGE_MODEL = "gpt-5.5"   # frontier judge; ~$0.025/output
JUDGE_SCHEMA = {"type": "object", "additionalProperties": False,
                "required": ["garment", "identity", "scene", "clean", "hands", "realism", "note"],
                "properties": {**{k: {"type": "integer", "minimum": 1, "maximum": 5}
                                  for k in ["garment", "identity", "scene", "clean", "hands", "realism"]},
                               "note": {"type": "string", "maxLength": 300}}}
JUDGE_PROMPT = (
    "You are judging a virtual try-on output. Image 1: the original person. "
    "Image 2: the reference garment. Image 3: the generated result. Score 1-5 "
    "(5 flawless): garment = is the output garment exactly the reference "
    "(color, print, cut); identity = same face/hair/body as image 1; scene = "
    "pose and background unchanged; clean = free of AI artifacts in skin, seams "
    "and textures; hands = hands specifically are anatomically correct (right "
    "finger count, natural poses) — score 5 if no hands are visible; realism = "
    "the image reads as a real photograph rather than an AI render (natural "
    "skin, lighting, fabric physics; no plastic or over-smoothed look). "
    "Return ONLY JSON matching the schema.")
def _b64(img):
    im = Image.open(img) if isinstance(img, str) else img
    im = im.copy(); im.thumbnail((768, 768))
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
def _call_judge(model, images, prompt):
    from openai import OpenAI
    resp = OpenAI().responses.create(
        model=model,
        input=[{"role": "user",
                "content": [{"type": "input_text", "text": prompt}] +
                           [{"type": "input_image", "image_url": _b64(im)}
                            for im in images]}])
    return resp.output_text
def vlm_judge(person_p, garment_p, result_img, model=None, attempts=3):
    from jsonschema import validate, ValidationError
    model = model or JUDGE_MODEL
    prompt = JUDGE_PROMPT
    for _ in range(attempts):
        raw = _call_judge(model, [person_p, garment_p, result_img], prompt)
        try:
            start, end = raw.find("{"), raw.rfind("}") + 1
            verdict = json.loads(raw[start:end]); validate(verdict, JUDGE_SCHEMA)
            return verdict
        except (ValueError, ValidationError) as e:
            prompt = (f"{JUDGE_PROMPT}\n\nYour previous reply failed validation "
                      f"({e}). Previous reply:\n{raw}\nReturn corrected JSON only.")
    return None
print(f"VLM judge ready: {JUDGE_MODEL}")

# %%
#  §9b · VLM judging run (paid) — executes only when RUN_VLM_JUDGE=True ------
if RUN_VLM_JUDGE:
    assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY missing (.env or Colab Secrets)"
    keys = sorted(RESULTS)
    def _judge_one(k):
        pair = PAIRS_BY_STAGE[k[0]][k[2]]
        v = vlm_judge(img_path("people", pair.person_id),
                      img_path("garments", pair.garment_id), RESULTS[k])
        return {"stage": k[0], "arm": k[1], "pair_idx": k[2],
                "pair": f"{pair.person_id}x{pair.garment_id}",
                **(v or {c: None for c in ("garment", "identity", "scene",
                                           "clean", "hands", "realism", "note")})}
    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(_judge_one, keys))
    print(f"judged {len(rows)} outputs (8-way parallel)")
    pd.DataFrame(rows).to_csv(os.path.join(OUT_ROOT, "vlm_judgments.csv"), index=False)
    unscored = sum(1 for r in rows if r["garment"] is None)
    print(f"VLM judging done -> vlm_judgments.csv ({unscored} unscored)")
else:
    print("VLM judging skipped (RUN_VLM_JUDGE=False)")

# %%
#  §9c · Deterministic judging run (free) — RUN_CV_JUDGE gate ----------------
if RUN_CV_JUDGE:
    stages = [s for s in ("triage", "grid", "holdout") if any(k[0] == s for k in RESULTS)]
    if not stages:
        print("no outputs to score yet — run a paid stage first")
    else:
        CV = pd.concat([cv_scores(s) for s in stages], ignore_index=True)
        CV.to_csv(os.path.join(OUT_ROOT, "cv_metrics.csv"), index=False)
        print(f"deterministic metrics saved -> cv_metrics.csv "
              f"({len(CV)} outputs, stages: {stages})")
else:
    print("deterministic judging skipped (RUN_CV_JUDGE=False)")

# %%
#  §10 · Leaderboards per stage + judge agreement (free) ---------------------
# The deterministic composite is the authoritative ranking. The VLM board is
# confirmation only: it carries no weight, but any arm whose VLM rank differs
# from its deterministic rank is flagged with the delta for human review.
CRIT = ["garment", "identity", "scene", "clean", "hands", "realism"]
def _per_stage(path):
    # Fresh Colab sessions have no local outputs; fall back to the committed
    # v2/artifacts copies so "Run all" still shows the boards without
    # re-running any paid stage. (V2 artifacts only — never v1/artifacts.)
    if not os.path.exists(path):
        alt = os.path.join(ARTIFACT_DIR, os.path.basename(path))
        if os.path.exists(alt):
            path = alt
    if not os.path.exists(path): return {}
    df = pd.read_csv(path)
    if "stage" not in df.columns: df["stage"] = "triage"
    return {s: g for s, g in df.groupby("stage")}
boards_cv, boards_vlm, boards_h = {}, {}, {}
for s, g in _per_stage(os.path.join(OUT_ROOT, "cv_metrics.csv")).items():
    boards_cv[s] = cv_matrix(g)
    print(f"[deterministic — {s}] authoritative ranking; score = weighted "
          "anchored composite (garment x2), higher is better")
    print(boards_cv[s].to_string(), "\n")
def _rubric_board(g):
    g = g.dropna(subset=CRIT)
    if not len(g): return None
    g = g.assign(overall=g[CRIT].mean(axis=1))
    return (g.groupby("arm")[CRIT + ["overall"]]
              .mean().round(2).sort_values("overall", ascending=False))
for s, g in _per_stage(os.path.join(OUT_ROOT, "vlm_judgments.csv")).items():
    b = _rubric_board(g)
    if b is not None: boards_vlm[s] = b
for s, g in _per_stage(os.path.join(OUT_ROOT, "judgments.csv")).items():
    b = _rubric_board(g)
    if b is not None:
        boards_h[s] = b
        print(f"[human insurance — {s}]"); print(b.to_string(), "\n")
for s in boards_cv:
    if s not in boards_vlm: continue
    det_rank = {a: i + 1 for i, a in enumerate(boards_cv[s].index)}
    vlm_rank = {a: i + 1 for i, a in enumerate(boards_vlm[s].index)}
    agree = pd.DataFrame([{"arm": a, "det_rank": det_rank[a],
                           "vlm_rank": vlm_rank.get(a),
                           "delta": vlm_rank.get(a, det_rank[a]) - det_rank[a]}
                          for a in det_rank]).set_index("arm")
    agree["flag"] = agree.delta.abs().map(lambda d: "DISAGREE" if d >= 2 else "")
    print(f"[judge agreement — {s}] deterministic is truth; VLM is "
          "confirmation only. delta = vlm_rank - det_rank; |delta| >= 2 flagged")
    print(agree.to_string(), "\n")
    flagged = list(agree[agree.flag == "DISAGREE"].index)
    if flagged:
        print(f"  -> review flagged arms by eye (grid PNG or judge_view): {flagged}\n")
# specialization: best arm per criterion — the data-derived case for (or
# against) a composite pipeline
for s in boards_vlm:
    spec = {c: boards_vlm[s][c].idxmax() for c in CRIT if c in boards_vlm[s]}
    print(f"[specialization — {s} (VLM)] best arm per criterion: {spec}")
for s in boards_cv:
    m = boards_cv[s]
    spec = {"garment_sim": m.garment_sim.idxmax(), "identity_cos": m.identity_cos.idxmax(),
            "pose_err": m.pose_err.idxmin(), "bg_psnr": m.bg_psnr.idxmax()}
    print(f"[specialization — {s} (deterministic)] best arm per metric: {spec}")
# complementarity matrix: two composite axes per arm. Arms strong on one axis
# and weak on the other justify a composite (transfer specialist -> refiner).
for s in boards_vlm:
    b = boards_vlm[s]
    axes = pd.DataFrame({
        "editing": b[[c for c in ("garment", "identity", "scene") if c in b]].mean(axis=1),
        "realism": b[[c for c in ("clean", "hands", "realism") if c in b]].mean(axis=1)})
    axes["edit_rank"] = axes.editing.rank(ascending=False).astype(int)
    axes["realism_rank"] = axes.realism.rank(ascending=False).astype(int)
    axes = axes.round(2).sort_values("editing", ascending=False)
    print(f"[complementarity — {s}] editing axis vs realism axis")
    print(axes.to_string())
    best_e, best_r = axes.editing.idxmax(), axes.realism.idxmax()
    if best_e != best_r:
        print(f"  -> composite candidate: {best_e} (edit) -> {best_r} (refine)\n")
    else:
        print(f"  -> {best_e} leads both axes; no composite needed\n")

# %%
#  §11 · Verdict card + spend (free) ----------------------------------------
ok = [r for r in RUNS if r.get("ok")]; err = [r for r in RUNS if not r.get("ok")]
print("=" * 46, f"\nruns ok {len(ok)} | failed {len(err)} | "
      f"est spend ${spent():.2f} / ${BUDGET_USD:.2f}")
if err: print("failures:", *[f"  {e['arm']}: {e.get('err', '')[:80]}" for e in err], sep="\n")
stage_used = next((s for s in ("holdout", "grid", "triage") if s in boards_cv), None)
final = boards_cv.get(stage_used) if stage_used else None
if final is not None and len(final):
    w = final.index[0]
    print(f"leader (deterministic, {stage_used} stage): {w} "
          f"(score {final.loc[w, 'score']}) — "
          f"{'BEATS' if w != BASELINE else 'baseline still leads'} vs {BASELINE}")
    if SURVIVORS:
        n_entered = sum(ARMS_ENABLED.values())   # arm count is derived, never hardcoded
        print(f"elimination: {n_entered} arms -> triage -> {SURVIVORS} -> grid")
print("=" * 46)

# %% [markdown]
# ---
# # §12 · Final implementation + the Key
# Two candidate serving paths, both open-weights:
# - **`try_on_single`** — the top non-composite arm on the deterministic
#   holdout board (grid board fallback until the benchmark runs).
# - **`try_on_composite`** — the `composite_v2ow` pipeline from
#   `v2/build/composite_cells.py` (§6e).
#
# **THE_KEY** is the frozen serving configuration. Its default implementation
# is selected from the data: composite if it beat the single winner on the
# same board, single otherwise — so the attempt is honored either way and the
# code stays correct regardless of outcome. `KEY_OVERRIDE` stays empty unless
# a documented human review overrides the data-driven pick. Call
# `run_final(person_path, garment_path)` for the one-click path (in Colab with
# no arguments, it prompts for uploads).

# %%
#  §12 · Final implementation + the Key (free to load; each call is paid) ----
# Selection is rank-driven, no hand-picked models:
#   1. SINGLE_MODEL = top non-composite arm on the deterministic holdout board
#      (unseen pairs); grid board fallback before the benchmark runs.
#   2. The composite comes from §6e; THE_KEY ships it only if its measured
#      score beats the single winner on the same board.
_board = next((boards_cv[s] for s in ("holdout", "grid") if s in boards_cv), None)
SINGLE_MODEL = BASELINE
if _board is not None and len(_board):
    SINGLE_MODEL = next((a for a in _board.index if a != COMPOSITE_ARM), BASELINE)
def _fal_image(endpoint, args):
    res = fal_client.subscribe(endpoint, arguments=args)
    url = (res.get("images") or [res.get("image", {})])[0].get("url")
    return Image.open(io.BytesIO(requests.get(url).content)).convert("RGB")
def try_on_single(person_path, garment_path, arm=None):
    """Winner arm via the harness registry: person + garment -> result."""
    cfg = ARM_REGISTRY[arm or SINGLE_MODEL]
    rz = cfg.get("resize", {})
    args = cfg["args"](upload(person_path, rz.get("person_mp")),
                       upload(garment_path, rz.get("garment_mp")), SEED_BASE)
    return _fal_image(cfg["endpoint"], args)
def try_on_composite(person_path, garment_path):
    """COMPOSITE-V2 integration point: prefers composite_try_on() from
    composite_cells.py (multi-call pipelines); falls back to the registry
    entry when the composite registered as a plain arm."""
    fn = globals().get("composite_try_on")
    if fn is not None:
        return fn(person_path, garment_path, SEED_BASE)[0]
    assert COMPOSITE_ARM in ARM_REGISTRY, (
        "composite arm not integrated — merge v2/build/composite_cells.py (§6e)")
    return try_on_single(person_path, garment_path, arm=COMPOSITE_ARM)
# Composite validation = "did it beat the single winner?", judged on the
# held-out board when the composite ran there, else the grid board.
_comp_validated = bool(_board is not None and COMPOSITE_ARM in _board.index
                       and SINGLE_MODEL in _board.index
                       and _board.loc[COMPOSITE_ARM, "score"]
                           >= _board.loc[SINGLE_MODEL, "score"])
# Empty = the data-driven selection above stands. Populate only after a
# documented human review (keys: "single_model", "implementation").
KEY_OVERRIDE = {}
SINGLE_MODEL = KEY_OVERRIDE.get("single_model", SINGLE_MODEL)
THE_KEY = {
    "implementation": KEY_OVERRIDE.get(
        "implementation", "composite" if _comp_validated else "single"),
    "single": {"model": SINGLE_MODEL,
               "endpoint": ARM_REGISTRY.get(SINGLE_MODEL, {}).get("endpoint"),
               "prompt": PROMPT_TEMPLATE,
               "selected_by": ("human review (see KEY_OVERRIDE)"
                               if "single_model" in KEY_OVERRIDE
                               else "deterministic board (holdout preferred)")},
    "composite": {"arm": COMPOSITE_ARM,
                  "source": "v2/build/composite_cells.py",
                  "validated_vs_single": _comp_validated},
    "seed_policy": ("SEED_BASE fixed; stage offsets triage +0 / grid +100 / "
                    "reserve +200 / holdout +300"),
    "weights": "all arms open checkpoints; fal-hosted for iteration only",
    "frozen": None,   # set a date when the serving config is locked
}
def run_final(person_path=None, garment_path=None, use=None):
    """One-click try-on with THE_KEY. In Colab, call with no args to upload."""
    if person_path is None or garment_path is None:
        assert IN_COLAB, "pass person_path and garment_path when running locally"
        from google.colab import files
        print("upload the PERSON image:"); person_path = list(files.upload())[0]
        print("upload the GARMENT image:"); garment_path = list(files.upload())[0]
    impl = use or THE_KEY["implementation"]
    img = (try_on_composite if impl == "composite" else try_on_single)(person_path, garment_path)
    out = os.path.join(OUT_ROOT, "final_result.png"); img.save(out)
    plt.figure(figsize=(4.2, 5)); plt.imshow(img); plt.axis("off"); plt.show()
    print(f"[{impl}] result saved -> {out}")
    return img
print(json.dumps(THE_KEY, indent=2))
# run_final(img_path("people", "p001"), img_path("garments", "g015"))  # paid example

# %% [markdown]
# ## §12a · Run it — single model
# The single-model deliverable: the board-selected winner (`SINGLE_MODEL`,
# printed by §12). One paid call per run. Uncomment the example or call
# `run_single()` with your own images (in Colab, call with no arguments to
# upload).

# %%
#  §12a · One-click — single model -------------------------------------------
# Examples use the img_path() helper, which resolves correctly both locally
# and on Colab (the working directory is not the repo on Colab).
def run_single(person_path=None, garment_path=None):
    return run_final(person_path, garment_path, use="single")
# run_single(img_path("people", "p001"), img_path("garments", "g015"))  # paid

# %% [markdown]
# ## §12b · Run it — composite (`composite_v2ow`)
# The composite deliverable from `v2/build/composite_cells.py` (§6e). Requires
# the composite integration to be merged; cost per run is declared by its
# cells. In Colab, call with no arguments to upload.

# %%
#  §12b · One-click — composite ----------------------------------------------
def run_composite(person_path=None, garment_path=None):
    return run_final(person_path, garment_path, use="composite")
# run_composite(img_path("people", "p001"), img_path("garments", "g015"))  # paid

# %%
#  §12c · Baseline comparison module (paid per call) --------------------------
# Runs the same inputs through the three deliverable configurations and
# renders them side by side: baseline (qwen_2511), the best single arm, and
# the composite (composite_v2ow).
def compare_vs_baseline(person_path, garment_path, show=True):
    outs = {f"baseline_{BASELINE}": try_on_single(person_path, garment_path, arm=BASELINE),
            f"single_{SINGLE_MODEL}": try_on_single(person_path, garment_path),
            COMPOSITE_ARM: try_on_composite(person_path, garment_path)}
    if show:
        panels = [("person", Image.open(person_path)),
                  ("garment", Image.open(garment_path))] + list(outs.items())
        fig, ax = plt.subplots(1, len(panels), figsize=(4.6 * len(panels), 7), dpi=110)
        for a, (ttl, im) in zip(ax, panels):
            a.imshow(im); a.set_title(ttl, fontsize=10); a.axis("off")
        plt.tight_layout(); plt.show()
    return outs
print("comparison module ready: compare_vs_baseline(person_path, garment_path)")
# compare_vs_baseline(img_path("people", "p001"), img_path("garments", "g015"))  # paid example

# %% [markdown]
# ---
# ## §13 · Self-hosted open weights (Colab)
# Everything above serves open checkpoints through fal, which the parity rule in
# `execution_conventions.md` treats as directional. This section is the other
# path: weights downloaded from Hugging Face onto the Colab VM, cached in Drive,
# and run on the GPU. Nothing is downloaded to the developer machine.
#
# Three storage locations, and the distinction matters:
#
# | Location | Speed | Survives the session |
# |---|---|---|
# | Hugging Face Hub | ~100-300 MB/s to the VM | source of truth |
# | Drive `tryon_models/` | slow to read, ~50-100 MB/s | **yes** — why `HF_HOME` points here |
# | VM disk `/content` | NVMe | no |
#
# Colab's default cache is the VM disk, which re-downloads every checkpoint every
# session. Setting `HF_HOME` to the Drive folder is what makes the download
# one-time.
#
# ### Two phases, deliberately split to keep paid GPU time short
# **Phase 1 (§13a-c) needs no GPU at all.** Run it on a CPU-only runtime, which
# is free and unmetered: ~23GB of weights, the VideoX-Fun clone and every pip
# wheel all land in Drive. Nothing here touches CUDA.
#
# **Phase 2 (§13e-f) is the only metered part** — switch the runtime to A100,
# install from the Drive wheel cache (offline, no network), load, generate. At
# ~5.4 compute units/hour for an A100-40GB and \$9.99 per 100 units, that is
# roughly \$0.55/hour, so the target is a ~25 minute session ≈ \$0.25.
#
# Switching runtime type restarts the VM and wipes `/content` — which is exactly
# why Phase 1 writes everything to Drive and Phase 2 re-links rather than
# re-downloads. Run §13d before switching; it refuses to pass unless every
# artifact Phase 2 needs is already on Drive.
#
# First target: **Z-Image Base + Fun tile-ControlNet** as an auxiliary realism
# pass. Highest-priority queued test, and it has no hosted equivalent — fal
# serves Z-Image Base as text-to-image only.

# %%
#  §13a · PHASE 1 (free, CPU runtime) · Drive mount + paths -------------------
#  Must run before any diffusers/transformers import: HF_HOME is read at import.
import os, subprocess, sys

MODELS_DIR = WHEELS = VFX = None
if IN_COLAB:
    from google.colab import drive
    drive.mount("/content/drive")
    _base = os.path.join("/content/drive/MyDrive", DRIVE_PROJECT_DIR)
    if not os.path.isdir(_base):
        raise SystemExit(f"{_base} not found — check DRIVE_PROJECT_DIR in §1")
    MODELS_DIR = os.path.join(_base, "tryon_models")      # created 2026-08-14
    WHEELS = os.path.join(MODELS_DIR, "wheels")           # pip cache, survives restarts
    VFX = os.path.join(MODELS_DIR, "VideoX-Fun")          # repo lives on Drive, not /content
    for d in (MODELS_DIR, WHEELS):
        os.makedirs(d, exist_ok=True)
    os.environ["HF_HOME"] = os.path.join(MODELS_DIR, "hf_cache")
    os.makedirs(os.environ["HF_HOME"], exist_ok=True)
    print("HF_HOME:", os.environ["HF_HOME"])
    print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                          "--format=csv,noheader"], capture_output=True,
                         text=True).stdout.strip() or "no GPU (correct for phase 1)")
else:
    print("§13 is Colab-only; skipping.")

# %%
#  §13b · PHASE 1 · Download the open weights into the Drive cache ------------
#  ~23GB on the first run, minutes over the VM's network. Later runs: cache hit,
#  no network. Resumable — re-run the cell if the session drops mid-download.
ZIMAGE_REPO = "Tongyi-MAI/Z-Image"                        # Base, ~20.5GB, Apache 2.0
CN_REPO     = "alibaba-pai/Z-Image-Fun-Controlnet-Union-2.1"
CN_FILE     = "Z-Image-Fun-Controlnet-Tile-2.1-lite.safetensors"   # 2.02GB; full is 6.71GB
ZIMAGE_PATH = CN_PATH = None

if IN_COLAB:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "huggingface_hub"], check=True)
    from huggingface_hub import snapshot_download, hf_hub_download
    ZIMAGE_PATH = snapshot_download(ZIMAGE_REPO)          # diffusers layout
    CN_PATH = hf_hub_download(CN_REPO, CN_FILE)
    print("base:", ZIMAGE_PATH)
    print("tile controlnet:", CN_PATH)

#  LoRA slot. "Lenovo UltraReal" is Civitai-hosted (model 1662740) and needs a
#  Civitai token, so it is not wired here; set LORA_PATH after uploading the
#  .safetensors, or leave None to measure the tile ControlNet on its own first.
#  Any LoRA must target Z-Image *Base* — Turbo realism LoRAs are a different base.
LORA_PATH, LORA_WEIGHT = None, 0.55

# %%
#  §13c · PHASE 1 · VideoX-Fun repo + wheel cache on Drive --------------------
#  The Fun ControlNets are NOT a diffusers pipeline: alibaba-pai ships them for
#  aigc-apps/VideoX-Fun, which expects a fixed models/ layout. Both the clone and
#  its wheels go to Drive so the A100 session installs offline instead of
#  re-resolving dependencies over the network.
if IN_COLAB:
    if not os.path.isdir(VFX):
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/aigc-apps/VideoX-Fun.git", VFX], check=True)
    req = os.path.join(VFX, "requirements.txt")
    if not os.listdir(WHEELS):
        subprocess.run([sys.executable, "-m", "pip", "download", "-q",
                        "-r", req, "-d", WHEELS], check=True)
    dt = os.path.join(VFX, "models", "Diffusion_Transformer")
    pm = os.path.join(VFX, "models", "Personalized_Model")
    os.makedirs(dt, exist_ok=True); os.makedirs(pm, exist_ok=True)
    for src, dst in ((ZIMAGE_PATH, os.path.join(dt, "Z-Image")),
                     (CN_PATH, os.path.join(pm, os.path.basename(CN_PATH)))):
        if not os.path.exists(dst):
            os.symlink(src, dst)          # symlink: the base is 20GB, never copy it
    print("repo:", VFX)
    print("wired:", os.listdir(dt), os.listdir(pm))
    print("wheels cached:", len(os.listdir(WHEELS)))

# %%
#  §13d · PHASE 1 · Preflight — do not start the A100 until this passes -------
#  Everything metered time depends on must already exist on Drive. A failure here
#  costs nothing; the same failure after switching runtimes costs GPU minutes.
def preflight_13():
    checks = {
        "Z-Image base snapshot": ZIMAGE_PATH and os.path.isdir(ZIMAGE_PATH),
        "tile controlnet file": CN_PATH and os.path.isfile(CN_PATH),
        "VideoX-Fun clone": VFX and os.path.isdir(os.path.join(VFX, "examples")),
        "example script": VFX and os.path.isfile(os.path.join(
            VFX, "examples", "z_image_fun", "predict_t2i_control_2.1.py")),
        "model symlinks": VFX and os.path.exists(os.path.join(
            VFX, "models", "Diffusion_Transformer", "Z-Image")),
        "wheel cache": WHEELS and bool(os.listdir(WHEELS)),
        # v2/runs/ is gitignored: the BEFORE images are uploaded to Drive, not cloned
        "klein BEFORE set (Drive)": all(os.path.exists(os.path.join(
            "/content/drive/MyDrive", DRIVE_PROJECT_DIR, "tryon_v2_runs",
            "before_klein", f"klein_4b_edit__{p}.png"))
            for p in ["ts2_01", "ts2_05", "ts2_07", "ts2_12", "ts2_13"]),
    }
    for k, ok in checks.items():
        print(f"  {'ok  ' if ok else 'MISS'} {k}")
    done = all(checks.values())
    print("\nphase 1 complete — switch Runtime > Change runtime type > A100, then run §13e"
          if done else "\nphase 1 incomplete — re-run the cells above before paying for a GPU")
    return done

if IN_COLAB:
    preflight_13()

# %%
#  §13e · PHASE 2 (metered, A100) · offline install + GPU check ---------------
#  Re-run §13a first (the runtime restart cleared the mount and the variables).
#  Installing from the Drive wheel cache avoids dependency resolution over the
#  network — the difference between ~1 and ~4 minutes of paid time.
import time
_T0 = time.time()

if IN_COLAB:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-index",
                    "--find-links", WHEELS, "-r",
                    os.path.join(VFX, "requirements.txt")], check=True)
    print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                          "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip())
    print(f"install took {time.time() - _T0:.0f}s")

# %%
#  §13f · PHASE 2 · Tile-ControlNet realism pass over the klein BEFORE set ----
#  BEFORE set = the klein batch from v2/build/aux_batch.py, i.e. the five
#  klein_4b_edit outputs. klein is the editing base (V2.1), so these are the
#  images the aux stage actually sees in the deployed pipeline.
#  Output follows the aux_batch contract — {batch}__{config}__{pair}.png plus its
#  sidecar — so `aux_batch.py --score --judge --html` picks the arm up unchanged.
#
#  Implementation note: we drive VideoX-Fun's own example script rather than
#  reimplementing its loader, patching only the config constants at its head.
#  Those constants are the documented interface; the internals are not.
AUX_CONFIG = "zbase_tile_lite"          # + "_ultrareal" once a Base LoRA is wired
AUX_BATCH = "klein"                     # matches aux_batch.py's batch key
CONTROL_SCALE = 0.90                    # README: useful range 0.65-1.00
STEPS, GUIDANCE, SEED_13 = 25, 4.0, 46
PAIRS_13 = ["ts2_01", "ts2_05", "ts2_07", "ts2_12", "ts2_13"]   # aux_batch.PAIRS
OUT_DIR = None

def before_set_13():
    """The klein outputs the aux stage will actually see.

    v2/runs/ is gitignored, so these are NOT in the clone — they live in Drive at
    tryon_v2_runs/before_klein/ (upload the five PNGs once). The repo path is
    kept as a fallback for local runs.
    """
    drive_d = os.path.join("/content/drive/MyDrive", DRIVE_PROJECT_DIR,
                           "tryon_v2_runs", "before_klein") if IN_COLAB else None
    repo_d = os.path.join(REPO_DIR, "v2", "runs", "ts2", "outputs")
    for d in [x for x in (drive_d, repo_d) if x]:
        paths = [os.path.join(d, f"klein_4b_edit__{p}.png") for p in PAIRS_13]
        if all(os.path.exists(p) for p in paths):
            return paths
    raise SystemExit(f"klein BEFORE set not found — upload the five "
                     f"klein_4b_edit__*.png to {drive_d or repo_d}")

def run_tile_refine(before_paths, config=AUX_CONFIG, scale=CONTROL_SCALE):
    """Tile-ControlNet pass over each BEFORE image; returns written PNG paths."""
    import re, shutil, glob as _glob, json as _json
    from PIL import Image
    src = os.path.join(VFX, "examples", "z_image_fun", "predict_t2i_control_2.1.py")
    drv = os.path.join("/content", "run_tile_refine.py")   # VM disk: Drive is slow to exec
    written = []
    for p in before_paths:
        t0 = time.time()
        pair = os.path.basename(p).replace("klein_4b_edit__", "").replace(".png", "")
        w, h = Image.open(p).size
        code = open(src).read()
        for k, v in {
            "model_name": '"models/Diffusion_Transformer/Z-Image"',
            "transformer_path": f'"models/Personalized_Model/{os.path.basename(CN_PATH)}"',
            "lora_path": f'"{LORA_PATH}"' if LORA_PATH else "None",
            "lora_weight": str(LORA_WEIGHT),
            "control_image": f'"{p}"',
            "sample_size": f"[{h}, {w}]",          # script order is [height, width]
            "num_inference_steps": str(STEPS),
            "guidance_scale": str(GUIDANCE),
            "control_context_scale": str(scale),
            "seed": str(SEED_13),
            "prompt": repr(REFINE_PROMPT),
            "save_path": f'"/content/out/{config}__{pair}"',
        }.items():
            code, n = re.subn(rf"^{k}\s*=.*$", f"{k} = {v}", code, count=1, flags=re.M)
            if not n:
                print(f"  warn: constant {k} not found in the example script")
        open(drv, "w").write(code)
        r = subprocess.run([sys.executable, drv], cwd=VFX, capture_output=True, text=True)
        got = sorted(_glob.glob(f"/content/out/{config}__{pair}/*.png"))
        if not got:
            print(f"  FAIL {pair}: {r.stderr.strip()[-400:]}"); continue
        os.makedirs(OUT_DIR, exist_ok=True)
        dst = os.path.join(OUT_DIR, f"{AUX_BATCH}__{config}__{pair}.png")
        shutil.copy(got[0], dst)
        _json.dump({"batch": AUX_BATCH, "config": config, "pair": pair,
                    "before": f"v2/runs/ts2/outputs/klein_4b_edit__{pair}.png",
                    "size": Image.open(dst).size, "seed": SEED_13,
                    "self_hosted": True, "base": ZIMAGE_REPO,
                    "controlnet": f"{CN_REPO}/{CN_FILE}", "lora": LORA_PATH,
                    "control_context_scale": scale, "steps": STEPS,
                    "guidance_scale": GUIDANCE, "seconds": round(time.time() - t0, 1)},
                   open(dst.replace(".png", ".json"), "w"), indent=2)
        written.append(dst)
        print(f"  ok {config} {pair} {Image.open(dst).size} in {time.time() - t0:.0f}s")
    return written

if IN_COLAB:
    OUT_DIR = os.path.join("/content/drive/MyDrive", DRIVE_PROJECT_DIR,
                           "tryon_v2_runs", "aux_selfhost")
    print("ready: run_tile_refine(before_set_13())")
    print("outputs ->", OUT_DIR)
    print("then: copy into v2/runs/aux_batches/ and run "
          "`python v2/build/aux_batch.py --score --judge --html` locally")
    print("stop the A100 runtime as soon as the outputs are on Drive")

# %% [markdown]
# ---
# ## §14 · v2.1.1 · klein parity on downloaded weights (free T4)
# The V2.1 decision picked klein 4B on **fal** numbers. The parity rule says a
# claim only counts once it is reproduced on downloaded weights, and we now have
# two Apache klein checkpoints that tied on fidelity through fal:
#
# | arm | source | what it trades |
# |---|---|---|
# | `klein_4b_edit_sh` | `black-forest-labs/FLUX.2-klein-4B` (distilled) | better garment transfer |
# | `klein_4b_base_edit_sh` | `black-forest-labs/FLUX.2-klein-base-4B` (undistilled) | better identity + background; true CFG |
#
# This section runs both, self-hosted, on the same 13 Testset2 pairs with the
# same seed and the **same prompt function imported from `ts2_harness.py`** — a
# re-implementation here would not be a parity test.
#
# **No A100 needed.** BFL states ~13GB VRAM for both; a free T4 is 16GB. Two
# Turing caveats: no bf16 (we run fp16) and no fp8/NVFP4, so the `-fp8` and
# `-nvfp4` repo variants are not usable here. If fp16 produces black frames or
# OOMs, fall back to a GGUF Q8 build and label the run as quantized — quantized
# output is evidence the weights run, but final parity numbers should come from
# the unquantized checkpoint.
#
# Phase split as in §13: **download on a CPU runtime (free, unmetered), run on
# the T4.** The `_sh` suffix keeps these arms separate from their fal rows so the
# two can be compared side by side in the same tables.

# %%
#  §14a · PHASE 1 (CPU runtime) · paths + the pair matrix -------------------
#  Test images: Testset2/ is untracked, so v2/runs/ts2/inputs/ (18 prepped JPEGs,
#  4.4MB) is uploaded to Drive once, at tryon_v2_runs/ts2_inputs/.
KLEIN_REPOS = {"klein_4b_edit_sh":      "black-forest-labs/FLUX.2-klein-4B",
               "klein_4b_base_edit_sh": "black-forest-labs/FLUX.2-klein-base-4B"}
TS2_INPUTS = KLEIN_OUT = None
MATRIX_13 = prompt_for_13 = None

if IN_COLAB:
    import sys as _sys
    _sys.path.insert(0, os.path.join(REPO_DIR, "v2", "build"))
    from ts2_harness import matrix_df, prompt_for, SEED as TS2_SEED   # parity: same prompts
    MATRIX_13, prompt_for_13 = matrix_df(), prompt_for
    _runs = os.path.join("/content/drive/MyDrive", DRIVE_PROJECT_DIR, "tryon_v2_runs")
    TS2_INPUTS = os.path.join(_runs, "ts2_inputs")
    KLEIN_OUT = os.path.join(_runs, "klein_parity")
    os.makedirs(KLEIN_OUT, exist_ok=True)
    print(f"{len(MATRIX_13)} pairs · seed {TS2_SEED} · inputs {TS2_INPUTS}")

def input_path_13(rel):
    """ts2_harness.local() rewritten against the Drive copy of the prepped inputs."""
    return os.path.join(TS2_INPUTS, os.path.splitext(os.path.basename(rel))[0] + ".jpg")

# %%
#  §14b · PHASE 1 · Download both klein checkpoints ---------------------------
#  ~13GB each into the same Drive HF cache as §13. Run §13a first for HF_HOME.
KLEIN_PATHS = {}
if IN_COLAB:
    from huggingface_hub import snapshot_download
    for arm, repo in KLEIN_REPOS.items():
        KLEIN_PATHS[arm] = snapshot_download(repo)
        print(f"{arm}: {KLEIN_PATHS[arm]}")

# %%
#  §14c · PHASE 1 · Preflight — everything the GPU session needs --------------
def preflight_14():
    checks = {"HF_HOME on Drive": os.environ.get("HF_HOME", "").startswith("/content/drive"),
              "distilled snapshot": os.path.isdir(KLEIN_PATHS.get("klein_4b_edit_sh", "")),
              "base snapshot": os.path.isdir(KLEIN_PATHS.get("klein_4b_base_edit_sh", "")),
              "output dir": bool(KLEIN_OUT) and os.path.isdir(KLEIN_OUT)}
    if MATRIX_13 is not None:
        need = sorted(set(MATRIX_13.person) | set(MATRIX_13.garment))
        checks["ts2 inputs on Drive"] = all(os.path.exists(input_path_13(r)) for r in need)
    for k, ok in checks.items():
        print(f"  {'ok  ' if ok else 'MISS'} {k}")
    done = all(checks.values())
    print("\nphase 1 complete — switch Runtime > Change runtime type > T4 GPU, then run §14d"
          if done else "\nphase 1 incomplete — upload the prepped inputs / re-run §14b")
    return done

if IN_COLAB:
    preflight_14()

# %%
#  §14d · PHASE 2 (T4) · run one klein variant over the 13 pairs --------------
#  Re-run §1, §2, §13a and §14a first — the runtime switch cleared the mount.
#  fp16 (Turing has no bf16) + sequential CPU offload keeps peak VRAM under 16GB
#  at the cost of speed; expect minutes per image, which is fine for 13 images.
def run_klein_selfhosted(arm, steps=None, guidance=None, dry_run=False):
    """Self-hosted klein pass over Testset2. Writes {arm}__{id}.png + sidecar."""
    import torch, json as _json, time as _time
    from diffusers import Flux2KleinPipeline
    from PIL import Image
    base = arm.endswith("base_edit_sh")
    steps = steps if steps is not None else (28 if base else 4)
    guidance = guidance if guidance is not None else (5.0 if base else 0.0)
    neg = ("different person, changed face, changed background, extra limbs, "
           "deformed hands") if base else None          # distilled has no true CFG

    pipe = Flux2KleinPipeline.from_pretrained(
        KLEIN_REPOS[arm], torch_dtype=torch.float16, low_cpu_mem_usage=True)
    pipe.enable_sequential_cpu_offload()                 # 16GB card, 13GB weights
    print(f"{arm} loaded · steps={steps} guidance={guidance} negative={bool(neg)}")

    written = []
    for r in MATRIX_13.itertuples():
        dst = os.path.join(KLEIN_OUT, f"{arm}__{r.id}.png")
        if os.path.exists(dst):
            continue
        p, g = input_path_13(r.person), input_path_13(r.garment)
        person = Image.open(p).convert("RGB")
        refs = [person, Image.open(g).convert("RGB")]
        prompt = prompt_for_13(r, r.duo)                 # identical to the fal run
        if dry_run:
            print(f"  would run {r.id} ({r.kind}) {person.size}"); continue
        t0 = _time.time()
        kw = {"prompt": prompt, "image": refs,
              "generator": torch.Generator("cpu").manual_seed(TS2_SEED),
              "num_inference_steps": steps, "guidance_scale": guidance}
        if neg:
            kw["negative_prompt"] = neg
        try:
            out = pipe(**kw).images[0]
        except Exception as e:
            print(f"  FAIL {r.id}: {str(e)[:200]}"); continue
        out.save(dst)
        _json.dump({"arm": arm, "id": r.id, "kind": r.kind, "category": r.category,
                    "target": r.target, "duo": bool(r.duo), "seed": TS2_SEED,
                    "endpoint": None, "self_hosted": True, "repo": KLEIN_REPOS[arm],
                    "dtype": "float16", "steps": steps, "guidance_scale": guidance,
                    "negative_prompt": neg, "size": out.size,
                    "person": r.person, "garment": r.garment,
                    "seconds": round(_time.time() - t0, 1)},
                   open(dst.replace(".png", ".json"), "w"), indent=2)
        written.append(dst)
        print(f"  ok {arm} {r.id} ({r.kind}) {out.size} in {_time.time() - t0:.0f}s")
    del pipe
    torch.cuda.empty_cache()                             # free VRAM before the next variant
    return written

if IN_COLAB:
    print("ready:")
    print("  run_klein_selfhosted('klein_4b_edit_sh')        # distilled, 4 steps")
    print("  run_klein_selfhosted('klein_4b_base_edit_sh')   # base, 28 steps + negative")
    print("outputs ->", KLEIN_OUT)
    print("then: copy into v2/runs/ts2/outputs/ and run "
          "`python v2/build/ts2_harness.py --score --judge --html` locally")

# %%
#  §14e · PHASE 2 (T4) · eyeball the two variants side by side ----------------
#  Renders person | garment | distilled | base per pair, so the call can be made
#  in the Colab UI without downloading anything. Thumbnails only: full-res inline
#  output stalls the notebook connection.
def show_klein_parity(pairs=None, thumb=340):
    from PIL import Image
    import matplotlib.pyplot as plt
    rows = [r for r in MATRIX_13.itertuples()
            if pairs is None or r.id in pairs]
    arms = ["klein_4b_edit_sh", "klein_4b_base_edit_sh"]
    for r in rows:
        panels = [("person", input_path_13(r.person)), ("garment", input_path_13(r.garment))]
        panels += [(a.replace("_sh", ""), os.path.join(KLEIN_OUT, f"{a}__{r.id}.png"))
                   for a in arms]
        panels = [(t, p) for t, p in panels if os.path.exists(p)]
        if len(panels) < 3:
            print(f"{r.id}: not generated yet"); continue
        fig, ax = plt.subplots(1, len(panels), figsize=(3.4 * len(panels), 5), dpi=90)
        for a, (title, path) in zip(ax, panels):
            im = Image.open(path).convert("RGB"); im.thumbnail((thumb, thumb))
            a.imshow(im); a.axis("off")
            a.set_title(title, fontsize=9)
        fig.suptitle(f"{r.id} · {r.kind} · target: {r.target}", fontsize=10, y=0.99)
        plt.tight_layout(); plt.show()

if IN_COLAB:
    print("after both arms finish:  show_klein_parity()")
    print("one pair only:           show_klein_parity(['ts2_07'])")
