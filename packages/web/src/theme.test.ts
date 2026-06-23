import { describe, expect, it } from "vitest";
import { theme } from "./theme";

describe("theme", () => {
	it("has 'coral' as the primaryColor", () => {
		expect(theme.primaryColor).toBe("coral");
	});

	it("defines the expected custom color palettes", () => {
		expect(theme.colors).toBeDefined();
		expect(theme.colors?.coral).toHaveLength(10);
		expect(theme.colors?.violet).toHaveLength(10);
		expect(theme.colors?.green).toHaveLength(10);
		expect(theme.colors?.dark).toHaveLength(10);
	});

	it("sets the correct font families", () => {
		expect(theme.fontFamily).toContain("Inter");
		expect(theme.fontFamilyMonospace).toContain("JetBrains Mono");
		expect(theme.headings?.fontFamily).toContain("Outfit");
	});

	it("contains Night Den brand tokens in theme.other", () => {
		expect(theme.other).toBeDefined();
		expect(theme.other?.coral).toBe("#FF5A4D");
		expect(theme.other?.bg).toBe("#121119");
		expect(theme.other?.violet).toBe("#9A8CF5");
		expect(theme.other?.green).toBe("#46C28A");
	});

	it("configures component defaults", () => {
		expect(theme.components).toBeDefined();
		expect(theme.components?.Button).toBeDefined();
		expect(theme.components?.Card).toBeDefined();
		expect(theme.components?.Paper).toBeDefined();
		expect(theme.components?.Badge).toBeDefined();
	});
});
