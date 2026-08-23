# v2/report — the deliverable

Two pages, self-contained. Nothing points outside the folder.

    index.html   the short version: base klein vs the shipped harness, in pictures
    deep.html    every decision, its evidence, and what failed
    *.html       the nine evidence pages the report links to
    img/         every image, downsized

## Rebuild

    .venv/bin/python -c "import sys; sys.path.insert(0,'v2/build'); \
      import report_simple, report_deep, report_deploy; \
      report_simple.build(); report_deep.build(); report_deploy.build()"

## Deploy

    npx vercel deploy v2/report

`index.html` is the entry point.

## Before deploying — read this

The images are AI-generated try-ons of **identifiable real people**, including
public figures, plus the p0xx individuals from the test set. A Vercel URL is
public by default. Deleting a deployment later does not unpublish what was
indexed or cached in the meantime.

That is a judgement for the repo owner, not a technical detail. If the report is
for internal review, `vercel deploy` without `--prod` gives a preview URL, and
Vercel's password protection or an SSO-gated team project keeps it private.

## Live

    https://report-g763vsjmj-ray-tans-projects.vercel.app

Deployed 2026-08-23. **Protected by Vercel SSO** — reachable only when signed in to
the owning Vercel account. That is the right default here: the images are
AI-generated try-ons of identifiable people, and a public URL cannot be un-published
once indexed.

To let someone else see it, in order of least to most exposure:

1. **Shareable link** — Vercel dashboard → the deployment → Share. Time-limited,
   no account needed, not indexable.
2. **Add them to the project** — Vercel dashboard → Settings → Members.
3. **Disable Deployment Protection** — Settings → Deployment Protection. This makes
   it world-readable. Consider whether the images should be.
