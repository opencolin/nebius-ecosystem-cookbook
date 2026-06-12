# Nebius Ecosystem & Partners + the Token Factory Cookbook — on GitHub Pages

A static, branded GitHub Pages site that hosts two things together:

1. **Ecosystem & Partners** — the Nebius stack (Token Factory · Tavily · Contree · AI Cloud), the partner channels, and the reference architectures (`index.html`).
2. **The full [Token Factory Cookbook](https://github.com/nebius/token-factory-cookbook)** — **every** recipe rendered and browsable (`/cookbook/`): **50 recipes across 17 categories, all 27 notebooks rendered with their outputs**, plus the per-recipe READMEs, with a filter/search and links to source.

The cookbook is the runnable backing for the ecosystem page's reference architectures.

## How it's built
- `build_cookbook.py` — clones the cookbook, renders every `.ipynb` via **nbconvert** (outputs embedded) and every README via **python-markdown**, wraps them in the Nebius brand chrome (`assets/css/main.css` + `assets/cookbook.css`), and generates the filterable index at `cookbook/index.html`. Notebooks that can't convert fall back to an nbviewer link (currently: 0).
- `build_index.py` — turns the internal `ecosystem.html` into a standalone, public `index.html` (clean nav, cookbook wiring, internal-only links stripped).
- `build.sh` — one-shot rebuild of the cookbook from upstream. A weekly GitHub Action (`.github/workflows/rebuild.yml`) keeps it in sync.

```bash
./build.sh          # rebuild the cookbook from the latest upstream
```

## Notes & tradeoffs (GitHub Pages)
- **Public** static hosting — no password gate (the original is gated on Vercel). The cookbook is already public OSS; the ecosystem page here is a sanitized, public-safe copy.
- Relative paths throughout (works under the `/<repo>/` project-pages subpath); `.nojekyll` disables Jekyll.

## Attribution
Cookbook recipes © Nebius B.V. — **MIT License** (see `cookbook/LICENSE`), from [nebius/token-factory-cookbook](https://github.com/nebius/token-factory-cookbook). Nebius name, marks, and products belong to Nebius. This is an ecosystem demo by opencolin.
