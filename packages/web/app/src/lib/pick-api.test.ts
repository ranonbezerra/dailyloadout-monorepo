import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@slate/shared/api", () => ({
	apiFetch: vi.fn(),
	BASE_URL: "http://test",
	getAccessToken: vi.fn(() => "test-token"),
}));

import { apiFetch } from "@slate/shared/api";
import { acceptPick, createPick, getLatestPick, listPicks, rejectPick } from "./pick-api";

const mockApiFetch = apiFetch as Mock;

beforeEach(() => {
	mockApiFetch.mockReset();
});

// ---------------------------------------------------------------------------
// Create pick
// ---------------------------------------------------------------------------

describe("createPick", () => {
	it("calls POST /v1/picks with snake_cased body and defaults", async () => {
		const apiResponse = [
			{
				public_id: "lo1",
				library_entry: null,
				mood: "chill",
				available_minutes: 60,
				mental_energy: "low",
				context: null,
				reasoning: "Perfect for a low-energy session",
				action: null,
				created_at: "2024-01-01",
				updated_at: "2024-01-01",
			},
		];
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await createPick("chill", 60, "low");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/picks", {
			method: "POST",
			body: JSON.stringify({
				mood: "chill",
				available_minutes: 60,
				mental_energy: "low",
				context: null,
				count: 1,
			}),
		});
		expect(result).toHaveLength(1);
		expect(result[0].publicId).toBe("lo1");
		expect(result[0].availableMinutes).toBe(60);
		expect(result[0].mentalEnergy).toBe("low");
	});

	it("passes custom count and context", async () => {
		mockApiFetch.mockResolvedValueOnce([]);

		await createPick("focused", 120, "high", 3, "Want something story-driven");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/picks", {
			method: "POST",
			body: JSON.stringify({
				mood: "focused",
				available_minutes: 120,
				mental_energy: "high",
				context: "Want something story-driven",
				count: 3,
			}),
		});
	});

	it("converts nested library_entry to camelCase", async () => {
		const apiResponse = [
			{
				public_id: "lo1",
				library_entry: {
					public_id: "le1",
					game: {
						public_id: "g1",
						title: "Hades",
						slug: "hades",
						metadata_source: "igdb",
						created_at: "2024-01-01",
					},
					platform: { id: 1, slug: "pc", label: "PC", family: "computer" },
					status: "playing",
					last_played_at: "2024-06-01",
					created_at: "2024-01-01",
					updated_at: "2024-01-01",
				},
				mood: "energetic",
				available_minutes: 90,
				mental_energy: "high",
				context: null,
				reasoning: "Time for action",
				action: null,
				created_at: "2024-01-01",
				updated_at: "2024-01-01",
			},
		];
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await createPick("energetic", 90, "high");

		expect(result[0].libraryEntry).not.toBeNull();
		expect(result[0].libraryEntry?.publicId).toBe("le1");
		expect(result[0].libraryEntry?.game.publicId).toBe("g1");
		expect(result[0].libraryEntry?.game.metadataSource).toBe("igdb");
		expect(result[0].libraryEntry?.lastPlayedAt).toBe("2024-06-01");
	});
});

// ---------------------------------------------------------------------------
// Accept pick
// ---------------------------------------------------------------------------

describe("acceptPick", () => {
	it("calls POST /v1/picks/:publicId/accept", async () => {
		const apiResponse = {
			public_id: "lo1",
			library_entry: null,
			mood: "chill",
			available_minutes: 60,
			mental_energy: "low",
			context: null,
			reasoning: "Good choice",
			action: "accepted",
			created_at: "2024-01-01",
			updated_at: "2024-01-01",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await acceptPick("lo1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/picks/lo1/accept", {
			method: "POST",
		});
		expect(result.publicId).toBe("lo1");
		expect(result.action).toBe("accepted");
	});
});

// ---------------------------------------------------------------------------
// Reject pick
// ---------------------------------------------------------------------------

describe("rejectPick", () => {
	it("calls POST /v1/picks/:publicId/reject", async () => {
		const apiResponse = {
			public_id: "lo1",
			library_entry: null,
			mood: "chill",
			available_minutes: 60,
			mental_energy: "low",
			context: null,
			reasoning: "Good choice",
			action: "rejected",
			created_at: "2024-01-01",
			updated_at: "2024-01-01",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await rejectPick("lo1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/picks/lo1/reject", {
			method: "POST",
		});
		expect(result.action).toBe("rejected");
	});
});

// ---------------------------------------------------------------------------
// List picks
// ---------------------------------------------------------------------------

describe("listPicks", () => {
	it("calls GET /v1/picks with no params when none given", async () => {
		const apiResponse = { items: [], total: 0 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await listPicks();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/picks");
		expect(result).toEqual(apiResponse);
	});

	it("appends query params for limit and offset", async () => {
		const apiResponse = { items: [], total: 0 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		await listPicks({ limit: 10, offset: 20 });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("limit=10");
		expect(calledPath).toContain("offset=20");
	});

	it("converts snake_case response items to camelCase", async () => {
		const apiResponse = {
			items: [
				{
					public_id: "lo1",
					library_entry: null,
					mood: "chill",
					available_minutes: 60,
					mental_energy: "low",
					context: null,
					reasoning: "Relax time",
					action: "accepted",
					created_at: "2024-01-01",
				},
			],
			total: 1,
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await listPicks();

		expect(result.items[0].publicId).toBe("lo1");
		expect(result.items[0].availableMinutes).toBe(60);
		expect(result.items[0].mentalEnergy).toBe("low");
		expect(result.items[0].createdAt).toBe("2024-01-01");
	});

	it("handles offset=0 correctly (falsy but valid)", async () => {
		mockApiFetch.mockResolvedValueOnce({ items: [], total: 0 });

		await listPicks({ offset: 0 });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("offset=0");
	});
});

// ---------------------------------------------------------------------------
// Latest pick
// ---------------------------------------------------------------------------

describe("getLatestPick", () => {
	it("calls GET /v1/picks/latest and returns camelCased data", async () => {
		const apiResponse = {
			public_id: "lo1",
			library_entry: null,
			mood: "chill",
			available_minutes: 60,
			mental_energy: "low",
			context: null,
			reasoning: "Relax time",
			action: null,
			created_at: "2024-01-01",
			updated_at: "2024-01-01",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await getLatestPick();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/picks/latest");
		expect(result).not.toBeNull();
		expect(result?.publicId).toBe("lo1");
	});

	it("returns null when API returns null", async () => {
		mockApiFetch.mockResolvedValueOnce(null);

		const result = await getLatestPick();

		expect(result).toBeNull();
	});
});
