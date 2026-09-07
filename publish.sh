#!/bin/bash
# Build the two things that get uploaded to Cloudflare when publishing a release.
#
#   ./publish.sh
#
# Produces publish/ containing:
#   MacHuna-<version>.zip   -> drag into the "machuna" R2 bucket
#   site/                   -> drag into the "dnsvision" Pages project
#
# Upload the zip FIRST. The page and version.json both announce a version number,
# so if they go up first MacHuna starts telling people about a release the
# download link cannot serve yet.
#
# publish/ is gitignored. It is a build output and is rebuilt from scratch here.

set -euo pipefail
cd "$(dirname "$0")"

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

ZIP_MB=$(( $(stat -f%z "publish/MacHuna-$VERSION.zip") / 1048576 ))
echo
echo "Ready to publish v$VERSION"
echo "  1. publish/MacHuna-$VERSION.zip  (${ZIP_MB} MB)  -> R2 bucket 'machuna'"
echo "  2. publish/site/                              -> Pages project 'dnsvision'"
echo
echo "  Zip first, then the site."
echo "  Then delete the previous zip from the bucket."
open publish 2>/dev/null || true
