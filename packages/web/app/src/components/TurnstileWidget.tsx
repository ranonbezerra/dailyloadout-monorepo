import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

// ---------------------------------------------------------------------------
// Cloudflare Turnstile widget.
//
// Renders the invisible/managed CAPTCHA challenge on the register form and
// hands the solved token back via `onToken`. The site key comes from
// `VITE_TURNSTILE_SITE_KEY`; when it's unset we render NOTHING and the caller
// submits with no token (the server's TURNSTILE_SECRET is then also unset, so
// the missing token is a no-op). Exposes an imperative `reset()` so the form
// can re-arm the widget after a failed submit (Turnstile tokens are single-use).
// ---------------------------------------------------------------------------

const SCRIPT_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js";
const SCRIPT_ID = "cf-turnstile-script";

interface TurnstileApi {
	render: (
		el: HTMLElement,
		opts: {
			sitekey: string;
			callback: (token: string) => void;
			"error-callback"?: () => void;
			"expired-callback"?: () => void;
		},
	) => string;
	reset: (widgetId?: string) => void;
	remove: (widgetId: string) => void;
}

declare global {
	interface Window {
		turnstile?: TurnstileApi;
	}
}

export const TURNSTILE_SITE_KEY: string | undefined =
	(typeof import.meta !== "undefined" && import.meta.env?.VITE_TURNSTILE_SITE_KEY) || undefined;

export interface TurnstileHandle {
	/** Reset the widget so it issues a fresh, single-use token. */
	reset: () => void;
}

interface TurnstileWidgetProps {
	/** Fired with the solved-challenge token (or null when it expires/errors). */
	onToken: (token: string | null) => void;
}

/** Inject the Turnstile script once; resolve when the global API is ready. */
function loadTurnstileScript(): Promise<void> {
	if (typeof document === "undefined") return Promise.resolve();
	if (window.turnstile) return Promise.resolve();

	return new Promise((resolve) => {
		const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
		if (existing) {
			existing.addEventListener("load", () => resolve(), { once: true });
			if (window.turnstile) resolve();
			return;
		}
		const script = document.createElement("script");
		script.id = SCRIPT_ID;
		script.src = SCRIPT_SRC;
		script.async = true;
		script.defer = true;
		script.addEventListener("load", () => resolve(), { once: true });
		document.head.appendChild(script);
	});
}

export const TurnstileWidget = forwardRef<TurnstileHandle, TurnstileWidgetProps>(
	function TurnstileWidget({ onToken }, ref) {
		const containerRef = useRef<HTMLDivElement | null>(null);
		const widgetIdRef = useRef<string | null>(null);

		useImperativeHandle(ref, () => ({
			reset: () => {
				if (window.turnstile && widgetIdRef.current) {
					window.turnstile.reset(widgetIdRef.current);
					onToken(null);
				}
			},
		}));

		useEffect(() => {
			// No site key → render nothing and never load the script.
			if (!TURNSTILE_SITE_KEY) return;

			let cancelled = false;

			loadTurnstileScript().then(() => {
				if (cancelled || !containerRef.current || !window.turnstile) return;
				if (widgetIdRef.current) return; // already rendered (StrictMode guard)
				widgetIdRef.current = window.turnstile.render(containerRef.current, {
					sitekey: TURNSTILE_SITE_KEY as string,
					callback: (token) => onToken(token),
					"error-callback": () => onToken(null),
					"expired-callback": () => onToken(null),
				});
			});

			return () => {
				cancelled = true;
				if (window.turnstile && widgetIdRef.current) {
					window.turnstile.remove(widgetIdRef.current);
					widgetIdRef.current = null;
				}
			};
		}, [onToken]);

		// Site key absent → render nothing (caller submits without a token).
		if (!TURNSTILE_SITE_KEY) return null;

		return <div ref={containerRef} data-testid="turnstile-widget" />;
	},
);
