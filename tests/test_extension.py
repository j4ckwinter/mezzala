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

    args = manifest["server"]["mcp_config"]["args"]
    assert args[args.index("--fog-of-war") - 1] in project["scripts"]


def test_the_desktop_extension_has_a_fog_of_war_setting_that_starts_off():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    setting = manifest["user_config"]["fog_of_war"]
    args = manifest["server"]["mcp_config"]["args"]

    assert setting["type"] == "boolean" and setting["default"] is False
    assert args[args.index("--fog-of-war") + 1] == "${user_config.fog_of_war}"


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ICON_SIZE = 512


def test_the_desktop_extension_has_a_square_png_icon_at_the_recommended_size():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    icon = (ROOT / manifest["icon"]).read_bytes()
    width, height = int.from_bytes(icon[16:20]), int.from_bytes(icon[20:24])

    assert icon.startswith(PNG_SIGNATURE)
    assert (width, height) == (ICON_SIZE, ICON_SIZE)
