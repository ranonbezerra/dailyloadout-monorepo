import { describe, expect, it } from "vitest";
import { isEmailNotVerifiedError } from "./errors";

describe("isEmailNotVerifiedError", () => {
	it("matches the API's 'Email not verified' detail (case-insensitive)", () => {
		expect(isEmailNotVerifiedError(new Error("Email not verified"))).toBe(true);
		expect(isEmailNotVerifiedError(new Error("email not verified"))).toBe(true);
	});

	it("does not match other errors", () => {
		expect(isEmailNotVerifiedError(new Error("Session expired"))).toBe(false);
		expect(isEmailNotVerifiedError(new Error("Not found"))).toBe(false);
	});

	it("returns false for non-Error values", () => {
		expect(isEmailNotVerifiedError("Email not verified")).toBe(false);
		expect(isEmailNotVerifiedError(null)).toBe(false);
		expect(isEmailNotVerifiedError(undefined)).toBe(false);
	});
});
