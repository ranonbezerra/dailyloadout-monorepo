import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@dl/shared/api", () => ({
	apiFetch: vi.fn(),
	BASE_URL: "http://test",
	getAccessToken: vi.fn(() => "test-token"),
}));

import { apiFetch } from "@dl/shared/api";
import {
	endMission,
	getActiveMission,
	getMission,
	listMissions,
	previewBriefing,
	regenerateBriefing,
	startMission,
	submitDebrief,
	submitRetroactiveDebrief,
} from "./mission-api";

const mockApiFetch = apiFetch as Mock;

// Shared factory for a snake_case mission response
function makeMissionResponse(overrides: Record<string, unknown> = {}) {
	return {
		public_id: "m1",
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
			created_at: "2024-01-01",
			updated_at: "2024-01-01",
		},
		mission_type: "regular",
		briefing_text: "Continue from Asphodel",
		debrief_text: null,
		extracted_state: null,
		ended_via: null,
		started_at: "2024-06-01T10:00:00Z",
		ended_at: null,
		created_at: "2024-06-01T10:00:00Z",
		updated_at: "2024-06-01T10:00:00Z",
		last_session_context: null,
		...overrides,
	};
}

beforeEach(() => {
	mockApiFetch.mockReset();
});

// ---------------------------------------------------------------------------
// Preview briefing
// ---------------------------------------------------------------------------

describe("previewBriefing", () => {
	it("calls POST /v1/missions/preview-briefing with library_entry_public_id", async () => {
		const apiResponse = {
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
				created_at: "2024-01-01",
				updated_at: "2024-01-01",
			},
			briefing_text: "Start from the beginning",
			last_session_context: null,
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await previewBriefing("le1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions/preview-briefing", {
			method: "POST",
			body: JSON.stringify({ library_entry_public_id: "le1", mode: "quick" }),
			signal: undefined,
		});
		expect(result.briefingText).toBe("Start from the beginning");
		expect(result.libraryEntry.publicId).toBe("le1");
	});

	it("includes position_override when provided", async () => {
		const apiResponse = {
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
				created_at: "2024-01-01",
				updated_at: "2024-01-01",
			},
			briefing_text: "Continue from Elysium",
			last_session_context: { location: "Elysium" },
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await previewBriefing("le1", "Elysium");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions/preview-briefing", {
			method: "POST",
			body: JSON.stringify({
				library_entry_public_id: "le1",
				mode: "quick",
				position_override: "Elysium",
			}),
			signal: undefined,
		});
		expect(result.lastSessionContext).not.toBeNull();
	});

	it("sends mode=deep and forwards the abort signal", async () => {
		mockApiFetch.mockResolvedValueOnce({
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
				created_at: "2024-01-01",
				updated_at: "2024-01-01",
			},
			briefing_text: "Web-researched recap",
			last_session_context: null,
		});
		const controller = new AbortController();

		await previewBriefing("le1", undefined, "deep", controller.signal);

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions/preview-briefing", {
			method: "POST",
			body: JSON.stringify({ library_entry_public_id: "le1", mode: "deep" }),
			signal: controller.signal,
		});
	});
});

// ---------------------------------------------------------------------------
// Retroactive debrief
// ---------------------------------------------------------------------------

describe("submitRetroactiveDebrief", () => {
	it("calls POST /v1/missions/retroactive-debrief", async () => {
		const apiResponse = {
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
				created_at: "2024-01-01",
				updated_at: "2024-01-01",
			},
			briefing_text: null,
			last_session_context: { location: "Tartarus" },
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await submitRetroactiveDebrief("le1", "Defeated Megaera");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions/retroactive-debrief", {
			method: "POST",
			body: JSON.stringify({
				library_entry_public_id: "le1",
				debrief_text: "Defeated Megaera",
			}),
		});
		expect(result.lastSessionContext).toEqual({ location: "Tartarus" });
	});
});

// ---------------------------------------------------------------------------
// Start mission
// ---------------------------------------------------------------------------

describe("startMission", () => {
	it("calls POST /v1/missions with library_entry_public_id only", async () => {
		mockApiFetch.mockResolvedValueOnce(makeMissionResponse());

		const result = await startMission("le1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions", {
			method: "POST",
			body: JSON.stringify({ library_entry_public_id: "le1" }),
		});
		expect(result.publicId).toBe("m1");
		expect(result.missionType).toBe("regular");
		expect(result.libraryEntry.publicId).toBe("le1");
	});

	it("includes briefing_text when provided", async () => {
		mockApiFetch.mockResolvedValueOnce(makeMissionResponse({ briefing_text: "Custom briefing" }));

		await startMission("le1", "Custom briefing");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions", {
			method: "POST",
			body: JSON.stringify({
				library_entry_public_id: "le1",
				briefing_text: "Custom briefing",
			}),
		});
	});
});

// ---------------------------------------------------------------------------
// Active mission
// ---------------------------------------------------------------------------

describe("getActiveMission", () => {
	it("calls GET /v1/missions/active and returns camelCased mission", async () => {
		mockApiFetch.mockResolvedValueOnce(makeMissionResponse());

		const result = await getActiveMission();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions/active");
		expect(result).not.toBeNull();
		expect(result?.publicId).toBe("m1");
		expect(result?.briefingText).toBe("Continue from Asphodel");
	});

	it("returns null when API returns null", async () => {
		mockApiFetch.mockResolvedValueOnce(null);

		const result = await getActiveMission();

		expect(result).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Mission detail
// ---------------------------------------------------------------------------

describe("getMission", () => {
	it("calls GET /v1/missions/:publicId", async () => {
		mockApiFetch.mockResolvedValueOnce(makeMissionResponse());

		const result = await getMission("m1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions/m1");
		expect(result.publicId).toBe("m1");
		expect(result.startedAt).toBe("2024-06-01T10:00:00Z");
	});

	it("converts deeply nested snake_case keys", async () => {
		const response = makeMissionResponse({
			last_session_context: {
				next_action: "Defeat Theseus",
				current_quest: "Escape from Elysium",
			},
		});
		mockApiFetch.mockResolvedValueOnce(response);

		const result = await getMission("m1");

		expect(result.lastSessionContext).toEqual({
			nextAction: "Defeat Theseus",
			currentQuest: "Escape from Elysium",
		});
	});
});

// ---------------------------------------------------------------------------
// List missions
// ---------------------------------------------------------------------------

describe("listMissions", () => {
	it("calls GET /v1/missions with no params when none given", async () => {
		const apiResponse = { items: [], total: 0 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await listMissions();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions");
		expect(result).toEqual(apiResponse);
	});

	it("appends query params for limit and offset", async () => {
		const apiResponse = { items: [], total: 0 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		await listMissions({ limit: 5, offset: 10 });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("limit=5");
		expect(calledPath).toContain("offset=10");
	});

	it("converts snake_case response items to camelCase", async () => {
		const apiResponse = {
			items: [
				{
					public_id: "m1",
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
						created_at: "2024-01-01",
						updated_at: "2024-01-01",
					},
					mission_type: "regular",
					ended_via: "debrief_completed",
					started_at: "2024-06-01T10:00:00Z",
					ended_at: "2024-06-01T11:00:00Z",
				},
			],
			total: 1,
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await listMissions();

		expect(result.items[0].publicId).toBe("m1");
		expect(result.items[0].missionType).toBe("regular");
		expect(result.items[0].endedVia).toBe("debrief_completed");
		expect(result.items[0].startedAt).toBe("2024-06-01T10:00:00Z");
		expect(result.items[0].endedAt).toBe("2024-06-01T11:00:00Z");
	});

	it("handles offset=0 correctly (falsy but valid)", async () => {
		mockApiFetch.mockResolvedValueOnce({ items: [], total: 0 });

		await listMissions({ offset: 0 });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("offset=0");
	});
});

// ---------------------------------------------------------------------------
// Submit debrief
// ---------------------------------------------------------------------------

describe("submitDebrief", () => {
	it("calls PATCH /v1/missions/:publicId/debrief with debrief_text", async () => {
		const response = makeMissionResponse({
			debrief_text: "Beat the final boss",
			ended_via: "debrief_completed",
			ended_at: "2024-06-01T11:00:00Z",
		});
		mockApiFetch.mockResolvedValueOnce(response);

		const result = await submitDebrief("m1", "Beat the final boss");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions/m1/debrief", {
			method: "PATCH",
			body: JSON.stringify({ debrief_text: "Beat the final boss" }),
		});
		expect(result.debriefText).toBe("Beat the final boss");
		expect(result.endedVia).toBe("debrief_completed");
	});
});

// ---------------------------------------------------------------------------
// End mission
// ---------------------------------------------------------------------------

describe("endMission", () => {
	it("calls POST /v1/missions/:publicId/end with default ended_via", async () => {
		const response = makeMissionResponse({
			ended_via: "paused_app",
			ended_at: "2024-06-01T11:00:00Z",
		});
		mockApiFetch.mockResolvedValueOnce(response);

		const result = await endMission("m1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions/m1/end", {
			method: "POST",
			body: JSON.stringify({ ended_via: "paused_app" }),
		});
		expect(result.endedVia).toBe("paused_app");
		expect(result.endedAt).toBe("2024-06-01T11:00:00Z");
	});

	it("accepts a custom ended_via value", async () => {
		const response = makeMissionResponse({ ended_via: "auto_clamp" });
		mockApiFetch.mockResolvedValueOnce(response);

		await endMission("m1", "auto_clamp");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions/m1/end", {
			method: "POST",
			body: JSON.stringify({ ended_via: "auto_clamp" }),
		});
	});
});

// ---------------------------------------------------------------------------
// Regenerate briefing
// ---------------------------------------------------------------------------

describe("regenerateBriefing", () => {
	it("calls POST /v1/missions/:publicId/briefing/regenerate without body", async () => {
		const response = makeMissionResponse({ briefing_text: "New briefing generated" });
		mockApiFetch.mockResolvedValueOnce(response);

		const result = await regenerateBriefing("m1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions/m1/briefing/regenerate", {
			method: "POST",
			body: undefined,
		});
		expect(result.briefingText).toBe("New briefing generated");
	});

	it("includes current_position when provided", async () => {
		const response = makeMissionResponse({ briefing_text: "Updated briefing" });
		mockApiFetch.mockResolvedValueOnce(response);

		await regenerateBriefing("m1", "Elysium");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/missions/m1/briefing/regenerate", {
			method: "POST",
			body: JSON.stringify({ current_position: "Elysium" }),
		});
	});
});
