"""Streamlit showcase app for orbitdc.

This package is the presentation layer behind the repo-root ``streamlit_app.py``:

- ``app.data``  — pure model glue (scenario discovery, override-aware runs,
  sensitivity/uncertainty). No streamlit or plotly imports, so it stays
  type-checked under mypy --strict and importable with only the base deps.
- ``app.theme`` — dark plotly template applied to every figure.
- ``app.tabs``  — one render function per dashboard tab (imports streamlit).
"""
