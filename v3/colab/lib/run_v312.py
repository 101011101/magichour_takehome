"""v3.12 - what a region request actually does to a garment photograph with no person in it.

v3.11 measured the detector and stopped there: Pose reports a hip on 6 of 10 flat-lay and
ghost-mannequin photographs, which contain no person at all. The reading that invites is
"so it works on the other 4", and that is backwards. Neither group produces a correct region
reference:

  hip reported   the band cuts at a row the detector invented on an image with no body in it,
                 and the run says nothing is wrong - a silent error
  no hip         the request falls back to `full` and records why, so the user gets the whole
                 outfit swapped instead of the half they asked for - a visible no-op

This module generates the outcome so the distinction can be looked at rather than argued. It
adds nothing to the pipeline: the plan is the shipping path (`full` under ER, `upper`/`lower`
under the region-named call 2) and every stage is `run_v311`'s, unchanged. What is new is the
hip line drawn on the photograph, so a reader can see where the cut would land.

  import run_v312 as V; V.main("v312_set.csv", gpu_usd_per_hour=0.689)
"""
import json
import os

import cv2
import numpy as np

import run_v311 as V311

OUT = V311.OUT
# The shipping path only. Arm B and the static call 2 are v3.11's business; repeating them here
# would double the cost and answer a question that is already answered.
PLAN = (("A", "full", "S"), ("A", "upper", "R"), ("A", "lower", "R"))
LINE = (64, 68, 255)        # BGR - the cut, in red
TEXT = (255, 255, 255)


def d(*p):
    return V311.d(*p)


def hip_overlay(bgr, y, label):
    """The photograph with the row the band would cut at drawn across it."""
    im = bgr.copy()
    h, w = im.shape[:2]
    if y is not None:
        row = int(round(max(0, min(h - 1, y))))
        cv2.line(im, (0, row), (w, row), LINE, max(2, h // 260))
        cv2.rectangle(im, (0, max(0, row - 26)), (min(w, 320), row - 2), (0, 0, 0), -1)
        cv2.putText(im, label, (6, row - 8), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, TEXT, 1, cv2.LINE_AA)
    else:
        cv2.rectangle(im, (0, 0), (min(w, 420), 30), (0, 0, 0), -1)
        cv2.putText(im, label, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT, 1, cv2.LINE_AA)
    return im


def overlays(garments):
    """Draw the hip line on each garment's bald frame and on the photograph itself.

    The hip is read from the BALD frame, because that is the image `references` reads it from;
    the bald pass resizes back to its source, so the same row is the same place in both.
    """
    rec = {}
    for g in sorted(garments):
        bald_p = d("refs", f"{g}__bald_A.jpg")
        orig_p = d("in1mp", f"{g}.jpg")
        bald, orig = cv2.imread(bald_p), cv2.imread(orig_p)
        if bald is None or orig is None:
            raise ValueError(f"missing {bald_p} or {orig_p} - run the pipeline first")
        y, why = V311.hip_line(bald)
        frac = None if y is None else round(y / bald.shape[0], 3)
        label = (f"hip reported at row {int(round(y))} ({frac:.2f} of height)"
                 if y is not None else f"no hip: {why}")
        for name, src in (("orig", orig), ("bald", bald)):
            cv2.imwrite(d("hip", f"{g}__{name}.jpg"), hip_overlay(src, y, label), V311.JPG)
        rec[g] = {"hip_reported": y is not None, "hip_y": None if y is None else round(y, 1),
                  "hip_frac": frac, "why": why, "size": [bald.shape[1], bald.shape[0]]}
        print(f"  {g:6s} {'HIP REPORTED' if y is not None else 'no hip':14s} "
              f"{'' if frac is None else f'{frac:.2f} of height'}{why}")
    return rec


def summarise(rows, rec):
    """Join the detector's answer to what each region request actually did."""
    meta = json.load(open(d("meta", "v311_meta.json")))
    out = {}
    for g, info in rec.items():
        entry = dict(info, regions={})
        for region in ("full", "upper", "lower"):
            i = meta.get("garments", {}).get(g, {}).get(f"A_{region}", {})
            entry["regions"][region] = {
                "route": ("cut at the reported hip" if region != "full" and not i.get("fallback")
                          else "fell back to full" if i.get("fallback") else "whole outfit"),
                "fallback": i.get("fallback", ""),
                "kept_fraction": i.get("kept_fraction"),
                "size": i.get("size"),
            }
        out[g] = entry
    cut = sum(1 for g in out.values()
              if g["regions"]["upper"]["route"] == "cut at the reported hip")
    fell = len(out) - cut
    doc = {"garments": out, "counts": {"garments": len(out), "cut_at_reported_hip": cut,
                                       "fell_back_to_full": fell},
           "cells": len(rows), "plan": [list(p) for p in PLAN]}
    json.dump(doc, open(d("meta", "v312_flatlay.json"), "w"), indent=1)
    print(f"\n{cut} of {len(out)} garments cut at a hip the detector reported on a photograph "
          f"with no person in it;\n{fell} fell back to the whole outfit. Neither is the region "
          "the user asked for.")
    return doc


def main(matrix="v312_set.csv", plan=PLAN, gpu_usd_per_hour=None, limit=None):
    import csv
    V311.main(matrix, plan=plan, gpu_usd_per_hour=gpu_usd_per_hour, limit=limit)
    rows = list(csv.DictReader(open(matrix)))
    if limit:
        rows = rows[:int(limit)]
    garments = {r["garment"] for r in rows}
    print("\nthe hip line, drawn:")
    return summarise(rows, overlays(garments))
