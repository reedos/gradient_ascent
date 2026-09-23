# Feedback and corrections

The quickest way to help is to tell us what is wrong. Every page on the site has a feedback link
at the bottom that opens [the feedback form](https://github.com/reedos/gradient_ascent/issues/new?template=feedback.yml)
with the page already filled in. You need a GitHub account; nothing else.

## What makes a correction easy to accept

This site's rule is that every claim about a product, a paper or a maker comes from that maker's
own page, and that every quotation is exact. So the most useful correction has three parts: the
sentence as it stands, what it should say, and a link to the primary source that shows it. News
coverage is a lead, not a source.

Names change often. If a product was renamed, retired or replaced, the registry
(`content/landscape.json`) has `formerly`, `retired` and `superseded_by` fields for exactly that,
and the site shows them as badges.

## Pull requests

Welcome, for fixes and for new material. Before you open one:

```
python scripts/validate.py
cd site && npm ci && npx astro check && npm run build && npm test && cd ..
python -m unittest discover -s tests
```

All of it must pass. Build the site before running the Python tests, because some of them read
the built pages. `docs/WRITING-A-TECHNIQUE-PAGE.md` and `docs/WRITING-A-TEARDOWN.md` describe how
a page is put together and sourced. Examples are standard-library Python and run on the stub
model with no network.

Every page is marked Sourced until a recorded run and a scored result exist for it; only then
is it Measured. Please do not
add measured numbers without the run that produced them.
