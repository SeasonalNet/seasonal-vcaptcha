#!/bin/sh
# Check tag-based versions in an isolated temporary Git repository.
set -eu
source_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT HUP INT TERM
mkdir -p "$fixture/repo/tools"
cp "$source_root/tools/version.sh" "$fixture/repo/tools/version.sh"
git -C "$fixture/repo" init -q
git -C "$fixture/repo" config user.name 'Version test'
git -C "$fixture/repo" config user.email 'version-test@example.invalid'
git -C "$fixture/repo" config commit.gpgSign false
git -C "$fixture/repo" config tag.gpgSign false
git -C "$fixture/repo" add tools/version.sh
git -C "$fixture/repo" commit -qm initial
revision=$(git -C "$fixture/repo" rev-parse --short=12 HEAD)
[ "$(sh "$fixture/repo/tools/version.sh")" = "0.0.0-dev.1+g$revision" ]
git -C "$fixture/repo" tag v1.2.3
[ "$(sh "$fixture/repo/tools/version.sh")" = '1.2.3' ]
[ "$(sh "$fixture/repo/tools/version.sh" --release v1.2.3)" = '1.2.3' ]
[ "$(sh "$fixture/repo/tools/version.sh" --image-tag 'v1.2.3+build.4')" = 'v1.2.3_build.4' ]
printf 'version tests: development and clean release tags passed\n'
