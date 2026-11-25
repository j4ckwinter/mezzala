import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_the_desktop_extension_has_the_same_version_as_the_package() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]

    assert manifest["version"] == project["version"]


def test_the_desktop_extension_starts_the_package_script() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]

    assert manifest["server"]["mcp_config"]["args"][-1] in project["scripts"]
