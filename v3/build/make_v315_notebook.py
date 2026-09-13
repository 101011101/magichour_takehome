"""v3.15 - the production notebook itself, run end to end with regions set.

Writes v3/colab/v315_prod_smoke.ipynb. The test does not carry a copy of the pipeline: at
run time it fetches vp/tryon_er.ipynb from the branch, resolves the commit that file was
last changed in, and executes that notebook's own section cells - Install, Downloads,
Inputs, Load, Pipeline - found by their markdown titles, byte for byte. Only the shipped
Run and Output cells are skipped, because they wait for a browser upload. It then drives
the shipped functions (prepare_garment, try_on, load_image) exactly as the Run cells do,
with the inputs set per case.

The one addition is a recorder around `klein`, rebound in the same namespace the shipped
functions resolve it from. It passes every argument through unchanged and notes which
prompt went in - which is how the test knows whether the bald pass ran and which call-2
sentence was sent, without reading anything the pipeline did not actually do.

  python3 v3/build/make_v315_notebook.py
"""
import csv
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v315_prod_smoke.ipynb")

PERSON_PRODUCT = ("p001", "test_set1/people/p001.jpg")
PERSON_WORN = ("p006", "test_set1/people/p006.jpg")
WORN = [
    ("g004", "test_set1/garments/g004.jpg", "tight top, an ordinary band cut"),
    ("g024", "test_set1/garments/g024.jpg", "lower-body garment, where lower is the meaningful half"),
    ("g015", "test_set1/garments/g015.jpg", "a dress - ATR labels it one class over the whole body"),
    ("g030", "test_set1/garments/g030.jpg", "no in-frame hip on the archived bald frame - expected to fall back"),
    ("p019", "test_set1/people/p019.jpg", "waist-up wearer - the lower band is likely too small, a second fallback path"),
]


def cases():
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3", "colab", "v314_set.csv"))))
    product = [(r["stem"], r["path"], r["photo_style"]) for r in rows if r["kind"] == "product"]
    out = []
    for stem, path, style in product:
        for region in ("upper", "lower"):
            out.append({"id": f"{stem}__{region}", "kind": "product", "garment": stem,
                        "garment_path": path, "person": PERSON_PRODUCT[0],
                        "person_path": PERSON_PRODUCT[1], "region": region,
                        "why": f"{style} - no person, must skip the bald pass and force full"})
    for stem, path, why in WORN:
        for region in ("upper", "lower"):
            out.append({"id": f"{stem}__{region}", "kind": "worn", "garment": stem,
                        "garment_path": path, "person": PERSON_WORN[0],
                        "person_path": PERSON_WORN[1], "region": region, "why": why})
    return out


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}


SETTINGS = r'''
import glob
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
TEST_SEED = 46
RUN = "/content/v315"
CASES = json.loads(CASES_JSON)

n_product = sum(1 for c in CASES if c["kind"] == "product")
n_worn = sum(1 for c in CASES if c["kind"] == "worn")
bald_calls = n_worn
tryon_calls = len(CASES)
estimate = bald_calls * 1.48 + tryon_calls * 1.9 + (n_worn + n_product // 2) * 0.58
print(f"{len(CASES)} cases: {n_product} product-shot requests, {n_worn} worn-garment requests")
print(f"klein calls expected: {bald_calls} bald passes + {tryon_calls} try-ons = {bald_calls + tryon_calls}")
print(f"generation estimate on an A100: ~{estimate / 60:.1f} min, plus the weight download and load")
'''

FETCH = r'''
api = f"https://api.github.com/repos/{REPO}/commits?path=vp/tryon_er.ipynb&sha={BRANCH}&per_page=1"
try:
    with urllib.request.urlopen(api, timeout=30) as r:
        COMMIT = json.load(r)[0]["sha"]
except Exception as e:
    COMMIT = None
    print(f"could not resolve the commit ({e}); testing the branch head instead")
RAW = f"https://raw.githubusercontent.com/{REPO}/{COMMIT or BRANCH}"
os.makedirs(f"{RUN}/shipped", exist_ok=True)
urllib.request.urlretrieve(f"{RAW}/vp/tryon_er.ipynb", f"{RUN}/shipped/tryon_er.ipynb")
SHIPPED_SHA256 = hashlib.sha256(open(f"{RUN}/shipped/tryon_er.ipynb", "rb").read()).hexdigest()
shipped = json.load(open(f"{RUN}/shipped/tryon_er.ipynb"))

SECTIONS = ["## 1 · Install", "## 2 · Downloads", "## 3 · Inputs", "## 4 · Load", "## 5 · Pipeline"]
SKIPPED = ["## 6a · Run", "## 6b · Run", "## 7 · Output"]


def section_cells(nb):
    found = {}
    cells = nb["cells"]
    for i, c in enumerate(cells):
        if c["cell_type"] != "markdown":
            continue
        title = "".join(c["source"]).strip()
        for s in SECTIONS + SKIPPED:
            if title.startswith(s):
                if i + 1 >= len(cells) or cells[i + 1]["cell_type"] != "code":
                    raise RuntimeError(f"section {s!r} is not followed by a code cell")
                found[s] = "".join(cells[i + 1]["source"])
    missing = [s for s in SECTIONS + SKIPPED if s not in found]
    if missing:
        raise RuntimeError(f"tryon_er.ipynb no longer has the sections this test drives: {missing}")
    return found


CELLS = section_cells(shipped)
for s in SECTIONS:
    name = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    open(f"{RUN}/shipped/{name}.py", "w").write(CELLS[s])
print(f"tryon_er.ipynb at {COMMIT or BRANCH}  sha256 {SHIPPED_SHA256[:16]}")
print("executing, unmodified:", ", ".join(SECTIONS))
print("skipped (they wait for an upload):", ", ".join(SKIPPED))
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
    print(f"{GPU}: not an A100 - this tests behaviour, so it still counts; timings are not comparable")
print("GPU", GPU, "| MAX_RES default", MAX_RES)
'''

INPUTS = r'''
os.makedirs(f"{RUN}/inputs", exist_ok=True)
for path in sorted({c["garment_path"] for c in CASES} | {c["person_path"] for c in CASES}):
    dst = f"{RUN}/inputs/" + os.path.basename(path)
    if not os.path.exists(dst):
        urllib.request.urlretrieve(f"{RAW}/{path}", dst)
    if cv2.imread(dst) is None:
        raise RuntimeError(f"unreadable input {path}")
print(len(os.listdir(f"{RUN}/inputs")), "photos from the repo at", COMMIT or BRANCH)
'''

HARNESS = r'''
_klein_shipped = klein
CALLS = []


def klein(images, prompt, seed, size):
    t = time.perf_counter()
    out = _klein_shipped(images, prompt, seed, size)
    CALLS.append({"kind": "bald" if prompt == BALD_PROMPT else "try-on", "prompt": prompt,
                  "seed": int(seed), "size": [int(size[0]), int(size[1])],
                  "seconds": round(time.perf_counter() - t, 3)})
    return out


def head_pixels(why):
    m = re.search(r"(\d+)", why or "")
    return int(m.group(1)) if m else None


def judge(case, info, prep_calls, tryon, cached):
    fails, notes = [], []
    req, kind = case["region"], case["kind"]
    route, applied, fallback = info.get("route"), info.get("region"), info.get("fallback", "")
    bald = any(c["kind"] == "bald" for c in prep_calls)
    sent = tryon[0]["prompt"] if tryon else None
    wanted = ER_PROMPT if applied == "full" else ER_REGION.get(applied)
    if len(tryon) != 1:
        fails.append(f"{len(tryon)} generations in try_on, expected 1")
    if sent != wanted:
        fails.append(f"call 2 was sent the wrong sentence for region {applied!r}")
    if kind == "product":
        if route != "product":
            fails.append(f"the gate saw a person on a product shot ({info.get('route_why')})")
        if bald:
            fails.append("the bald pass ran on a product shot")
        if applied != "full":
            fails.append(f"a product shot was cut to {applied!r} instead of forced to full")
        if info.get("requested") != req:
            notes.append(f"the garment record reads requested={info.get('requested')!r}, not {req!r}:"
                         " the forcing is visible through route=product, not through requested")
    else:
        if route != "worn":
            fails.append(f"the gate missed the wearer ({info.get('route_why')})")
        if not bald and not cached:
            fails.append("a worn garment was prepared without the bald pass")
        if applied not in ("full", req):
            fails.append(f"applied region {applied!r} is neither {req!r} nor full")
        if applied == "full" and not fallback:
            fails.append(f"{req} was silently treated as full, with no recorded reason")
        if applied == req and "kept_fraction" not in info:
            fails.append("the band was applied but kept_fraction was not recorded")
        if fallback:
            notes.append(f"fell back to full: {fallback}")
    if cached:
        notes.append("the reference came from the cache (same garment, same applied region, same route)")
    return fails, notes


def run_case(case):
    rec = {"case": case, "pass": False, "fails": [], "notes": []}
    t0 = time.perf_counter()
    try:
        garment = load_image(f"{RUN}/inputs/" + os.path.basename(case["garment_path"]), "garment")
        person = load_image(f"{RUN}/inputs/" + os.path.basename(case["person_path"]), "person")
        CALLS.clear()
        reference, info, garment_times, cached = prepare_garment(garment, case["region"])
        prep_calls = list(CALLS)
        CALLS.clear()
        result, tryon_times = try_on(person, reference, TEST_SEED, info["region"], MAX_RES)
        tryon = list(CALLS)
        fails, notes = judge(case, info, prep_calls, tryon, cached)
        cv2.imwrite(f"{RUN}/refs/{case['id']}.jpg", reference, [cv2.IMWRITE_JPEG_QUALITY, 92])
        cv2.imwrite(f"{RUN}/gen/{case['id']}.jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 92])
        rec.update({
            "pass": not fails, "fails": fails, "notes": notes,
            "actual": {"gate": info.get("route") == "worn", "head_px": head_pixels(info.get("route_why")),
                       "route_why": info.get("route_why"), "route": info.get("route"),
                       "bald_pass": any(c["kind"] == "bald" for c in prep_calls),
                       "requested": case["region"], "applied": info.get("region"),
                       "fallback": info.get("fallback", ""), "kept_fraction": info.get("kept_fraction"),
                       "head_route": info.get("head_route"), "cached": bool(cached),
                       "call2": "region" if tryon and tryon[0]["prompt"] in ER_REGION.values() else "full",
                       "output": f"{result.shape[1]}x{result.shape[0]}",
                       "reference": f"{reference.shape[1]}x{reference.shape[0]}"},
            "times": {**{"garment " + k: round(v, 3) for k, v in garment_times.items()},
                      **{"person " + k: round(v, 3) for k, v in tryon_times.items()}},
            "klein_calls": prep_calls + tryon,
        })
    except Exception as e:
        rec["fails"] = [f"raised {type(e).__name__}: {e}"]
        rec["traceback"] = traceback.format_exc()
    rec["expected"] = ({"gate": False, "route": "product", "bald_pass": False, "applied": "full", "call2": "full"}
                       if case["kind"] == "product" else
                       {"gate": True, "route": "worn", "bald_pass": True,
                        "applied": f"{case['region']} (or full with a recorded fallback)",
                        "call2": "region (or full with a recorded fallback)"})
    rec["wall_seconds"] = round(time.perf_counter() - t0, 2)
    return rec
'''

RUN_ALL = r'''
shutil.rmtree(CACHE_DIR, ignore_errors=True)
for d in ("refs", "gen"):
    os.makedirs(f"{RUN}/{d}", exist_ok=True)
RECORDS = []
for i, case in enumerate(CASES, 1):
    rec = run_case(case)
    RECORDS.append(rec)
    a = rec.get("actual", {})
    print(f"{i:2d}/{len(CASES)} {'PASS' if rec['pass'] else 'FAIL'}  {case['id']:14s} "
          f"route={a.get('route')} bald={a.get('bald_pass')} applied={a.get('applied')} call2={a.get('call2')}"
          + (f"  <- {rec['fails'][0]}" if rec["fails"] else ""))
    json.dump(RECORDS, open(f"{RUN}/records.json", "w"), indent=1)
'''

SUMMARY = r'''
width = max(len(r["case"]["id"]) for r in RECORDS)
print(f"{'case':{width}s}  kind     req    route    bald   applied  call2   head_px  result")
for r in sorted(RECORDS, key=lambda r: (r["pass"], r["case"]["kind"], r["case"]["id"])):
    a = r.get("actual", {})
    print(f"{r['case']['id']:{width}s}  {r['case']['kind']:7s}  {r['case']['region']:5s}  "
          f"{str(a.get('route')):7s}  {str(a.get('bald_pass')):5s}  {str(a.get('applied')):7s}  "
          f"{str(a.get('call2')):6s}  {str(a.get('head_px')):7s}  {'PASS' if r['pass'] else 'FAIL'}")
    for f in r["fails"]:
        print(f"{'':{width}s}    FAIL: {f}")
passed = sum(r["pass"] for r in RECORDS)
for kind in ("product", "worn"):
    group = [r for r in RECORDS if r["case"]["kind"] == kind]
    print(f"{kind:8s} {sum(r['pass'] for r in group)}/{len(group)} pass")
klein_total = sum(len(r.get("klein_calls", [])) for r in RECORDS)
print(f"TOTAL    {passed}/{len(RECORDS)} pass · {klein_total} klein calls · tryon_er.ipynb at {COMMIT or BRANCH}")
json.dump({"commit": COMMIT, "branch": BRANCH, "shipped_sha256": SHIPPED_SHA256, "gpu": GPU,
           "max_res": MAX_RES, "seed": TEST_SEED, "passed": passed, "cases": len(RECORDS),
           "klein_calls": klein_total}, open(f"{RUN}/meta.json", "w"), indent=1)
'''

ZIP = r'''
TERMINATE_WHEN_DONE = True  #@param {type:"boolean"}
DOWNLOAD_GRACE_SECONDS = 120  #@param {type:"integer"}

name = f"v315_prod_smoke_{time.strftime('%Y%m%d_%H%M')}"
zip_path = f"/content/{name}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for sub in ("inputs", "refs", "gen", "shipped"):
        for f in sorted(os.listdir(f"{RUN}/{sub}")):
            z.write(f"{RUN}/{sub}/{f}", f"{sub}/{f}")
    for f in ("records.json", "meta.json"):
        z.write(f"{RUN}/{f}", f)
with zipfile.ZipFile(zip_path) as z:
    if z.testzip() is not None:
        raise RuntimeError("the zip is corrupt")
    names = z.namelist()
print(f"{name}.zip · {len(names)} files · {os.path.getsize(zip_path) / 1e6:.1f} MB")

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
        md("# v3.15 — the production notebook, run end to end with regions set\n\n"
           "Fetches `vp/tryon_er.ipynb` from the branch and executes its own Install, Downloads, "
           "Inputs, Load and Pipeline cells unmodified, then drives its functions over every "
           "product shot at `upper` and `lower` and five worn garments at both. Prints PASS/FAIL "
           "per case and a total. Drive-free; any GPU with 20 GB works. Runtime → Run all."),
        md("## 1 · Settings and budget"),
        code(SETTINGS.replace("CASES_JSON", repr(json.dumps(cases())))),
        md("## 2 · Fetch the shipped notebook and find its sections"),
        code(FETCH),
        md("## 3 · Run the shipped Install cell"),
        code(EXEC_INSTALL),
        md("## 4 · Run the shipped Downloads, Inputs, Load and Pipeline cells"),
        code(EXEC_REST),
        md("## 5 · The test photos, from the repo"),
        code(INPUTS),
        md("## 6 · The harness: a pass-through recorder on klein, and the expectations"),
        code(HARNESS),
        md("## 7 · Run every case"),
        code(RUN_ALL),
        md("## 8 · PASS / FAIL"),
        code(SUMMARY),
        md("## 9 · Zip, download, release the GPU"),
        code(ZIP),
    ]
    nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"gpuType": "A100"},
                                       "kernelspec": {"display_name": "Python 3", "name": "python3"}},
          "nbformat": 4, "nbformat_minor": 5}
    json.dump(nb, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"{os.path.relpath(OUT, REPO)}  ({len(cells)} cells, {len(cases())} cases)")


if __name__ == "__main__":
    main()
