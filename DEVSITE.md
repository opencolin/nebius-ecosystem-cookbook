# Builder devsite mirror (`/devsite/`)

A static snapshot of the **demo.buildspace.tv** builder devsite — the
dev.nebius.com mock-up — hosted alongside the Ecosystem page and the Token
Factory Cookbook on GitHub Pages, at
`https://opencolin.github.io/nebius-ecosystem-cookbook/devsite/`.

The devsite is a Next.js (Pages Router) SSR app backed by Directus, with
`getServerSideProps` + API routes. It can't be `next export`-ed and its repo
must not be modified, so this is a **wget mirror** of the rendered output, with
post-processing so it works from a project-page subpath with no server.

## Rebuild

```bash
./mirror_devsite.sh          # sitemap → wget → fixups → ./devsite/
```

Idempotent. The whole pipeline lives in [`mirror_devsite.sh`](mirror_devsite.sh):

1. **URL list** from the live `sitemap.xml` (its `<loc>` host is the stale
   `demo.buildspace.sh`; forced to the live `demo.buildspace.tv`), plus core
   pages the sitemap omits.
2. **Mirror** with `wget --mirror`-style flags: `--page-requisites`
   (css/js/img), `--convert-links` (relativize refs), `--adjust-extension`
   (`/events` → `events.html`), rejecting `/api/` and `/_next/data/`.
3. **Neutralize the first-visit redirect.** `FirstVisitRedirect` bounces
   `pathname === '/'` to `/about-this-build` once (gated on
   `localStorage['nb_first_visit_done']`). Under the subpath that
   `router.replace` hits the Pages root and 404s, so the flag is pre-set in
   `index.html`'s `<head>` and the homepage shows normally.
4. **Rewrite absolute runtime paths.** The app has no `assetPrefix`, so its
   client runtime hardcodes absolute `/_next/` (webpack `publicPath`) and emits
   `/nebius-logo.svg`. wget only fixes refs in the static HTML, not strings
   inside JS, so the 3 affected bundles are rewritten to the subpath-absolute
   prefix.
5. **Make navigation work.** Next `<Link>` drives client-side routing to the
   app's internal absolute routes (`/library/x`, no extension), which 404 under
   the subpath. A capture-phase click interceptor injected into every page
   turns internal link clicks into hard navigations to the mirrored `.html`
   (relative → resolved `a.href`; absolute route → subpath + `.html`),
   preempting the SPA router.

## Fidelity report

**What survived (high fidelity):**

- **367 pages** — every URL in the sitemap: homepage, `/events`, `/library`
  (+ ~160 detail pages), `/apps` (+ ~190 project/integration detail pages),
  `/ecosystem`, `/team`, `/office-hours`, `/about-this-build`, `/serverless`,
  `/signup`, etc.
- **Branding is near pixel-identical** to the live site: lime Nebius logo,
  Space Mono headings, the nav (Events / Library / Ecosystem / Docs + search +
  dark-mode toggle + Get started), both "MOCKUP FOR REVIEW" banners, the
  brand toggle, and the full footer. CSS, images, and SSR content all render.
- **Navigation works** — top nav, footer links, and directory cards all
  resolve to the mirrored detail pages (verified end-to-end).
- **Deep links / direct URLs work** — e.g.
  `/devsite/library/<slug>.html` loads standalone.

**What degraded (expected for a static snapshot):**

- **Server features are gone** — the password gate (`middleware.js`), API
  routes, GitHub OAuth login, and live Directus reads. Content is frozen at
  mirror time.
- **Filters/search are not wired** — the `/library` and `/apps` filter chips
  render but don't re-query (no backend); every card is present and clickable.
- **Background prefetch 404s** — Next optimistically prefetches `/_next/data/*`
  and sibling route chunks for client-side nav; those aren't mirrored, so the
  console shows background 404s. They don't affect rendering or navigation (the
  interceptor hard-navigates instead).
- **Caching note** — Pages serves HTML with a ~10-minute cache; a returning
  visitor may briefly see a previous version of a page after a rebuild.

**Not exposed:** the mirror is the already-public mock-up. No credentials,
tokens, or non-public data are included.
