import { describe, expect, it } from "vitest";
import { safeImageUrl } from "./safe-image";

describe("safeImageUrl", () => {
	it("passes an https IGDB cover URL through unchanged", () => {
		const url = "https://images.igdb.com/igdb/image/upload/t_cover_big/abc123.jpg";
		expect(safeImageUrl(url)).toBe(url);
	});

	it("rejects http (insecure) URLs", () => {
		expect(safeImageUrl("http://images.igdb.com/igdb/image/x.jpg")).toBeUndefined();
	});

	it("rejects javascript: URLs", () => {
		expect(safeImageUrl("javascript:alert(1)")).toBeUndefined();
	});

	it("rejects data: URLs", () => {
		expect(safeImageUrl("data:image/png;base64,iVBORw0KGgo=")).toBeUndefined();
	});

	it("rejects https URLs from other hosts", () => {
		expect(safeImageUrl("https://evil.example.com/cover.jpg")).toBeUndefined();
	});

	it("rejects malformed / non-URL strings", () => {
		expect(safeImageUrl("not a url")).toBeUndefined();
	});

	it("returns undefined for null / undefined / empty", () => {
		expect(safeImageUrl(null)).toBeUndefined();
		expect(safeImageUrl(undefined)).toBeUndefined();
		expect(safeImageUrl("")).toBeUndefined();
	});
});
