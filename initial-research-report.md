# Building a CLI Scaffolder with Copier as the Core Engine

## Executive summary

You can build a “`setup`” CLI that scaffolds **repeatable full-stack project stacks** (e.g., Angular + FastAPI + SQLAlchemy) by treating **Copier templates as composable “feature packs”** and writing a thin orchestration layer that applies them in a deterministic order, records their state, and can later update them. Copier is well-suited because it is explicitly designed not just for initial scaffolding but for **ongoing lifecycle management**, including **smart updates** from Git-tagged template versions and **versioned migrations**. citeturn11view0turn16view0turn14view0

A pragmatic architecture is:

1. **CLI UX layer:** Python CLI built with **Typer** for ergonomics and packaging patterns (typed options/arguments, subcommands), with **Rich** for clear progress, tables, and error presentation. citeturn19view0turn19view2turn18search3  
2. **Template application engine:** call Copier via the **Python API** (`run_copy`, `run_update`) so you can programmatically pass data, set answers-file paths, and handle exceptions. citeturn26view0turn32view0  
3. **Composition model:** represent each feature (fastapi/angular/sqlalchemy/etc.) as either:
   - an **independent Copier template** applied into the same destination using its **own answers file**, which Copier explicitly supports; or  
   - a “base template” that directly renders optional blocks for features (less modular, but fewer file conflicts). citeturn15view0turn12view0  
4. **State tracking:** write a `setup.lock.yml` (your tool’s lockfile) that records the selected features, their template refs/tags, and the answers file used for each, aligning with Copier’s model of “one answers file per applied template.” citeturn15view0turn16view0  

Key tradeoffs you must design around:

- **File conflicts:** applying multiple templates into the same directory is powerful, but you need a conflict policy (fail fast vs. allow overrides vs. structured merges). Copier’s update workflow can surface conflicts as inline markers or `.rej` files, but your “multi-feature overlay” needs its own, earlier detection. citeturn16view0turn13view3  
- **Security:** Copier deliberately gates “unsafe” features (tasks, migrations, Jinja extensions) behind `--trust/--UNSAFE`, but recent advisories show “safe template” assumptions can still be risky if you run untrusted templates or are on vulnerable Copier versions. Your CLI should adopt a strict trust-and-pinning stance by default. citeturn15view0turn20view0turn31search8turn30view2  

Open items you should keep configurable (because you did not specify constraints): Python/Node versions, default ports, DB engine (postgres/sqlite), containerization strategy (Docker vs. none), and formatter/linter toolchains. Copier supports typed questions and defaults in `copier.yml`, so you can keep these as user-facing prompts or flags. citeturn12view0turn22view0

## Copier vs Cookiecutter and Hygen

Copier’s core differentiator is **first-class updating**: it expects templates to be versioned (Git tags) and supports updating generated projects while trying to respect downstream edits. This is why Copier describes itself as a **code lifecycle management tool**, not merely a scaffolder. citeturn11view0turn16view0

### Comparison table

| Dimension | Copier | Cookiecutter | Hygen |
|---|---|---|---|
| Primary purpose | Project templating **plus updates** (lifecycle management) citeturn11view0turn16view0 | Project scaffolding (no native updating) citeturn11view0 | In-project code generator (best at local generators + injection) citeturn7view1turn10search1 |
| Template updates | Built-in `copier update`; uses Git tags & diffs citeturn16view0turn11view0 | Not built-in; updates typically require external tooling (e.g., Cruft) citeturn11view0 | Not a “template update” system; focus is generating/injecting code citeturn10search1turn7view1 |
| Hooks/tasks | `_tasks` and `_migrations` (unsafe-gated) citeturn14view0turn13view2 | Hooks supported (`pre_prompt`, `pre_gen_project`, `post_gen_project`, etc.) citeturn7view2 | Can run shell actions; strong injection story citeturn10search1turn10search19 |
| Migrations for template evolution | First-class migrations with version constraints and stage variables citeturn13view2turn16view0 | No native equivalent; you code it in hooks or external processes citeturn7view2 | No native “versioned migrations” model; you implement in generators citeturn7view1turn10search19 |
| “Injection into existing files” | Not a core primitive; usually handled via deliberate design, tasks, or structured merges (your responsibility) citeturn13view1turn14view0 | Not a core primitive; you implement in hooks or templates citeturn7view2 | Core capability (`inject: true`, `skip_if`, `before/after`, etc.) citeturn10search1 |

### Why choose Copier for a “stack scaffolder” CLI

Copier is a good fit when you care about:

- **Reproducible stacks that evolve**: you can regenerate/update projects as the template versions advance, instead of “copy once, diverge forever.” citeturn16view0turn11view0  
- **Versioned updates + migrations**: Copier’s update process explicitly includes pre/post migration stages and a conflict strategy (`rej` vs `inline`). citeturn16view0turn13view2turn13view3  
- **Composing multiple templates**: Copier documents a pattern for applying multiple independent templates to the same directory by using a different answers file for each template, and updating each independently later. This is a direct conceptual match for your “base + feature packs” goal. citeturn15view0  

### Where Hygen can be better

If your main pain is **surgically editing existing files** (e.g., adding a dependency to an existing `package.json` or inserting a new export line), Hygen’s injection model is purpose-built: templates can declare `inject: true`, specify insertion anchors (`before/after`, `append/prepend`, etc.), and guard against double insertions (`skip_if`). citeturn10search1turn10search0

In a Copier-centered scaffolder, you typically handle this by:

- designing base templates to include feature “slots,” or  
- converting shared configuration files into structured data merges, or  
- executing post-copy tasks that patch files (with all the security/portability tradeoffs that implies). citeturn14view0turn12view0

## Recommended CLI stack and how it orchestrates Copier

A clean, “Python-native” approach is:

- **Typer** for CLI surface area (subcommands, typed flags, help text, completions). Typer’s docs and the PyPA CLI packaging guide show Typer-based CLIs paired with standard packaging entry points. citeturn19view0turn21view1  
- **Rich** for terminal UX: progress bars for long runs and tables for stack/feature listing. Rich explicitly supports multi-task progress and a `Table` abstraction for tabular output. citeturn19view2turn18search3  
- **Copier Python API** (`run_copy`, `run_update`, `run_recopy`) for deterministic orchestration and structured error handling instead of shelling out. The API exposes key switches like `answers_file`, `vcs_ref`, `defaults`, `overwrite`, `unsafe`, and `skip_tasks`. citeturn32view0turn26view0  

### Orchestration responsibilities

Your CLI becomes a “composition controller” that:

- resolves selected features and their dependencies (topological sort);  
- for each template, calls `run_copy(..., dst_path=<project>, answers_file=<feature answers>, data=<merged answers>, vcs_ref=<pinned tag>)`;  
- writes/updates a `setup.lock.yml` so you can list/update later;  
- optionally creates a Git repo and initial commits in a controlled manner.

Copier supports “settings from CLI/API args” plus “answers from CLI/API args,” and also defines an **answer precedence order** (CLI/API > prompt > last answers > template defaults). This is essential for designing `--non-interactive` behavior. citeturn12view0turn32view0  

### Minimal Typer skeleton

```python
# setup_cli/cli.py
import typer
from rich.console import Console

app = typer.Typer(help="Project scaffolder built on Copier")
console = Console()

@app.command()
def init(
    directory: str = typer.Argument(..., help="Target directory to create"),
    angular: bool = typer.Option(False, help="Add Angular frontend"),
    fastapi: bool = typer.Option(False, help="Add FastAPI backend"),
    sqlalchemy: bool = typer.Option(False, help="Add SQLAlchemy persistence"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Use defaults / provided values only"),
):
    console.print(f"Initializing project in {directory}...")
    # resolve feature plan -> apply templates via copier.run_copy()

@app.command()
def add(feature: str, directory: str = "."):
    console.print(f"Adding feature {feature} to {directory}...")
    # apply one feature pack template

@app.command()
def list(directory: str = "."):
    console.print(f"Listing applied features for {directory}...")
    # read setup.lock.yml and/or .copier-answers.*.yml files

def main():
    app()

if __name__ == "__main__":
    main()
```

This is intentionally thin: the “real” design work is in feature resolution, file conflict policies, and safe Copier invocation. citeturn32view0turn12view0  

## Template repo layout and concrete Copier examples

### Layout: base template and feature packs

Copier recommends **one template per Git repository** to avoid tag collisions, because tags are used to reason about versions during smart updates. citeturn24view0turn16view0

A production-grade base template repo often looks like:

```text
base-template/
  copier.yml
  README.md
  template/                  # actual rendered content
    {{ _copier_conf.answers_file }}.jinja
    backend/
    frontend/
    docker-compose.yml.jinja
    ...
```

and uses:

```yaml
# copier.yml
_subdirectory: template
```

so the template’s “repo-only” files (docs, release tooling, tests) don’t end up in generated projects. citeturn24view0turn14view0

A feature pack template repo is similar, but should ideally limit itself to a well-scoped subtree and a small number of shared integration points.

### Required answers file template

Copier expects templates intended for updates (and multi-template application) to include the answers-file template `{{ _copier_conf.answers_file }}.jinja`, and documents the canonical content using `_copier_answers|to_nice_yaml`. citeturn7view3turn14view0

```jinja
# {{ _copier_conf.answers_file }}.jinja
# Changes here will be overwritten by Copier; NEVER EDIT MANUALLY
{{ _copier_answers|to_nice_yaml -}}
```

Copier explicitly warns you not to edit generated answers files manually because it undermines the smart diff/update algorithm. citeturn16view0turn15view0

### Example base `copier.yml` with “stack-level” questions

```yaml
# copier.yml (base)
_subdirectory: template

project_name:
  type: str
  help: Project name

python_package:
  type: str
  help: Python package/module name

use_docker:
  type: bool
  default: true
  help: Include Docker Compose / Dockerfiles?

frontend_port:
  type: int
  default: 4200

backend_port:
  type: int
  default: 8000
```

Copier supports typed questions (`str`, `int`, `bool`, `yaml`, etc.), defaults, and choice validation, allowing you to keep a single “stack questionnaire” consistent across templates. citeturn12view0

### Jinja usage and template suffix

In modern Copier versions (7+), Copier uses **Jinja defaults**; older versions used bracket-based delimiters, and the docs show how to preserve old behavior using `_envops`. This matters if you import or fork older templates. citeturn27view1turn28view0  

A simple template file:

```jinja
# template/backend/app/main.py.jinja
from fastapi import FastAPI

app = FastAPI(title="{{ project_name }}")

@app.get("/health")
def health():
    return {"status": "ok"}
```

Copier renders files that end with `.jinja` by default (`_templates_suffix` is configurable), and otherwise copies files verbatim. citeturn7view3turn14view0

### Hooks in Copier: tasks and migrations

Copier provides two primary “hook-like” mechanisms:

- **Tasks (`_tasks`)** run after generating **or updating** and execute in order in subprocesses. The docs describe dict/array/string formats, conditions (`when`), and OS-specific branching. citeturn14view0turn13view1  
- **Migrations (`_migrations`)** are like tasks but are **update-only**, and can be version-gated and run in “before/after” stages with well-defined version environment variables. citeturn13view2turn16view0  

Tasks example:

```yaml
# copier.yml
_tasks:
  - command: ["git", "init"]
    when: "{{ _copier_operation == 'copy' }}"
  - command: ["pre-commit", "install"]
    when: "{{ use_docker == false }}"
```

Migrations example:

```yaml
# copier.yml
_migrations:
  - version: v1.2.0
    command: ["python", "-m", "alembic", "revision", "--autogenerate", "-m", "update schema"]
    when: "{{ _stage == 'after' }}"
```

Important security note: tasks/migrations are considered **unsafe features**; Copier disables them unless the user explicitly trusts the template (via `--trust/--UNSAFE` or trusted settings). citeturn24view0turn20view0turn22view0  

### Update strategy: pinning and tags

Copier selects template versions from Git tags (sorted as PEP 440) and can update to the latest tag or a specific ref (`--vcs-ref`). For updates to work best, Copier recommends: template contains answers file, template is versioned with Git tags, and destination is git-tracked. citeturn22view0turn16view0turn6search14  

For a “setup CLI,” this implies your feature manifest should record template sources and pinned tags, so two developers running `setup init` get identical stacks.

## Composition algorithm and feature metadata design

### Copier-native composition mechanism

Copier documents an explicit “apply multiple templates to the same subproject” workflow:

- create a directory and initialize Git  
- apply template A with `copier copy -a <answersA> <templateA> .`  
- commit  
- apply template B with `copier copy -a <answersB> <templateB> .`  
- …and update each later with `copier update -a <answersX>` citeturn15view0  

This is the most direct foundation for “base + feature packs.” Your CLI simply automates the planning and the repeated `copy` operations, while also ensuring predictable ordering and conflict checks.

### Recommended feature manifest format

A single manifest file per feature pack (YAML recommended) keeps your CLI decoupled from Copier internals while still aligning with Copier’s YAML-centric approach. Copier itself also supports splitting YAML config with `!include`, which is useful if you want to share question fragments across templates. citeturn17search2turn12view0  

A minimal manifest schema that supports composition:

| Field | Type | Why it exists |
|---|---|---|
| `id` | string | Stable identifier (used in answers filename, lockfile, CLI flags) |
| `name` / `description` | string | UX (`setup list`, prompts) |
| `template` | string | Copier template source (local path / Git URL / `gh:` shortcut) citeturn22view0turn28view0 |
| `ref` | string | Pinned tag/branch/commit; align with `--vcs-ref` citeturn22view0turn16view0 |
| `answers_file` | string | Stable per-feature answers file (Copier expects one per applied template) citeturn15view0 |
| `depends_on` | list[string] | Dependency ordering (topological sort) |
| `conflicts_with` | list[string] | Mutual exclusivity (e.g., `sqlalchemy` vs `django-orm`) |
| `writes` | list[string] | Expected file globs for conflict detection (your policy layer) |
| `merge_policy` | object | How to resolve overlaps when allowed (owner, structured merge, etc.) |
| `vars` | object | Defaults/overrides for Copier questions (mapped to `data`/`data_file`) citeturn16view0turn22view0 |

Example manifest:

```yaml
# features/fastapi/feature.yml
id: fastapi
name: FastAPI backend
template: gh:your-org/template-fastapi
ref: v0.3.0
answers_file: .copier-answers.fastapi.yml

depends_on: [python-base]
conflicts_with: [django]

writes:
  - backend/**
  - docker-compose.yml
merge_policy:
  docker-compose.yml:
    strategy: structured_merge
    format: yaml

vars:
  backend_port: 8000
```

### Composition and apply algorithm

A robust algorithm should be explicit about ordering, conflict handling, and idempotency.

```mermaid
flowchart TD
  A[Parse CLI inputs] --> B[Resolve features from flags/stack name]
  B --> C[Load feature manifests]
  C --> D[Validate: conflicts, missing deps, cycles]
  D --> E[Compute apply order: base then topo-sort features]
  E --> F[Preflight: check destination, trust policy, pinned refs]
  F --> G[Plan file writes & detect conflicts]
  G -->|conflicts not allowed| H[Abort with actionable report]
  G --> I[Apply templates in order]
  I --> J[For each template: copier run_copy with answers_file]
  J --> K[Run orchestrator post-steps (format, git init/commit optional)]
  K --> L[Write setup.lock.yml]
  L --> M[Done]
```

This design is grounded in Copier’s documented “apply multiple templates” model and its answers-file conventions, but adds a missing layer: **feature dependency resolution and conflict policy**, which Copier does not provide because Copier is not a multi-template dependency manager. citeturn15view0turn14view0turn32view0  

### Conflict detection and resolution policies

Copier “won’t overwrite existing files unless instructed,” which is helpful, but not sufficient as a composition policy because you must decide *what to do* when a later feature pack needs to add content to a shared file. citeturn28view0turn32view0  

Recommended policy tiers:

- **Tier one: forbid overlapping ownership by default.**  
  If two features claim they write the same path (via `writes` globs), error out with a clear message and suggested resolutions (pick one feature, or use a different stack). This keeps the system predictable.

- **Tier two: allow overlaps only for explicitly “mergeable” files.**  
  Examples: `docker-compose.yml`, `.pre-commit-config.yaml`, `pyproject.toml`, `package.json`. Here you can implement “structured merges,” or designate a single owner template and force overrides. Copier itself supports `exclude` / `skip_if_exists` patterns, but cross-template merging is your responsibility. citeturn27view1turn24view0turn14view0  

- **Tier three: user-mediated conflicts.**  
  For updates, Copier already supports explicit conflict handling (`--conflict inline` vs `--conflict rej`). For your composition step, you can mimic this UX by writing conflict markers or generating `.rej` patches, but that’s a custom feature—Copier’s conflict mechanism is primarily described for `update`. citeturn16view0turn13view3turn32view0  

### Idempotency expectations

For a scaffolder, “idempotent” means:

- `setup init` run twice should either:
  - refuse to run because destination exists (safe default), or  
  - run with `--force`/`--overwrite` semantics explicitly chosen. citeturn32view0turn28view0  

- `setup add fastapi` run twice should not duplicate actions. Achieve this via:
  - refusing to apply an already-applied feature (tracked in `setup.lock.yml`), and/or  
  - using `skip_if_exists` to preserve generated secrets/config once created. citeturn24view0turn15view0  

Copier’s own `skip_if_exists` semantics are explicitly designed for “generate once, preserve on future runs,” and are a key part of making repeated renders safe. citeturn24view0turn14view0

## Implementation notes, distribution, updates, and security

### Invoking Copier programmatically vs shelling out

Prefer programmatic invocation for:

- passing structured `data` and “answers_file per feature” deterministically,  
- catching typed exceptions (unsafe template errors, task errors, interrupt handling),  
- writing your own retry/cleanup logic, and  
- integrating with Rich progress output.

Copier’s API surface includes `run_copy`, `run_update`, and `run_recopy`, all of which accept `answers_file`, `vcs_ref`, `overwrite`, `defaults`, `unsafe`, and other controls. citeturn32view0turn26view0

Key behavior notes you can build on:

- Copier’s docs show you can use `copier.run_copy(...)` directly from Python, and that templates can be local paths or Git URLs (including `gh:` and `gl:` shortcuts). citeturn22view0turn28view0  
- Copier can raise `CopierAnswersInterrupt` during interactive prompts; the API docs describe it as an opportunity to persist partially completed answers. This is relevant if your CLI offers an interactive mode and wants to avoid losing progress on Ctrl+C. citeturn32view0  

### Interactive vs non-interactive runs

Copier’s update docs describe patterns for non-interactive behavior:

- `copier update --defaults` to reuse previous answers without prompting.  
- `copier update --defaults --data key="value"` to change one answer while keeping others.  
- Use a data file (`--data-file`) for more complex cases, with a noted limitation for multiselect updates. citeturn16view0turn18search6  

In automation contexts, running Copier “non-interactively” can still be subtle; a recent issue reports that under some conditions the interactive TUI can appear even with `--defaults --skip-answered`, requiring stdin to be closed. If your CLI runs Copier in scripts/CI, you should explicitly manage stdin and provide an unambiguous `--non-interactive` mode that refuses to prompt. citeturn18search1turn6search16  

### Post-hooks: formatting, git init, alembic, etc.

Copier `_tasks` are the native way to run post-generation commands, and can be conditional and OS-specific. This is where you might:

- initialize a git repo,  
- run `pre-commit install`,  
- run formatters,  
- set up initial DB migrations (e.g., Alembic) or front-end installs.

However, tasks are **unsafe-gated** and run with the same privileges as the user. Your CLI should treat them as an explicit opt-in and prefer to centralize “stack-wide” tasks in your orchestrator (so they run once), instead of duplicating tasks across multiple feature templates. citeturn14view0turn24view0turn22view0  

### Packaging and distribution

For distribution, follow standard Python packaging patterns:

- Define an executable via `[project.scripts]` in `pyproject.toml` (console entry point). The PyPA guide shows this directly and demonstrates installing the CLI with pipx. citeturn21view1turn21view0  
- Recommend installation via pipx for end-user CLIs, since pipx installs apps into isolated environments and exposes their scripts on PATH. citeturn3search8turn21view0  

Example snippet:

```toml
# pyproject.toml
[project]
name = "setup"
version = "0.1.0"
dependencies = ["typer>=0.12", "rich>=13", "copier>=9"]

[project.scripts]
setup = "setup_cli.cli:main"
```

### CI for templates: linting and test generation

Template CI is critical because you are shipping code generators.

Two practical testing layers:

- **Render tests:** in CI, generate a project from each template and run basic assertions (files exist, configuration parses, etc.). Copier can render from local paths or pinned refs; so CI can generate from “current HEAD” then from a tagged release. citeturn22view0turn16view0  
- **Template test tooling:** there are pytest plugins and tools specifically aimed at testing Copier templates (e.g., `pytest-copier` and template-testing utilities), which provide fixtures to generate and clean up projects under pytest. citeturn23search0turn23search6turn23search34  

### Versioning strategy for templates

Copier’s update mechanism is deeply tied to Git tags:

- It reads tags, compares them as PEP 440, and selects a version to copy/update from; updates are “smart diffs” between versions. citeturn16view0turn22view0turn11view0  
- Because tags are shared across a repo, Copier explicitly warns against hosting multiple independent templates in one Git repo (for production). citeturn24view0  

For your feature pack manifests, the practical implication is: store `template` + `ref` in the manifest and in `setup.lock.yml`, and default to pinned tags (not floating branches).

### Security considerations and trust model

Copier’s documentation and recent advisories imply you should adopt a strict stance:

- Copier warns to generate projects only from trusted templates because tasks run with user-level access. citeturn22view0  
- Copier treats tasks, migrations, and Jinja extensions as **unsafe features** and requires explicit `--trust/--UNSAFE` (or trusted locations configured in settings) to enable them. citeturn24view0turn20view0  
- Users can configure trusted template locations/prefixes in Copier’s settings (`trust:` list), which your CLI can lean on rather than inventing its own separate trust file. citeturn20view0turn26view0  

Recent vulnerability disclosures also matter operationally:

- CVE-2025-55214 describes that “safe templates” could write outside destination paths in affected Copier versions, with fixed version guidance (e.g., upgrade to at least 9.9.1 per the GitLab advisory database). citeturn30view2  
- CVE-2026-23968 (and related GHSA) describes filesystem read access via symlinks in safe templates, patched in newer versions (e.g., 9.11.2 per NVD). citeturn31search8turn31search0  

Practical mitigations your `setup` CLI can enforce:

- Require pinned refs (tags/commits) and refuse floating `main`/`master` unless `--allow-floating`. citeturn16view0turn22view0  
- Default to **no unsafe features** unless the template is in Copier trusted locations *and* the user passes `--trust`. citeturn24view0turn20view0  
- Provide a “safe mode” that sets `skip_tasks=True` and never enables `unsafe=True`; note that `skip_tasks` does not skip migrations. citeturn24view0turn32view0  
- Document minimum supported Copier versions for your CLI and templates to ensure patched behavior where relevant. citeturn24view0turn31search8turn30view2  

### Update workflow and surfacing conflicts

Your CLI should offer `setup update` that:

- reads `setup.lock.yml` (or enumerates `.copier-answers.*.yml` files),  
- runs `copier update` per applied template (or `run_update` programmatically) using the correct answers file,  
- chooses a conflict style (inline or `.rej`) and reports conflicts clearly.

Copier documents how its update algorithm works (regenerate fresh project, diff, apply pre-migrations, update, reapply diff, post-migrations) and how conflicts are represented, with recommended Git/pre-commit practices to avoid committing unresolved conflicts. citeturn16view0turn13view3  

## Minimal proof-of-concept plan

### Starter repo structure

A minimal PoC can live in one repo (local templates), but you should treat it as a prototype; for production, split templates into separate repos with tags. citeturn24view0turn16view0  

```text
setup/
  pyproject.toml
  src/
    setup_cli/
      __init__.py
      cli.py
      registry.py            # loads feature manifests
      composer.py            # resolves plan and applies Copier templates
      lockfile.py            # reads/writes setup.lock.yml
  templates/
    base/
      copier.yml
      template/
        {{ _copier_conf.answers_file }}.jinja
        backend/...
        frontend/...
    feature-fastapi/
      copier.yml
      template/
        {{ _copier_conf.answers_file }}.jinja
        backend/app/main.py.jinja
        backend/requirements.txt.jinja
    feature-angular/
      copier.yml
      template/
        {{ _copier_conf.answers_file }}.jinja
        frontend/...
  features/
    fastapi/feature.yml
    angular/feature.yml
    sqlalchemy/feature.yml
```

The templates use `_subdirectory: template` so metadata doesn’t leak into generated projects. citeturn24view0turn14view0  

### PoC templates

- **Base template**: creates directory layout similar to your example (backend + frontend + docker compose scaffolding) and asks only for a few stable variables (project name, ports). citeturn12view0turn7view3turn28view0  
- **feature-fastapi**: adds a minimal FastAPI app file and requirements, ideally confined to `backend/`. citeturn7view3turn22view0  
- **feature-angular**: adds minimal angular structure under `frontend/` (in PoC, stub files are fine; in real templates you may generate via Angular CLI, but that’s outside Copier’s core and would likely be a task/hook). Tasks are possible but unsafe-gated. citeturn14view0turn24view0  

### PoC Typer + Copier integration

In `composer.py`, implement:

- `resolve_features(flags) -> ordered_feature_ids`
- `apply_feature(feature, dst, answers_file, data, vcs_ref)` using `copier.run_copy`

Example invocation:

```python
from pathlib import Path
from copier import run_copy

def apply_template(template_path: str, dst: Path, answers_file: str, data: dict, *, vcs_ref: str | None):
    run_copy(
        src_path=template_path,
        dst_path=str(dst),
        answers_file=answers_file,
        data=data,
        vcs_ref=vcs_ref,
        overwrite=False,
        defaults=True,        # for non-interactive mode
        unsafe=False,         # PoC: keep safe by default
        skip_tasks=True,      # PoC: avoid tasks entirely unless user opts in
    )
```

These parameters align with Copier’s API surface for `run_copy`. citeturn32view0turn22view0  

### Local getting-started steps

- Install your CLI in editable mode and run it to scaffold a project directory.  
- Ensure each template includes the answers-file template so Copier can record state. citeturn14view0turn7view3  

Example flow:

1. Create venv and install:
   - `pip install -e .`
2. Generate a stack:
   - `setup init myproj --fastapi --angular --sqlalchemy`
3. Verify that `.copier-answers.*.yml` files exist (one per applied template) and that `setup.lock.yml` was written by your CLI. Copier’s docs show and rely on this answers-file mechanism for updates and multi-template application. citeturn15view0turn16view0turn14view0  

### Publishing steps

For publishing the CLI:

- Add `[project.scripts]` so pip/pipx installs a `setup` executable. citeturn21view1turn21view0  
- Recommend `pipx install setup` (or `pipx install .` for local) to keep it isolated. citeturn21view0turn3search8  
- Follow the PyPA packaging flow to build and upload distributions; the PyPA CLI guide explicitly points you to “Packaging your project” for publishing. citeturn21view0turn21view2  

For publishing templates:

- Put each template in its own Git repo (production), add Git tags per release, and reference those tags in your feature manifests. This aligns with Copier’s update model and avoids tag collisions. citeturn24view0turn16view0turn11view0  

### Optional integrations: repo creation from templates

If you want `setup init` to also create a remote repository, note that entity["company","GitHub","code hosting platform"] documents creating repos from templates and the `gh repo create` CLI supports template-driven creation. citeturn2search14turn2search22  
This is optional and orthogonal to Copier; you can add it as a later enhancement after the scaffolding engine is stable.

## Prioritized primary sources consulted

Copier’s official docs are the backbone for this design: multi-template application via multiple answers files, tasks/migrations, safe/unsafe features, update algorithm, and Git-tag versioning. citeturn15view0turn14view0turn16view0turn22view0turn20view0  
The CLI stack recommendations are grounded in Typer’s packaging guidance, PyPA’s CLI tooling guide (including pipx and entry points), and Rich’s documentation for tables and progress rendering. citeturn19view0turn21view1turn19view2turn18search3  
Comparisons against Cookiecutter and Yeoman come from Copier’s own comparisons page, while Hygen capabilities (particularly injection) are evidenced by Hygen’s README. citeturn11view0turn10search1turn7view1  
Security recommendations include Copier’s own trust/unsafe model documentation and recent CVE/GHSA disclosures captured by authoritative vulnerability databases (notably the entity["organization","National Vulnerability Database","nist vulnerability db"] and entity["company","GitLab","advisory database"] advisory database). citeturn20view0turn31search8turn30view2turn24view0