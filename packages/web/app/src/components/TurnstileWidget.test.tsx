import { render, waitFor } from "@testing-library/react";
import { createRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { TurnstileHandle } from "./TurnstileWidget";

// ---------------------------------------------------------------------------
// The widget reads VITE_TURNSTILE_SITE_KEY at module-eval time, so each test
// stubs the env, resets the module registry, then dynamically imports a fresh
// copy of the component.
// ---------------------------------------------------------------------------

async function loadWidget() {
	return import("./TurnstileWidget");
}

afterEach(() => {
	vi.unstubAllEnvs();
	vi.resetModules();
	// Clean up any injected Turnstile globals/scripts between tests.
	(window as { turnstile?: unknown }).turnstile = undefined;
	document.getElementById("cf-turnstile-script")?.remove();
});

describe("TurnstileWidget", () => {
	it("renders nothing when no site key is configured", async () => {
		vi.stubEnv("VITE_TURNSTILE_SITE_KEY", "");
		vi.resetModules();
		const { TurnstileWidget } = await loadWidget();

		const { container } = render(<TurnstileWidget onToken={vi.fn()} />);

		expect(container.querySelector('[data-testid="turnstile-widget"]')).toBeNull();
		// No script injected either.
		expect(document.getElementById("cf-turnstile-script")).toBeNull();
	});

	describe("with a site key configured", () => {
		let renderMock: ReturnType<typeof vi.fn>;
		let capturedCallback: ((token: string) => void) | undefined;

		beforeEach(() => {
			vi.stubEnv("VITE_TURNSTILE_SITE_KEY", "site-key-123");
			vi.resetModules();
			renderMock = vi.fn((_el: HTMLElement, opts: { callback: (t: string) => void }) => {
				capturedCallback = opts.callback;
				return "widget-1";
			});
			// Pretend the Cloudflare script already loaded.
			(window as { turnstile?: unknown }).turnstile = {
				render: renderMock,
				reset: vi.fn(),
				remove: vi.fn(),
			};
		});

		it("renders the widget container and reports the solved token", async () => {
			const { TurnstileWidget } = await loadWidget();
			const onToken = vi.fn();

			const { container } = render(<TurnstileWidget onToken={onToken} />);

			await waitFor(() => {
				expect(renderMock).toHaveBeenCalled();
			});
			expect(container.querySelector('[data-testid="turnstile-widget"]')).toBeInTheDocument();

			// Simulate Cloudflare solving the challenge.
			capturedCallback?.("solved-token");
			expect(onToken).toHaveBeenCalledWith("solved-token");
		});

		it("reset() clears the token via the imperative handle", async () => {
			const { TurnstileWidget } = await loadWidget();
			const onToken = vi.fn();
			const ref = createRef<TurnstileHandle>();

			render(<TurnstileWidget ref={ref} onToken={onToken} />);

			await waitFor(() => {
				expect(renderMock).toHaveBeenCalled();
			});

			ref.current?.reset();

			const turnstile = (window as { turnstile?: { reset: ReturnType<typeof vi.fn> } }).turnstile;
			expect(turnstile?.reset).toHaveBeenCalledWith("widget-1");
			expect(onToken).toHaveBeenCalledWith(null);
		});

		it("forwards null on the error and expired callbacks", async () => {
			const { TurnstileWidget } = await loadWidget();
			const onToken = vi.fn();

			render(<TurnstileWidget onToken={onToken} />);

			await waitFor(() => {
				expect(renderMock).toHaveBeenCalled();
			});

			const opts = renderMock.mock.calls[0][1] as {
				"error-callback": () => void;
				"expired-callback": () => void;
			};
			opts["error-callback"]();
			opts["expired-callback"]();
			expect(onToken).toHaveBeenNthCalledWith(1, null);
			expect(onToken).toHaveBeenNthCalledWith(2, null);
		});

		it("removes the widget on unmount", async () => {
			const { TurnstileWidget } = await loadWidget();
			const { unmount } = render(<TurnstileWidget onToken={vi.fn()} />);

			await waitFor(() => {
				expect(renderMock).toHaveBeenCalled();
			});

			unmount();

			const turnstile = (window as { turnstile?: { remove: ReturnType<typeof vi.fn> } }).turnstile;
			expect(turnstile?.remove).toHaveBeenCalledWith("widget-1");
		});
	});

	describe("script injection (Cloudflare API not yet loaded)", () => {
		beforeEach(() => {
			vi.stubEnv("VITE_TURNSTILE_SITE_KEY", "site-key-123");
			vi.resetModules();
			(window as { turnstile?: unknown }).turnstile = undefined;
		});

		it("injects the api.js script and renders once it loads", async () => {
			const { TurnstileWidget } = await loadWidget();
			const onToken = vi.fn();

			render(<TurnstileWidget onToken={onToken} />);

			// The script tag is injected while the global API is unavailable.
			const script = document.getElementById("cf-turnstile-script") as HTMLScriptElement | null;
			expect(script).not.toBeNull();
			expect(script?.src).toContain("challenges.cloudflare.com/turnstile/v0/api.js");

			// Simulate Cloudflare finishing loading: define the global, fire `load`.
			const renderMock = vi.fn(() => "widget-script");
			(window as { turnstile?: unknown }).turnstile = {
				render: renderMock,
				reset: vi.fn(),
				remove: vi.fn(),
			};
			script?.dispatchEvent(new Event("load"));

			await waitFor(() => {
				expect(renderMock).toHaveBeenCalled();
			});
		});
	});
});
