# Purpose: Stage trusted XY UI assets and reuse application icons as an inline SVG sprite.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_plot_qml.py
from __future__ import annotations

from importlib import resources
from pathlib import Path
import shutil
from xml.etree import ElementTree

from ea_node_editor.web_host.xy_client import precise_xy_client

HOST_FILES = ("index.html", "host.js", "host.css", "gestures.js", "controls.js", "toolbar.js", "readouts.js",
              "probes.js", "probe_scheduler.js", "probe_coordinates.js", "probe_readouts.js")
HOST_ICONS = ("fit-width", "fit-height", "zoom-fit", "fullscreen", "video-fit", "settings", "x", "chevron-down", "link", "format-list-bulleted", "focus")


def stage_xy_host_assets(destination: Path) -> None:
    package = resources.files("ea_node_editor")
    for name in HOST_FILES:
        with resources.as_file(package.joinpath("web_assets", "xy_host", name)) as source:
            shutil.copyfile(source, destination / name)
    symbols = []
    for name in HOST_ICONS:
        icon = ElementTree.fromstring(package.joinpath("ui_qml", "components", "shell", "icons", name + ".svg").read_text(encoding="utf-8"))
        for element in icon.iter():
            element.tag = element.tag.rsplit("}", 1)[-1]
        icon.tag = "symbol"
        icon.set("id", "icon-" + name)
        for attribute in ("width", "height"):
            icon.attrib.pop(attribute, None)
        symbols.append(ElementTree.tostring(icon, encoding="unicode"))
    html = destination / "index.html"
    html.write_text(html.read_text(encoding="utf-8").replace("<!--COREX_XY_ICONS-->", "\n".join(symbols)), encoding="utf-8")
    with resources.as_file(resources.files("xy").joinpath("static", "index.js")) as source:
        (destination / "xy-widget.js").write_text(precise_xy_client(source.read_text(encoding="utf-8")), encoding="utf-8")
