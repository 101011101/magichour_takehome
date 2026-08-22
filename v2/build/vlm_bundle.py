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

            # the garment reference travels too, so a prompt can be tested both
            # blind (output only, which is what VLM-A sees in production) and
            # garment-aware (which is the only way to catch a wrong-garment error)
            ref = ""
            p = meta.get(r["garment"])
            if p and os.path.exists(p):
                ref = "refs/" + os.path.basename(p)
                if ref not in seen:
                    z.write(p, ref)
                    seen[ref] = 1

            manifest.append({"set_id": r["set_id"], "arm": r["arm"],
                             "tier": r["tier"], "condition": r["condition"],
                             "output": f"outputs/{gen}", "garment_ref": ref,
                             "hair_over_garment": r["hair_over_garment"],
                             "det_gate_score": r["gate_score"]})

        buf = ["set_id,arm,tier,condition,output,garment_ref,hair_over_garment,det_gate_score"]
        for m in manifest:
            buf.append(",".join('"' + str(m[k]).replace('"', '""') + '"' for k in
                                ("set_id", "arm", "tier", "condition", "output",
                                 "garment_ref", "hair_over_garment", "det_gate_score")))
        z.writestr("manifest.csv", "\n".join(buf))
    return OUT, len(manifest), len(seen), os.path.getsize(OUT)


if __name__ == "__main__":
    p, n, r, s = build()
    print(f"{p}\n  {n} outputs, {r} garment refs, {s/1048576:.1f} MB")
