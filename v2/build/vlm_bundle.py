# Pack everything the Colab VLM evaluation needs into one zip.
#
# The notebook must be self-contained: v2/runs/ is gitignored and ~1GB, so cloning
# the repo in Colab would not bring the images. 27MB uploads in seconds.
import csv, json, os, zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v2", "runs", "vlm_eval_bundle.zip")


def build():
    run = json.load(open(f"{REPO}/v2/runs/amt/_run.json"))
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(f"{REPO}/v2/runs/crop_screen/crop_log.csv"))}
    rows = list(csv.DictReader(open(f"{REPO}/v223_perfect_tier_picks.csv")))

    manifest, seen = [], {}
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for r in rows:
            key = f'{r["set_id"]}|{r["arm"]}'
            gen = run["gen"].get(key)
            if not gen:
                continue
            src = os.path.join(REPO, "v2", "runs", "amt", "gen", gen)
            if not os.path.exists(src):
                continue
            z.write(src, f"outputs/{gen}")

            # Both source images travel. The garment reference is the only way to
            # catch a wrong-garment error; the person photo is the only way to catch
            # a no-op, which is a perfectly coherent photograph of the wrong thing
            # and therefore invisible to any prompt that sees the output alone.
            def stash(stem, folder):
                sp = meta.get(stem)
                if not sp or not os.path.exists(sp):
                    return ""
                rel = f"{folder}/" + os.path.basename(sp)
                if rel not in seen:
                    z.write(sp, rel)
                    seen[rel] = 1
                return rel

            manifest.append({"set_id": r["set_id"], "arm": r["arm"],
                             "tier": r["tier"], "condition": r["condition"],
                             "output": f"outputs/{gen}",
                             "garment_ref": stash(r["garment"], "refs"),
                             "person_ref": stash(r["person"], "person"),
                             "hair_over_garment": r["hair_over_garment"],
                             "det_gate_score": r["gate_score"]})

        COLS = ("set_id", "arm", "tier", "condition", "output", "garment_ref",
                "person_ref", "hair_over_garment", "det_gate_score")
        buf = [",".join(COLS)]
        for m in manifest:
            buf.append(",".join('"' + str(m[k]).replace('"', '""') + '"' for k in COLS))
        z.writestr("manifest.csv", "\n".join(buf))
    return OUT, len(manifest), len(seen), os.path.getsize(OUT)


if __name__ == "__main__":
    p, n, r, s = build()
    print(f"{p}\n  {n} outputs, {r} garment refs, {s/1048576:.1f} MB")
