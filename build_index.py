#!/usr/bin/env python3
"""Transform the internal ecosystem.html into a standalone, public index.html:
 - swap the internal sibling-page nav for a clean [Ecosystem · Cookbook] nav
 - neutralize the internal 'for team review' byline
 - wire the Cookbook into the hero + reference-architectures section
 - strip links to internal sibling pages (which aren't published here) to plain text
"""
import re
from pathlib import Path

SRC = Path("/Users/colin/Code/nebius-devrel/ecosystem.html")
OUT = Path(__file__).resolve().parent / "index.html"
html = SRC.read_text(encoding="utf-8")

# internal pages not published in this project
SIBLINGS = ["strategy", "programs", "community", "content", "events",
            "benchmarks", "swot-analysis", "metrics-dashboard", "presentation"]

NEW_NAV = """<nav class="nav">
  <div class="nav-inner">
    <a class="brand" href="index.html" aria-label="Nebius — home"><span class="brand-logo" id="nav-logo"></span></a>
    <div class="nav-links" id="nav-menu">
      <a href="index.html" class="active">Ecosystem</a>
      <a href="cookbook/index.html">Cookbook</a>
    </div>
    <div class="nav-actions">
      <a class="nav-cta" href="cookbook/index.html">Cookbook →</a>
      <button class="nav-toggle" type="button" aria-label="Toggle navigation menu" aria-expanded="false" aria-controls="nav-menu"><span></span><span></span><span></span></button>
    </div>
  </div>
</nav>"""

NEW_FOOTER = """<footer>
  <div class="container">
    <div class="footer-grid">
      <div class="footer-col">
        <a class="brand" href="index.html" style="color: white;"><span class="brand-mark"></span> Nebius Ecosystem</a>
        <p style="font-size: 0.9rem; margin-top: 1rem; max-width: 38ch;">An ecosystem demo — the Nebius stack &amp; partners, with the full open-source <a href="https://github.com/nebius/token-factory-cookbook">Token Factory Cookbook</a> rendered and browsable. Hosted on GitHub Pages.</p>
      </div>
      <div class="footer-col">
        <h4>This site</h4>
        <ul>
          <li><a href="index.html">Ecosystem &amp; Partners</a></li>
          <li><a href="cookbook/index.html">Cookbook (50 recipes)</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Nebius</h4>
        <ul>
          <li><a href="https://nebius.com">nebius.com</a></li>
          <li><a href="https://github.com/nebius/token-factory-cookbook">Cookbook repo ↗</a></li>
          <li><a href="https://demo.buildspace.tv/ecosystem">Builder directory ↗</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <span>Nebius products &amp; trademarks belong to Nebius. Cookbook recipes © Nebius (MIT). Ecosystem demo by opencolin.</span>
      <span>GitHub Pages experiment</span>
    </div>
  </div>
</footer>"""

# 1) nav + footer
html = re.sub(r"<nav class=\"nav\">.*?</nav>", lambda m: NEW_NAV, html, count=1, flags=re.S)
html = re.sub(r"<footer>.*?</footer>", lambda m: NEW_FOOTER, html, count=1, flags=re.S)

# 2) title + meta
html = re.sub(r"<title>.*?</title>",
              "<title>Nebius Ecosystem &amp; Partners + Token Factory Cookbook</title>", html, count=1, flags=re.S)

# 3) hero: add a Cookbook button to the first .btn-row
html = html.replace('<a class="btn secondary" href="#directory">The directory</a>',
                    '<a class="btn secondary" href="#directory">The directory</a>\n      <a class="btn" href="cookbook/index.html">Browse the Cookbook →</a>', 1)

# 4) wire the reference-architectures section to the cookbook (insert a callout after its lede)
ref_lede = 'each shipping a repo + short video + written guide + cost calculator. The workshop library on the builder site is the home; several are already drafted there.</p>'
cookbook_cta = ref_lede + """
    <div class="callout coral"><p><strong>▶ These reference architectures are real, runnable recipes.</strong> The full <a href="cookbook/index.html">Token Factory Cookbook</a> — <strong>50 recipes across 17 categories, 27 notebooks rendered with their outputs</strong> — backs every architecture below: <a href="cookbook/index.html">research agents</a> (CrewAI / LangChain + Tavily), <a href="cookbook/index.html">fine-tuning &amp; LoRA</a>, the <a href="cookbook/index.html">one-<code>base_url</code> API quickstarts</a>, RAG, distillation, and more. <a href="cookbook/index.html">Browse all 50 →</a></p></div>"""
html = html.replace(ref_lede, cookbook_cta, 1)

# 5) strip links to internal sibling pages -> plain text (keep inner content)
for s in SIBLINGS:
    html = re.sub(rf'<a [^>]*href="{re.escape(s)}\.html"[^>]*>(.*?)</a>', r"\1", html, flags=re.S)

# self-link
html = html.replace('href="ecosystem.html"', 'href="index.html"')

OUT.write_text(html, encoding="utf-8")
# report leftover internal links
leftovers = re.findall(r'href="(' + "|".join(SIBLINGS) + r')\.html"', html)
print(f"index.html written ({len(html)} bytes). leftover internal sibling links: {len(leftovers)}")
