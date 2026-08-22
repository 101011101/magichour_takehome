# Pack what the parity notebook needs: the inputs, the stored fal outputs to compare
# against, and a manifest. Small deliberately -- parity is about whether conclusions
# survive a change of host, which 8 well-chosen pairs answer as well as 38.
import csv, json, os, zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v2", "runs", "parity_bundle.zip")

# Chosen to span the interesting cases rather than sampled at random:
#   two the harness ships from PHEAD, two from BC_klein, two escalations to QX,
#   the frame the identity check saved, and the worst hair-damage reference.
PAIRS = ["ts2_11", "p019+p010", "HD_p019", "HD_p028",
         "HD_p023", "p018+p016", "HD_p028+dualuse_navy_peacoat_onmodel", "HD_p021"]


def build():
    run = json.load(open(f"{REPO}/v2/runs/amt/_run.json"))
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(f"{REPO}/v2/runs/crop_screen/crop_log.csv"))}
    T = {(r["set_id"], r["arm"]): r for r in csv.DictReader(
        open(f"{REPO}/v223_perfect_tier_picks.csv"))}
    sets = {r["set_id"]: r for r in T.values()}
    real = json.load(open(f"{REPO}/v2/runs/realism/_realism.json"))

    import sys
    sys.path.insert(0, os.path.join(REPO, "v2"))
    from pipeline import arms

    rows, seen = [], set()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        def add(path, rel):
            if rel not in seen and path and os.path.exists(path):
                z.write(path, rel); seen.add(rel)
            return rel if path and os.path.exists(path) else ""

        for sid in PAIRS:
            if sid not in sets:
                continue
            s = sets[sid]
            person = add(os.path.join(REPO, meta[s["person"]]),
                         f"person/{os.path.basename(meta[s['person']])}")
            for arm in ("PHEAD", "BC_klein", "QX_qwen_p1"):
                ref = arms.reference(arm, s["garment"])
                refr = add(ref, f"refs/{arm}/{os.path.basename(ref)}") if ref else ""
                gen = run["gen"].get(f"{sid}|{arm}")
                falo = add(os.path.join(REPO, "v2/runs/amt/gen", gen),
                           f"fal_outputs/{gen}") if gen else ""
                rows.append(dict(set_id=sid, arm=arm, person=person,
                                 garment_ref=refr, fal_output=falo,
                                 human_tier=T[(sid, arm)]["tier"],
                                 shipped=int(real.get(sid, {}).get("arm") == arm)))
            # the realism pair, for SeedVR2 parity
            if sid in real:
                add(real[sid]["src"], f"realism_in/{os.path.basename(real[sid]['src'])}")
                add(os.path.join(REPO, real[sid]["after"]),
                    f"realism_fal/{os.path.basename(real[sid]['after'])}")

        COLS = ("set_id", "arm", "person", "garment_ref", "fal_output",
                "human_tier", "shipped")
        z.writestr("manifest.csv", "\n".join(
            [",".join(COLS)] + [",".join('"' + str(r[c]).replace('"', '""') + '"'
                                         for c in COLS) for r in rows]))
    return OUT, len(rows), len(seen), os.path.getsize(OUT)


if __name__ == "__main__":
    p, n, f, s = build()
    print(f"{p}\n  {n} rows, {f} files, {s/1048576:.1f} MB")
