/**
 * Build-only Content-Security-Policy for the Slate web apps.
 *
 * Injected as a <meta http-equiv="Content-Security-Policy"> ONLY in production
 * builds (``apply: "build"``) — the dev server is left untouched because Vite's
 * HMR needs inline scripts, eval, and a ws: connection that a strict policy
 * would break. It's a defense-in-depth second line: the apps have no XSS sinks
 * today, but a CSP contains the blast radius if one ever appears.
 *
 * ``connect-src`` tracks ``VITE_API_URL`` (the same origin the API client calls),
 * so a build for any environment automatically allows exactly its own API and
 * nothing else. ``frame-ancestors`` is included for completeness but browsers
 * ignore it in a meta tag — real clickjacking protection must be an
 * X-Frame-Options / frame-ancestors *response header* at the web host.
 */

/** Return the origin of *url* (scheme://host:port), or "" if unparseable. */
export function originOf(url) {
  if (!url) return "";
  try {
    return new URL(url).origin;
  } catch {
    return "";
  }
}

/** Build the CSP header/meta value. */
export function buildCsp({ apiOrigin = "", allowCloudflare = false } = {}) {
  const script = ["'self'"];
  const connect = ["'self'"];
  const frame = [];
  if (apiOrigin) connect.push(apiOrigin);
  if (allowCloudflare) {
    // Cloudflare Turnstile: loads a script, opens a challenge iframe, and posts
    // the solved token back — needed only by the player app's registration.
    script.push("https://challenges.cloudflare.com");
    connect.push("https://challenges.cloudflare.com");
    frame.push("https://challenges.cloudflare.com");
  }
  return [
    "default-src 'self'",
    `script-src ${script.join(" ")}`,
    // 'unsafe-inline' styles: Mantine injects inline style props; Google Fonts CSS.
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    // Scoped to the IGDB cover CDN (not a bare `https:` wildcard) so an XSS
    // blast radius can't beacon the in-memory access token out via image GETs.
    "img-src 'self' data: https://images.igdb.com",
    `connect-src ${connect.join(" ")}`,
    `frame-src ${frame.length ? frame.join(" ") : "'none'"}`,
    "base-uri 'self'",
    "object-src 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");
}

/** A Vite plugin that injects the CSP meta into the built index.html only. */
export function cspPlugin({ apiOrigin = "", allowCloudflare = false } = {}) {
  return {
    name: "slate-csp-meta",
    apply: "build",
    transformIndexHtml(html) {
      const csp = buildCsp({ apiOrigin, allowCloudflare });
      const tag = `<meta http-equiv="Content-Security-Policy" content="${csp}" />`;
      return html.replace("</head>", `  ${tag}\n  </head>`);
    },
  };
}
