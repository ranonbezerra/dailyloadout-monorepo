import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SocialLoginButtons } from "./SocialLoginButtons";

function renderButtons(props: { label?: string } = {}) {
	return render(
		<MantineProvider>
			<SocialLoginButtons {...props} />
		</MantineProvider>,
	);
}

describe("SocialLoginButtons", () => {
	const originalLocation = window.location;

	beforeEach(() => {
		vi.unstubAllEnvs();
		// Replace window.location with a writable href so clicks can be asserted.
		Object.defineProperty(window, "location", {
			configurable: true,
			writable: true,
			value: { ...originalLocation, href: "" },
		});
	});

	afterEach(() => {
		Object.defineProperty(window, "location", {
			configurable: true,
			writable: true,
			value: originalLocation,
		});
		vi.unstubAllEnvs();
	});

	it("renders a button per default provider (google + twitch)", () => {
		vi.stubEnv("VITE_OAUTH_PROVIDERS", "google,twitch");
		renderButtons();

		expect(screen.getByRole("button", { name: /continue with google/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /continue with twitch/i })).toBeInTheDocument();
	});

	it("uses the provided divider label", () => {
		vi.stubEnv("VITE_OAUTH_PROVIDERS", "google");
		renderButtons({ label: "or sign up with" });

		expect(screen.getByText("or sign up with")).toBeInTheDocument();
	});

	it("renders nothing (no buttons, no divider) when no providers are enabled", () => {
		vi.stubEnv("VITE_OAUTH_PROVIDERS", "");
		renderButtons({ label: "or continue with" });

		expect(screen.queryByRole("button")).not.toBeInTheDocument();
		expect(screen.queryByText("or continue with")).not.toBeInTheDocument();
	});

	it("navigates to the provider start URL on click", () => {
		vi.stubEnv("VITE_OAUTH_PROVIDERS", "google");
		renderButtons();

		screen.getByRole("button", { name: /continue with google/i }).click();

		expect(window.location.href).toMatch(/\/v1\/auth\/oauth\/google\/start$/);
	});
});
