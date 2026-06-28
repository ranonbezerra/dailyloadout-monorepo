import { BASE_URL } from "@dl/shared/api";
import { afterEach, describe, expect, it, vi } from "vitest";
import { enabledOAuthProviders, oauthErrorMessage, oauthStartUrl } from "./oauth";

afterEach(() => {
	vi.unstubAllEnvs();
});

describe("oauthStartUrl", () => {
	it("builds the API start URL for a provider", () => {
		expect(oauthStartUrl("google")).toBe(`${BASE_URL}/v1/auth/oauth/google/start`);
		expect(oauthStartUrl("twitch")).toBe(`${BASE_URL}/v1/auth/oauth/twitch/start`);
	});
});

describe("enabledOAuthProviders", () => {
	it("defaults to google and twitch when the env var is unset", () => {
		vi.stubEnv("VITE_OAUTH_PROVIDERS", undefined as unknown as string);
		const providers = enabledOAuthProviders();
		expect(providers.map((p) => p.provider)).toEqual(["google", "twitch"]);
		expect(providers.map((p) => p.label)).toEqual(["Google", "Twitch"]);
	});

	it("honours a custom env list and ignores unknown providers", () => {
		vi.stubEnv("VITE_OAUTH_PROVIDERS", "twitch,facebook");
		expect(enabledOAuthProviders().map((p) => p.provider)).toEqual(["twitch"]);
	});

	it("trims whitespace and lowercases entries", () => {
		vi.stubEnv("VITE_OAUTH_PROVIDERS", " Google , TWITCH ");
		expect(enabledOAuthProviders().map((p) => p.provider)).toEqual(["google", "twitch"]);
	});

	it("returns no providers for an explicit empty string", () => {
		vi.stubEnv("VITE_OAUTH_PROVIDERS", "");
		expect(enabledOAuthProviders()).toEqual([]);
	});
});

describe("oauthErrorMessage", () => {
	it("maps each known reason to a specific message", () => {
		expect(oauthErrorMessage("invalid_state")).toMatch(/expired or was invalid/i);
		expect(oauthErrorMessage("provider_unavailable")).toMatch(/currently unavailable/i);
		expect(oauthErrorMessage("oauth_failed")).toMatch(/couldn't sign you in with that provider/i);
		expect(oauthErrorMessage("account_exists")).toBe(
			"An account with this email already exists. Log in with your password, then link this provider in settings.",
		);
	});

	it("falls back to a generic message for unknown or missing reasons", () => {
		const fallback = "We couldn't sign you in. Please try again.";
		expect(oauthErrorMessage("something_else")).toBe(fallback);
		expect(oauthErrorMessage(null)).toBe(fallback);
		expect(oauthErrorMessage(undefined)).toBe(fallback);
	});
});
