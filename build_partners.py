#!/usr/bin/env python3
"""Render nebius/nebius-partner-cookbook (Agent Blueprint Recipes) into the
ecosystem site as a branded, browsable 'Agent Blueprints' section at
/blueprints/. Reuses the Token Factory Cookbook's markdown renderer + brand
chrome. Source: .cache/partner-cookbook-src (cloned by build.sh)."""
import json, os, re, html, shutil
from pathlib import Path
from build_cookbook import render_markdown, slug, title_of, first_para, ROOT, IMG_EXT

PSRC = ROOT / ".cache" / "partner-cookbook-src"
POUT = ROOT / "blueprints"
REPO = "https://github.com/nebius/nebius-partner-cookbook"
GH_TREE = REPO + "/tree/main"
GH_BLOB = REPO + "/blob/main"


def rel_root(depth):
    return "../" * depth if depth else "./"


def rewrite_links(body, rel):
    """Relative non-image file links -> source on the partner repo; images stay relative."""
    def repl(m):
        attr, url = m.group(1), m.group(2)
        if re.match(r"^(https?:|mailto:|#|/)", url):
            return m.group(0)
        if attr == "src":
            return m.group(0)
        ext = os.path.splitext(url.split("?")[0])[1].lower()
        if ext in IMG_EXT:
            return m.group(0)
        clean = url.lstrip("./")
        return f'{attr}="{GH_BLOB}/{rel}/{clean}" target="_blank" rel="noopener"'
    return re.sub(r'(href|src)="([^"]+)"', repl, body)


def pills(items, cls="pill"):
    return "".join(f'<span class="{cls}">{html.escape(str(x))}</span>' for x in items if x)


def nav(rr):
    return f"""<nav class="nav"><div class="nav-inner">
    <a class="brand" href="{rr}index.html" aria-label="Nebius — home"><span class="brand-logo" id="nav-logo"></span></a>
    <div class="nav-links" id="nav-menu">
      <a href="{rr}index.html">Ecosystem</a>
      <a href="{rr}cookbook/index.html">Cookbook</a>
      <a href="{rr}blueprints/index.html" class="active">Agent Blueprints</a>
      <a href="{rr}devsite/index.html">Builder devsite</a>
    </div>
    <div class="nav-actions">
      <a class="nav-cta" href="{REPO}" target="_blank" rel="noopener">Blueprints repo ↗</a>
      <button class="nav-toggle" type="button" aria-label="Toggle navigation menu" aria-expanded="false" aria-controls="nav-menu"><span></span><span></span><span></span></button>
    </div></div></nav>"""


def footer(rr):
    return f"""<footer><div class="container"><div class="footer-bottom">
  <span>Recipes © Nebius · <a href="{REPO}" target="_blank" rel="noopener">nebius/nebius-partner-cookbook</a> (MIT). Rendered for an ecosystem demo.</span>
  <span><a href="{rr}index.html">Ecosystem &amp; Partners</a></span>
</div></div></footer>"""


def meta_header(rj):
    if not rj:
        return ""
    st = rj.get("stack", {}) or {}
    stack = list(st.get("primary", [])) + list(st.get("secondary", []))
    facts = []
    if rj.get("difficulty"):
        facts.append(rj["difficulty"])
    if rj.get("estimatedReadingTime"):
        facts.append("read " + rj["estimatedReadingTime"])
    if rj.get("estimatedRunTime"):
        facts.append("run " + rj["estimatedRunTime"])
    qs = rj.get("quickstart", {}) or {}
    code = "\n".join(x for x in [qs.get("clone"), qs.get("configure"), qs.get("run")] if x)
    qs_block = (f'<details class="bp-quick"><summary>Run it locally</summary>'
                f'<pre><code>{html.escape(code)}</code></pre></details>') if code else ""
    return (f'<div class="bp-meta">'
            f'<div class="bp-row">{pills(facts, "pill coral")}</div>'
            f'<div class="bp-row">{pills(stack)}</div>'
            f'{qs_block}</div>')


def shell(title, body, depth, source_url, meta_top=""):
    rr = rel_root(depth)
    src = (f'<a class="btn secondary" href="{source_url}" target="_blank" rel="noopener">'
           f'View recipe on GitHub ↗</a>') if source_url else ""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)} · Nebius Agent Blueprints</title>
<link rel="stylesheet" href="{rr}assets/css/main.css"/>
<link rel="stylesheet" href="{rr}assets/cookbook.css"/>
</head><body>
{nav(rr)}
<div class="cb-recipe container">
  <div class="cb-crumb"><a href="{rr}blueprints/index.html">← Agent Blueprints</a>{src}</div>
  {meta_top}
  <article class="cb-content">
{body}
  </article>
</div>
{footer(rr)}
<script src="{rr}assets/js/main.js"></script>
<script src="{rr}assets/nav-logo.js"></script>
</body></html>
"""


def copy_imgs(d, out_dir):
    for p in d.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMG_EXT and ".git" not in p.parts:
            dest = out_dir / p.relative_to(d)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)


def load(d, kind):
    readme = d / "README.md"
    if not readme.exists():
        return None
    text = readme.read_text(encoding="utf-8")
    rj = {}
    rjp = d / "recipe.json"
    if rjp.exists():
        try:
            rj = json.loads(rjp.read_text(encoding="utf-8"))
        except Exception:
            rj = {}
    sl = rj.get("slug") or slug(d.name)
    title = rj.get("title") or title_of(text, d.name.replace("-", " ").title())
    rel = f"{'cookbooks' if kind == 'recipe' else 'blueprints'}/{d.name}"
    return {"dir": d, "slug": sl, "rel": rel, "kind": kind, "rj": rj, "text": text, "title": title}


def write_recipe(r):
    out_dir = POUT / r["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    copy_imgs(r["dir"], out_dir)
    body = rewrite_links(render_markdown(r["text"]), r["rel"])
    page = shell(r["title"], body, 2, f"{GH_TREE}/{r['rel']}", meta_header(r["rj"]))
    (out_dir / "index.html").write_text(page, encoding="utf-8")


def card(r):
    rj = r["rj"]
    n = rj.get("order")
    num = f'<span class="bp-num">{int(n):02d}</span>' if isinstance(n, int) else ""
    eyebrow = rj.get("eyebrow", "")
    diff = rj.get("difficulty", "")
    tagline = rj.get("tagline") or first_para(r["text"])
    stack = list((rj.get("stack", {}) or {}).get("primary", []))[:3]
    tags = "".join([num,
                    f'<span class="pill">{html.escape(eyebrow)}</span>' if eyebrow else "",
                    f'<span class="pill coral">{html.escape(diff)}</span>' if diff else ""])
    return f"""<a class="cb-card bp-card" href="{r['slug']}/index.html">
  <div class="cb-card-body">
    <div class="cb-tags">{tags}</div>
    <h3>{html.escape(r['title'])}</h3>
    <p>{html.escape(tagline)}</p>
    <div class="cb-tags">{pills(stack)}</div>
  </div></a>"""


def write_index(recipes):
    recs = sorted([r for r in recipes if r["kind"] == "recipe"],
                  key=lambda r: r["rj"].get("order", 99))
    bps = [r for r in recipes if r["kind"] == "blueprint"]
    rr = "../"
    sections = [f'<section class="cb-cat"><div class="section-eyebrow">Recipes · {len(recs)}</div>'
                f'<p class="section-lede">A sequenced arc — each recipe is a typed, observable, '
                f'containerized FastAPI agent you can clone and deploy in minutes, building on the one before it.</p>'
                f'<div class="cb-grid">{"".join(card(r) for r in recs)}</div></section>']
    if bps:
        sections.append(f'<section class="cb-cat"><div class="section-eyebrow">Blueprints · {len(bps)}</div>'
                        f'<p class="section-lede">Complete, deployable reference applications that combine many '
                        f'recipe concepts into something you could put in front of users.</p>'
                        f'<div class="cb-grid">{"".join(card(r) for r in bps)}</div></section>')
    page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Agent Blueprints · Nebius</title>
<meta name="description" content="Production-grade, runnable agent recipes on Nebius — Pinecone, Tavily, LangChain/LangGraph, LangSmith, Stripe, Snowglobe — rendered and browsable."/>
<link rel="stylesheet" href="{rr}assets/css/main.css"/>
<link rel="stylesheet" href="{rr}assets/cookbook.css"/>
</head><body>
{nav(rr)}
<header class="hero">
  <div class="container">
    <span class="hero-eyebrow">Runnable reference · the Agent Blueprint Recipes</span>
    <h1>Production-shaped agents, on Nebius.</h1>
    <p class="lede">The <a href="{REPO}" target="_blank" rel="noopener">nebius-partner-cookbook</a> — {len(recs)} sequenced recipes + {len(bps)} full blueprint, each integrating a partner (Pinecone, Tavily, LangChain/LangGraph, LangSmith, Stripe, Snowglobe) on Nebius. Typed, observable, containerized, tested — clone one directory and deploy in minutes.</p>
  </div>
</header>
<div class="container cb-index">
  {''.join(sections)}
</div>
{footer(rr)}
<script src="{rr}assets/js/main.js"></script>
<script src="{rr}assets/nav-logo.js"></script>
</body></html>
"""
    (POUT / "index.html").write_text(page, encoding="utf-8")


def main():
    if not PSRC.exists():
        raise SystemExit(f"partner cookbook source not found at {PSRC} — clone it first")
    if POUT.exists():
        shutil.rmtree(POUT)
    POUT.mkdir(parents=True)
    recipes = []
    for sub, kind in [("cookbooks", "recipe"), ("blueprints", "blueprint")]:
        base = PSRC / sub
        if not base.exists():
            continue
        for d in sorted(base.glob("*")):
            if not d.is_dir() or d.name.startswith("_"):
                continue
            r = load(d, kind)
            if r:
                recipes.append(r)
                write_recipe(r)
    write_index(recipes)
    print(f"DONE  blueprints  recipes={sum(1 for r in recipes if r['kind']=='recipe')}  "
          f"blueprints={sum(1 for r in recipes if r['kind']=='blueprint')}  pages={len(recipes)+1}")


if __name__ == "__main__":
    main()
