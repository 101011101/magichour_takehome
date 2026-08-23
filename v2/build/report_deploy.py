# Make v2/report/ a standalone site: pull in the linked evidence pages and rewrite
# every image path to a local copy, so nothing points at the gitignored v2/runs/.
#
# Without this the report deploys but its nine "evidence:" links 404 -- which is the
# worst outcome, because the links are the part that makes the claims checkable.
import os, re, shutil

import report_assets as A

REPO, OUT = A.REPO, A.OUT
ART = os.path.join(REPO, "v2", "artifacts")
PAGES = ["progression_grid.html", "v20_arms_ts2.html", "v20_klein_variant.html",
         "v221_attention_mod.html", "v221_review.html", "v223_harness_picks.html",
         "v223_realism_pass.html", "v223_self_hosted_parity.html",
         "v223_vlm_eval.html"]
# Match ANY relative image path anywhere in the file, not just src= attributes.
# Three of these pages build their paths in JavaScript from an embedded data blob
# (src="'+it.src+'"), so an attribute-only regex silently rewrote nothing and the
# page deployed with every image broken.
PATHY = re.compile(r"""((?:\.\./|\./)?[\w./+-]+?\.(?:jpg|jpeg|png))""", re.I)


VERCEL_JSON = """{
  "cleanUrls": true,
  "headers": [
    {
      "source": "/img/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
      ]
    }
  ]
}
"""


def build(maxw=900):
    os.makedirs(OUT, exist_ok=True)
    # written here rather than by hand: v2/report/ is gitignored and rebuilt from
    # scratch, so anything not generated is lost on the next build
    open(os.path.join(OUT, "vercel.json"), "w").write(VERCEL_JSON)
    stats = []
    for page in PAGES:
        p = os.path.join(ART, page)
        if not os.path.exists(p):
            stats.append((page, 0, 0, "missing"))
            continue
        s = open(p, encoding="utf-8").read()
        hit = miss = 0
        seen = {}

        def repl(m):
            nonlocal hit, miss
            rel = m.group(1)
            if rel.startswith(("http", "data:", "img/")) or rel in seen:
                return seen.get(rel, m.group(0))
            src = os.path.normpath(os.path.join(ART, rel))
            if not os.path.exists(src):
                miss += 1
                seen[rel] = m.group(0)
                return m.group(0)
            new = A.asset(src, maxw)
            hit += 1
            seen[rel] = new
            return new

        s = PATHY.sub(repl, s)
        # relative doc links between artifact pages keep working; anything pointing
        # outside the report folder is neutered rather than left to 404
        s = re.sub(r"""(href\s*=\s*)(['"])\.\./\.\./([^'"]+)\2""",
                   r"\1\2#\2", s)
        open(os.path.join(OUT, page), "w", encoding="utf-8").write(s)
        stats.append((page, hit, miss, ""))
    return stats


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    for page, hit, miss, note in build():
        print(f"  {page:34}{hit:5d} images{'  MISSING '+str(miss) if miss else ''}"
              f"{'  '+note if note else ''}")
