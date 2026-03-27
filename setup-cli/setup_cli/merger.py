from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w


def _merge_toml_dicts(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, patch_val in patch.items():
        if key in result:
            base_val = result[key]
            if isinstance(base_val, dict) and isinstance(patch_val, dict):
                result[key] = _merge_toml_dicts(base_val, patch_val)
            elif isinstance(base_val, list) and isinstance(patch_val, list):
                existing = set(base_val)
                result[key] = base_val + [v for v in patch_val if v not in existing]
            else:
                result[key] = patch_val
        else:
            result[key] = patch_val
    return result


def merge_toml_files(base_path: Path, patch_path: Path) -> None:
    if not base_path.exists():
        raise FileNotFoundError(
            f"Patch target {base_path.name!r} does not exist in {base_path.parent}. "
            "Was the base pack applied first?"
        )

    with open(base_path, "rb") as f:
        base = tomllib.load(f)

    with open(patch_path, "rb") as f:
        patch = tomllib.load(f)

    merged = _merge_toml_dicts(base, patch)

    with open(base_path, "wb") as f:
        tomli_w.dump(merged, f)

    patch_path.unlink()


def merge_env_files(base_path: Path, patch_path: Path) -> None:
    patch_text = patch_path.read_text()
    patch_lines = patch_text.splitlines(keepends=True)

    if not base_path.exists():
        base_path.write_text(patch_text)
        patch_path.unlink()
        return

    base_text = base_path.read_text()
    existing_keys: set[str] = set()
    for line in base_text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            existing_keys.add(stripped.split("=", 1)[0].strip())

    new_lines = []
    for line in patch_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in existing_keys:
                continue
            existing_keys.add(key)
        new_lines.append(line)

    if new_lines:
        with open(base_path, "a") as f:
            if base_text and not base_text.endswith("\n"):
                f.write("\n")
            f.writelines(new_lines)

    patch_path.unlink()


def apply_patches(dest: Path) -> None:
    for patch_file in sorted(dest.rglob("*.patch.toml")):
        target_name = patch_file.name.replace(".patch.toml", ".toml")
        target = patch_file.parent / target_name
        merge_toml_files(target, patch_file)

    for patch_file in sorted(dest.rglob("*.patch")):
        target_name = patch_file.name[: -len(".patch")]
        target = patch_file.parent / target_name
        merge_env_files(target, patch_file)
