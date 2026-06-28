import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@dl/shared/api", () => {
	const getAccessToken = vi.fn(() => "test-token" as string | null);
	// Mirror the real fetchWithAuthRetry: attach the bearer token as a Headers
	// instance (never forcing Content-Type) and delegate to globalThis.fetch so
	// per-test fetch mocks still drive responses.
	const fetchWithAuthRetry = vi.fn((path: string, init: RequestInit = {}) => {
		const headers = new Headers(init.headers);
		const token = getAccessToken();
		if (token) headers.set("Authorization", `Bearer ${token}`);
		return fetch(`http://test${path}`, { ...init, headers });
	});
	return {
		apiFetch: vi.fn(),
		BASE_URL: "http://test",
		getAccessToken,
		fetchWithAuthRetry,
	};
});

import { apiFetch, getAccessToken } from "@dl/shared/api";
import {
	bulkConfirmCandidates,
	confirmCandidate,
	getCapture,
	listCaptures,
	rejectCandidate,
	submitLibraryImport,
	submitPhotoCapture,
	submitTextCapture,
	transcribeAudio,
} from "./capture-api";

const mockApiFetch = apiFetch as Mock;
const mockGetAccessToken = getAccessToken as Mock;

beforeEach(() => {
	mockApiFetch.mockReset();
	mockGetAccessToken.mockReturnValue("test-token");
});

// ---------------------------------------------------------------------------
// Text capture
// ---------------------------------------------------------------------------

describe("submitTextCapture", () => {
	it("calls POST /v1/captures/text with raw_text and default input_type", async () => {
		const apiResponse = {
			public_id: "cap1",
			input_type: "text",
			raw_text: "Just finished Hades",
			status: "queued",
			error_message: null,
			candidates: [],
			created_at: "2024-01-01",
			updated_at: "2024-01-01",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await submitTextCapture("Just finished Hades");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/captures/text", {
			method: "POST",
			body: JSON.stringify({ raw_text: "Just finished Hades", input_type: "text" }),
		});
		expect(result.publicId).toBe("cap1");
		expect(result.inputType).toBe("text");
		expect(result.rawText).toBe("Just finished Hades");
	});

	it("passes a custom input_type", async () => {
		const apiResponse = {
			public_id: "cap2",
			input_type: "voice",
			raw_text: "some voice text",
			status: "queued",
			error_message: null,
			candidates: [],
			created_at: "2024-01-01",
			updated_at: "2024-01-01",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		await submitTextCapture("some voice text", "voice");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/captures/text", {
			method: "POST",
			body: JSON.stringify({ raw_text: "some voice text", input_type: "voice" }),
		});
	});

	it("converts nested snake_case candidates to camelCase", async () => {
		const apiResponse = {
			public_id: "cap3",
			input_type: "text",
			raw_text: "Hades",
			status: "review",
			error_message: null,
			candidates: [
				{
					public_id: "cand1",
					title: "Hades",
					platform_hint: "PC",
					igdb_title: "Hades",
					igdb_cover_url: "https://img.example.com/hades.jpg",
					igdb_summary: "A roguelike",
					igdb_genres: ["Roguelike"],
					confidence: 0.95,
					status: "pending",
					matched_game: null,
				},
			],
			created_at: "2024-01-01",
			updated_at: "2024-01-01",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await submitTextCapture("Hades");

		expect(result.candidates[0].publicId).toBe("cand1");
		expect(result.candidates[0].platformHint).toBe("PC");
		expect(result.candidates[0].igdbTitle).toBe("Hades");
		expect(result.candidates[0].igdbCoverUrl).toBe("https://img.example.com/hades.jpg");
		expect(result.candidates[0].igdbSummary).toBe("A roguelike");
		expect(result.candidates[0].igdbGenres).toEqual(["Roguelike"]);
	});
});

// ---------------------------------------------------------------------------
// Voice transcription
// ---------------------------------------------------------------------------

describe("transcribeAudio", () => {
	it("sends FormData with audio blob to /v1/captures/transcribe", async () => {
		const mockFetch = vi.fn().mockResolvedValueOnce({
			ok: true,
			json: () =>
				Promise.resolve({
					text: "hello",
					language: "en",
					duration_seconds: 2.5,
				}),
		});
		globalThis.fetch = mockFetch;

		const blob = new Blob(["audio"], { type: "audio/webm" });
		const result = await transcribeAudio(blob);

		expect(mockFetch).toHaveBeenCalledWith(
			expect.stringContaining("/v1/captures/transcribe"),
			expect.objectContaining({ method: "POST" }),
		);

		// Verify FormData was sent
		const callArgs = mockFetch.mock.calls[0];
		expect(callArgs[1].body).toBeInstanceOf(FormData);

		// Verify Authorization header
		expect((callArgs[1].headers as Headers).get("Authorization")).toBe("Bearer test-token");

		expect(result.text).toBe("hello");
		expect(result.language).toBe("en");
		expect(result.durationSeconds).toBe(2.5);
	});

	it("throws on non-ok response with error body", async () => {
		globalThis.fetch = vi.fn().mockResolvedValueOnce({
			ok: false,
			status: 500,
			text: () => Promise.resolve("Server error"),
		});

		await expect(transcribeAudio(new Blob())).rejects.toThrow("Server error");
	});

	it("throws with status code when error body is empty", async () => {
		globalThis.fetch = vi.fn().mockResolvedValueOnce({
			ok: false,
			status: 413,
			text: () => Promise.resolve(""),
		});

		await expect(transcribeAudio(new Blob())).rejects.toThrow("Transcription failed: 413");
	});

	it("omits Authorization header when no access token", async () => {
		mockGetAccessToken.mockReturnValueOnce(null);

		const mockFetch = vi.fn().mockResolvedValueOnce({
			ok: true,
			json: () =>
				Promise.resolve({
					text: "test",
					language: null,
					duration_seconds: null,
				}),
		});
		globalThis.fetch = mockFetch;

		await transcribeAudio(new Blob());

		const callArgs = mockFetch.mock.calls[0];
		expect((callArgs[1].headers as Headers).get("Authorization")).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Photo capture
// ---------------------------------------------------------------------------

describe("submitPhotoCapture", () => {
	it("sends FormData with image file to /v1/captures/photo", async () => {
		const mockFetch = vi.fn().mockResolvedValueOnce({
			ok: true,
			json: () =>
				Promise.resolve({
					public_id: "cap-photo-1",
					input_type: "photo",
					raw_text: null,
					status: "review",
					error_message: null,
					candidates: [
						{
							public_id: "cand1",
							title: "Hollow Knight",
							platform_hint: "PC",
							igdb_title: "Hollow Knight",
							igdb_cover_url: null,
							igdb_summary: null,
							igdb_genres: [],
							confidence: 0.85,
							status: "pending",
							matched_game: null,
						},
					],
					created_at: "2024-01-01",
					updated_at: "2024-01-01",
				}),
		});
		globalThis.fetch = mockFetch;

		const file = new File(["pixels"], "test.png", { type: "image/png" });
		const result = await submitPhotoCapture(file);

		expect(mockFetch).toHaveBeenCalledWith(
			expect.stringContaining("/v1/captures/photo"),
			expect.objectContaining({ method: "POST" }),
		);

		// Verify FormData was sent
		const callArgs = mockFetch.mock.calls[0];
		expect(callArgs[1].body).toBeInstanceOf(FormData);

		// Verify Authorization header
		expect((callArgs[1].headers as Headers).get("Authorization")).toBe("Bearer test-token");

		expect(result.publicId).toBe("cap-photo-1");
		expect(result.inputType).toBe("photo");
		expect(result.candidates[0].publicId).toBe("cand1");
		expect(result.candidates[0].title).toBe("Hollow Knight");
	});

	it("throws on non-ok response with error body", async () => {
		globalThis.fetch = vi.fn().mockResolvedValueOnce({
			ok: false,
			status: 500,
			text: () => Promise.resolve("Upload failed"),
		});

		const file = new File(["pixels"], "test.png", { type: "image/png" });
		await expect(submitPhotoCapture(file)).rejects.toThrow("Upload failed");
	});

	it("throws with status code when error body is empty", async () => {
		globalThis.fetch = vi.fn().mockResolvedValueOnce({
			ok: false,
			status: 413,
			text: () => Promise.resolve(""),
		});

		const file = new File(["big-image"], "big.png", { type: "image/png" });
		await expect(submitPhotoCapture(file)).rejects.toThrow("Photo capture failed: 413");
	});

	it("omits Authorization header when no access token", async () => {
		mockGetAccessToken.mockReturnValueOnce(null);

		const mockFetch = vi.fn().mockResolvedValueOnce({
			ok: true,
			json: () =>
				Promise.resolve({
					public_id: "cap-photo-2",
					input_type: "photo",
					raw_text: null,
					status: "queued",
					error_message: null,
					candidates: [],
					created_at: "2024-01-01",
					updated_at: "2024-01-01",
				}),
		});
		globalThis.fetch = mockFetch;

		const file = new File(["pixels"], "test.png", { type: "image/png" });
		await submitPhotoCapture(file);

		const callArgs = mockFetch.mock.calls[0];
		expect((callArgs[1].headers as Headers).get("Authorization")).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Bulk library import (multipart)
// ---------------------------------------------------------------------------

describe("submitLibraryImport", () => {
	it("appends each file under the 'files' field and POSTs to library-import", async () => {
		const mockFetch = vi.fn().mockResolvedValueOnce({
			ok: true,
			json: () =>
				Promise.resolve({
					public_id: "cap-import-1",
					input_type: "library_import",
					raw_text: null,
					status: "review",
					error_message: null,
					candidates: [
						{
							public_id: "cand1",
							title: "Hades",
							platform_hint: null,
							igdb_title: "Hades",
							igdb_cover_url: null,
							igdb_summary: null,
							igdb_genres: [],
							confidence: 0.9,
							status: "pending",
							matched_game: null,
						},
					],
					created_at: "2024-01-01",
					updated_at: "2024-01-01",
				}),
		});
		globalThis.fetch = mockFetch;

		const files = [
			new File(["a"], "shot1.png", { type: "image/png" }),
			new File(["b"], "shot2.png", { type: "image/png" }),
		];
		const result = await submitLibraryImport(files);

		expect(mockFetch).toHaveBeenCalledWith(
			expect.stringContaining("/v1/captures/library-import"),
			expect.objectContaining({ method: "POST" }),
		);

		const callArgs = mockFetch.mock.calls[0];
		const body = callArgs[1].body as FormData;
		expect(body).toBeInstanceOf(FormData);
		expect(body.getAll("files")).toHaveLength(2);
		expect((callArgs[1].headers as Headers).get("Authorization")).toBe("Bearer test-token");

		expect(result.publicId).toBe("cap-import-1");
		expect(result.candidates[0].igdbTitle).toBe("Hades");
	});

	it("throws on non-ok response with error body", async () => {
		globalThis.fetch = vi.fn().mockResolvedValueOnce({
			ok: false,
			status: 429,
			text: () => Promise.resolve("Daily cap reached"),
		});

		await expect(
			submitLibraryImport([new File(["x"], "a.png", { type: "image/png" })]),
		).rejects.toThrow("Daily cap reached");
	});

	it("throws with status code when error body is empty", async () => {
		globalThis.fetch = vi.fn().mockResolvedValueOnce({
			ok: false,
			status: 400,
			text: () => Promise.resolve(""),
		});

		await expect(
			submitLibraryImport([new File(["x"], "a.png", { type: "image/png" })]),
		).rejects.toThrow("Library import failed: 400");
	});

	it("omits Authorization header when no access token", async () => {
		mockGetAccessToken.mockReturnValueOnce(null);

		const mockFetch = vi.fn().mockResolvedValueOnce({
			ok: true,
			json: () =>
				Promise.resolve({
					public_id: "cap-import-2",
					input_type: "library_import",
					raw_text: null,
					status: "queued",
					error_message: null,
					candidates: [],
					created_at: "2024-01-01",
					updated_at: "2024-01-01",
				}),
		});
		globalThis.fetch = mockFetch;

		await submitLibraryImport([new File(["x"], "a.png", { type: "image/png" })]);

		const callArgs = mockFetch.mock.calls[0];
		expect((callArgs[1].headers as Headers).get("Authorization")).toBeNull();
	});
});

describe("bulkConfirmCandidates", () => {
	it("POSTs confirm ids, platform, and default status", async () => {
		mockApiFetch.mockResolvedValueOnce({ confirmed: 2, rejected: 1 });

		const result = await bulkConfirmCandidates("cap1", ["c1", "c2"], 3);

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/captures/cap1/candidates/bulk-confirm", {
			method: "POST",
			body: JSON.stringify({
				confirm_public_ids: ["c1", "c2"],
				platform_id: 3,
				status: "backlog",
				title_overrides: {},
			}),
		});
		expect(result).toEqual({ confirmed: 2, rejected: 1 });
	});

	it("uses a custom status when provided", async () => {
		mockApiFetch.mockResolvedValueOnce({ confirmed: 1, rejected: 0 });

		await bulkConfirmCandidates("cap1", ["c1"], 5, "playing");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/captures/cap1/candidates/bulk-confirm", {
			method: "POST",
			body: JSON.stringify({
				confirm_public_ids: ["c1"],
				platform_id: 5,
				status: "playing",
				title_overrides: {},
			}),
		});
	});
});

// ---------------------------------------------------------------------------
// Capture listing
// ---------------------------------------------------------------------------

describe("listCaptures", () => {
	it("calls GET /v1/captures with no params when none given", async () => {
		const apiResponse = { items: [], total: 0 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await listCaptures();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/captures");
		expect(result).toEqual(apiResponse);
	});

	it("appends query params for status, limit, offset", async () => {
		const apiResponse = { items: [], total: 0 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		await listCaptures({ status: "review", limit: 10, offset: 5 });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("status=review");
		expect(calledPath).toContain("limit=10");
		expect(calledPath).toContain("offset=5");
	});

	it("converts snake_case response items to camelCase", async () => {
		const apiResponse = {
			items: [
				{
					public_id: "cap1",
					input_type: "text",
					raw_text: "Hades",
					status: "review",
					error_message: null,
					candidate_titles: ["Hades"],
					created_at: "2024-01-01",
					updated_at: "2024-01-01",
				},
			],
			total: 1,
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await listCaptures();

		expect(result.items[0].publicId).toBe("cap1");
		expect(result.items[0].inputType).toBe("text");
		expect(result.items[0].candidateTitles).toEqual(["Hades"]);
	});

	it("handles offset=0 correctly (falsy but valid)", async () => {
		mockApiFetch.mockResolvedValueOnce({ items: [], total: 0 });

		await listCaptures({ offset: 0 });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("offset=0");
	});
});

// ---------------------------------------------------------------------------
// Capture detail
// ---------------------------------------------------------------------------

describe("getCapture", () => {
	it("calls GET /v1/captures/:publicId and returns camelCased data", async () => {
		const apiResponse = {
			public_id: "cap1",
			input_type: "text",
			raw_text: "Hades",
			status: "review",
			error_message: null,
			candidates: [],
			created_at: "2024-01-01",
			updated_at: "2024-01-01",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await getCapture("cap1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/captures/cap1");
		expect(result.publicId).toBe("cap1");
		expect(result.errorMessage).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Candidate actions
// ---------------------------------------------------------------------------

describe("confirmCandidate", () => {
	it("calls POST /v1/captures/:captureId/candidates/:candidateId/confirm", async () => {
		const apiResponse = {
			public_id: "le1",
			game: {
				public_id: "g1",
				title: "Hades",
				slug: "hades",
				metadata_source: "igdb",
				created_at: "2024-01-01",
			},
			platform: { id: 1, slug: "pc", label: "PC", family: "computer" },
			status: "backlog",
			created_at: "2024-01-01",
			updated_at: "2024-01-01",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await confirmCandidate("cap1", "cand1", 1);

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/captures/cap1/candidates/cand1/confirm", {
			method: "POST",
			body: JSON.stringify({ platform_id: 1, status: "backlog" }),
		});
		expect(result.publicId).toBe("le1");
		expect(result.game.publicId).toBe("g1");
	});

	it("uses custom status when provided", async () => {
		const apiResponse = {
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
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		await confirmCandidate("cap1", "cand1", 1, "playing");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/captures/cap1/candidates/cand1/confirm", {
			method: "POST",
			body: JSON.stringify({ platform_id: 1, status: "playing" }),
		});
	});
});

describe("rejectCandidate", () => {
	it("calls POST /v1/captures/:captureId/candidates/:candidateId/reject", async () => {
		mockApiFetch.mockResolvedValueOnce(undefined);

		await rejectCandidate("cap1", "cand1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/captures/cap1/candidates/cand1/reject", {
			method: "POST",
		});
	});
});
