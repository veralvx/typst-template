#!/usr/bin/env bash
# The two pinned tools no action installs, into ~/.local/bin, put on PATH: typstyle, its release's
# binary; typst-package-check, the image typst/packages' CI runs (its action.yml), as a command
# that runs it on the working directory. checks.yml's and publish.yml's, on Linux x86_64 runners;
# TYPSTYLE and PACKAGE_CHECK are tools.toml's versions, each tool installed only if its is set.
set -euo pipefail

bin="$HOME/.local/bin"
mkdir -p "$bin"
if [ -n "${TYPSTYLE:-}" ]; then
  curl --fail --silent --show-error --location --retry 3 --output "$bin/typstyle" \
    "https://github.com/typstyle-rs/typstyle/releases/download/v$TYPSTYLE/typstyle-x86_64-unknown-linux-gnu"
  chmod +x "$bin/typstyle"
fi

if [ -n "${PACKAGE_CHECK:-}" ]; then
  image="ghcr.io/typst/package-check:$PACKAGE_CHECK"
  docker pull --quiet "$image" > /dev/null
  cat > "$bin/typst-package-check" << EOF
#!/bin/sh
# the working directory mounted at its own path, so the paths given are the container's too
exec docker run --rm --volume "\$PWD:\$PWD" --workdir "\$PWD" $image "\$@"
EOF
  chmod +x "$bin/typst-package-check"
fi
echo "$bin" >> "${GITHUB_PATH:?}"
