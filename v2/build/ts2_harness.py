# Testset2 harness — editing models on the high-res set, including duo pairs
# (the garment reference is itself a photo of a person wearing the garment).
#
# Three pair kinds, deliberately increasing in difficulty:
#   product     flat-lay / ghost-mannequin garment -> person   (shop2model)
#   duo_lookbook  editorial ON-MODEL garment photo -> person   (model2model)
#   duo_swap    a people/ photo used as the garment source     (clothes swap)
# The catalog's benchmark anchor has every open model collapsing on model2model
# (VTEdit: best universal 2.06, Qwen 1.17, klein 1.03), so the duo rows are the
# discriminating part of this matrix, not the product rows.
#
# Usage: python v2/build/ts2_harness.py --prep --generate --score --judge --html
import argparse
import base64
import io
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics_v2 as M

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _l in (open(os.path.join(REPO, ".env")) if os.path.exists(os.path.join(REPO, ".env")) else []):
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        _k, _, _v = _l.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip())

TS2 = os.path.join(REPO, "Testset2")
RUNS = os.path.join(REPO, "v2", "runs", "ts2")
INP = os.path.join(RUNS, "inputs")
OUT = os.path.join(RUNS, "outputs")
ART = os.path.join(REPO, "v2", "artifacts")
RUNS_REL = "../runs/ts2"    # page lives in v2/artifacts/, images stay in v2/runs/ts2/
JUDGE_MODEL = "gpt-5.5"
SEED = 46
BUDGET_USD = 4.00
MAX_SIDE = 1536          # inputs are up to 5152x7728; cap upload size

P, C = "people", "clothes"
# id, person, garment, kind, category, target garment phrase
MATRIX = [
    # -- product: flat-lay / ghost garment -> person -------------------------
    ("ts2_01", f"{P}/dualuse_emma_watson_black_blazer_armscrossed.jpg",
     f"{C}/clothesonly_ts1g026_metallica_text_tee_flat.jpg", "product", "tops",
     "the black text-print t-shirt"),
    ("ts2_02", f"{P}/dualuse_hugh_jackman_grey_suit_outdoor.jpg",
     f"{C}/clothesonly_ts1g008_plaid_flannel.jpg", "product", "tops",
     "the plaid flannel shirt"),
    ("ts2_03", f"{P}/dualuse_woman_top_denim_skirt_nonceleb.jpg",
     f"{C}/clothesonly_ts1g023_plaid_mini_skirt_flat.jpg", "product", "bottoms",
     "the plaid mini skirt"),
    ("ts2_04", f"{P}/dualuse_man_black_suit_studio_nonceleb.jpg",
     f"{C}/clothesonly_ts1g001_graphic_logo_tee.jpg", "product", "tops",
     "the graphic logo t-shirt"),
    ("ts2_05", f"{P}/dualuse_zendaya_white_blazer_skirt.jpeg",
     f"{C}/clothesonly_ts1g028_fine_stripe_shirt_ghost.jpg", "product", "tops",
     "the fine-striped shirt"),
    ("ts2_06", f"{P}/dualuse_scarlett_johansson_black_dress_backview_night.avif",
     f"{C}/clothesonly_ts1g010_plain_tee_ghost.jpg", "product", "tops",
     "the plain t-shirt"),          # back view: extreme pose control
    # -- duo_lookbook: on-model editorial garment -> person ------------------
    ("ts2_07", f"{P}/dualuse_gal_gadot_blue_dress_redcarpet.jpg",
     f"{C}/dualuse_lp_beige_long_coat_menswear.webp", "duo_lookbook", "one-pieces",
     "the long beige coat"),
    ("ts2_08", f"{P}/dualuse_queen_latifah_gown_stage.jpg",
     f"{C}/dualuse_navy_peacoat_onmodel.webp", "duo_lookbook", "tops",
     "the navy peacoat"),
    ("ts2_09", f"{P}/dualuse_hugh_jackman_grey_suit_outdoor.jpg",
     f"{C}/dualuse_lp_plaid_overcoat_brown_suit.jpg", "duo_lookbook", "tops",
     "the brown plaid overcoat"),
    ("ts2_10", f"{P}/dualuse_zendaya_white_blazer_skirt.jpeg",
     f"{C}/dualuse_lp_floral_kimono_set.webp", "duo_lookbook", "one-pieces",
     "the floral kimono outfit"),
    # -- duo_swap: a people/ photo is the garment source ---------------------
    ("ts2_11", f"{P}/dualuse_emma_watson_black_blazer_armscrossed.jpg",
     f"{P}/dualuse_man_black_suit_studio_nonceleb.jpg", "duo_swap", "one-pieces",
     "the black suit"),
    ("ts2_12", f"{P}/dualuse_man_black_suit_studio_nonceleb.jpg",
     f"{P}/dualuse_hugh_jackman_grey_suit_outdoor.jpg", "duo_swap", "one-pieces",
     "the grey suit"),
    ("ts2_13", f"{P}/dualuse_woman_top_denim_skirt_nonceleb.jpg",
     f"{P}/dualuse_gal_gadot_blue_dress_redcarpet.jpg", "duo_swap", "one-pieces",
     "the blue floor-length gown"),
]
COLS = ["id", "person", "garment", "kind", "category", "target"]


def prompt_for(row, duo):
    """Duo references show a whole outfit on a whole person, so the prompt must
    name the target garment and state which person to keep (README: on-model
    refs need a per-pair target designation)."""
    if duo:
        return (f"Take {row.target} worn by the person in image 2 and put it on the "
                f"person in image 1. Keep the person in image 1 — their face, hair, "
                f"body, pose — and the background completely unchanged. Do not copy "
                f"the face, body or background of image 2. Preserve the exact color, "
                f"pattern and cut of {row.target}.")
    return (f"Replace the clothing of the person in image 1 with {row.target} shown in "
            f"image 2. Keep the person's face, hair, pose, hands, body and the "
            f"background completely unchanged. Preserve the garment's exact color, "
            f"pattern, print and cut.")


def person_size(row):
    """Arms that take an explicit output size get the person image's own dimensions
    (rounded to /16) so aspect and framing match the free-running arms."""
    w, h = Image.open(local(row.person)).size
    return {"width": max(256, w // 16 * 16), "height": max(256, h // 16 * 16)}


ARMS = {
    "fashn_v15": {"endpoint": "fal-ai/fashn/tryon/v1.5", "est_usd": 0.075,
                  "args": lambda r, p, g, duo: {
                      "model_image": p, "garment_image": g,
                      "category": r.category,
                      "garment_photo_type": "model" if duo else "flat-lay",
                      "mode": "quality", "seed": SEED, "num_samples": 1,
                      "output_format": "png"}},
    "klein_4b_edit": {"endpoint": "fal-ai/flux-2/klein/4b/distilled/edit", "est_usd": 0.015,
                      "args": lambda r, p, g, duo: {
                          "prompt": prompt_for(r, duo), "image_urls": [p, g],
                          "seed": SEED, "num_images": 1}},
    # klein 4B *base* — the undistilled sibling of klein_4b_edit. Same Apache 2.0
    # family, but true CFG + negative prompts and none of the distillation flake
    # (one solid-black frame in 16 triage runs). $0.009/MP.
    "klein_4b_base_edit": {"endpoint": "fal-ai/flux-2/klein/4b/base/edit", "est_usd": 0.02,
                           "args": lambda r, p, g, duo: {
                               "prompt": prompt_for(r, duo), "image_urls": [p, g],
                               "negative_prompt": "different person, changed face, "
                                                  "changed background, extra limbs, "
                                                  "deformed hands",
                               "seed": SEED, "num_images": 1, "output_format": "png"}},
    # HiDream-O1-Image (MIT, pixel-native, no VAE) — multi-reference edit endpoint.
    # image_size defaults to 2048^2 (square); we pass the person's own dimensions so
    # framing/aspect match the other arms. Priced $0.01/MP.
    "hidream_o1_edit": {"endpoint": "fal-ai/hidream-o1-image/edit", "est_usd": 0.03,
                        "args": lambda r, p, g, duo: {
                            "prompt": prompt_for(r, duo), "reference_image_urls": [p, g],
                            "image_size": person_size(r), "seed": SEED, "num_images": 1,
                            "output_format": "png"}},
    "qwen_2511": {"endpoint": "fal-ai/qwen-image-edit-2511", "est_usd": 0.03,
                  "args": lambda r, p, g, duo: {
                      "prompt": prompt_for(r, duo), "image_urls": [p, g],
                      "seed": SEED, "num_images": 1, "acceleration": "none"}},
}

_lock = threading.Lock()
_spent = [0.0]


def matrix_df():
    df = pd.DataFrame(MATRIX, columns=COLS)
    df["duo"] = df.kind.str.startswith("duo")
    return df


def prep():
    """Normalize mixed formats (avif/webp) to JPEG and cap the long side."""
    os.makedirs(INP, exist_ok=True)
    df = matrix_df()
    for rel in sorted(set(df.person) | set(df.garment)):
        dst = os.path.join(INP, os.path.splitext(os.path.basename(rel))[0] + ".jpg")
        if os.path.exists(dst):
            continue
        im = Image.open(os.path.join(TS2, rel)).convert("RGB")
        if max(im.size) > MAX_SIDE:
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        im.save(dst, "JPEG", quality=95)
        print(f"  prepped {os.path.basename(dst)} {im.size}")
    df.to_csv(os.path.join(RUNS, "matrix.csv"), index=False)
    print(f"matrix: {len(df)} pairs -> {os.path.join(RUNS, 'matrix.csv')}")
    print(df.groupby("kind").size().to_string())


def local(rel):
    return os.path.join(INP, os.path.splitext(os.path.basename(rel))[0] + ".jpg")


def generate(arms):
    import fal_client
    os.makedirs(OUT, exist_ok=True)
    df = matrix_df()
    todo = [(a, r) for a in arms for r in df.itertuples()
            if not os.path.exists(os.path.join(OUT, f"{a}__{r.id}.png"))]
    est = sum(ARMS[a]["est_usd"] for a, _ in todo)
    print(f"{len(todo)} generations ({len(arms)} arms x {len(df)} pairs) — est ${est:.2f}")
    if est > BUDGET_USD:
        sys.exit(f"estimate ${est:.2f} exceeds ${BUDGET_USD:.2f} ceiling")

    cache = {}
    def url(path):
        with _lock:
            if path not in cache:
                cache[path] = fal_client.upload_file(path)
        return cache[path]

    def one(job):
        arm, r = job
        cfg = ARMS[arm]
        try:
            args = cfg["args"](r, url(local(r.person)), url(local(r.garment)), r.duo)
            res = fal_client.subscribe(cfg["endpoint"], arguments=args)
            import requests
            u = (res.get("images") or [res.get("image", {})])[0]["url"]
            img = Image.open(io.BytesIO(requests.get(u).content)).convert("RGB")
        except Exception as e:
            print(f"  FAIL {arm} {r.id}: {str(e)[:150]}")
            return
        img.save(os.path.join(OUT, f"{arm}__{r.id}.png"))
        json.dump({"arm": arm, "id": r.id, "kind": r.kind, "category": r.category,
                   "target": r.target, "duo": bool(r.duo), "seed": SEED,
                   "endpoint": cfg["endpoint"], "size": img.size,
                   "person": r.person, "garment": r.garment},
                  open(os.path.join(OUT, f"{arm}__{r.id}.json"), "w"), indent=2)
        with _lock:
            _spent[0] += cfg["est_usd"]
        print(f"  ok {arm} {r.id} ({r.kind}) {img.size}")

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(one, todo))
    print(f"generation done — est ${_spent[0]:.2f}")


def garment_reference(path, duo):
    """A duo reference is a whole person: the garment lives in its torso crop.
    A product shot is already the garment."""
    im = Image.open(path).convert("RGB")
    return M._torso_crop(im) if duo else im


def score_all():
    import glob
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT, "*.png"))):
        m = json.load(open(f.replace(".png", ".json")))
        person = Image.open(local(m["person"])).convert("RGB")
        gref = garment_reference(local(m["garment"]), m["duo"])
        res = Image.open(f).convert("RGB")
        rows.append({
            "arm": m["arm"], "id": m["id"], "kind": m["kind"], "duo": m["duo"],
            "garment_sim": float(np.dot(M._embed(gref), M._embed(M._torso_crop(res)))),
            "identity_cos": M.identity_cosine(person, res),
            "pose_err": M.pose_error(person, res),
            "bg_psnr": M.background_psnr(person, res),
        })
    df = pd.DataFrame(rows)
    A = M.CV_ANCHORS
    W = {"garment_sim": 2.0, "identity_cos": 1.0, "pose_err": 1.0, "bg_psnr": 1.0}

    def comp(r):
        n = d = 0.0
        for k, w in W.items():
            if pd.isna(r[k]):
                continue
            lo, hi = A[k]
            n += w * min(1.0, max(0.0, (r[k] - lo) / (hi - lo)))
            d += w
        return round(n / d, 3) if d else None
    df["score"] = df.apply(comp, axis=1)
    df.to_csv(os.path.join(RUNS, "ts2_cv_metrics.csv"), index=False)
    print(f"deterministic: {len(df)} outputs -> ts2_cv_metrics.csv")
    print(df.groupby(["kind", "arm"]).score.mean().round(3).to_string())
    return df


# -- VLM (editing rubric; fidelity/realism buckets per SCORING_CRITERIA.md) ---
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["garment", "identity", "scene", "clean", "hands", "realism",
                       "wrong_person", "note"],
          "properties": {**{k: {"type": "integer", "minimum": 1, "maximum": 5} for k in
                            ("garment", "identity", "scene", "clean", "hands", "realism")},
                         "wrong_person": {"type": "boolean"},
                         "note": {"type": "string", "maxLength": 300}}}

PROMPT = """You are grading a virtual try-on result, blind to which model produced it.
IMAGE 1 = the person (the identity and scene that must be kept).
IMAGE 2 = the garment reference. {gnote}
IMAGE 3 = the result.
Target garment: {target}.

Score 1-5 (5 best):
- garment: is the target garment transferred faithfully (color, pattern, print, cut)?
- identity: is the IMAGE 1 person's face, hair and body unchanged?
- scene: is the IMAGE 1 background and framing preserved?
- clean: absence of seams, smears, warped fabric.
- hands: hands and arms correct and unmangled.
- realism: does it read as a real photograph?
Also set wrong_person = true if the result shows the person from IMAGE 2 instead of
the person from IMAGE 1 (identity substitution), otherwise false.
note: one sentence on the dominant failure or success.

Reply with ONLY a JSON object with keys:
garment, identity, scene, clean, hands, realism, wrong_person, note."""


def _b64(img):
    im = img.copy(); im.thumbnail((768, 768))
    b = io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def judge_all():
    from openai import OpenAI
    import glob, jsonschema
    prev_path = os.path.join(RUNS, "ts2_vlm.csv")
    prev = pd.read_csv(prev_path) if os.path.exists(prev_path) else pd.DataFrame()
    done = set(zip(prev.arm, prev.id)) if len(prev) else set()   # judging is paid: never re-judge
    jobs = [json.load(open(f.replace(".png", ".json"))) | {"_f": f}
            for f in sorted(glob.glob(os.path.join(OUT, "*.png")))]
    jobs = [m for m in jobs if (m["arm"], m["id"]) not in done]
    print(f"VLM: judging {len(jobs)} new outputs on {JUDGE_MODEL} ({len(done)} cached)")
    if not jobs:
        return prev
    client = OpenAI()

    def one(m):
        gnote = ("It is a photo of a DIFFERENT person wearing the target garment; only "
                 "the garment should be taken from it." if m["duo"] else
                 "It is a product photo of the garment.")
        msg = PROMPT.format(gnote=gnote, target=m["target"])
        imgs = [Image.open(local(m["person"])), Image.open(local(m["garment"])),
                Image.open(m["_f"])]
        for _ in range(3):
            r = client.responses.create(model=JUDGE_MODEL, input=[{"role": "user", "content":
                [{"type": "input_text", "text": msg}] +
                [{"type": "input_image", "image_url": _b64(i)} for i in imgs]}])
            t = r.output_text
            try:
                o = json.loads(t[t.index("{"):t.rindex("}") + 1])
                jsonschema.validate(o, SCHEMA)
                return {"arm": m["arm"], "id": m["id"], "kind": m["kind"],
                        "duo": m["duo"], **o}
            except Exception as e:
                msg = f"{msg}\n\nPrevious reply invalid ({str(e)[:100]}). JSON only."
        return {"arm": m["arm"], "id": m["id"], "kind": m["kind"], "duo": m["duo"]}

    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(one, jobs))
    df = pd.concat([prev, pd.DataFrame(rows)], ignore_index=True)
    df.to_csv(prev_path, index=False)
    print(f"VLM: {df.get('realism', pd.Series(dtype=float)).notna().sum()}/{len(df)} scored")
    return df


KIND_LABEL = {"product": "garment only",
              "duo_lookbook": "garment + human (lookbook)",
              "duo_swap": "garment + human (swap)"}
KIND_DESC = {"product": "flat-lay / ghost-mannequin garment reference — no person in image 2",
             "duo_lookbook": "editorial ON-MODEL reference: a model wearing the target garment",
             "duo_swap": "a people/ photo is the garment source — swap what person B wears onto person A"}
ARM_ROLE = {"fashn_v15": "dedicated try-on model (Apache 2.0)",
            "klein_4b_edit": "general multi-image editor (Apache 2.0)",
            "qwen_2511": "baseline — the model currently on the website (Apache 2.0)"}

FID = ["garment", "identity", "scene"]
REAL = ["clean", "hands", "realism"]


def boards():
    d = pd.read_csv(os.path.join(RUNS, "ts2_cv_metrics.csv"))
    v = pd.read_csv(os.path.join(RUNS, "ts2_vlm.csv"))
    v["fidelity"] = v[FID].mean(axis=1)
    v["realism_ax"] = v[REAL].mean(axis=1)
    overall = (v.groupby("arm")[FID + REAL + ["fidelity", "realism_ax"]].mean()
               .join(d.groupby("arm")[["garment_sim", "identity_cos", "bg_psnr", "score"]].mean())
               .round(3).sort_values("fidelity", ascending=False))
    overall["wrong_person"] = v.groupby("arm").wrong_person.mean().round(2)
    bykind = (v.groupby(["kind", "arm"])[["fidelity", "realism_ax"]].mean()
              .join(d.groupby(["kind", "arm"])[["garment_sim", "score"]].mean()).round(3))
    return overall, bykind, d, v


def html():
    overall, bykind, d, v = boards()
    df = matrix_df().set_index("id")
    arms = list(overall.index)
    sets = []
    for pid, r in df.iterrows():
        items = [{"label": "PERSON (image 1)", "src": f"{RUNS_REL}/inputs/{os.path.basename(local(r.person))}",
                  "sub": f"{KIND_LABEL[r.kind]} — {KIND_DESC[r.kind]}", "gate": None},
                 {"label": "GARMENT REF (image 2)", "src": f"{RUNS_REL}/inputs/{os.path.basename(local(r.garment))}",
                  "sub": f"target: {r.target}" + ("  ·  worn by another person (duo)" if r.duo else "  ·  product shot"),
                  "gate": None}]
        for a in arms:
            f = os.path.join(OUT, f"{a}__{pid}.png")
            if not os.path.exists(f):
                continue
            dm = d[(d.arm == a) & (d.id == pid)]
            vm = v[(v.arm == a) & (v.id == pid)]
            sub, wrong = [], False
            if len(vm):
                sub += [f"fidelity {vm[FID].mean(axis=1).iloc[0]:.2f}",
                        f"realism {vm[REAL].mean(axis=1).iloc[0]:.2f}",
                        f"garment {vm.garment.iloc[0]}", f"identity {vm.identity.iloc[0]}"]
                wrong = bool(vm.wrong_person.iloc[0])
            if len(dm):
                sub += [f"det {dm.score.iloc[0]:.3f}", f"gsim {dm.garment_sim.iloc[0]:.3f}",
                        f"id {dm.identity_cos.iloc[0]:.3f}"]
            items.append({"label": a + ("   [WRONG PERSON]" if wrong else ""),
                          "src": f"{RUNS_REL}/outputs/{a}__{pid}.png",
                          "sub": " · ".join(sub), "gate": (not wrong) if len(vm) else None})
        sets.append({"pair": f"{pid} · {KIND_LABEL[r.kind]}", "items": items})

    def tbl(dfx, first):
        head = "".join(f"<th>{c}</th>" for c in [first] + list(dfx.columns))
        body = "".join("<tr><td class='n'>" + (" · ".join(map(str, i)) if isinstance(i, tuple) else str(i))
                       + "</td>" + "".join(f"<td>{'' if pd.isna(x) else (f'{x:.3f}' if isinstance(x, float) else x)}</td>"
                                           for x in row) + "</tr>"
                       for i, row in dfx.iterrows())
        return f"<div class='tw'><table><tr>{head}</tr>{body}</table></div>"

    counts = matrix_df().groupby("kind").size().to_dict()
    kindrows = "".join(
        f'<div class="kind"><span class="n-pill">{counts.get(k, 0)}</span>'
        f'<span class="kname">{KIND_LABEL[k]}</span>'
        f'<span class="kdesc">{KIND_DESC[k]}</span></div>'
        for k in ("product", "duo_lookbook", "duo_swap"))
    _top = overall.index[0]
    armrows = "".join(
        f'<div class="armr"><span class="badge {"lead" if a == _top else ("base" if a == "qwen_2511" else "")}">'
        f'{"leads fidelity" if a == _top else ("baseline" if a == "qwen_2511" else "tested")}</span>'
        f'<span class="kname">{a}</span><span class="arole">{ARM_ROLE.get(a, "")}</span></div>'
        for a in arms)
    page = f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Testset2 — Editing Models</title><style>
:root{{--bg:#14141d;--card:#1b1b26;--card2:#20202c;--line:#2b2b3a;--ink:#f3f3f7;
--body:#aab0be;--mut:#868da0;--acc:#928af5;--acc2:#b7b1fa;--ok:rgba(90,200,140,.14);
--bad:rgba(230,110,110,.12);--okb:rgba(90,200,140,.65);--badb:rgba(230,110,110,.6)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--body);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1600px;margin:0 auto;padding:30px 28px 60px}}
h1{{font-size:29px;margin:2px 0 6px;color:var(--ink);font-weight:700;letter-spacing:-.4px}}
h2{{font-size:19px;margin:34px 0 8px;color:var(--ink);font-weight:700}}
.kick{{color:var(--mut);font-size:13.5px}}p{{max-width:1000px}}b{{color:var(--ink)}}
.mut{{color:var(--mut);font-size:12.5px}}
table{{border-collapse:collapse;margin:10px 0;width:100%;font-variant-numeric:tabular-nums}}
th,td{{border-bottom:1px solid var(--line);padding:6px 9px;font-size:12.5px;text-align:right}}
th{{color:var(--mut);font-weight:600;text-transform:uppercase;font-size:10.5px;letter-spacing:.5px}}
td.n,th:first-child{{text-align:left}}td.n{{color:var(--ink);font-weight:600;white-space:nowrap}}
.tw{{overflow-x:auto}}
.meta{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0 4px}}
@media(max-width:1100px){{.meta{{grid-template-columns:1fr}}}}
.mcard{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.mh{{font-size:10.5px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
color:var(--acc);margin-bottom:6px}}
.mt{{font-size:17px;font-weight:700;color:var(--ink);margin-bottom:6px}}
.mp{{font-size:12.5px;color:var(--mut);margin:8px 0 0;max-width:none}}
.kinds,.arms{{display:flex;flex-direction:column;gap:7px;margin-top:10px}}
.kind,.armr{{display:flex;gap:10px;align-items:baseline;font-size:12.5px}}
.n-pill{{flex:0 0 auto;background:var(--card2);border:1px solid var(--line);border-radius:99px;
padding:1px 9px;font-size:11px;color:var(--acc2);font-weight:700;font-variant-numeric:tabular-nums}}
.kname{{color:var(--ink);font-weight:600;flex:0 0 auto}}
.kdesc{{color:var(--mut)}}
.arole{{color:var(--mut)}}
.badge{{flex:0 0 auto;font-size:9.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
padding:2px 7px;border-radius:99px;background:var(--card2);border:1px solid var(--line);color:var(--body)}}
.badge.lead{{background:var(--ok);border-color:var(--okb);color:#7fe3ac}}
.badge.base{{background:rgba(146,138,245,.14);border-color:var(--acc);color:var(--acc2)}}
#v{{margin:14px 0 0;background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 18px 18px;position:sticky;top:0;z-index:5}}
.vbar{{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px}}
.vlabel{{font-size:20px;font-weight:700;color:var(--ink);letter-spacing:-.2px}}
.vlabel.before{{color:var(--acc2)}}
.pill{{font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
padding:2px 8px;border-radius:99px}}
.pill.pass{{background:var(--ok);color:#7fe3ac;border:1px solid var(--okb)}}
.pill.fail{{background:var(--bad);color:#ff9d9d;border:1px solid var(--badb)}}
.vsub{{color:var(--mut);font-size:13px;font-variant-numeric:tabular-nums}}
.vpos{{margin-left:auto;color:var(--mut);font-size:12.5px;font-family:ui-monospace,Menlo,monospace}}
#stage{{background:#0d0d14;border-radius:10px;display:flex;align-items:center;
justify-content:center;overflow:auto;height:74vh;min-height:420px}}
#stage img{{display:block;max-width:100%;max-height:74vh;object-fit:contain;cursor:zoom-in}}
#stage.zoom{{align-items:flex-start;justify-content:flex-start}}
#stage.zoom img{{max-width:none;max-height:none;cursor:zoom-out}}
.keys{{margin-top:10px;color:var(--mut);font-size:12.5px}}
kbd{{background:var(--card2);border:1px solid var(--line);border-bottom-width:2px;
border-radius:4px;padding:1px 6px;font-size:11.5px;color:var(--body)}}
.strip{{display:flex;gap:8px;overflow-x:auto;margin-top:12px;padding-bottom:4px}}
.strip figure{{margin:0;flex:0 0 auto;width:104px;text-align:center;cursor:pointer;opacity:.5}}
.strip figure.on{{opacity:1}}
.strip img{{width:100%;height:104px;object-fit:cover;border-radius:6px;
border:2px solid transparent;background:var(--card2);display:block}}
.strip figure.on img{{border-color:var(--acc)}}
.strip figure.fail img{{border-color:var(--badb)}}
.strip figcaption{{font-size:10px;color:var(--mut);margin-top:4px;line-height:1.3;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pairs{{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}}
.pairs button{{border:1px solid var(--line);background:var(--card2);color:var(--body);
border-radius:6px;padding:5px 12px;font-size:12px;cursor:pointer;
font-family:ui-monospace,Menlo,monospace}}
.pairs button.on{{background:var(--acc);color:#14141d;border-color:var(--acc);font-weight:700}}
footer{{margin:40px 0 8px;padding-top:14px;border-top:1px solid var(--line);
color:var(--mut);font-size:12.5px}}
</style><div class="wrap">
<div class="kick">Virtual try-on V2 — Testset2 (high-res), editing models</div>
<h1>Editing Models on Testset2</h1>
<div class="meta">
  <div class="mcard">
    <div class="mh">Test set</div>
    <div class="mt">Testset2 &mdash; high resolution</div>
    <p class="mp">Full-resolution originals (up to 5152&times;7728, capped to 1536 on
    the long side for upload). Replaces test_set/, which was normalized to 1024px and
    too soft for identity metrics. Two non-celebrity controls guard against celebrity
    memorization inflating identity scores.</p>
    <div class="kinds">{kindrows}</div>
  </div>
  <div class="mcard">
    <div class="mh">Models under test &mdash; editing bucket</div>
    <div class="arms">{armrows}</div>
    <p class="mp">Editing models take <b>person + garment</b> and are scored on
    <b>fidelity</b> first (garment, identity, scene). The realism axis is repaired by a
    separate auxiliary model &mdash; current auxiliary leader
    <code>seedvr2_x2_noise0</code>, screened separately in
    <code>v2/runs/v21_aux_screen.html</code> and not part of this page.</p>
  </div>
</div>
<div id="v">
<div class="vbar"><span class="vlabel" id="vl"></span><span id="vp"></span>
<span class="vsub" id="vs"></span><span class="vpos" id="vpos"></span></div>
<div id="stage"><img id="vi"></div>
<div class="keys"><kbd>&larr;</kbd><kbd>&rarr;</kbd> step through this set &middot;
<kbd>&uarr;</kbd><kbd>&darr;</kbd> previous / next pair &middot;
<kbd>B</kbd> hold to flip back to the person input &middot; <kbd>Z</kbd> or click to zoom 1:1 &middot;
<kbd>O</kbd> open full size</div>
<div class="strip" id="strip"></div>
<div class="pairs" id="pairs"></div>
</div>
<p>Each set starts with the two inputs (person, garment reference) and then every
arm's result. <b>duo</b> pairs use a garment reference that is itself a photo of a
different person wearing the garment &mdash; the model2model case that open models
historically collapse on. A red border and <b>[WRONG PERSON]</b> mark identity
substitution (the result shows the reference's person).</p>
<h2>Overall by arm</h2>
{tbl(overall, 'arm')}
<h2>By pair kind</h2>
{tbl(bykind, 'kind · arm')}
<p class="mut">VLM 1&ndash;5 blind gpt-5.5; fidelity = mean(garment, identity, scene),
realism = mean(clean, hands, realism); wrong_person = share of outputs showing the
reference's person. Deterministic: garment_sim = FashionSigLIP (duo references use
their torso crop as the garment), identity = AuraFace, score = anchored composite
(garment &times;2).</p>
<footer>Generated by v2/build/ts2_harness.py. Images live in v2/runs/ts2/; open from v2/artifacts/.</footer></div>
<script>
const SETS={json.dumps(sets)};
let S=0,I=0,ZOOM=false,PEEK=false;
const el=id=>document.getElementById(id);
const strip=el("strip"),pairs=el("pairs");
SETS.forEach((s,i)=>{{const b=document.createElement("button");b.textContent=s.pair;
b.onclick=()=>{{S=i;I=0;build();render()}};pairs.appendChild(b)}});
function build(){{strip.innerHTML="";SETS[S].items.forEach((it,i)=>{{
const f=document.createElement("figure");f.className=(it.gate===false?"fail":"");
f.innerHTML='<img src="'+it.src+'"><figcaption>'+it.label+'</figcaption>';
f.onclick=()=>{{I=i;render()}};strip.appendChild(f)}})}}
function render(){{const set=SETS[S];const it=set.items[PEEK?0:I];
el("vi").src=it.src;
el("vl").textContent=it.label;el("vl").className="vlabel"+((I<2||PEEK)?" before":"");
el("vs").textContent=it.sub;
el("vp").innerHTML=it.gate===false?'<span class="pill fail">wrong person</span>':
(it.gate===true?'<span class="pill pass">right person</span>':"");
el("vpos").textContent=set.pair+"   "+(I+1)+"/"+set.items.length+
"   set "+(S+1)+"/"+SETS.length+(PEEK?"   [PERSON INPUT]":"");
[...strip.children].forEach((c,i)=>c.classList.toggle("on",i===I));
[...pairs.children].forEach((c,i)=>c.classList.toggle("on",i===S));
const nx=SETS[(S+1)%SETS.length];nx.items.forEach(x=>{{(new Image()).src=x.src}});}}
el("stage").onclick=()=>{{ZOOM=!ZOOM;el("stage").classList.toggle("zoom",ZOOM)}};
document.addEventListener("keydown",e=>{{const n=SETS[S].items.length;
if(e.key==="ArrowRight"){{I=(I+1)%n;render();e.preventDefault()}}
else if(e.key==="ArrowLeft"){{I=(I+n-1)%n;render();e.preventDefault()}}
else if(e.key==="ArrowDown"){{S=(S+1)%SETS.length;I=0;build();render();e.preventDefault()}}
else if(e.key==="ArrowUp"){{S=(S+SETS.length-1)%SETS.length;I=0;build();render();e.preventDefault()}}
else if(e.key==="b"||e.key==="B"){{if(!PEEK){{PEEK=true;render()}}}}
else if(e.key==="z"||e.key==="Z"){{ZOOM=!ZOOM;el("stage").classList.toggle("zoom",ZOOM)}}
else if(e.key==="o"||e.key==="O"){{window.open(SETS[S].items[I].src,"_blank")}}}});
document.addEventListener("keyup",e=>{{if((e.key==="b"||e.key==="B")&&PEEK){{PEEK=false;render()}}}});
build();render();
</script>"""
    os.makedirs(ART, exist_ok=True)
    out = os.path.join(ART, "v20_arms_ts2.html")
    open(out, "w").write(page)
    print(f"wrote {out} ({len(page)//1024}KB, {len(sets)} sets)")
    print(overall.to_string())
    print()
    print(bykind.to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", action="store_true")
    ap.add_argument("--generate", action="store_true", help="paid")
    ap.add_argument("--arms", default="fashn_v15,klein_4b_edit,qwen_2511")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--judge", action="store_true", help="paid")
    ap.add_argument("--html", action="store_true")
    a = ap.parse_args()
    os.makedirs(RUNS, exist_ok=True)
    if a.prep:
        prep()
    if a.generate:
        generate(a.arms.split(","))
    if a.score:
        score_all()
    if a.judge:
        judge_all()
    if a.html:
        html()
