# Syntheris Continuum Theme Notes

Dark-first, futuristic UI. Keep accessibility: body text contrast ≥ 4.5.

Palette
- Background 900: #0B0F17
- Surface 800: #0E1420
- Primary (Cyan): #6DF0FF
- Secondary (Magenta): #FF38A1
- Success (Teal): #38F7A1
- Warning (Amber): #FFD166
- Text Primary: #E6F0FF
- Text Muted: #9FB3C8
- Stroke: #1D2736

Usage
- Title text gradient: cyan→magenta with subtle glow
- Buttons: pill radius (9999px), bold labels, hover border accent
- Inputs: subtle inner glow on focus using Primary
- Tabs: underline indicator in Primary; hover tint to Secondary
- Header: Surface 800 background, slim Stroke border at bottom

Implementation
- Gradio theme via gr.themes.Soft(...).set(...)
- CSS only for header, gradient text, pill buttons, status accent
- Avoid layout/grid overrides

Assets
- assets/logo_continuum.svg: geometric C with orbit ring (gradient stroke)
- assets/favicon_continuum.png: 32×32 cyan glyph on dark (placeholder; replace later)

