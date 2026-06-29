import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createWrapper } from "../test/wrapper";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@slate/shared/api", () => ({
	BASE_URL: "http://localhost:8100",
	apiFetch: vi.fn(() => Promise.resolve(null)),
	getAccessToken: vi.fn(() => null),
	getRefreshToken: vi.fn(() => null),
	saveTokens: vi.fn(),
	clearTokens: vi.fn(),
}));

const mockLibraryEntry = {
	publicId: "entry-1",
	game: {
		publicId: "game-1",
		slug: "elden-ring",
		title: "Elden Ring",
		metadataSource: "igdb",
		createdAt: "2024-01-01T00:00:00Z",
	},
	platform: { id: 1, slug: "pc", label: "PC", family: "computer" },
	status: "playing" as const,
	createdAt: "2024-01-01T00:00:00Z",
	updatedAt: "2024-06-01T00:00:00Z",
};

const mockPlaySession = {
	publicId: "playSession-1",
	libraryEntry: mockLibraryEntry,
	playSessionType: "regular" as const,
	recapText: "Continue from Stormveil Castle.",
	wrapUpText: null,
	extractedState: null,
	endedVia: null,
	startedAt: "2024-06-15T18:00:00Z",
	endedAt: null,
	createdAt: "2024-06-15T18:00:00Z",
	updatedAt: "2024-06-15T18:00:00Z",
	lastSessionContext: {
		location: "Stormveil Castle",
		nextAction: "Defeat Godrick",
		level: "45",
		currentQuest: "Main story",
	},
};

const mockPlaySessionListResponse = {
	items: [
		{
			publicId: "playSession-1",
			libraryEntry: mockLibraryEntry,
			playSessionType: "regular" as const,
			endedVia: null,
			startedAt: "2024-06-15T18:00:00Z",
			endedAt: null,
		},
	],
	total: 1,
};

const mockRecapPreview = {
	libraryEntry: mockLibraryEntry,
	recapText: "You are about to enter Stormveil Castle.",
	lastSessionContext: {
		location: "Limgrave",
		nextAction: "Head to Stormveil",
		level: "40",
		currentQuest: null,
	},
};

vi.mock("../lib/play-session-api", () => ({
	listPlaySessions: vi.fn(() => Promise.resolve(mockPlaySessionListResponse)),
	getPlaySession: vi.fn(() => Promise.resolve(mockPlaySession)),
	getActivePlaySession: vi.fn(() => Promise.resolve(mockPlaySession)),
	previewRecap: vi.fn(() => Promise.resolve(mockRecapPreview)),
	startPlaySession: vi.fn(() => Promise.resolve(mockPlaySession)),
	submitWrapUp: vi.fn(() =>
		Promise.resolve({ ...mockPlaySession, wrapUpText: "Defeated Godrick." }),
	),
	endPlaySession: vi.fn(() =>
		Promise.resolve({
			...mockPlaySession,
			endedVia: "paused_app",
			endedAt: "2024-06-15T20:00:00Z",
		}),
	),
	regenerateRecap: vi.fn(() =>
		Promise.resolve({ ...mockPlaySession, recapText: "New recap text." }),
	),
	submitRetroactiveWrapUp: vi.fn(() => Promise.resolve(mockRecapPreview)),
}));

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
} from "../lib/play-session-api";
import {
	useActivePlaySession,
	useEndPlaySession,
	usePlaySession,
	usePlaySessions,
	usePreviewRecap,
	useRegenerateRecap,
	useRetroactiveWrapUp,
	useStartPlaySession,
	useSubmitWrapUp,
} from "./usePlaySession";

beforeEach(() => {
	vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

describe("usePlaySessions", () => {
	it("returns playSession list without params", async () => {
		const { result } = renderHook(() => usePlaySessions(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listPlaySessions).toHaveBeenCalledWith(undefined);
		expect(result.current.data).toEqual(mockPlaySessionListResponse);
	});

	it("passes pagination params to listPlaySessions", async () => {
		const params = { limit: 10, offset: 5 };
		const { result } = renderHook(() => usePlaySessions(params), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listPlaySessions).toHaveBeenCalledWith(params);
	});
});

describe("usePlaySession", () => {
	it("is disabled when publicId is empty", () => {
		const { result } = renderHook(() => usePlaySession(""), {
			wrapper: createWrapper(),
		});

		expect(result.current.fetchStatus).toBe("idle");
		expect(getPlaySession).not.toHaveBeenCalled();
	});

	it("fetches a single playSession when publicId is truthy", async () => {
		const { result } = renderHook(() => usePlaySession("playSession-1"), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(getPlaySession).toHaveBeenCalledWith("playSession-1");
		expect(result.current.data).toEqual(mockPlaySession);
	});
});

describe("useActivePlaySession", () => {
	it("returns the active playSession", async () => {
		const { result } = renderHook(() => useActivePlaySession(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(getActivePlaySession).toHaveBeenCalledOnce();
		expect(result.current.data).toEqual(mockPlaySession);
	});
});

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

describe("usePreviewRecap", () => {
	it("calls previewRecap with libraryEntryPublicId", async () => {
		const { result } = renderHook(() => usePreviewRecap(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ libraryEntryPublicId: "entry-1" });

		expect(previewRecap).toHaveBeenCalledWith("entry-1", undefined, undefined, undefined);
	});

	it("calls previewRecap with optional positionOverride", async () => {
		const { result } = renderHook(() => usePreviewRecap(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			libraryEntryPublicId: "entry-1",
			positionOverride: "Chapter 3",
		});

		expect(previewRecap).toHaveBeenCalledWith("entry-1", "Chapter 3", undefined, undefined);
	});
});

describe("useStartPlaySession", () => {
	it("calls startPlaySession with libraryEntryPublicId", async () => {
		const { result } = renderHook(() => useStartPlaySession(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ libraryEntryPublicId: "entry-1" });

		expect(startPlaySession).toHaveBeenCalledWith("entry-1", undefined, undefined);
	});

	it("calls startPlaySession with optional recapText", async () => {
		const { result } = renderHook(() => useStartPlaySession(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			libraryEntryPublicId: "entry-1",
			recapText: "Custom recap",
		});

		expect(startPlaySession).toHaveBeenCalledWith("entry-1", "Custom recap", undefined);
	});

	it("passes skipRecap through to start with no recap", async () => {
		const { result } = renderHook(() => useStartPlaySession(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ libraryEntryPublicId: "entry-1", skipRecap: true });

		expect(startPlaySession).toHaveBeenCalledWith("entry-1", undefined, true);
	});
});

describe("useSubmitWrapUp", () => {
	it("calls submitWrapUp with publicId and wrapUpText", async () => {
		const { result } = renderHook(() => useSubmitWrapUp(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			publicId: "playSession-1",
			wrapUpText: "Defeated Godrick. Heading to Liurnia.",
		});

		expect(submitWrapUp).toHaveBeenCalledWith(
			"playSession-1",
			"Defeated Godrick. Heading to Liurnia.",
		);
	});
});

describe("useEndPlaySession", () => {
	it("calls endPlaySession with publicId and default endedVia", async () => {
		const { result } = renderHook(() => useEndPlaySession(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ publicId: "playSession-1" });

		expect(endPlaySession).toHaveBeenCalledWith("playSession-1", undefined);
	});

	it("calls endPlaySession with explicit endedVia", async () => {
		const { result } = renderHook(() => useEndPlaySession(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ publicId: "playSession-1", endedVia: "paused_app" });

		expect(endPlaySession).toHaveBeenCalledWith("playSession-1", "paused_app");
	});
});

describe("useRegenerateRecap", () => {
	it("calls regenerateRecap with publicId", async () => {
		const { result } = renderHook(() => useRegenerateRecap(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ publicId: "playSession-1" });

		expect(regenerateRecap).toHaveBeenCalledWith("playSession-1", undefined);
	});

	it("calls regenerateRecap with currentPosition", async () => {
		const { result } = renderHook(() => useRegenerateRecap(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			publicId: "playSession-1",
			currentPosition: "Liurnia of the Lakes",
		});

		expect(regenerateRecap).toHaveBeenCalledWith("playSession-1", "Liurnia of the Lakes");
	});
});

describe("useRetroactiveWrapUp", () => {
	it("calls submitRetroactiveWrapUp with libraryEntryPublicId and wrapUpText", async () => {
		const { result } = renderHook(() => useRetroactiveWrapUp(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			libraryEntryPublicId: "entry-1",
			wrapUpText: "Played for two hours, cleared a dungeon.",
		});

		expect(submitRetroactiveWrapUp).toHaveBeenCalledWith(
			"entry-1",
			"Played for two hours, cleared a dungeon.",
		);
	});
});
