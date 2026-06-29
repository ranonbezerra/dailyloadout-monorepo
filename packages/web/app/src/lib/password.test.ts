import { describe, expect, it } from "vitest";
import { validatePasswordComplexity, validatePasswordMatch } from "./password";

describe("validatePasswordComplexity", () => {
	it("accepts a compliant password", () => {
		expect(validatePasswordComplexity("StrongPass1")).toBeNull();
	});

	it("rejects passwords shorter than 8 characters", () => {
		expect(validatePasswordComplexity("Aa1")).toBe("Password must be at least 8 characters");
	});

	it("requires an uppercase letter", () => {
		expect(validatePasswordComplexity("lowercase1")).toBe(
			"Password must contain an uppercase letter",
		);
	});

	it("requires a lowercase letter", () => {
		expect(validatePasswordComplexity("UPPERCASE1")).toBe(
			"Password must contain a lowercase letter",
		);
	});

	it("requires a digit", () => {
		expect(validatePasswordComplexity("NoDigitsHere")).toBe("Password must contain a digit");
	});
});

describe("validatePasswordMatch", () => {
	it("returns null when the values match", () => {
		expect(validatePasswordMatch("abc", "abc")).toBeNull();
	});

	it("returns an error when the values differ", () => {
		expect(validatePasswordMatch("abc", "xyz")).toBe("Passwords do not match");
	});
});
