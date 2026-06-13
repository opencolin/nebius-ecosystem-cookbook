#!/usr/bin/env bash
# mirror_devsite.sh — snapshot the demo.buildspace.tv builder devsite (the
# dev.nebius.com mock-up, a Next.js SSR app) into ./devsite/ as a static site
# that can be hosted under the GitHub Pages subpath /<repo>/devsite/.
#
# Why a snapshot (not a build): the devsite is a Pages-Router app with
# getServerSideProps + API routes + a Directus CMS backend. It can't be
# `next export`-ed, and we must not modify its repo. wget captures the
# already-rendered SSR HTML + static assets and relativizes every link so the
# result works from a subpath with no server.
#
# Re-run any time to refresh the snapshot. Idempotent.
set -euo pipefail
cd "$(dirname "$0")"

HOST="https://demo.buildspace.tv"
URLS=".cache/devsite-urls.txt"

# 1) Build the URL list from the live sitemap (the sitemap's <loc> host is the
#    stale demo.buildspace.sh — force it to the live .tv host).
mkdir -p .cache
echo "→ fetching sitemap…"
curl -fsSL "$HOST/sitemap.xml" \
  | grep -oE '<loc>[^<]+</loc>' \
  | sed -E 's#</?loc>##g; s#https?://[^/]+#'"$HOST"'#' \
  | sort -u > "$URLS"
# core pages the sitemap may omit
for p in "" about-this-build ecosystem apps library events team office-hours serverless; do
  echo "$HOST/$p"
done >> "$URLS"
sort -u -o "$URLS" "$URLS"
echo "  $(wc -l < "$URLS" | tr -d ' ') urls"

# 2) Mirror. --page-requisites pulls css/js/img; --convert-links relativizes
#    every href/src so it resolves from ./devsite/ under a subpath. Reject the
#    runtime data/api routes (they 404 statically and aren't needed for render).
echo "→ mirroring (this takes a few minutes)…"
rm -rf devsite && mkdir devsite
( cd devsite && wget -nv -nH -e robots=off \
    --adjust-extension --page-requisites --convert-links \
    --reject-regex '/api/|/_next/data/' \
    --no-parent --timeout=25 --tries=2 --wait=0 \
    --input-file="../$URLS" )

# 3) Neutralize the first-visit redirect on the homepage.
#    FirstVisitRedirect.tsx bounces pathname==='/' to /about-this-build once,
#    gated on localStorage['nb_first_visit_done']. Under the /devsite/ subpath
#    that router.replace('/about-this-build') resolves to the Pages root and
#    404s. Pre-set the flag in index.html's <head> (before the Next bundle
#    hydrates) so the redirect no-ops and /devsite/ shows the homepage.
echo "→ neutralizing first-visit redirect…"
python3 - <<'PY'
from pathlib import Path
idx = Path("devsite/index.html")
html = idx.read_text(encoding="utf-8")
marker = "/*devsite-no-redirect*/"
if marker not in html:
    snippet = f"<head><script>{marker}try{{localStorage.setItem('nb_first_visit_done','1')}}catch(e){{}}</script>"
    html = html.replace("<head>", snippet, 1)
    idx.write_text(html, encoding="utf-8")
    print("  injected flag into index.html")
else:
    print("  already neutralized")
PY

# 4) Rewrite absolute root paths baked into the JS bundles.
#    The devsite has no Next assetPrefix/basePath, so its client runtime hardcodes
#    absolute "/_next/" (webpack publicPath) and components emit absolute asset
#    refs like "/nebius-logo.svg". Those resolve to the Pages domain root and 404
#    under the /<repo>/devsite/ subpath. wget only relativizes refs in the static
#    HTML, not strings inside JS — so rewrite the bundles to the subpath-absolute
#    prefix. (Match the QUOTED literals so re-runs stay idempotent.)
PREFIX="/nebius-ecosystem-cookbook/devsite"
echo "→ rewriting absolute runtime paths to $PREFIX …"
python3 - "$PREFIX" <<'PY'
import sys, glob
prefix = sys.argv[1]
subs = [('"/_next/"', f'"{prefix}/_next/"'),
        ('"/nebius-logo.svg"', f'"{prefix}/nebius-logo.svg"')]
n = 0
for f in glob.glob("devsite/_next/static/chunks/**/*.js", recursive=True):
    s = open(f, encoding="utf-8").read()
    o = s
    for a, b in subs:
        s = s.replace(a, b)
    if s != o:
        open(f, "w", encoding="utf-8").write(s); n += 1
print(f"  rewrote {n} JS chunk(s)")
PY

# 5) Make in-site navigation work. Next <Link> re-asserts absolute routes
#    (href="/events") on hydration and drives client-side routing, which is
#    broken under the subpath (the app has no basePath, so the router targets
#    the domain root + 404s on _next/data). Inject a capture-phase click
#    interceptor that turns internal absolute-route clicks into hard
#    navigations to the mirrored .html. Runs before React's handler, so the
#    SPA router never sees the click. External/hash/asset links pass through.
echo "→ injecting nav interceptor into all pages…"
python3 - "$PREFIX" <<'PY'
import sys, glob
prefix = sys.argv[1]
marker = "/*devsite-navfix*/"
script = ('<head><script>' + marker +
  '(function(){var B="' + prefix + '";'
  'document.addEventListener("click",function(e){'
  'var a=e.target&&e.target.closest?e.target.closest("a"):null;if(!a)return;'
  'var h=a.getAttribute("href");if(!h)return;'
  'if(h[0]==="#"||h.indexOf("//")===0||/^[a-z]+:/i.test(h))return;'        # hash / protocol-relative / scheme
  'if(h.indexOf(B)===0||h[0]!=="/")return;'                                # already-subpath or relative: leave
  'var q=h.replace(/[?#].*$/,"");if(/\\.[a-z0-9]+$/i.test(q))return;'      # already a file (.html/.svg)
  'var p=q==="/"?"/index":q.replace(/\\/$/,"");'
  'e.preventDefault();e.stopPropagation();window.location.href=B+p+".html"'
  '},true)})();</script>')
n = 0
for f in glob.glob("devsite/**/*.html", recursive=True):
    s = open(f, encoding="utf-8").read()
    if marker in s:
        continue
    s2 = s.replace("<head>", script, 1)
    if s2 != s:
        open(f, "w", encoding="utf-8").write(s2); n += 1
print(f"  injected nav interceptor into {n} page(s)")
PY

echo "✓ devsite mirror ready ($(find devsite -name '*.html' | wc -l | tr -d ' ') pages, $(du -sh devsite | cut -f1))"
