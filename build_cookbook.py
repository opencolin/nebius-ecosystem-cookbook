#!/usr/bin/env python3
"""
Build the Token Factory Cookbook into branded, static HTML for GitHub Pages.

- Renders every .ipynb -> HTML via nbconvert (no execution; existing outputs kept).
- Renders every recipe README.md -> HTML via python-markdown.
- Wraps both in the Nebius brand chrome (shared assets/css/main.css + cookbook.css).
- Mirrors the source tree under cookbook/r/<path>/ and copies images alongside,
  so relative image refs resolve.
- Emits cookbook/index.html: a filterable, category-grouped grid of recipe cards.

Run from the project root (where assets/ lives). Source repo expected at
.cache/cookbook-src (clone of github.com/nebius/token-factory-cookbook).
"""
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

import markdown as md
import nbformat
from nbconvert import HTMLExporter
from traitlets.config import Config

ROOT = Path(__file__).resolve().parent
SRC = ROOT / ".cache" / "cookbook-src"
OUT = ROOT / "cookbook"
RDIR = OUT / "r"
GH_BLOB = "https://github.com/nebius/token-factory-cookbook/blob/main"
GH_TREE = "https://github.com/nebius/token-factory-cookbook/tree/main"
NBVIEWER = "https://nbviewer.org/github/nebius/token-factory-cookbook/blob/main"

IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
CODE_EXT = {".ipynb", ".py", ".js", ".ts", ".tsx", ".pynb"}

CATEGORY = {
    "api":          ("API Quickstarts", 1, "Point one base_url at Token Factory — the OpenAI-compatible on-ramp, plus aisuite, LiteLLM, and LlamaIndex SDKs."),
    "agents":       ("Agents", 2, "Production agents across every major framework — LangChain, CrewAI, Agno, AWS Strands, Google ADK, LlamaIndex, Pydantic, and more."),
    "tool-calling": ("Tool Calling", 3, "Function calling and live web tools (Tavily) on open models."),
    "rag":          ("RAG", 4, "Retrieval-augmented generation over PDFs and vector stores — Milvus, Qdrant, Weaviate, LlamaIndex."),
    "lora":         ("LoRA Fine-tuning", 5, "Train and serve LoRA adapters on open models."),
    "post-training":("Fine-tuning & Post-training", 6, "Full fine-tuning pipelines on Token Factory."),
    "distillation": ("Distillation", 7, "Generate training data, distill, and evaluate smaller models."),
    "models":       ("Models", 8, "Model-specific quickstarts — GLM-4.5, GPT-OSS, Qwen3, Nemotron."),
    "images":       ("Image Generation", 9, "Text-to-image and image LoRA recipes."),
    "integrations": ("Integrations", 10, "Token Factory inside OpenClaw, Tavily, and more."),
    "apps":         ("Apps", 11, "End-to-end applications built on Token Factory."),
    "coding":       ("Coding", 12, "Coding-agent and code-generation recipes."),
    "workshops":    ("Workshops", 13, "Hands-on workshop material."),
    "builder-hour": ("Builder Hour", 14, "Builder-hour sessions and walkthroughs."),
    "articles":     ("Articles", 15, "Written deep-dives."),
    "community":    ("Community", 16, "Community-contributed guides."),
    "fun":          ("Fun", 17, "Pelicans on bicycles, snake games — open models having fun."),
    "data":         ("Datasets", 18, "Reference datasets used by the recipes."),
    "_root":        ("Essentials", 0, "Core Token Factory notebooks — adding a LoRA, batch inference, guided JSON, image LoRA."),
}

# nbconvert exporter (basic template = body only, outputs embedded as data URIs)
_cfg = Config()
_exporter = HTMLExporter(config=_cfg)
try:
    _exporter.template_name = "basic"
except Exception:
    pass


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def rel_root(depth: int) -> str:
    return "../" * depth if depth else "./"


def page_shell(title, body, depth, source_url=None, source_label="View source on GitHub",
               crumb="Cookbook", extra_top=""):
    rr = rel_root(depth)
    src_btn = f'<a class="btn secondary" href="{source_url}" target="_blank" rel="noopener">{source_label} ↗</a>' if source_url else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)} · Nebius Token Factory Cookbook</title>
<link rel="stylesheet" href="{rr}assets/css/main.css" />
<link rel="stylesheet" href="{rr}assets/cookbook.css" />
</head>
<body>
<nav class="nav">
  <div class="nav-inner">
    <a class="brand" href="{rr}index.html" aria-label="Nebius — home"><span class="brand-logo" id="nav-logo"></span></a>
    <div class="nav-links" id="nav-menu">
      <a href="{rr}index.html">Ecosystem</a>
      <a href="{rr}cookbook/index.html">Cookbook</a>
      <a href="{rr}devsite/index.html">Builder devsite</a>
    </div>
    <div class="nav-actions">
      <a class="nav-cta" href="https://github.com/nebius/token-factory-cookbook" target="_blank" rel="noopener">Cookbook repo ↗</a>
      <button class="nav-toggle" type="button" aria-label="Toggle navigation menu" aria-expanded="false" aria-controls="nav-menu"><span></span><span></span><span></span></button>
    </div>
  </div>
</nav>
<div class="cb-recipe container">
  <div class="cb-crumb"><a href="{rr}cookbook/index.html">← {html.escape(crumb)}</a>{src_btn}</div>
  {extra_top}
  <article class="cb-content">
{body}
  </article>
</div>
<footer><div class="container"><div class="footer-bottom">
  <span>Recipes © Nebius · <a href="https://github.com/nebius/token-factory-cookbook" target="_blank" rel="noopener">nebius/token-factory-cookbook</a> (MIT). Rendered for an ecosystem demo.</span>
  <span><a href="{rr}index.html">Ecosystem &amp; Partners</a></span>
</div></div></footer>
<script src="{rr}assets/js/main.js"></script>
<script src="{rr}assets/nav-logo.js"></script>
</body>
</html>
"""


def render_notebook(path: Path):
    try:
        nb = nbformat.read(str(path), as_version=4)
        # strip malformed widget metadata (missing 'state') that breaks nbconvert
        w = nb.get("metadata", {}).get("widgets")
        if w is not None:
            key = "application/vnd.jupyter.widget-state+json"
            ok = isinstance(w, dict) and isinstance(w.get(key), dict) and "state" in w[key]
            if not ok:
                nb["metadata"].pop("widgets", None)
        body, _ = _exporter.from_notebook_node(nb)
        return body
    except Exception as e:
        print(f"  ! nbconvert failed: {path.relative_to(SRC)} ({e})")
        return None


MD = md.Markdown(extensions=["fenced_code", "tables", "codehilite", "sane_lists", "toc"],
                 extension_configs={"codehilite": {"guess_lang": False}})


def render_markdown(text: str) -> str:
    MD.reset()
    return MD.convert(text)


def rewrite_links(body: str, recipe_rel: str) -> str:
    """Rewrite relative hrefs in rendered README: .ipynb->.html, other code/files->GitHub."""
    def repl(m):
        attr, url = m.group(1), m.group(2)
        if re.match(r"^(https?:|mailto:|#|/)", url):
            return m.group(0)
        # image src stays relative (copied alongside)
        ext = os.path.splitext(url.split("?")[0])[1].lower()
        if attr == "src":
            return m.group(0)
        if ext == ".ipynb":
            return f'{attr}="{os.path.splitext(url)[0]}.html"'
        if ext in IMG_EXT:
            return m.group(0)
        # other relative file -> GitHub source
        clean = url.lstrip("./")
        return f'{attr}="{GH_BLOB}/{recipe_rel}/{clean}" target="_blank" rel="noopener"'
    return re.sub(r'(href|src)="([^"]+)"', repl, body)


def first_para(text: str) -> str:
    # strip front-matter images/badges, find first real paragraph
    lines = text.splitlines()
    buf = []
    started = False
    for ln in lines:
        s = ln.strip()
        if not started:
            if not s or s.startswith("#") or s.startswith("![") or s.startswith("<") or s.startswith("[!["):
                continue
            started = True
        if started:
            if not s:
                break
            buf.append(s)
    para = " ".join(buf)
    para = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", para)   # md links -> text
    para = re.sub(r"[*`_#>]", "", para)
    return para.strip()[:240]


def title_of(text: str, fallback: str) -> str:
    for ln in text.splitlines():
        m = re.match(r"#\s+(.+)", ln.strip())
        if m:
            return re.sub(r"[*`_]", "", m.group(1)).strip()[:90]
    return fallback


def copy_assets(src_dir: Path, out_dir: Path):
    for f in src_dir.iterdir():
        if f.is_file() and f.suffix.lower() in IMG_EXT:
            shutil.copy2(f, out_dir / f.name)


def has_code(d: Path) -> bool:
    return any(p.is_file() and p.suffix.lower() in CODE_EXT for p in d.iterdir())


def has_child_readme(d: Path) -> bool:
    return any(p.parent != d for p in d.rglob("README*.md"))


def main():
    if not SRC.exists():
        sys.exit(f"cookbook source not found at {SRC}")
    if RDIR.exists():
        shutil.rmtree(RDIR)
    RDIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    recipes = []          # dicts: title, desc, category, subcat, tags, banner, href, source, kind
    nb_ok = nb_fail = readme_n = 0

    # 1) README-based recipes (dir with README + code directly in it)
    # A recipe = a README dir that is a leaf example (no child README dir) OR has
    # code directly, capped at depth 3 so internal src/ subdirs don't become recipes.
    readme_dirs = sorted({p.parent for p in SRC.rglob("README*.md")})
    recipe_dirs = [d for d in readme_dirs
                   if d != SRC
                   and len(d.relative_to(SRC).parts) <= 3
                   and (has_code(d) or not has_child_readme(d))]
    recipe_dir_set = set(recipe_dirs)

    for d in recipe_dirs:
        rel = d.relative_to(SRC)
        parts = rel.parts
        category = parts[0]
        subcat = parts[1] if len(parts) > 2 else ""
        out_dir = RDIR / rel
        out_dir.mkdir(parents=True, exist_ok=True)
        copy_assets(d, out_dir)
        depth = len(rel.parts) + 2   # file at cookbook/r/<rel>/...  -> +2 for cookbook/ + r/

        readme = next((p for p in d.iterdir() if p.name.lower().startswith("readme") and p.suffix.lower() == ".md"), None)
        text = readme.read_text(encoding="utf-8", errors="replace") if readme else ""
        title = title_of(text, rel.name.replace("-", " ").replace("_", " ").title())
        desc = first_para(text) if text else ""

        # render notebooks anywhere under this recipe (mirror subpaths), skipping
        # any that belong to a deeper recipe dir.
        nbs = sorted(p for p in d.rglob("*.ipynb")
                     if not any(rd != d and rd in p.parents for rd in recipe_dir_set))
        nb_links = []
        for nb in nbs:
            nb_rel = nb.relative_to(SRC)
            nb_out_dir = RDIR / nb_rel.parent
            nb_out_dir.mkdir(parents=True, exist_ok=True)
            copy_assets(nb.parent, nb_out_dir)
            nb_depth = len(nb_rel.parent.parts) + 2
            bod = render_notebook(nb)
            nb_out = nb_out_dir / (nb.stem + ".html")
            link = os.path.relpath(nb_out, out_dir)
            label = str(nb_rel.relative_to(rel))
            if bod is not None:
                nb_out.write_text(page_shell(f"{title} — {nb.name}", bod, nb_depth,
                                             source_url=f"{GH_BLOB}/{nb_rel}",
                                             crumb="Cookbook"), encoding="utf-8")
                nb_ok += 1
                nb_links.append(f'<li><a href="{link}">{html.escape(label)}</a> · <a href="{NBVIEWER}/{nb_rel}" target="_blank" rel="noopener">nbviewer ↗</a></li>')
            else:
                nb_fail += 1
                nb_links.append(f'<li>{html.escape(label)} — <a href="{NBVIEWER}/{nb_rel}" target="_blank" rel="noopener">open in nbviewer ↗</a></li>')

        body = render_markdown(text) if text else "<p>See source on GitHub.</p>"
        body = rewrite_links(body, str(rel))
        extra = ""
        if nb_links:
            extra = '<div class="callout"><strong>Notebooks in this recipe:</strong><ul>' + "".join(nb_links) + "</ul></div>"
        page = page_shell(title, body + extra, depth, source_url=f"{GH_TREE}/{rel}", crumb="Cookbook")
        (out_dir / "index.html").write_text(page, encoding="utf-8")
        readme_n += 1

        banner = next((p.name for p in d.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXT and "banner" in p.name.lower()), None)
        if not banner:
            banner = next((p.name for p in d.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXT), None)
        tags = [t for t in (category, subcat) if t]
        recipes.append(dict(title=title, desc=desc, category=category, subcat=subcat,
                            tags=tags, banner=(f"r/{rel}/{banner}" if banner else ""),
                            href=f"r/{rel}/index.html", source=f"{GH_TREE}/{rel}",
                            kind="notebook" if nbs else "guide", nbs=len(nbs)))

    # 1.5) loose category-level content markdown (articles, builder-hour, events…)
    for mdf in sorted(SRC.rglob("*.md")):
        rel = mdf.relative_to(SRC)
        if mdf.name.lower().startswith("readme"):
            continue
        if len(rel.parts) > 2 or rel.parts[0] in ("data",):
            continue
        if mdf.parent in recipe_dir_set or mdf.parent == SRC:
            continue
        category = rel.parts[0] if len(rel.parts) > 1 else "_root"
        out_dir = RDIR / rel.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        copy_assets(mdf.parent, out_dir)
        depth = len(rel.parts) + 1
        text = mdf.read_text(encoding="utf-8", errors="replace")
        title = title_of(text, mdf.stem.replace("-", " ").replace("_", " ").title())
        base = str(rel.parent) if str(rel.parent) != "." else ""
        body = rewrite_links(render_markdown(text), base)
        (out_dir / (mdf.stem + ".html")).write_text(
            page_shell(title, body, depth, source_url=f"{GH_BLOB}/{rel}", crumb="Cookbook"), encoding="utf-8")
        readme_n += 1
        recipes.append(dict(title=title, desc=first_para(text), category=category, subcat="",
                            tags=[category, "doc"], banner="", href=f"r/{rel.parent}/{mdf.stem}.html",
                            source=f"{GH_BLOB}/{rel}", kind="doc", nbs=0))

    # 2) standalone notebooks not inside a README-recipe dir
    for nb in sorted(SRC.rglob("*.ipynb")):
        if any(rd == nb.parent or rd in nb.parents for rd in recipe_dir_set):
            continue
        rel = nb.relative_to(SRC)
        category = rel.parts[0] if len(rel.parts) > 1 else "_root"
        out_dir = RDIR / rel.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        copy_assets(nb.parent, out_dir)
        depth = len(rel.parts) + 1
        bod = render_notebook(nb)
        title = nb.stem.replace("_", " ").replace("-", " ").title()
        out_html = out_dir / (nb.stem + ".html")
        if bod is not None:
            out_html.write_text(page_shell(title, bod, depth, source_url=f"{GH_BLOB}/{rel}", crumb="Cookbook"), encoding="utf-8")
            nb_ok += 1
            href = f"r/{rel.parent}/{nb.stem}.html" if str(rel.parent) != "." else f"r/{nb.stem}.html"
        else:
            nb_fail += 1
            href = f"{NBVIEWER}/{rel}"
        recipes.append(dict(title=title, desc=f"Notebook · {category if category!='_root' else 'core'}",
                            category=category, subcat="", tags=[category if category != "_root" else "essentials"],
                            banner="", href=href, source=f"{GH_BLOB}/{rel}", kind="notebook", nbs=1))

    # 3) index page
    write_index(recipes)
    print(f"\nDONE  recipes={len(recipes)}  notebooks_rendered={nb_ok}  nb_fallback={nb_fail}  readme_pages={readme_n}")


def write_index(recipes):
    cats = {}
    for r in recipes:
        cats.setdefault(r["category"], []).append(r)

    def cat_key(c):
        return CATEGORY.get(c, (c, 99, ""))[1]

    cards_html = []
    chips = ['<button class="cb-chip cb-chip-on" data-cat="all">All</button>']
    for c in sorted(cats, key=cat_key):
        label, _, blurb = CATEGORY.get(c, (c.replace("-", " ").title(), 99, ""))
        chips.append(f'<button class="cb-chip" data-cat="{html.escape(c)}">{html.escape(label)}</button>')
        items = sorted(cats[c], key=lambda r: r["title"].lower())
        rows = []
        for r in items:
            thumb = f'<div class="cb-thumb" style="background-image:url({html.escape(r["banner"])})"></div>' if r["banner"] else '<div class="cb-thumb cb-thumb-blank"></div>'
            tagspans = "".join(f'<span class="pill">{html.escape(t)}</span>' for t in r["tags"][:2])
            nb = f'<span class="pill coral">{r["nbs"]} nb</span>' if r.get("nbs") else ""
            rows.append(f"""<a class="cb-card" href="{html.escape(r['href'])}" data-search="{html.escape((r['title']+' '+r['desc']+' '+' '.join(r['tags'])).lower())}">
  {thumb}
  <div class="cb-card-body">
    <div class="cb-tags">{tagspans}{nb}</div>
    <h3>{html.escape(r['title'])}</h3>
    <p>{html.escape(r['desc'])}</p>
    <span class="cb-src" onclick="event.preventDefault();event.stopPropagation();window.open('{html.escape(r['source'])}','_blank')">source ↗</span>
  </div>
</a>""")
        cards_html.append(f'<section class="cb-cat" data-cat="{html.escape(c)}"><div class="section-eyebrow">{html.escape(label)} · {len(items)}</div><p class="section-lede">{html.escape(blurb)}</p><div class="cb-grid">{"".join(rows)}</div></section>')

    total_nb = sum(r["nbs"] for r in recipes if r.get("nbs"))
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Token Factory Cookbook · Nebius</title>
<meta name="description" content="Every recipe from the Nebius Token Factory Cookbook — agents, RAG, fine-tuning, tool-calling, models, and more — rendered and browsable." />
<link rel="stylesheet" href="../assets/css/main.css" />
<link rel="stylesheet" href="../assets/cookbook.css" />
</head>
<body>
<nav class="nav">
  <div class="nav-inner">
    <a class="brand" href="../index.html" aria-label="Nebius — home"><span class="brand-logo" id="nav-logo"></span></a>
    <div class="nav-links" id="nav-menu">
      <a href="../index.html">Ecosystem</a>
      <a href="index.html" class="active">Cookbook</a>
      <a href="../devsite/index.html">Builder devsite</a>
    </div>
    <div class="nav-actions">
      <a class="nav-cta" href="https://github.com/nebius/token-factory-cookbook" target="_blank" rel="noopener">Cookbook repo ↗</a>
      <button class="nav-toggle" type="button" aria-label="Toggle navigation menu" aria-expanded="false" aria-controls="nav-menu"><span></span><span></span><span></span></button>
    </div>
  </div>
</nav>
<header class="hero">
  <div class="container">
    <span class="hero-eyebrow">Runnable reference · the Token Factory Cookbook</span>
    <h1>Every recipe, rendered and browsable.</h1>
    <p class="lede">The full <a href="https://github.com/nebius/token-factory-cookbook" target="_blank" rel="noopener">Token Factory Cookbook</a> — {len(recipes)} recipes across {len(cats)} categories, {total_nb} notebooks rendered with their outputs. The runnable backing for the <a href="../index.html#partners">reference architectures</a> on the ecosystem page. Built on open models through one OpenAI-compatible <code>base_url</code>.</p>
    <div class="cb-controls">
      <input class="cb-search" type="search" placeholder="Search recipes… (framework, task, model)" aria-label="Search recipes" />
    </div>
    <div class="cb-chips">{''.join(chips)}</div>
  </div>
</header>
<div class="container cb-index">
  {''.join(cards_html)}
  <p class="cb-empty" hidden>No recipes match.</p>
</div>
<footer><div class="container"><div class="footer-bottom">
  <span>Recipes © Nebius · <a href="https://github.com/nebius/token-factory-cookbook" target="_blank" rel="noopener">nebius/token-factory-cookbook</a> (MIT). Rendered for an ecosystem demo by opencolin.</span>
  <span><a href="../index.html">Ecosystem &amp; Partners</a></span>
</div></div></footer>
<script src="../assets/js/main.js"></script>
<script src="../assets/nav-logo.js"></script>
<script src="../assets/cookbook-filter.js"></script>
</body>
</html>
"""
    (OUT / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
