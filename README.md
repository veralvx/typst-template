# typst-template

A [`cargo-generate`](https://github.com/cargo-generate/cargo-generate) template for a
[Typst](https://typst.app) package -- a library, or a template package `typst init` starts
projects from -- that starts with the whole toolchain wired up and with
[Typst Universe](https://typst.app/universe)'s rules already kept: tests by
[tytanic](https://typst-community.github.io/tytanic/) (visual references, assertions, the template
as initialized), formatting by typstyle, the bundle linted by the same `typst-package-check`
typst/packages runs on a submission, every warning an error, the README's examples compiled, the
oldest Typst declared tested in CI, Conventional Commits, changelogs by git-cliff, a release recipe
that shows every step, a publish workflow that prepares the Universe submission, a Nix flake whose
tools are the pinned ones, and a `justfile` that runs locally what CI runs remotely.

It is the counterpart of the [rust-template](https://github.com/veralvx/rust-template) and the
[python-template](https://github.com/veralvx/python-template). See [Attribution](#attribution).

## Usage

```sh
cargo install --locked cargo-generate   # 0.25 or later (the template refuses older)
cargo generate --git https://github.com/veralvx/typst-template template
```

cargo-generate is language-agnostic: Liquid over files, with conditionals; nothing here is Rust.
nixpkgs-unstable carries 0.25 (`nix run nixpkgs#cargo-generate`), built without its `git`
feature, so it makes no repository: `git init` in the new project.

The trailing `template` is the sub-folder that holds the template; the repository root holds this
README and the template's own CI.

Everything can be answered non-interactively, which is what the smoke test does:

```sh
cargo generate --git https://github.com/veralvx/typst-template template \
  --name my-package --silent \
  -d project_kind=package \
  -d description="Draw tidy timelines from a list of events." \
  -d author_name="Jane Doe" \
  -d author_email=jane@example.com \
  -d github_username=jane \
  -d license="MIT OR Apache-2.0" \
  -d compiler=0.14.0 \
  -d keywords="timeline, chronology" \
  -d categories="visualization" \
  -d disciplines=""
```

Then, in the new project, the first steps its `CONTRIBUTING.md` gives (Maintainers, First steps):
the first commit, the repository's settings, the fork that receives submissions.

### If generation fails

`cargo-generate` creates the destination directory *before* it validates any answer, and leaves it
behind when validation rejects one. The retry then stops with
`Target directory already exists, aborting!` -- remove the empty directory and try again.

## What you are asked

| Prompt            | Default                     | Goes into                                                       |
| ----------------- | --------------------------- | --------------------------------------------------------------- |
| *(project name)*  | --                          | the package's name, the repository, every `@preview/` import    |
| `project_kind`    | `package`                   | `package` or `template` -- see below                            |
| `description`     | one per kind                | `typst.toml`'s `description`, the README                        |
| `author_name`     | --                          | `authors` (`Name <@github-user>`), the licence's copyright line |
| `author_email`    | *(empty)*                   | the code of conduct's contact -- omitted if blank               |
| `github_username` | --                          | the repository's URLs, `authors`' handle, security advisories   |
| `license`         | `MIT OR Apache-2.0`         | `license`, the licence files, the README -- see below           |
| `compiler`        | `0.14.0`                    | `compiler`, the oldest Typst CI compiles the package on         |
| `keywords`        | *(empty)*                   | `keywords` (comma-separated)                                    |
| `categories`      | none; `report` (a template) | `categories`, at most three of Universe's; a template needs one |
| `disciplines`     | *(empty)*                   | `disciplines`, of Universe's list                               |

Every answer is validated at the prompt, against Universe's rules where it has one: its 19
categories and 39 disciplines, a GitHub handle as its bundler checks it in `authors`, nothing that
would break a TOML string or the `Name <@handle>` form, a `compiler` that is a released Typst from
0.12 (the oldest the checks are verified on) to the pinned one. The project name is checked before
any file is written -- only the empty directory above is (`template/validate-name.rhai`, a pre
hook): kebab-case, a letter first, and no
"typst", as Universe's naming rules ask -- and, as no regex can say it, a description without
"Typst" and a GitHub handle of at most 39 characters. What a hook cannot judge -- that the name is
not the obvious, canonical one for what the package does -- is typst/packages' review.

### What `project_kind` selects

| Value      | What it is                                                                                                                                           |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `package`  | a library: `greet` in `src/greet.typ`, a visual test and an assertion test                                                                           |
| `template` | a template package: `report` in `src/report.typ`, which `template/main.typ` applies with a show rule, as Universe asks; `[template]` in `typst.toml` |

Either way, `src/lib.typ` is the entrypoint and defines nothing: what it imports is the public API
(Typst has no `pub`), the pattern typst/packages recommends.

### The licence

Universe takes an OSI-approved licence (or CC-BY, CC-BY-SA, CC0) and a file named `LICENSE`, or one
the README links. `LICENSE` is always there: the licence's text, or -- for `MIT OR Apache-2.0` -- a
pointer to `LICENSE-MIT` and `LICENSE-APACHE` beside it, as Universe's own dual-licensed packages
do.

A template package's `template/` is what users copy and make their own, so Universe asks that they
may use and share what they make from it without restriction, and recommends MIT-0 for it. Here it
is always MIT-0: `license` becomes `<choice> AND MIT-0` (`(MIT OR Apache-2.0) AND MIT-0` for the
dual licence), with `LICENSE-MIT-0` beside the others and the README saying which covers what.
Choosing `MIT-0` makes the whole package MIT-0, as Typst's own templates are.

## What you get

```text
typst.toml            the manifest Universe reads: every field its review asks for
src/lib.typ           the entrypoint: the public API, imported from the modules beside it
src/greet.typ         the starter code (a template package's: src/report.typ, template/main.typ)
tests/                tytanic's: a visual test (its reference in ref/), an assertion test
README.md             the package's page on Universe: its examples compile, against the bundle
tools.toml            the pinned typst, tytanic, typstyle, typst-package-check, just, shellcheck
                      and shfmt
justfile              `just checks` = what CI runs; `just bundle`, `just release`, `just floor`...
.gitattributes        what typst/packages does not get (export-ignore): the bundle is git archive
.editorconfig         shfmt's style, for the shell scripts and the git hooks
flake.nix, flake.lock the dev shell, `nix fmt` and the checks; the lock pins nixos-unstable
.githooks/            opt-in (`just install-hooks`): formatting, the shell and the imports'
                      versions before a commit; Conventional Commits for the message and the push
cliff.toml, cog.toml  git-cliff changelogs, cocogitto's commit checks
dprint.json           Markdown and TOML formatting, plugins at their latest
AGENTS.md             the rules: the public API, warnings, what a package can hold, the tests
CONTRIBUTING, SECURITY, CODE_OF_CONDUCT
LICENSE (+ LICENSE-MIT, LICENSE-APACHE, LICENSE-MIT-0 by the choice and the kind)
.github/              6 workflows, dependabot, issue and PR templates, the tools' and the
                      release notes' scripts
```

### The checks

`just checks` runs, in order: the tools on `PATH` against `tools.toml`; typstyle over every `.typ`
file; shellcheck and shfmt over the shell scripts, the git hooks and the justfile's script recipes
(read out of `just --dump`); the tests; every `@preview/<name>:<version>` import against
`typst.toml`'s version; each `typ` block of the README compiled alone, importing the bundle; a
template package's template, as `typst init` makes it from the bundle, compiled;
typst-package-check on the bundle; dprint; `cog check`; and last the flake: `nix fmt -- --ci`
(nixfmt, shfmt and typstyle, through treefmt; it formats, and fails if that changed a file) and its
checks. A compiler warning fails each
compile, and a package-check warning fails too -- a warning on Universe is a review comment.

The bundle (`just bundle`, `dist/preview/<name>/<version>`) is `git archive` of the repository, less
what `.gitattributes` marks `export-ignore` -- the tooling, the tests, the contributors' documents
-- laid out as a package path holds it, so `--package-path dist` imports it as `@preview`. A
published version never changes, so the bundle holds the package alone -- `typst.toml`, the README,
the licences, the changelog, the entrypoint's directory, the template -- and what `exclude` names
(documentation the README links); a file new to the repository and none of these stops it, until it
is export-ignored or given a place. For a template package, its thumbnail is rendered there from a
`typst init` of the bundle: always the template as initialized, as Universe asks, and never
committed, as Universe leaves it out of downloads. It is held to what typst/packages' bundler -- not
package-check -- enforces: 250 ppi, or more until its longer edge reaches 1080 px (a business card's
page), and at most 3 MiB.

### The pinned tools

tytanic's references are its Typst's rendering, typstyle's and shfmt's format are their own,
package-check's lints are typst/packages' at its version, shellcheck's its version's, and
`just shell-check` reads just's own `--dump`: their verdicts depend on their versions, so
`tools.toml` pins them (typst 0.15.1, tytanic 0.4.1 -- the one for that Typst -- typstyle 0.15.1,
typst-package-check 0.7.0, typst/packages' own, just 1.58.0, shellcheck 0.11.0, shfmt 3.14.1), and
`just tools-check` refuses others. The pins
are the flake's nixpkgs' versions, and its `pins` check holds them there, so `nix develop`, CI and a
manual install judge alike. That is why the template ships its `flake.lock`, as the python-template
does.

### The CI workflows

- `checks.yml` -- the checks above but the flake's, the commits' and dprint's; tytanic's output
  and differences kept when a test fails, the bundle kept when the checks pass. A second job
  compiles the README and the template on `compiler`'s Typst (`just floor`): the floor is tested,
  not declared.
- `nix.yml` -- `nix fmt -- --ci`, then `nix flake check`, on x86_64 Linux, aarch64 Linux and Apple
  silicon: the pins, the format, the shell, the tests (so the references hold on each), and
  typst-package-check built from its flake input (nixpkgs carries none, so an update that breaks
  its build shows here); every system also evaluated.
- `publish.yml` -- see below.
- `style-check-dprint.yml`, `style-check-cocogitto.yml` -- formatting, and Conventional Commits:
  every commit, and a pull request's title (a squash merge makes it the commit).
- `dependabot-automerge.yml` -- merges Dependabot's patch and minor action bumps once the required
  checks pass. Read its setup comment: without required checks it merges what CI never gated.

Every action is pinned to a commit, its version in a comment; Dependabot moves them -- in this
repository too, the template's workflows with this repository's, in one pull request
(`.github/dependabot.yml`).

### The changelog, `just release` and Typst Universe

There is no `CHANGELOG.md` until the first release writes one: git-cliff generates it from the
commits, never a hand. `just release <major|minor|patch>` shows every step in order and runs no
tests -- it releases `origin/main`, which CI checks: it refuses a dirty tree, another branch, a
`main` that is not `origin/main` or a release with nothing in it; sets the version in `typst.toml`
and in every `@preview/<name>:<version>` import (the README's, the template's: Universe asks that a
release's examples import it), the first release being the declared `0.1.0`; writes the changelog;
commits; tags `v<version>`; pushes the commit and the tag atomically. If a step fails before the
commit -- a git hook refusing it, say -- it puts the files back.

The tag runs `publish.yml`: the bundle made once and linted as typst/packages will, online this
time (the repository must answer); the GitHub release, the bundle as a tarball and the changelog's
section as notes; and, once the repository variable `UNIVERSE_FORK` names your fork of
typst/packages, a branch on it holding the bundle at `packages/preview/<name>/<version>` -- on
typst/packages' main, the fork's main synced to it first, committed as the release's author --
with the pull request to open linked in the run's summary, titled `<name>:<version>` as
typst/packages asks. The submission itself, and its
checklist, stay yours: a fine-grained token for the fork alone is all it needs
(`UNIVERSE_TOKEN`, which the `universe` environment can hold and keep to release tags), where
opening the pull request for you would need one that writes to any public repository.

## Developing this template

The repository is a project of its own around `template/`, with the files a generated project
has, adapted: [CONTRIBUTING.md](CONTRIBUTING.md) (the tools, the release), [AGENTS.md](AGENTS.md)
(the rules), [SECURITY.md](SECURITY.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), a `justfile`,
the git hooks, `dprint.json`, `cog.toml` and `cliff.toml` (the changelog), `.editorconfig`, a
flake and its lock (the tools' shell, `nix fmt`, the checks), issue and pull request templates.
Some are the template's own files, copied: render-check holds each copy to its original.

```sh
nix develop               # every tool below (or CONTRIBUTING.md's list, installed yourself)
just checks               # render-check, the shell, the workflows, dprint, cog, the flake's last
just smoke package        # generated by cargo-generate, then its own checks (and `template`)
just generate template    # into target/template/demo, to look at
```

`just render-check` installs `tools/requirements.txt` into `.venv` (Python 3.11+, for tomllib) and
runs `tools/render-check.py`, which renders every templated file for 32 combinations of
`project_kind` × `license` × categories (none or one; one or three) × email, keywords and
disciplines (empty or present), then checks that nothing is left unexpanded and that the result
parses as TOML, YAML, JSON and -- with `nix-instantiate` on `PATH` -- Nix. It also guards what fails
silently otherwise:

- **Every referenced variable is declared.** cargo-generate renders an unknown variable as an
  empty string, and a file it cannot render at all as it stands, without a word -- no "leftover
  `{{`" check sees either.
- **No file on the `exclude` list contains a placeholder, and every binary file is on it**: those
  are copied verbatim -- the workflows (GitHub's `${{ }}`), the justfile (just's `{{ }}`),
  cliff.toml (Tera, which Liquid would evaluate silently), the Typst code, the flake -- and a binary
  one (the tests' references) cargo-generate refuses to render and aborts on.
- **The regexes are Universe's.** Each default passes its own; every category and discipline
  passes, and an unknown one, a fourth category, a template without one, a GitHub handle with
  `--` and a `compiler` above the pinned Typst do not.
- **Every `ignore` and `export-ignore` path exists**, and none of the latter is the package's own.
- **The licence texts agree**: `LICENSE`'s branch for each licence is byte for byte the file it
  also is.
- **Each `typst.toml` describes its case**: the licence expression, `authors`, `[template]`
  exactly for a template package, the lists, the entrypoint's module; and each case keeps exactly
  the licence files its `license` and README name.
- **The copies are the template's**: `cog.toml`, `cliff.toml`, `.editorconfig`, `flake.lock`
  (`just flake-sync`), the release-notes script, two hooks and three workflows byte for byte (and
  executable alike), the justfiles' `shell-check` and `shfmt` recipes, and dprint's plugins.

The rest of `just checks`: `just shell-check` (shellcheck and shfmt over every shell script, the
hooks and this justfile's script recipes) and `just template-shell-check` (the template's, its
justfile's recipes included); actionlint over both sets of workflows; dprint over this
repository's Markdown and TOML (`template/` is the generated projects'); `cog check`; and
`just nix` -- `nix fmt -- --ci` (nixfmt and shfmt, through treefmt; it formats, and fails if that
changed a file) and the flake's checks, which
run the shell and actionlint again in the sandbox.

CI runs them: `nix.yml` the flake (`just nix`, step by step), `style-check-dprint.yml` and
`style-check-cocogitto.yml` dprint and the commits, `dependabot-automerge.yml` Dependabot's action
and render-check bumps, `release.yml` a release tag's GitHub release (`just release` cuts it: the
changelog, the tag `v<version>`, which `cargo generate --tag` takes) -- with every tracked file as
a tarball, as GitHub's own source archives are `git archive`'s, and so lack what
`template/.gitattributes` export-ignores. And
`.github/workflows/template-smoke-test.yml` does the real end-to-end check, weekly, on pushes to
`main` and on every pull request: render-check; every kind × licence × email answer through the
real cargo-generate (typst.toml, the licence files, dprint), and the names, and the template
without a category, that must be refused; for each kind, with the tools its own CI installs, the
hooks refusing what CI would, `just checks` but the flake's, `just floor`, and two releases against
a bare remote, each tag then read and bundled as `publish.yml` does; and for each kind under Nix,
generated by nixpkgs' cargo-generate, the flake's checks and `just checks` in its dev shell.

## Verification status

The template is driven end to end with the real tools, not reasoned about. With
**cargo-generate 0.25.0**, **typst 0.15.1**, **tytanic 0.4.1**, **typstyle 0.15.1**,
**typst-package-check 0.7.0** (built from its tag), **just 1.58.0**, **shellcheck 0.11.0**,
**shfmt 3.14.1**, **cocogitto 7.0.0**, **git-cliff 2.14.2** and **dprint 0.61.1** (markdown 0.26.0,
TOML 0.9.0), all 16 kind × licence × email combinations generate and, after their first commit,
pass `just --fmt --check` and `just checks` but for `nix`: `tools-check`, `format-check`,
`shell-check`, `test`, `versions-check`, `readme-check`, `template-check`, `package-check`,
`dprint-check` and `cog`.

Also confirmed by running it:

- **The floor**: the README and the template compile on Typst 0.12.0 and 0.14.0 (`just floor`,
  with `compiler` set to each).
- **The bundle**: exactly the package's files (typst.toml, src/, template/, README.md, the
  licences, after a release the changelog); a template's thumbnail 2067 × 2923 px, about 650 KB, of
  the template as `typst init` made it; package-check silent on it offline, and failing on a staged
  file it warns of (`exclude/example`) and, online, on a repository that does not answer.
- **The checks fail when they should**: a README block with a warning (an unknown font) or with no
  language -- fenced with backticks or tildes, indented in a list or not -- an import of a stale
  version, unformatted Typst code; and only a diagnostic counts, not a dependency's download
  progress on Typst's stderr.
- **Releases** against a bare remote, through the git hooks: a package's first release tags
  `v0.1.0` (the declared version, whatever the level) and writes the changelog; a second, after a
  `fix!`, bumps to `v0.2.0` -- `typst.toml` and the README's import -- the breaking change first and
  a compare link; a template package's moves `template/main.typ`'s import too, and its template
  still compiles; an empty release, an unpushed `main`, a dirty tree and an unknown level are
  refused; a planted stale import makes the release refuse and put every file back. Each tag, at
  its own commit, passes publish.yml's steps: its version, its notes, its bundle linted.
- **typst/packages' own bundler** (its deploy's, built from its main) accepts all 16 bundles --
  their SPDX expressions, `authors`, categories, entrypoints and thumbnails -- and a template whose
  page is a business card's, its thumbnail re-rendered to 1081 px. package-check, in its
  typst/packages mode (`check @preview/<name>:<version>` in a clone, the submission committed as
  publish.yml commits it), is silent too.
- **The smoke test's own steps**, run locally as written (installs aside) for both kinds: generate,
  the hooks, `just checks` but `nix`, `just floor` on Typst 0.14.0, the releases and each tag's
  bundle, and the bundler's acceptance. publish.yml's push to a fork, run against a local bare
  repository standing in for it: the branch, the commit's author and message, the link; and, the
  fork synced and then checked out itself, the push sends the package alone (7 objects over a
  200-commit history, with `push.negotiate` off and typst/packages moved before the sync).
- **`just install`**: the bundle as `@local/<name>:<version>`, which a document then imports; for
  a template package, `just install preview`, which `typst init` then starts a project from that
  compiles (its `main.typ` imports `@preview/`).
- **The git hooks**: unformatted Typst code, a stale import, a message cog rejects and a pushed
  revert refused; a clean push accepted.
- **The flake** of each kind evaluates on all three systems (`nix flake check --no-build
  --all-systems`, Nix 2.34.6, the shipped flake.lock) and is nixfmt-clean; its `pins` check
  reports nothing for the shipped pins, and names a mutated pin and an unknown one. Its tests and
  format checks, run as the derivations run them -- the test files copied out, no network -- pass.
- **The bundle's allowlist**: a committed `scripts/dev.sh` and `docs/manual.pdf` stop
  `just bundle`, naming each; listed in `exclude`, the manual passes, and export-ignored, the
  script.
- **render-check** catches each of eleven planted defects: a misspelled variable, a glob in
  `ignore`, a placeholder in an excluded file, a drifted licence text, a stale and a package
  `export-ignore`, a `compiler` regex past the pins, a binary file not excluded, a wrong licence
  file kept, an SPDX expression without its parentheses, a fourth category.
- **The shell**: `just shell-check` passes here, in `template/` and in both kinds generated; here it
  fails on a planted unquoted variable (SC2086), a script recipe with a `{{ }}` interpolation, a
  recipe line indented off its style and an unformatted script; in a generated project, on a
  bashism in a `#!/bin/sh` recipe (checked as sh) and an unquoted variable in a
  `#!/usr/bin/env -S bash -eu` one; a recipe named `exports` is checked like any other, and a
  `#!/usr/bin/env python3` recipe and an `export x := env(...)` pass.
- **The smoke test's downloads**: `.github/install-release-tools.sh` installs cargo-generate and
  cocogitto from archives checked against their pinned SHA-256, and refuses one that differs.
- **`nix fmt`**: each flake's formatter, run as treefmt 2.6.0 with the same settings and `--ci`,
  passes on this repository and on both kinds generated, and fails on a planted change; the flakes
  are nixfmt 1.5.0-clean. The flakes' `shell` checks, run as their derivations run them in a
  namespace without `/usr/bin/env` -- the Linux sandbox has none, and just runs a script recipe
  through its shebang -- pass, and fail without the shebang rewritten.
- **This repository's flake** evaluates on all three systems; its lock is the template's, so its
  dev shell has the versions named above (typst-package-check built from its tag), and actionlint
  1.7.12.
- **`just release` here**, against a bare remote, through the hooks: `v0.1.0` first, whatever the
  level, then `v0.1.1` with its compare link; a bad level, a dirty tree, an unpushed `main`,
  another branch and a release with nothing in it refused; a revert refused at the push, a
  message cog rejects at the commit. release.yml's step on each tag: its notes, and a tarball of
  every tracked file that cargo-generate generates from (`--path`); a changelog whose first
  section is another version's, refused.
- **render-check's copies**: each of nine planted drifts caught -- a copied file changed, an
  executable bit lost, either justfile's `shell-check` or `shfmt` recipe changed, the locks'
  nixpkgs apart, dprint's plugins apart, Liquid in an original, a copy missing.
- **`just smoke package`** and **`just smoke template`** pass.
- The workflows -- this repository's and the template's -- pass actionlint 1.7.12 with
  shellcheck 0.11.0.

What this does **not** cover -- the smoke-test workflow is what does:

- **Builds under Nix.** The flake's derivations were evaluated, never built: this environment
  reaches no binary cache. So typst-package-check's build from its flake (its `cargoHash` against
  this nixpkgs) and the checks as derivations have not run here.
- **GitHub Actions itself**: setup-typst, setup-tytanic, the package-check image, the GitHub
  releases (`gh release create`) and the push to a typst/packages fork are linted, not run.

## Attribution

The workflows, the justfile's shape, `cliff.toml`, `cog.toml`, the hooks, the community documents
and the render-check and smoke-test harness are adapted from the
[rust-template](https://github.com/veralvx/rust-template) and the
[python-template](https://github.com/veralvx/python-template), which took them from
[`veralvx/imi`](https://github.com/veralvx/imi) (MIT OR Apache-2.0). The Universe rules followed are
typst/packages' documentation and its bundler's and package-check's source.

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or
  <http://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or <http://opensource.org/licenses/MIT>)

at your option.

The generated projects are yours: their licence is the one you choose at generation.
