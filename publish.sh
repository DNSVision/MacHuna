#!/bin/bash
#
# ############################################################################
# ##  RETIRED 2026-09-25. THIS SCRIPT PUBLISHES A DOWNGRADE. DO NOT RUN IT. ##
# ############################################################################
#
# dnsvision.tv/machuna serves MacHuna 2.0, the Swift app, from
# DNSVision/MacHuna-Swift. Publishing from here would upload MacHuna-1.11.0.zip
# and deploy a page announcing 1.11.0, and every 2.0 user checking for updates
# would be offered a downgrade.
#
# This was verified, not assumed: on 2026-09-26 a dry run of this script said
# "Ready to publish v1.11.0" with every one of its own guards satisfied. They
# all compare this repo against ITSELF - machuna.py, version.json, the page and
# the built app all agree on 1.11.0 - and nothing here knows what is live. That
# is precisely why a comment was not considered enough and the refusal below
# exists.
#
# TO PUBLISH: use MacHuna-Swift/publish.sh, which carries the same checks plus
# one this never had - it asks the live site its version and refuses to go
# backwards.
#
# IF v1.11.0 EVER GENUINELY NEEDS TO GO BACK UP, do it deliberately by hand;
# a verified copy is kept at dist/released/MacHuna-1.11.0.zip:
#   export CLOUDFLARE_API_TOKEN=$(cat ~/.machuna_publish_token)
#   export CLOUDFLARE_ACCOUNT_ID=6929e90daf2e30ca1a943c9c2801b38b
#   npx wrangler@latest r2 object put machuna/MacHuna-1.11.0.zip \
#       --file dist/released/MacHuna-1.11.0.zip --content-type application/zip \
#       --content-disposition 'attachment; filename="MacHuna-1.11.0.zip"' --remote
# That restores the download WITHOUT touching the page or version.json, so
# nobody is offered it as an update - which is almost certainly what you want.
#
# Everything below is kept as a record of how releases worked from this repo,
# and because the Swift script is a port of it.
#
# ---------------------------------------------------------------------------
# Build, and optionally upload, a MacHuna release.
#
#   ./publish.sh            build publish/ only, upload by hand
#   ./publish.sh --upload   build and upload to Cloudflare
#
# Produces publish/ containing:
#   MacHuna-<version>.zip   -> drag into the "machuna" R2 bucket
#   site/                   -> drag into the "dnsvision" Pages project
#
# The zip always goes up FIRST. The page and version.json both announce a version
# number, so if they went first MacHuna would start telling people about a release
# the download link could not serve yet. --upload enforces that order; by hand it
# is down to you.
#
# publish/ is gitignored. It is a build output and is rebuilt from scratch here.

set -euo pipefail
cd "$(dirname "$0")"

# ── RETIRED: refuse, loudly, before doing anything at all ────────────────────
cat >&2 <<'RETIRED'

  ========================================================================
   publish.sh in the MacHuna (Python) repo is RETIRED as of 2026-09-25.
  ========================================================================

   dnsvision.tv/machuna serves MacHuna 2.0, the Swift app.
   This script would publish v1.11.0 over it and offer every user a
   downgrade. Its own guards do not catch that: they only check that
   this repo agrees with itself, and it does.

   To publish:   cd ../MacHuna-Swift && ./publish.sh --upload

   To restore the old 1.11.0 download WITHOUT announcing it as an
   update, see the header of this file for the exact wrangler command.

RETIRED
exit 1

UPLOAD=0
[ "${1:-}" = "--upload" ] && UPLOAD=1

ACCOUNT_ID=6929e90daf2e30ca1a943c9c2801b38b
BUCKET=machuna
TOKEN_FILE="$HOME/.machuna_publish_token"

VERSION=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' machuna.py)
[ -n "$VERSION" ] || { echo "ERROR: could not read VERSION from machuna.py"; exit 1; }

[ -d dist/MacHuna.app ] || { echo "ERROR: dist/MacHuna.app not found - build first:"; \
                             echo "  python3.12 -m PyInstaller MacHuna.spec -y"; exit 1; }

BUILT=$(/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" \
        dist/MacHuna.app/Contents/Info.plist 2>/dev/null || echo "?")
if [ "$BUILT" != "$VERSION" ]; then
  echo "ERROR: machuna.py says $VERSION but dist/MacHuna.app is $BUILT."
  echo "       Rebuild before publishing:  python3.12 -m PyInstaller MacHuna.spec -y"
  exit 1
fi

DECLARED=$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' website/machuna/version.json)
if [ "$DECLARED" != "$VERSION" ]; then
  echo "ERROR: website/machuna/version.json says $DECLARED but this release is $VERSION."
  echo "       Update version, released, summary and download in that file first."
  exit 1
fi

# The page announces the version too, in three places, and it drifts silently.
# version.json being right is not enough: the download button is on the page.
for want in "v$VERSION" "MacHuna-$VERSION.zip"; do
  grep -qF "$want" website/machuna/index.html || {
    echo "ERROR: website/machuna/index.html does not mention $want."
    echo "       Update the current-release panel, the download link and the"
    echo "       release notes before publishing $VERSION."
    exit 1
  }
done
PREV=$(grep -oE 'MacHuna-[0-9]+\.[0-9]+\.[0-9]+\.zip' website/machuna/index.html | grep -v "MacHuna-$VERSION.zip" | head -1 || true)
if [ -n "$PREV" ]; then
  echo "ERROR: the download button still points at $PREV."
  exit 1
fi

rm -rf publish
mkdir -p publish

# The site: page source from website/, manual from the repo root so there is only
# ever one manual to keep current.
cp -R website publish/site
rm -f publish/site/README.md
find publish/site -name .DS_Store -delete
cp MacHuna_User_Manual.pdf publish/site/machuna/MacHuna_User_Manual.pdf

# The download
ditto -c -k --sequesterRsrc --keepParent dist/MacHuna.app "publish/MacHuna-$VERSION.zip"

ZIP="publish/MacHuna-$VERSION.zip"
ZIP_MB=$(( $(stat -f%z "$ZIP") / 1048576 ))

if [ "$UPLOAD" -eq 0 ]; then
  echo
  echo "Ready to publish v$VERSION"
  echo "  1. $ZIP  (${ZIP_MB} MB)  -> R2 bucket '$BUCKET'"
  echo "  2. publish/site/                          -> Worker 'soft-glade-217b'"
  echo
  echo "  Zip first, then the site."
  echo "  Then delete the previous zip from the bucket."
  echo
  echo "  Or run:  ./publish.sh --upload"
  open publish 2>/dev/null || true
  exit 0
fi

# ── upload ───────────────────────────────────────────────────────────────────
[ -f "$TOKEN_FILE" ] || {
  echo "ERROR: no Cloudflare token at $TOKEN_FILE."
  echo "       Create one at dash.cloudflare.com > My Profile > API Tokens with"
  echo "       Workers R2 Storage:Edit and Workers Scripts:Edit, then save it there."
  exit 1
}
export CLOUDFLARE_API_TOKEN
CLOUDFLARE_API_TOKEN=$(cat "$TOKEN_FILE")
export CLOUDFLARE_ACCOUNT_ID="$ACCOUNT_ID"

# Fail early and in plain English if the token has expired or been revoked,
# rather than letting wrangler produce something cryptic mid-upload.
VERIFY=$(curl -sS -m 20 "https://api.cloudflare.com/client/v4/user/tokens/verify" \
         -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" || true)
case "$VERIFY" in
  *'"success":true'*) : ;;
  *) echo "ERROR: Cloudflare rejected the API token."
     echo "       It has probably expired or been revoked. Make a new one at"
     echo "       dash.cloudflare.com > My Profile > API Tokens (Workers R2"
     echo "       Storage:Edit + Workers Scripts:Edit) and save it to:"
     echo "         $TOKEN_FILE"
     exit 1 ;;
esac

echo
echo "Publishing MacHuna v$VERSION"
echo "  1/2  uploading $ZIP (${ZIP_MB} MB) to R2..."
# Content-Disposition matters: without it the browser is left to guess what to
# do with the URL and can simply navigate to a blank page instead of saving the
# file. The usual fix of putting download= on the link does not work here, as
# the page and the file are on different subdomains and browsers ignore that
# attribute across origins.
npx --yes wrangler@latest r2 object put "$BUCKET/MacHuna-$VERSION.zip" \
    --file "$ZIP" --content-type application/zip \
    --content-disposition "attachment; filename=\"MacHuna-$VERSION.zip\"" \
    --remote >/dev/null
echo "       done."

echo "  2/2  deploying the site..."
npx --yes wrangler@latest deploy >/dev/null
echo "       done."

# ── verify what is actually live, rather than trusting the uploads ───────────
echo
echo "Checking the live site..."
FAIL=0
# Cloudflare's edge keeps serving the previous page for a few seconds after a
# deploy, so a single immediate check reports a failure that is not real.
# Retry for up to a minute before believing it.
check() {  # url, expected-substring, label
  for _ in $(seq 1 12); do
    body=$(curl -sS -m 25 -L "$1" 2>/dev/null || true)
    if printf '%s' "$body" | grep -qF "$2"; then echo "  ok    $3"; return; fi
    sleep 5
  done
  echo "  FAIL  $3  ($1)"
  FAIL=1
}
code() {   # url, label
  # HEAD, not GET: the app zip is 34 MB and downloading all of it just to learn
  # the link works timed out and reported a false failure. Also note the code
  # is captured on its own - a "|| echo 000" fallback concatenates with curl's
  # own output and produces nonsense like "200000".
  local c
  for _ in $(seq 1 12); do
    c=$(curl -sS -m 20 -o /dev/null -w '%{http_code}' -I -L "$1" 2>/dev/null)
    [ -n "$c" ] || c=000
    if [ "$c" = "200" ]; then echo "  ok    $2"; return; fi
    sleep 5
  done
  echo "  FAIL  $2 (HTTP $c)"
  FAIL=1
}
echo "  (allowing up to a minute for Cloudflare's cache to turn over)"
check "https://dnsvision.tv/machuna/version.json" "\"version\": \"$VERSION\"" "version.json announces $VERSION"
check "https://dnsvision.tv/machuna" "v$VERSION" "page shows $VERSION"
code  "https://downloads.dnsvision.tv/MacHuna-$VERSION.zip" "download link works"
code  "https://dnsvision.tv/machuna/MacHuna_User_Manual.pdf" "manual works"

echo
if [ "$FAIL" -eq 0 ]; then
  echo "Published. https://dnsvision.tv/machuna is live on v$VERSION."
  echo
  echo "The previous release is still in the bucket, on purpose."
  echo "Delete it yourself when nobody needs it - it is the only irreversible"
  echo "step here, so the script will not do it for you."
else
  echo "Something is not right. The uploads may have half-completed;"
  echo "check the failures above before telling anyone about this release."
  exit 1
fi
