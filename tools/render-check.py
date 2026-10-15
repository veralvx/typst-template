#!/usr/bin/env python3
"""Render the template with Liquid and check the result, without cargo-generate.

A fast local gate for template authors. It answers the questions that only surface *after*
generation otherwise:

  * does every templated file still parse (TOML / YAML / JSON / Nix) once the placeholders are
    substituted, for every combination of prompts?
  * did any placeholder survive into the output unexpanded, or name an undeclared variable?
    (cargo-generate renders a file it cannot render as it stands, and an unknown variable as an
    empty string -- both silently)
  * did a file that must NOT be templated (a workflow, cliff.toml, the justfile, the Typst code,
    the flake) hold one of our placeholders -- and is every binary file (the tests' references)
    excluded, as cargo-generate aborts on one it tries to render?
  * do the placeholder regexes accept their own defaults, Universe's categories and disciplines,
    and the pinned Typst as a `compiler` -- and refuse what Universe would?
  * do `ignore` paths and `.gitattributes`' export-ignore paths exist, and does the latter keep
    every file the package needs?
  * do the licence texts agree -- LICENSE's branch with the file each also is?
  * does each typst.toml describe its kind and licence, and does each case keep exactly the
    licence files its README and its `license` name?
  * are this repository's copies of the template's files still the template's (AGENTS.md, Copies
    stay copies): the files (flake.lock among them), the justfiles' shell recipes?

An approximation: cargo-generate uses the Rust `liquid` crate, this python-liquid. They agree on
the subset used here (assign, if/elsif/else, for, split, strip, date), which is why the template
stays inside it. One known divergence: after a `-%}` trim tag, python-liquid also drops a file's
final newline where liquid-rust keeps it -- so whitespace is the smoke test's to check, not this.

Usage:  python3 tools/render-check.py   (python-liquid and PyYAML; nix-instantiate if on PATH)
Exit:   0 = all good, 1 = at least one check failed.
"""

from __future__ import annotations

import fnmatch
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tomllib

try:
    from liquid import Environment
except ImportError:  # pragma: no cover - dependency hint
    sys.exit("python-liquid is required:  pip install python-liquid")

try:
    import yaml
except ImportError:  # pragma: no cover - dependency hint
    sys.exit("PyYAML is required:  pip install pyyaml")

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "template"
CONFIG = TEMPLATE / "cargo-generate.toml"

# typst/packages' lists (docs/CATEGORIES.md, docs/DISCIPLINES.md; bundler/src/*.rs)
CATEGORIES = (
    "components visualization model layout text languages scripting integration utility fun "
    "book report paper thesis poster flyer presentation cv office"
).split()
DISCIPLINES = (
    "accounting agriculture anthropology archaeology architecture biology business chemistry "
    "communication computer-science design drawing economics education engineering environment "
    "fashion film finance geography geology history journalism law linguistics literature "
    "mathematics medicine music painting philosophy photography physics politics psychology "
    "sociology theater theology transportation"
).split()
# what the package is, which .gitattributes must never export-ignore
PACKAGE = ("typst.toml", "src", "template", "README.md", "LICENSE", "CHANGELOG.md")

# The template's files this repository keeps a copy of, byte for byte (and mode): not rendered here,
# so each original must render to itself
COPIES = (
    "cog.toml",
    "cliff.toml",
    "flake.lock",
    ".editorconfig",
    ".github/release-notes.sh",
    ".githooks/commit-msg",
    ".githooks/pre-push",
    ".github/workflows/style-check-dprint.yml",
    ".github/workflows/style-check-cocogitto.yml",
    ".github/workflows/dependabot-automerge.yml",
)
# the justfile recipes both justfiles hold, the same
COPIED_RECIPES = ("shell-check", "shfmt")

# cargo-generate's built-ins, plus one sample answer per prompt; `CASES` varies the rest.
BASE_VARS = {
    "project-name": "sample-package",
    "crate_name": "sample_package",
    "authors": "Jane Doe <jane@example.com>",
    "username": "jane",
    "os-arch": "linux-x86_64",
    "within_cargo_project": False,
    "is_init": False,
    "author_name": "Jane Doe",
    "author_email": "jane@example.com",
    "github_username": "jane",
    "compiler": "0.14.0",
}
LICENCES = ("MIT OR Apache-2.0", "MIT", "Apache-2.0", "MIT-0")
FULL = {
    "keywords": "greeting, Institute of Something",
    "disciplines": "computer-science, mathematics",
}
EMPTY = {"author_email": "", "keywords": "", "disciplines": ""}
CASES = [
    {"project_kind": kind, "license": lic, "description": "Does a thing well enough to say so.",
     "categories": cats, **extra}
    for kind, cat_choices in (("package", ("", "utility, scripting")), ("template", ("report", "paper, thesis, cv")))
    for cats in cat_choices
    for lic in LICENCES
    for extra in (FULL, EMPTY)
]


def holds(expr: str, vars_: dict[str, object]) -> bool:
    """A conditional's Rhai expression -- comparisons, `&&`, `||`, `!` -- over the answers."""
    python = expr.replace("&&", " and ").replace("||", " or ")
    python = re.sub(r"!(?!=)", " not ", python)
    names = {k.replace("-", "_"): v for k, v in vars_.items()}
    return bool(eval(python, {"__builtins__": {}}, names))  # noqa: S307 - our own config's


# `{{project-name}}` is valid for the Rust liquid crate but the dash parses as subtraction in
# python-liquid, so rewrite the identifier inside tags only -- never in prose that mentions it.
TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)


def normalise(text: str) -> str:
    return TAG.sub(lambda m: m.group(0).replace("project-name", "project_name"), text)


def matches_any(rel: str, globs: list[str]) -> bool:
    return any(
        fnmatch.fnmatch(rel, g) or rel == g or rel.startswith(g.rstrip("/") + "/") for g in globs
    )


def recipe(justfile: pathlib.Path, name: str) -> str | None:
    """A recipe's text: its comments and attributes, its line, its body (blank lines included, to
    the next line at the margin)."""
    lines = justfile.read_text().splitlines()
    for i, line in enumerate(lines):
        if re.match(rf"{re.escape(name)}(\s[^:]*)?:", line):
            start = i
            while start > 0 and lines[start - 1].startswith(("#", "[")):
                start -= 1
            end = i + 1
            while end < len(lines) and (not lines[end] or lines[end][0].isspace()):
                end += 1
            while end > i + 1 and not lines[end - 1].strip():
                end -= 1
            return "\n".join(lines[start:end])
    return None


def main() -> int:  # noqa: C901, PLR0912, PLR0915 - one gate, read top to bottom
    cfg = tomllib.loads(CONFIG.read_text())
    excluded = cfg["template"].get("exclude", [])
    conditionals = cfg.get("conditional", {})
    # every prompt, with the condition it is asked under (None: always); a name may be asked
    # under several, each with its own default and regex
    prompts = [(None, name, spec) for name, spec in cfg["placeholders"].items()] + [
        (expr, name, spec)
        for expr, section in conditionals.items()
        for name, spec in section.get("placeholders", {}).items()
    ]
    env = Environment()
    failures: list[str] = []

    def fail(msg: str) -> None:
        failures.append(msg)
        print(f"  FAIL {msg}")

    def regex_of(name: str, condition: str | None = None) -> list[str]:
        return [spec["regex"] for expr, n, spec in prompts if n == name and "regex" in spec
                and (condition is None or expr == condition)]

    # 1. Every placeholder default satisfies its own regex; the regexes accept and refuse what
    #    Universe does. cargo-generate matches with `is_match`: anchors are the regex's own.
    print("== placeholder defaults and regexes")
    for expr, name, spec in prompts:
        if "regex" in spec and "default" in spec and not re.search(spec["regex"], str(spec["default"])):
            fail(f"{name} ({expr or 'always'}): default {spec['default']!r} rejected by its own regex")
    for regex in regex_of("categories"):
        for category in CATEGORIES:
            if not re.search(regex, category):
                fail(f"categories regex refuses Universe's {category!r}")
        for bad in ("slides", "report, paper, thesis, cv", "Report"):
            if re.search(regex, bad):
                fail(f"categories regex accepts {bad!r}")
    for regex in regex_of("categories", 'project_kind == "template"'):
        if re.search(regex, ""):
            fail("a template package's categories regex accepts none (Universe requires one)")
    for regex in regex_of("disciplines"):
        if not re.search(regex, ", ".join(DISCIPLINES)):
            fail("disciplines regex refuses one of Universe's disciplines")
        if re.search(regex, "astrology"):
            fail("disciplines regex accepts 'astrology'")
    pinned = tomllib.loads((TEMPLATE / "tools.toml").read_text())["typst"]
    major, minor, _ = pinned.split(".")
    for regex in regex_of("compiler"):
        if not re.search(regex, pinned):
            fail(f"compiler regex refuses the pinned Typst, {pinned}")
        patch = pinned.split(".")[2]
        for newer in (f"{major}.{int(minor) + 1}.0", f"{major}.{minor}.{int(patch) + 1}"):
            if re.search(regex, newer):
                fail(f"compiler regex accepts {newer}, above the pinned Typst ({pinned}): CI could not test it")
        if re.search(regex, "0.11.0"):
            fail("compiler regex accepts 0.11.0, below what the checks are verified on")
    for regex in regex_of("github_username"):
        for bad in ("a--b", "-a", "a-", "a" * 40):
            if re.search(regex, bad):
                fail(f"github_username regex accepts {bad!r}, which Universe's `<@handle>` refuses")
    for regex in regex_of("author_name"):
        if re.search(regex, "Jane <Doe>"):
            fail("author_name regex accepts angle brackets, which break typst.toml's `<@handle>`")
    print(f"  checked {len(prompts)} prompts")

    # 2. `ignore` entries are literal paths, not globs: cargo-generate joins each onto its copy of
    #    the template and removes it; a glob resolves to nothing and ships the file silently.
    print("== conditional ignore paths")
    for expr, section in conditionals.items():
        for entry in section.get("ignore", []):
            if any(ch in entry for ch in "*?["):
                fail(f"{expr}: ignore entry {entry!r} looks like a glob; ignore takes literal paths")
            elif not (TEMPLATE / entry).exists():
                fail(f"{expr}: ignore entry {entry!r} does not exist in the template")
    print(f"  checked {sum(len(s.get('ignore', [])) for s in conditionals.values())} paths")

    # 3. .gitattributes' export-ignore paths exist (a stale one is dead weight), and none of
    #    them is the package itself.
    print("== export-ignore paths")
    for line in (TEMPLATE / ".gitattributes").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        path, *attributes = line.split()
        if attributes != ["export-ignore"] or not path.startswith("/"):
            fail(f".gitattributes: {line!r} is not `/<path> export-ignore`")
            continue
        if not (TEMPLATE / path.lstrip("/")).exists():
            fail(f".gitattributes: {path} does not exist in the template")
        if path.lstrip("/") in PACKAGE:
            fail(f".gitattributes: {path} is the package's, which typst/packages must get")

    # 4. This repository's copies are the template's: the files (an original holding Liquid would
    #    render to something else; flake.lock, so the tools are those a project pins), the shell
    #    recipes, dprint's plugins.
    print("== copies of the template's files")
    for rel in COPIES:
        original, copy = TEMPLATE / rel, ROOT / rel
        if not copy.is_file() or not original.is_file():
            fail(f"{rel}: missing, here or in template/")
            continue
        if copy.read_bytes() != original.read_bytes():
            fail(f"{rel} differs from template/{rel}: change the original, then copy it")
        if os.access(copy, os.X_OK) != os.access(original, os.X_OK):
            fail(f"{rel}: executable here or in template/, not both")
        if not matches_any(rel, excluded) and TAG.search(original.read_text()):
            fail(f"template/{rel} holds Liquid: its copy here would not be what it renders to")
    for name in COPIED_RECIPES:
        mine, theirs = recipe(ROOT / "justfile", name), recipe(TEMPLATE / "justfile", name)
        if mine is None or theirs is None:
            fail(f"justfile recipe {name}: missing, here or in template/")
        elif mine != theirs:
            fail(f"justfile recipe {name} differs from template/justfile's")
    plugins = [
        json.loads(re.sub(r"(?m)^\s*//.*$", "", (d / "dprint.json").read_text()))["plugins"]
        for d in (ROOT, TEMPLATE)
    ]
    if plugins[0] != plugins[1]:
        fail("dprint.json's plugins are not template/dprint.json's")
    print(f"  checked {len(COPIES)} files, {len(COPIED_RECIPES)} recipes, the plugins")

    nix = shutil.which("nix-instantiate")
    files = sorted(
        p for p in TEMPLATE.rglob("*")
        if p.is_file() and p.name not in ("cargo-generate.toml", "validate-name.rhai")
    )

    # 5. Every variable referenced in a templated file is declared or built in (an unknown one
    #    renders as an empty string), and every file that is not UTF-8 is excluded.
    print("== variable references, binary files")
    builtins = {
        "project-name", "crate_name", "crate_type", "authors",
        "username", "os-arch", "within_cargo_project", "is_init",
    }
    known = builtins | {name for _, name, _ in prompts}
    ident = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
    literal = re.compile(r"\"[^\"]*\"|'[^']*'")
    reserved = {
        "if", "elsif", "else", "endif", "unless", "endunless", "for", "endfor", "in", "assign",
        "and", "or", "contains", "true", "false", "nil", "empty", "forloop", "last", "first",
        "now", "strip", "split", "date", "downcase", "upcase", "join", "size",
    }
    refs = 0
    for path in files:
        rel = str(path.relative_to(TEMPLATE))
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            if not matches_any(rel, excluded):
                fail(f"{rel} is not UTF-8 but not excluded: cargo-generate would abort on it")
            continue
        if matches_any(rel, excluded):
            continue
        local = set(re.findall(r"assign\s+([A-Za-z_][A-Za-z0-9_]*)\s*=", text))
        local |= set(re.findall(r"for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in", text))
        for match in TAG.finditer(text):
            expr = literal.sub("", match.group(0).strip("{}%- "))
            for token in ident.findall(expr):
                refs += 1
                if token not in reserved and token not in known and token not in local:
                    fail(f"{rel}: unknown variable {token!r} -- it would render as an empty string")
    print(f"  checked {refs} identifier references")

    # 6. Excluded files are free of *our* placeholders: copied verbatim, one would ship unexpanded.
    print("== exclude list integrity")
    ours = {name for _, name, _ in prompts} | {"project-name", "crate_name", "authors"}
    count = 0
    for path in files:
        rel = str(path.relative_to(TEMPLATE))
        if not matches_any(rel, excluded):
            continue
        count += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for var in ours:
            if re.search(r"\{\{\s*" + re.escape(var) + r"\s*\}\}", text):
                fail(f"{rel} is on the exclude list but contains {{{{{var}}}}}")
    print(f"  checked {count} excluded files")

    def render(rel: str, vars_: dict[str, object]) -> str:
        return env.from_string(normalise((TEMPLATE / rel).read_text())).render(**vars_)

    # 7. The licence texts agree: LICENSE's branch for a licence is the file it also is (the
    #    dual licence's texts, a template's MIT-0 text).
    print("== licence copies")
    for licence, copy in (("MIT", "LICENSE-MIT"), ("Apache-2.0", "LICENSE-APACHE"), ("MIT-0", "LICENSE-MIT-0")):
        vars_ = {**BASE_VARS, **CASES[0], "license": licence, "project_name": "sample-package"}
        if render("LICENSE", vars_) != render(copy, vars_):
            fail(f"LICENSE's {licence} text differs from {copy}")

    # 8. Render every case and validate the output.
    for case in CASES:
        vars_ = {**BASE_VARS, **case}
        vars_["project_name"] = vars_["project-name"]
        kind, licence = case["project_kind"], case["license"]
        label = f"{kind}/{licence}/[{case['categories']}]" + ("/empty" if case["keywords"] == "" else "")
        print(f"== render {label}")

        ignored: list[str] = []
        for expr, section in conditionals.items():
            if holds(expr, vars_):
                ignored.extend(section.get("ignore", []))

        rendered = 0
        outputs: dict[str, str] = {}
        for path in files:
            rel = str(path.relative_to(TEMPLATE))
            if matches_any(rel, ignored):
                continue
            if matches_any(rel, excluded):
                if path.suffix in (".png",):
                    continue
                out = path.read_text(encoding="utf-8")
            else:
                try:
                    out = render(rel, vars_)
                except Exception as exc:  # noqa: BLE001 - report and continue
                    fail(f"{label}: {rel}: liquid error: {exc}")
                    continue
                leftovers = TAG.findall(out)
                if leftovers:
                    fail(f"{label}: {rel}: unexpanded template syntax: {leftovers[:3]}")
                rendered += 1
            outputs[rel] = out
            try:
                if path.suffix == ".toml":
                    tomllib.loads(out)
                elif path.suffix in (".yml", ".yaml"):
                    yaml.safe_load(out)
                elif path.suffix in (".json", ".lock"):
                    json.loads(re.sub(r"(?m)^\s*//.*$", "", out))
                elif path.suffix == ".nix" and nix:
                    parsed = subprocess.run(
                        [nix, "--parse", "-"], input=out, capture_output=True, text=True, check=False
                    )
                    if parsed.returncode != 0:
                        raise ValueError(parsed.stderr.strip())
            except Exception as exc:  # noqa: BLE001 - report and continue
                fail(f"{label}: {rel}: invalid {path.suffix.lstrip('.')} after render: {exc}")

        # 9. typst.toml describes the case as Universe reads it.
        manifest = tomllib.loads(outputs["typst.toml"])
        package = manifest["package"]
        expected = {
            ("template", "MIT OR Apache-2.0"): "(MIT OR Apache-2.0) AND MIT-0",
            ("template", "MIT"): "MIT AND MIT-0",
            ("template", "Apache-2.0"): "Apache-2.0 AND MIT-0",
        }.get((kind, licence), licence)
        if package["license"] != expected:
            fail(f"{label}: license is {package['license']!r}, expected {expected!r}")
        if package["authors"] != ["Jane Doe <@jane>"]:
            fail(f"{label}: authors is {package['authors']!r}")
        if ("template" in manifest) != (kind == "template"):
            fail(f"{label}: [template] present={('template' in manifest)} for {kind}")
        if kind == "template" and not package.get("categories"):
            fail(f"{label}: a template package needs a category")
        for key in ("keywords", "categories", "disciplines"):
            want = [item.strip() for item in case[key].split(",") if item.strip()]
            if package.get(key, []) != want:
                fail(f"{label}: {key} is {package.get(key)!r}, expected {want!r}")
        if len(package.get("categories", [])) > 3:
            fail(f"{label}: more than three categories")
        entry = manifest.get("template", {}).get("path")
        if entry and f"{entry}/main.typ" not in outputs:
            fail(f"{label}: [template] path {entry} has no main.typ")
        lib = outputs["src/lib.typ"]
        module = "report" if kind == "template" else "greet"
        if f'#import "{module}.typ": {module}' not in lib or f"src/{module}.typ" not in outputs:
            fail(f"{label}: src/lib.typ does not import the {kind}'s module, or it is missing")

        # 10. The licence files: LICENSE always; the dual licence's two texts; a template's MIT-0
        #     text unless MIT-0 is the whole package's -- and each one the README links exists.
        want = {"LICENSE"}
        if licence == "MIT OR Apache-2.0":
            want |= {"LICENSE-MIT", "LICENSE-APACHE"}
        if kind == "template" and licence != "MIT-0":
            want.add("LICENSE-MIT-0")
        have = {rel for rel in outputs if rel.startswith("LICENSE")}
        if have != want:
            fail(f"{label}: licence files {sorted(have)}, expected {sorted(want)}")
        for link in re.findall(r"\]\((LICENSE[^)]*)\)", outputs["README.md"]):
            if link not in outputs:
                fail(f"{label}: README.md links {link}, which this case does not keep")

        print(f"  rendered {rendered} files, manifest checks done")

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
