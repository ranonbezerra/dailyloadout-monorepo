/**
 * Defense-in-depth validation for cover-image URLs.
 *
 * Cover URLs originate from untrusted sources (IGDB results, LLM-derived
 * candidates) and are rendered directly as `<img src>`. To keep a `javascript:`,
 * `data:`, or other-scheme payload from ever reaching the DOM, only allow
 * `https:` URLs served from the IGDB image CDN.
 */

const ALLOWED_HOST = "images.igdb.com";

/**
 * Returns `url` only when it is an `https:` URL on the IGDB image host;
 * otherwise returns `undefined`.
 *
 * Pass the result straight to an `<img src>` / Mantine `<Image src>` — an
 * `undefined` src renders nothing (or the component's placeholder).
 */
export function safeImageUrl(url: string | null | undefined): string | undefined {
	if (!url) return undefined;

	let parsed: URL;
	try {
		parsed = new URL(url);
	} catch {
		return undefined;
	}

	if (parsed.protocol !== "https:") return undefined;
	if (parsed.hostname !== ALLOWED_HOST) return undefined;

	return url;
}
