"""ironman_vlm.score() on the iron man 2 VEi cells (200 pairs x seeds 46/47/48 = 600),
with only the note-length cap relaxed (300 -> 2000 chars), same as judge_vei/run_judge.py:
gpt-5.5 writes ~350-char notes and the 300 cap burned 3 attempts per cell in
judge_fal_vs_a100. PROMPT, model, images and the six scores are unchanged from
v3/build/ironman_vlm.py. gen/ and inputs/ are symlinks into ../ironman2/."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "build"))
import ironman_vlm as iv
iv.SCHEMA["properties"]["note"]["maxLength"] = 2000
iv.score(os.path.dirname(os.path.abspath(__file__)), "gpt-5.5", None, 8, float(sys.argv[1]) if len(sys.argv) > 1 else 15.0)
