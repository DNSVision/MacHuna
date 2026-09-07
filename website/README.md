# website/ — source for dnsvision.tv

The public download page, kept here so it is version-controlled and regenerated
as part of a release rather than living loose on somebody's Desktop.

**Nothing here is part of the shipping app.** It is not imported by `machuna.py`,
not bundled by `MacHuna.spec`, and not covered by `test_machuna.py`.

## What is here

- `index.html` — the site root. Sends visitors to `/machuna` until there is a
  DNS Vision front page worth showing.
- `machuna/index.html` — the download page itself.
- `machuna/version.json` — the small file MacHuna's update check will read.
  **Its `version` and `download` fields must match what is actually published.**

`machuna/MacHuna_User_Manual.pdf` is *not* kept here. It is copied from the repo
root at publish time, so there is only ever one manual to keep up to date.

## Publishing (checklist step 9, only when David asks)

Run `./publish.sh` from the repo root. It builds `publish/` containing the two
things to upload, and nothing else needs preparing by hand.

1. `publish/MacHuna-x.y.z.zip` → drag into the **machuna** R2 bucket
2. `publish/site/` → drag into the **dnsvision** Pages project

**The zip goes up before the site.** The page and `version.json` both announce a
version number; if they go first, MacHuna tells people about a release the
download link cannot serve yet.

Then delete the previous zip from the bucket once nobody needs it.

`publish/` is gitignored — it is a build output, like `dist/`.
