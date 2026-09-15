#!/usr/bin/env python3
"""Idempotent patch: wire AnalystPanel into App.jsx.

Preferred flow if UI looks wrong:
  git checkout main -- frontend/src/App.jsx
  python frontend/apply_frontend_patch.py
"""
from __future__ import annotations

from pathlib import Path

APP = Path(__file__).resolve().parent / "src" / "App.jsx"


def patch(text: str) -> str:
    if "AnalystPanel" in text and "simulation?.analyst" in text:
        print("Already patched")
        return text

    if "from \"./components/AnalystPanel\"" not in text and "from './components/AnalystPanel'" not in text:
        if 'from "./components/EarthImpactMap"' in text:
            text = text.replace(
                'from "./components/EarthImpactMap";',
                'from "./components/EarthImpactMap";\nimport AnalystPanel\n  from "./components/AnalystPanel";',
                1,
            )
        elif "from \"./components/EarthImpactMap\"" in text:
            text = text.replace(
                'from "./components/EarthImpactMap";',
                'from "./components/EarthImpactMap";\nimport AnalystPanel from "./components/AnalystPanel";',
                1,
            )

    if 'import "./analyst.css"' not in text:
        text = text.replace('import "./App.css";', 'import "./App.css";\nimport "./analyst.css";', 1)

    needle = "  const simulationData = simulation?.simulation ?? null;\n  const trajectory = simulation?.trajectory ?? null;"
    if needle in text and "const analyst = simulation?.analyst" not in text:
        text = text.replace(
            needle,
            "  const simulationData = simulation?.simulation ?? null;\n"
            "  const trajectory = simulation?.trajectory ?? null;\n"
            "  const analyst = simulation?.analyst ?? null;\n"
            "  const terrain = simulation?.terrain ?? null;\n"
            "  const tsunami = simulation?.tsunami ?? null;",
            1,
        )

    if "<AnalystPanel" not in text:
        old = (
            "<ConsequencesPanel\n"
            "  consequences={\n"
            "    simulationData?.consequences\n"
            "  }\n"
            "/>"
        )
        new = (
            "<ConsequencesPanel\n"
            "  consequences={\n"
            "    simulationData?.consequences\n"
            "  }\n"
            "/>\n"
            "            <AnalystPanel\n"
            "              analyst={analyst}\n"
            "              terrain={terrain}\n"
            "              tsunami={tsunami}\n"
            "            />"
        )
        if old not in text:
            # looser match
            if "<ConsequencesPanel" in text and "consequences=" in text:
                print("WARN: ConsequencesPanel found but exact block mismatch — add AnalystPanel manually")
            else:
                raise SystemExit("ConsequencesPanel block not found")
        else:
            text = text.replace(old, new, 1)

    return text


def main() -> None:
    original = APP.read_text()
    updated = patch(original)
    APP.write_text(updated)
    print(f"Patched {APP}")


if __name__ == "__main__":
    main()
