"""v3.16 - what happens to the try-on above the 1 MP ceiling.

Writes v3/colab/v316_highres.ipynb. Like v3.15 it carries no copy of the pipeline: it fetches
vp/tryon_er.ipynb, executes its Install, Downloads, Inputs, Load and Pipeline cells unmodified,
prepares every garment with the shipped prepare_garment, and then runs call 2 with the shipped
klein, prompt and reference at six canvases. Only the canvas area changes between arms, plus
one of two pipeline internals on the two diagnostic arms.

  R10    1.0 MP  the shipped rule (4,096 tokens, the distilled schedule)
  R15    1.5 MP  past the 4,300-token branch
  R20    2.0 MP
  R20s   2.0 MP  scheduler mu computed with the below-branch formula, as if the branch were not there
  R20c   2.0 MP  person photo conditioned at 2 MP too (diffusers shrinks every input image to 1 MP)
  R40    4.0 MP

R20 against R20s separates "more pixels" from "the schedule switch"; R20 against R20c
separates the output size from the person photo diffusers silently caps at 1 MP. Every person
photo is at least 4 MP, so no arm upscales its input.

  python3 v3/build/make_v316_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v316_highres.ipynb")

PEOPLE = [
    ("emma_blazer", "test_set2/people/dualuse_emma_watson_black_blazer_armscrossed.jpg"),
    ("man_suit", "test_set2/people/dualuse_man_black_suit_studio_nonceleb.jpg"),
    ("queen_gown", "test_set2/people/dualuse_queen_latifah_gown_stage.jpg"),
    ("woman_denim", "test_set2/people/dualuse_woman_top_denim_skirt_nonceleb.jpg"),
    ("beige_coat", "test_set3/people/dualuse_lp_beige_long_coat_menswear.webp"),
    ("floral_kimono", "test_set3/people/dualuse_lp_floral_kimono_set.webp"),
]
GARMENTS = [
    ("g005", "test_set1/garments/g005.jpg", "tight top"),
    ("g013", "test_set1/garments/g013.jpg", "dress"),
    ("g018", "test_set1/garments/g018.jpg", "outerwear"),
    ("g024", "test_set1/garments/g024.jpg", "lower body"),
    ("p014", "test_set1/people/p014.jpg", "full outfit on a person"),
    ("plaid_overcoat", "test_set2/clothes/dualuse_lp_plaid_overcoat_brown_suit.jpg", "coat over a suit"),
]


def pairs():
    return [{"id": f"{p}+{g}", "person": p, "person_path": pp, "garment": g, "garment_path": gp, "garment_kind": k}
            for p, pp in PEOPLE for g, gp, k in GARMENTS]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}


SETTINGS = r'''
import hashlib
import json
import os
import re
import shutil
import time
import traceback
import urllib.request
import zipfile

REPO = "101011101/magichour_takehome"
BRANCH = "v3.3-lock"
SEEDS = [46]  #@param {type:"raw"}
RUN = "/content/v316"
PAIRS = json.loads(PAIRS_JSON)
ARMS = [
    {"arm": "R10", "area": 1_048_576, "schedule": "default", "condition": "1MP", "why": "the shipped rule"},
    {"arm": "R15", "area": 1_572_864, "schedule": "default", "condition": "1MP", "why": "1.5 MP"},
    {"arm": "R20", "area": 2_097_152, "schedule": "default", "condition": "1MP", "why": "2 MP"},
    {"arm": "R20s", "area": 2_097_152, "schedule": "below_branch", "condition": "1MP",
     "why": "2 MP, schedule formula without the 4,300-token branch"},
    {"arm": "R20c", "area": 2_097_152, "schedule": "default", "condition": "full",
     "why": "2 MP, person photo conditioned at 2 MP instead of shrunk to 1 MP"},
    {"arm": "R40", "area": 4_194_304, "schedule": "default", "condition": "1MP", "why": "4 MP"},
]
SECONDS = {"R10": 1.9, "R15": 3.2, "R20": 4.6, "R20s": 4.6, "R20c": 7.0, "R40": 13.0}

n = len(PAIRS) * len(SEEDS)
estimate = n * sum(SECONDS.values()) + len({p["garment"] for p in PAIRS}) * 2.1
print(f"{len(PAIRS)} pairs x {len(SEEDS)} seed(s) x {len(ARMS)} arms = {n * len(ARMS)} try-ons")
print(f"generation estimate on an A100: ~{estimate / 60:.0f} min (a guess above 1 MP), plus download and load")
'''

FETCH = r'''
api = f"https://api.github.com/repos/{REPO}/commits?path=vp/tryon_er.ipynb&sha={BRANCH}&per_page=1"
try:
    with urllib.request.urlopen(api, timeout=30) as r:
        COMMIT = json.load(r)[0]["sha"]
except Exception as e:
    COMMIT = None
    print(f"could not resolve the commit ({e}); using the branch head instead")
RAW = f"https://raw.githubusercontent.com/{REPO}/{COMMIT or BRANCH}"
os.makedirs(f"{RUN}/shipped", exist_ok=True)
urllib.request.urlretrieve(f"{RAW}/vp/tryon_er.ipynb", f"{RUN}/shipped/tryon_er.ipynb")
SHIPPED_SHA256 = hashlib.sha256(open(f"{RUN}/shipped/tryon_er.ipynb", "rb").read()).hexdigest()
shipped = json.load(open(f"{RUN}/shipped/tryon_er.ipynb"))

SECTIONS = ["## 1 · Install", "## 2 · Downloads", "## 3 · Inputs", "## 4 · Load", "## 5 · Pipeline"]
CELLS = {}
for i, c in enumerate(shipped["cells"]):
    title = "".join(c["source"]).strip()
    for s in SECTIONS:
        if c["cell_type"] == "markdown" and title.startswith(s):
            CELLS[s] = "".join(shipped["cells"][i + 1]["source"])
missing = [s for s in SECTIONS if s not in CELLS]
if missing:
    raise RuntimeError(f"tryon_er.ipynb no longer has the sections this inquiry drives: {missing}")
print(f"tryon_er.ipynb at {COMMIT or BRANCH}  sha256 {SHIPPED_SHA256[:16]}")
'''

EXEC_INSTALL = r'''
exec(compile(CELLS["## 1 · Install"], "tryon_er.ipynb · 1 Install", "exec"), globals())
'''

EXEC_REST = r'''
for s in ("## 2 · Downloads", "## 3 · Inputs", "## 4 · Load", "## 5 · Pipeline"):
    t = time.perf_counter()
    exec(compile(CELLS[s], f"tryon_er.ipynb · {s[3:]}", "exec"), globals())
    print(f"{s[3:]:14s} {time.perf_counter() - t:7.1f} s")
GPU = torch.cuda.get_device_name(0)
if "A100" not in GPU:
    print(f"{GPU}: not an A100 - quality still counts; timings and memory are not comparable")
print("GPU", GPU, f"{torch.cuda.get_device_properties(0).total_memory / 1024 ** 3:.0f} GB")
'''

INPUTS = r'''
os.makedirs(f"{RUN}/inputs", exist_ok=True)
PHOTOS = {}
for path in sorted({p["garment_path"] for p in PAIRS} | {p["person_path"] for p in PAIRS}):
    dst = f"{RUN}/inputs/" + os.path.basename(path)
    if not os.path.exists(dst):
        urllib.request.urlretrieve(f"{RAW}/{path}", dst)
    PHOTOS[path] = load_image(dst, "photo")
    if PHOTOS[path] is None:
        raise RuntimeError(f"unreadable input {path}")
for p in {p["person_path"] for p in PAIRS}:
    h, w = PHOTOS[p].shape[:2]
    if h * w < max(a["area"] for a in ARMS):
        raise RuntimeError(f"{p} is {w}x{h}; the 4 MP arm would upscale it")
print(len(PHOTOS), "photos from the repo at", COMMIT or BRANCH)
'''

HARNESS = r'''
import diffusers.pipelines.flux2.pipeline_flux2_klein as klein_module

_mu_default = klein_module.compute_empirical_mu
_resize_default = pipe.image_processor._resize_to_target_area
SCHEDULE = []


def mu_below_branch(image_seq_len, num_steps):
    a1, b1 = 8.73809524e-05, 1.89833333
    a2, b2 = 0.00016927, 0.45666666
    m_200 = a2 * image_seq_len + b2
    m_10 = a1 * image_seq_len + b1
    a = (m_200 - m_10) / 190.0
    return float(a * num_steps + m_200 - 200.0 * a)


def set_arm(arm):
    chosen = mu_below_branch if arm["schedule"] == "below_branch" else _mu_default

    def recorded(image_seq_len, num_steps):
        mu = chosen(image_seq_len, num_steps)
        SCHEDULE.append({"tokens": int(image_seq_len), "mu": round(mu, 4)})
        return mu

    klein_module.compute_empirical_mu = recorded
    pipe.image_processor._resize_to_target_area = (
        (lambda image, target_area: image) if arm["condition"] == "full" else _resize_default)


def reset_arm():
    klein_module.compute_empirical_mu = _mu_default
    pipe.image_processor._resize_to_target_area = _resize_default


def canvas_at(bgr, area):
    h, w = bgr.shape[:2]
    k = min(1.0, (area / (h * w)) ** 0.5)
    return max(32, int(h * k) // 32 * 32), max(32, int(w * k) // 32 * 32)


def generate(person, reference, seed, arm):
    photo = jpeg(normalise(person, arm["area"]))
    size = canvas_at(photo, arm["area"])
    SCHEDULE.clear()
    set_arm(arm)
    torch.cuda.reset_peak_memory_stats()
    try:
        t = time.perf_counter()
        out = klein([photo, reference], call2("full"), seed, size)
        seconds = time.perf_counter() - t
    finally:
        reset_arm()
    sigmas = [round(float(s), 4) for s in pipe.scheduler.sigmas.tolist()]
    return out, {"output": f"{size[1]}x{size[0]}", "megapixels": round(size[0] * size[1] / 1e6, 3),
                 "person_input": f"{photo.shape[1]}x{photo.shape[0]}", "tokens": SCHEDULE[-1]["tokens"],
                 "mu": SCHEDULE[-1]["mu"], "sigmas": sigmas, "seconds": round(seconds, 3),
                 "peak_gb": round(torch.cuda.max_memory_allocated() / 1024 ** 3, 2)}
'''

PREPARE = r'''
shutil.rmtree(CACHE_DIR, ignore_errors=True)
for d in ("refs", "gen", "persons"):
    os.makedirs(f"{RUN}/{d}", exist_ok=True)
REFS = {}
for g in sorted({(p["garment"], p["garment_path"]) for p in PAIRS}):
    reference, info, times, cached = prepare_garment(PHOTOS[g[1]], "full")
    REFS[g[0]] = reference
    cv2.imwrite(f"{RUN}/refs/{g[0]}.jpg", reference, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"{g[0]:16s} route={info.get('route')} head={info.get('head_route')} "
          f"{reference.shape[1]}x{reference.shape[0]}  {sum(times.values()):.2f} s")
for p in sorted({(p["person"], p["person_path"]) for p in PAIRS}):
    cv2.imwrite(f"{RUN}/persons/{p[0]}.jpg", normalise(PHOTOS[p[1]], AREA), [cv2.IMWRITE_JPEG_QUALITY, 92])

first = PAIRS[0]
shipped_out, _ = try_on(PHOTOS[first["person_path"]], REFS[first["garment"]], SEEDS[0], "full", None)
harness_out, _ = generate(PHOTOS[first["person_path"]], REFS[first["garment"]], SEEDS[0], ARMS[0])
PARITY = bool(shipped_out.shape == harness_out.shape and (shipped_out == harness_out).all())
print("R10 through the harness is byte-identical to the shipped try_on:", PARITY)
if not PARITY:
    diff = float(np.abs(shipped_out.astype(np.float32) - harness_out.astype(np.float32)).mean())
    print(f"not byte-identical: mean pixel difference {diff:.2f}/255. Above ~1 this is a harness bug; stop and check")
for arm in ARMS[1:]:
    generate(PHOTOS[first["person_path"]], REFS[first["garment"]], SEEDS[0], arm)
print("warm-up done at every canvas")
'''

RUN_ALL = r'''
RECORDS = []
total = len(PAIRS) * len(SEEDS) * len(ARMS)
done = 0
t_run = time.perf_counter()
for pair in PAIRS:
    person, reference = PHOTOS[pair["person_path"]], REFS[pair["garment"]]
    for seed in SEEDS:
        for arm in ARMS:
            done += 1
            rec = {"pair": pair["id"], "person": pair["person"], "garment": pair["garment"],
                   "seed": seed, **arm}
            try:
                out, facts = generate(person, reference, seed, arm)
                name = f"{pair['id']}__{arm['arm']}__s{seed}.jpg"
                cv2.imwrite(f"{RUN}/gen/{name}", out, [cv2.IMWRITE_JPEG_QUALITY, 92])
                rec.update(facts, file=name)
            except torch.cuda.OutOfMemoryError as e:
                rec["error"] = f"out of memory: {e}"
                torch.cuda.empty_cache()
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {e}"
                rec["traceback"] = traceback.format_exc()
            RECORDS.append(rec)
            print(f"{done:3d}/{total} {pair['id']:28s} s{seed} {arm['arm']:5s} "
                  + (rec.get("error") or f"{rec['output']:>9s} tok={rec['tokens']:5d} mu={rec['mu']:.3f} "
                                          f"{rec['seconds']:5.2f}s {rec['peak_gb']:5.1f}GB"))
        json.dump(RECORDS, open(f"{RUN}/records.json", "w"), indent=1)
print(f"{(time.perf_counter() - t_run) / 60:.1f} min")
'''

SUMMARY = r'''
import statistics

print(f"{'arm':5s} {'canvas':>9s} {'tokens':>6s} {'mu':>6s}  sigmas                          "
      f"{'median s':>8s} {'peak GB':>7s} errors")
for arm in ARMS:
    ok = [r for r in RECORDS if r["arm"] == arm["arm"] and "error" not in r]
    bad = [r for r in RECORDS if r["arm"] == arm["arm"] and "error" in r]
    if not ok:
        print(f"{arm['arm']:5s} all {len(bad)} failed: {bad[0]['error'][:80] if bad else ''}")
        continue
    ex = ok[0]
    print(f"{arm['arm']:5s} {statistics.median(r['megapixels'] for r in ok):8.2f}M "
          f"{int(statistics.median(r['tokens'] for r in ok)):6d} {statistics.median(r['mu'] for r in ok):6.3f}  "
          f"{str(ex['sigmas']):32s} {statistics.median(r['seconds'] for r in ok):8.2f} "
          f"{max(r['peak_gb'] for r in ok):7.1f} {len(bad)}")
json.dump({"commit": COMMIT, "branch": BRANCH, "shipped_sha256": SHIPPED_SHA256, "gpu": GPU,
           "seeds": SEEDS, "arms": ARMS, "pairs": PAIRS, "parity_r10": PARITY,
           "images": sum(1 for r in RECORDS if "error" not in r)},
          open(f"{RUN}/meta.json", "w"), indent=1)
'''

ZIP = r'''
TERMINATE_WHEN_DONE = True  #@param {type:"boolean"}
DOWNLOAD_GRACE_SECONDS = 240  #@param {type:"integer"}

name = f"v316_highres_{time.strftime('%Y%m%d_%H%M')}"
zip_path = f"/content/{name}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as z:
    for sub in ("inputs", "persons", "refs", "gen", "shipped"):
        for f in sorted(os.listdir(f"{RUN}/{sub}")):
            z.write(f"{RUN}/{sub}/{f}", f"{sub}/{f}")
    for f in ("records.json", "meta.json"):
        z.write(f"{RUN}/{f}", f)
with zipfile.ZipFile(zip_path) as z:
    if z.testzip() is not None:
        raise RuntimeError("the zip is corrupt")
    names = z.namelist()
print(f"{name}.zip · {len(names)} files · {os.path.getsize(zip_path) / 1e6:.0f} MB")

from google.colab import files
downloaded = False
try:
    files.download(zip_path)
    downloaded = True
except Exception as e:
    print(f"download failed ({e}); the zip is at {zip_path} and the runtime is kept")
if downloaded:
    print(f"downloading; waiting {DOWNLOAD_GRACE_SECONDS}s before the runtime is released")
    time.sleep(DOWNLOAD_GRACE_SECONDS)
    if TERMINATE_WHEN_DONE:
        from google.colab import runtime
        runtime.unassign()
'''


def main():
    cells = [
        md("# v3.16 — the try-on above the 1 MP ceiling\n\n"
           "Fetches `vp/tryon_er.ipynb` and executes its Install, Downloads, Inputs, Load and Pipeline "
           "cells unmodified, prepares six worn garments with the shipped `prepare_garment`, then runs "
           "the shipped call 2 on six person photos of 4 MP or more at six canvases: 1.0, 1.5, 2.0 and "
           "4.0 MP, plus two 2 MP diagnostics — the scheduler branch removed, and the person photo "
           "conditioned at 2 MP rather than shrunk to 1 MP. Same pair, seed, prompt and reference "
           "across arms. Records canvas, tokens, mu, sigmas, seconds and peak memory. A100 40 GB. "
           "Runtime → Run all."),
        md("## 1 · Settings and budget"),
        code(SETTINGS.replace("PAIRS_JSON", repr(json.dumps(pairs())))),
        md("## 2 · Fetch the shipped notebook"),
        code(FETCH),
        md("## 3 · Run the shipped Install cell"),
        code(EXEC_INSTALL),
        md("## 4 · Run the shipped Downloads, Inputs, Load and Pipeline cells"),
        code(EXEC_REST),
        md("## 5 · The photos, from the repo"),
        code(INPUTS),
        md("## 6 · The harness: canvas, schedule and conditioning per arm"),
        code(HARNESS),
        md("## 7 · Prepare the garments, check parity with the shipped try_on, warm up"),
        code(PREPARE),
        md("## 8 · Run every pair at every canvas"),
        code(RUN_ALL),
        md("## 9 · Canvas, schedule, time and memory per arm"),
        code(SUMMARY),
        md("## 10 · Zip, download, release the GPU"),
        code(ZIP),
    ]
    nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"gpuType": "A100"},
                                       "kernelspec": {"display_name": "Python 3", "name": "python3"}},
          "nbformat": 4, "nbformat_minor": 5}
    json.dump(nb, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"{os.path.relpath(OUT, REPO)}  ({len(cells)} cells, {len(pairs())} pairs)")


if __name__ == "__main__":
    main()
