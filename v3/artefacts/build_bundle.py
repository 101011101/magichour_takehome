"""Build the v3 evidence bundle: for each of the 4 sets where BC_klein failed and QX
rescued it, copy the inputs, references and outputs into v3/artefacts/cases/<set_id>/
under canonical names, compute SSIM / white-fraction / skin-fraction metrics, and write
v3/artefacts/manifest.json. Reads only; safe to re-run."""

import json
import shutil
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "v3" / "artefacts"
CASES = OUT / "cases"

ARMS = ["BC_klein", "PHEAD", "QX_qwen_p1", "control"]

SETS = [
    {
        "set_id": "p015+p007",
        "person_stem": "p015",
        "garment_stem": "p007",
        "tiers": {"BC_klein": "fail", "PHEAD": "perfect", "QX_qwen_p1": "perfect"},
    },
    {
        "set_id": "dualuse_navy_peacoat_onmodel+p012",
        "person_stem": "dualuse_navy_peacoat_onmodel",
        "garment_stem": "p012",
        "tiers": {"BC_klein": "fail", "PHEAD": "fail", "QX_qwen_p1": "perfect"},
    },
    {
        "set_id": "HD_p023",
        "person_stem": "dualuse_lp_floral_kimono_set",
        "garment_stem": "p023",
        "tiers": {"BC_klein": "fail", "PHEAD": "fail", "QX_qwen_p1": "perfect"},
    },
    {
        "set_id": "HD_p023+p019",
        "person_stem": "p019",
        "garment_stem": "p023",
        "tiers": {"BC_klein": "fail", "PHEAD": "fail", "QX_qwen_p1": "ok"},
    },
]

SSIM_SIZE = (512, 768)  # w, h
C1 = (0.01 * 255) ** 2
C2 = (0.03 * 255) ** 2


def src_path_map():
    """stem -> src_path, from the crop screen log."""
    import csv

    m = {}
    with open(REPO / "v2/runs/crop_screen/crop_log.csv", newline="") as fh:
        for row in csv.DictReader(fh):
            m.setdefault(row["stem"], row["src_path"])
    return m


def ssim(a_path, b_path):
    a = cv2.imread(str(a_path), cv2.IMREAD_GRAYSCALE)
    b = cv2.imread(str(b_path), cv2.IMREAD_GRAYSCALE)
    if a is None or b is None:
        return None
    a = cv2.resize(a, SSIM_SIZE, interpolation=cv2.INTER_AREA).astype(np.float64)
    b = cv2.resize(b, SSIM_SIZE, interpolation=cv2.INTER_AREA).astype(np.float64)
    blur = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    mu_a, mu_b = blur(a), blur(b)
    saa = blur(a * a) - mu_a * mu_a
    sbb = blur(b * b) - mu_b * mu_b
    sab = blur(a * b) - mu_a * mu_b
    num = (2 * mu_a * mu_b + C1) * (2 * sab + C2)
    den = (mu_a**2 + mu_b**2 + C1) * (saa + sbb + C2)
    return float(np.mean(num / den))


def ref_stats(path):
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        return None
    white = np.all(img > 245, axis=2)
    n = img.shape[0] * img.shape[1]
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    cr, cb = ycrcb[:, :, 1], ycrcb[:, :, 2]
    skin = (cr >= 133) & (cr <= 173) & (cb >= 77) & (cb <= 127)
    nonwhite = ~white
    nw = int(nonwhite.sum())
    return {
        "white_frac": round(float(white.sum()) / n, 6),
        "skin_frac": round(float((skin & nonwhite).sum()) / nw, 6) if nw else None,
    }


def dims(path):
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return None if img is None else [int(img.shape[1]), int(img.shape[0])]


def main():
    srcs = src_path_map()
    CASES.mkdir(parents=True, exist_ok=True)
    source_paths = {}
    out_cases = []

    for spec in SETS:
        sid, pstem, gstem = spec["set_id"], spec["person_stem"], spec["garment_stem"]
        cdir = CASES / sid
        cdir.mkdir(parents=True, exist_ok=True)

        plan = {
            "01_person.jpg": srcs.get(pstem),
            "02_garment_src.jpg": srcs.get(gstem),
            "03_bald_call1.jpg": f"v2/runs/phase3/{gstem}__PRE2raw.jpg",
            "04_ref_BC_klein.jpg": f"v2/runs/amt/{gstem}__BC_klein.jpg",
            "05_ref_PHEAD.jpg": f"v2/runs/amt/{gstem}__PHEAD.jpg",
            "06_ref_QX.jpg": f"v2/runs/acab/{gstem}__QX_qwen_p1.jpg",
            "07_ref_control.jpg": f"v2/runs/amt/{gstem}__control.jpg",
            "10_out_BC_klein.jpg": f"v2/runs/amt/gen/{sid}__BC_klein.jpg",
            "11_out_PHEAD.jpg": f"v2/runs/amt/gen/{sid}__PHEAD.jpg",
            "12_out_QX.jpg": f"v2/runs/amt/gen/{sid}__QX_qwen_p1.jpg",
            "13_out_control.jpg": f"v2/runs/amt/gen/{sid}__control.jpg",
        }

        missing, paths = [], {}
        for name, rel in plan.items():
            dst = cdir / name
            if rel is None or not (REPO / rel).is_file():
                missing.append({"canonical": name, "expected_src": rel})
                if dst.exists():
                    dst.unlink()  # idempotent: drop stale copy
                continue
            shutil.copyfile(REPO / rel, dst)
            rel_dst = f"v3/artefacts/cases/{sid}/{name}"
            paths[name] = rel_dst
            source_paths[rel_dst] = rel

        person = cdir / "01_person.jpg"
        ssim_out = {}
        for arm, fname in zip(ARMS, ["10_out_BC_klein.jpg", "11_out_PHEAD.jpg",
                                     "12_out_QX.jpg", "13_out_control.jpg"]):
            f = cdir / fname
            ssim_out[arm] = ssim(f, person) if f.exists() and person.exists() else None

        refs = {}
        for arm, fname in zip(ARMS, ["04_ref_BC_klein.jpg", "05_ref_PHEAD.jpg",
                                     "06_ref_QX.jpg", "07_ref_control.jpg"]):
            f = cdir / fname
            refs[arm] = ref_stats(f) if f.exists() else None

        out_cases.append({
            "set_id": sid,
            "person_stem": pstem,
            "garment_stem": gstem,
            "human_tiers": spec["tiers"],
            "paths": paths,
            "missing": missing,
            "metrics": {
                "ssim_out_vs_person": {k: (round(v, 6) if v is not None else None)
                                       for k, v in ssim_out.items()},
                "reference_stats": refs,
                "dims": {n: dims(cdir / n) for n in plan if (cdir / n).exists()},
            },
        })

    manifest = {
        "description": "BC_klein failures rescued by QX: inputs, references, outputs, metrics.",
        "ssim_params": {"resize_wh": list(SSIM_SIZE), "gaussian": [11, 11],
                        "sigma": 1.5, "C1": C1, "C2": C2, "colorspace": "grayscale"},
        "reference_stat_params": {"white": "all channels > 245",
                                  "skin_ycrcb": {"cr": [133, 173], "cb": [77, 127]},
                                  "skin_frac_denominator": "non-white pixels"},
        "cases": out_cases,
        "source_paths": source_paths,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {OUT / 'manifest.json'}")


if __name__ == "__main__":
    main()
