import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@slate/shared/api", () => ({
	apiFetch: vi.fn(),
	BASE_URL: "http://test",
	getAccessToken: vi.fn(() => "test-token"),
}));

import { apiFetch } from "@slate/shared/api";
import {
	endPlaySession,
	getActivePlaySession,
	getPlaySession,
	listPlaySessions,
	previewRecap,
	regenerateRecap,
	startPlaySession,
	submitRetroactiveWrapUp,
	submitWrapUp,
} from "./play-session-api";

const mockApiFetch = apiFetch as Mock;

// Shared factory for a snake_case playSession response
function makePlaySessionResponse(overrides: Record<string, unknown> = {}) {
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
		play_session_type: "regular",
		recap_text: "Continue from Asphodel",
		wrap_up_text: null,
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
// Preview recap
// ---------------------------------------------------------------------------

describe("previewRecap", () => {
	it("calls POST /v1/play-sessions/preview-recap with library_entry_public_id", async () => {
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
			recap_text: "Start from the beginning",
			last_session_context: null,
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await previewRecap("le1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions/preview-recap", {
			method: "POST",
			body: JSON.stringify({ library_entry_public_id: "le1", mode: "quick" }),
			signal: undefined,
		});
		expect(result.recapText).toBe("Start from the beginning");
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
			recap_text: "Continue from Elysium",
			last_session_context: { location: "Elysium" },
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await previewRecap("le1", "Elysium");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions/preview-recap", {
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
			recap_text: "Web-researched recap",
			last_session_context: null,
		});
		const controller = new AbortController();

		await previewRecap("le1", undefined, "deep", controller.signal);

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions/preview-recap", {
			method: "POST",
			body: JSON.stringify({ library_entry_public_id: "le1", mode: "deep" }),
			signal: controller.signal,
		});
	});
});

// ---------------------------------------------------------------------------
// Retroactive wrapUp
// ---------------------------------------------------------------------------

describe("submitRetroactiveWrapUp", () => {
	it("calls POST /v1/play-sessions/retroactive-wrap-up", async () => {
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
			recap_text: null,
			last_session_context: { location: "Tartarus" },
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await submitRetroactiveWrapUp("le1", "Defeated Megaera");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions/retroactive-wrap-up", {
			method: "POST",
			body: JSON.stringify({
				library_entry_public_id: "le1",
				wrap_up_text: "Defeated Megaera",
			}),
		});
		expect(result.lastSessionContext).toEqual({ location: "Tartarus" });
	});
});

// ---------------------------------------------------------------------------
// Start playSession
// ---------------------------------------------------------------------------

describe("startPlaySession", () => {
	it("calls POST /v1/play-sessions with library_entry_public_id only", async () => {
		mockApiFetch.mockResolvedValueOnce(makePlaySessionResponse());

		const result = await startPlaySession("le1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions", {
			method: "POST",
			body: JSON.stringify({ library_entry_public_id: "le1" }),
		});
		expect(result.publicId).toBe("m1");
		expect(result.playSessionType).toBe("regular");
		expect(result.libraryEntry.publicId).toBe("le1");
	});

	it("includes recap_text when provided", async () => {
		mockApiFetch.mockResolvedValueOnce(makePlaySessionResponse({ recap_text: "Custom recap" }));

		await startPlaySession("le1", "Custom recap");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions", {
			method: "POST",
			body: JSON.stringify({
				library_entry_public_id: "le1",
				recap_text: "Custom recap",
			}),
		});
	});
});

// ---------------------------------------------------------------------------
// Active playSession
// ---------------------------------------------------------------------------

describe("getActivePlaySession", () => {
	it("calls GET /v1/play-sessions/active and returns camelCased playSession", async () => {
		mockApiFetch.mockResolvedValueOnce(makePlaySessionResponse());

		const result = await getActivePlaySession();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions/active");
		expect(result).not.toBeNull();
		expect(result?.publicId).toBe("m1");
		expect(result?.recapText).toBe("Continue from Asphodel");
	});

	it("returns null when API returns null", async () => {
		mockApiFetch.mockResolvedValueOnce(null);

		const result = await getActivePlaySession();

		expect(result).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// PlaySession detail
// ---------------------------------------------------------------------------

describe("getPlaySession", () => {
	it("calls GET /v1/play-sessions/:publicId", async () => {
		mockApiFetch.mockResolvedValueOnce(makePlaySessionResponse());

		const result = await getPlaySession("m1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions/m1");
		expect(result.publicId).toBe("m1");
		expect(result.startedAt).toBe("2024-06-01T10:00:00Z");
	});

	it("converts deeply nested snake_case keys", async () => {
		const response = makePlaySessionResponse({
			last_session_context: {
				next_action: "Defeat Theseus",
				current_quest: "Escape from Elysium",
			},
		});
		mockApiFetch.mockResolvedValueOnce(response);

		const result = await getPlaySession("m1");

		expect(result.lastSessionContext).toEqual({
			nextAction: "Defeat Theseus",
			currentQuest: "Escape from Elysium",
		});
	});
});

// ---------------------------------------------------------------------------
// List playSessions
// ---------------------------------------------------------------------------

describe("listPlaySessions", () => {
	it("calls GET /v1/play-sessions with no params when none given", async () => {
		const apiResponse = { items: [], total: 0 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await listPlaySessions();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions");
		expect(result).toEqual(apiResponse);
	});

	it("appends query params for limit and offset", async () => {
		const apiResponse = { items: [], total: 0 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		await listPlaySessions({ limit: 5, offset: 10 });

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
					play_session_type: "regular",
					ended_via: "wrap_up_completed",
					started_at: "2024-06-01T10:00:00Z",
					ended_at: "2024-06-01T11:00:00Z",
				},
			],
			total: 1,
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await listPlaySessions();

		expect(result.items[0].publicId).toBe("m1");
		expect(result.items[0].playSessionType).toBe("regular");
		expect(result.items[0].endedVia).toBe("wrap_up_completed");
		expect(result.items[0].startedAt).toBe("2024-06-01T10:00:00Z");
		expect(result.items[0].endedAt).toBe("2024-06-01T11:00:00Z");
	});

	it("handles offset=0 correctly (falsy but valid)", async () => {
		mockApiFetch.mockResolvedValueOnce({ items: [], total: 0 });

		await listPlaySessions({ offset: 0 });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("offset=0");
	});
});

// ---------------------------------------------------------------------------
// Submit wrapUp
// ---------------------------------------------------------------------------

describe("submitWrapUp", () => {
	it("calls PATCH /v1/play-sessions/:publicId/wrapUp with wrap_up_text", async () => {
		const response = makePlaySessionResponse({
			wrap_up_text: "Beat the final boss",
			ended_via: "wrap_up_completed",
			ended_at: "2024-06-01T11:00:00Z",
		});
		mockApiFetch.mockResolvedValueOnce(response);

		const result = await submitWrapUp("m1", "Beat the final boss");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions/m1/wrap-up", {
			method: "PATCH",
			body: JSON.stringify({ wrap_up_text: "Beat the final boss" }),
		});
		expect(result.wrapUpText).toBe("Beat the final boss");
		expect(result.endedVia).toBe("wrap_up_completed");
	});
});

// ---------------------------------------------------------------------------
// End session
// ---------------------------------------------------------------------------

describe("endPlaySession", () => {
	it("calls POST /v1/play-sessions/:publicId/end with default ended_via", async () => {
		const response = makePlaySessionResponse({
			ended_via: "paused_app",
			ended_at: "2024-06-01T11:00:00Z",
		});
		mockApiFetch.mockResolvedValueOnce(response);

		const result = await endPlaySession("m1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions/m1/end", {
			method: "POST",
			body: JSON.stringify({ ended_via: "paused_app" }),
		});
		expect(result.endedVia).toBe("paused_app");
		expect(result.endedAt).toBe("2024-06-01T11:00:00Z");
	});

	it("accepts a custom ended_via value", async () => {
		const response = makePlaySessionResponse({ ended_via: "auto_clamp" });
		mockApiFetch.mockResolvedValueOnce(response);

		await endPlaySession("m1", "auto_clamp");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions/m1/end", {
			method: "POST",
			body: JSON.stringify({ ended_via: "auto_clamp" }),
		});
	});
});

// ---------------------------------------------------------------------------
// Regenerate recap
// ---------------------------------------------------------------------------

describe("regenerateRecap", () => {
	it("calls POST /v1/play-sessions/:publicId/recap/regenerate without body", async () => {
		const response = makePlaySessionResponse({ recap_text: "New recap generated" });
		mockApiFetch.mockResolvedValueOnce(response);

		const result = await regenerateRecap("m1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions/m1/recap/regenerate", {
			method: "POST",
			body: undefined,
		});
		expect(result.recapText).toBe("New recap generated");
	});

	it("includes current_position when provided", async () => {
		const response = makePlaySessionResponse({ recap_text: "Updated recap" });
		mockApiFetch.mockResolvedValueOnce(response);

		await regenerateRecap("m1", "Elysium");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/play-sessions/m1/recap/regenerate", {
			method: "POST",
			body: JSON.stringify({ current_position: "Elysium" }),
		});
	});
});
