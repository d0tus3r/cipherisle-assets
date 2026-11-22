# Cipher Isle public assets

Brand images for cipherisle.com and our profiles, served by GitHub Pages at
`https://d0tus3r.github.io/cipherisle-assets/<path>`. Public on purpose: everything here is marketing art.
The source (and the scripts that make these) lives in the private puzzle-engine repo:
`brand_apply.py`, `site_assets.py`, `brand_assets.py`. Re-run them, copy here, push.

## Of the day (homepage)
`daily.py` renders `today/*.jpg` (quote and verse of the day, puzzle + answer) and `week/1-7.jpg`
(past week, solved) from `data/calendar-<year>.json`. The **Of the day** workflow runs it every night
after midnight Eastern and commits the result; cipherisle.com links to the files on
raw.githubusercontent.com so the page updates by itself. Run it by hand from the Actions tab.
Add next year's calendar to `data/` before January (puzzle-engine `daily/calendar-<year>.json`).
