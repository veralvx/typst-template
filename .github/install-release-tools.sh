#!/usr/bin/env bash
# cargo-generate (0.25.0, the template's floor) and cocogitto (7.0.0) from their GitHub releases,
# each archive checked against the SHA-256 it had when pinned, into ~/.local/bin, put on PATH: the
# smoke test's, on Linux x86_64 runners. A new version is a new URL and a new sum.
set -euo pipefail

bin="$HOME/.local/bin"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$bin"
fetch() { # fetch <url> <sha256> <executable>: the archive's executable of that name, installed
  curl --fail --silent --show-error --location --retry 3 --output "$work/archive.tar.gz" "$1"
  echo "$2  $work/archive.tar.gz" | sha256sum --check --quiet
  tar -xzf "$work/archive.tar.gz" -C "$work"
  install "$(find "$work" -type f -name "$3" | head -n 1)" "$bin/$3"
}
fetch https://github.com/cargo-generate/cargo-generate/releases/download/v0.25.0/cargo-generate-v0.25.0-x86_64-unknown-linux-gnu.tar.gz \
  2e71538c10410827579987c546db7030f71c0283774891bd8ebf107962260e80 cargo-generate
fetch https://github.com/cocogitto/cocogitto/releases/download/7.0.0/cocogitto-7.0.0-x86_64-unknown-linux-musl.tar.gz \
  e03938ff2c4c86d71c00c0f3284dbbe95c5ca76fe34a51f33e945c23010d59bb cog
echo "$bin" >> "${GITHUB_PATH:?}"
