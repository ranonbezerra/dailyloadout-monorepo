import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createWrapper } from "../test/wrapper";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@dl/shared/api", () => ({
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

const mockMission = {
	publicId: "mission-1",
	libraryEntry: mockLibraryEntry,
	missionType: "regular" as const,
	briefingText: "Continue from Stormveil Castle.",
	debriefText: null,
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

const mockMissionListResponse = {
	items: [
		{
			publicId: "mission-1",
			libraryEntry: mockLibraryEntry,
			missionType: "regular" as const,
			endedVia: null,
			startedAt: "2024-06-15T18:00:00Z",
			endedAt: null,
		},
	],
	total: 1,
};

const mockBriefingPreview = {
	libraryEntry: mockLibraryEntry,
	briefingText: "You are about to enter Stormveil Castle.",
	lastSessionContext: {
		location: "Limgrave",
		nextAction: "Head to Stormveil",
		level: "40",
		currentQuest: null,
	},
};

vi.mock("../lib/mission-api", () => ({
	listMissions: vi.fn(() => Promise.resolve(mockMissionListResponse)),
	getMission: vi.fn(() => Promise.resolve(mockMission)),
	getActiveMission: vi.fn(() => Promise.resolve(mockMission)),
	previewBriefing: vi.fn(() => Promise.resolve(mockBriefingPreview)),
	startMission: vi.fn(() => Promise.resolve(mockMission)),
	submitDebrief: vi.fn(() =>
		Promise.resolve({ ...mockMission, debriefText: "Defeated Godrick." }),
	),
	endMission: vi.fn(() =>
		Promise.resolve({
			...mockMission,
			endedVia: "paused_app",
			endedAt: "2024-06-15T20:00:00Z",
		}),
	),
	regenerateBriefing: vi.fn(() =>
		Promise.resolve({ ...mockMission, briefingText: "New briefing text." }),
	),
	submitRetroactiveDebrief: vi.fn(() => Promise.resolve(mockBriefingPreview)),
}));

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
} from "../lib/mission-api";
import {
	useActiveMission,
	useEndMission,
	useMission,
	useMissions,
	usePreviewBriefing,
	useRegenerateBriefing,
	useRetroactiveDebrief,
	useStartMission,
	useSubmitDebrief,
} from "./useMission";

beforeEach(() => {
	vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

describe("useMissions", () => {
	it("returns mission list without params", async () => {
		const { result } = renderHook(() => useMissions(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listMissions).toHaveBeenCalledWith(undefined);
		expect(result.current.data).toEqual(mockMissionListResponse);
	});

	it("passes pagination params to listMissions", async () => {
		const params = { limit: 10, offset: 5 };
		const { result } = renderHook(() => useMissions(params), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listMissions).toHaveBeenCalledWith(params);
	});
});

describe("useMission", () => {
	it("is disabled when publicId is empty", () => {
		const { result } = renderHook(() => useMission(""), {
			wrapper: createWrapper(),
		});

		expect(result.current.fetchStatus).toBe("idle");
		expect(getMission).not.toHaveBeenCalled();
	});

	it("fetches a single mission when publicId is truthy", async () => {
		const { result } = renderHook(() => useMission("mission-1"), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(getMission).toHaveBeenCalledWith("mission-1");
		expect(result.current.data).toEqual(mockMission);
	});
});

describe("useActiveMission", () => {
	it("returns the active mission", async () => {
		const { result } = renderHook(() => useActiveMission(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(getActiveMission).toHaveBeenCalledOnce();
		expect(result.current.data).toEqual(mockMission);
	});
});

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

describe("usePreviewBriefing", () => {
	it("calls previewBriefing with libraryEntryPublicId", async () => {
		const { result } = renderHook(() => usePreviewBriefing(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ libraryEntryPublicId: "entry-1" });

		expect(previewBriefing).toHaveBeenCalledWith("entry-1", undefined, undefined, undefined);
	});

	it("calls previewBriefing with optional positionOverride", async () => {
		const { result } = renderHook(() => usePreviewBriefing(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			libraryEntryPublicId: "entry-1",
			positionOverride: "Chapter 3",
		});

		expect(previewBriefing).toHaveBeenCalledWith("entry-1", "Chapter 3", undefined, undefined);
	});
});

describe("useStartMission", () => {
	it("calls startMission with libraryEntryPublicId", async () => {
		const { result } = renderHook(() => useStartMission(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ libraryEntryPublicId: "entry-1" });

		expect(startMission).toHaveBeenCalledWith("entry-1", undefined, undefined);
	});

	it("calls startMission with optional briefingText", async () => {
		const { result } = renderHook(() => useStartMission(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			libraryEntryPublicId: "entry-1",
			briefingText: "Custom briefing",
		});

		expect(startMission).toHaveBeenCalledWith("entry-1", "Custom briefing", undefined);
	});

	it("passes skipBriefing through to start with no briefing", async () => {
		const { result } = renderHook(() => useStartMission(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ libraryEntryPublicId: "entry-1", skipBriefing: true });

		expect(startMission).toHaveBeenCalledWith("entry-1", undefined, true);
	});
});

describe("useSubmitDebrief", () => {
	it("calls submitDebrief with publicId and debriefText", async () => {
		const { result } = renderHook(() => useSubmitDebrief(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			publicId: "mission-1",
			debriefText: "Defeated Godrick. Heading to Liurnia.",
		});

		expect(submitDebrief).toHaveBeenCalledWith(
			"mission-1",
			"Defeated Godrick. Heading to Liurnia.",
		);
	});
});

describe("useEndMission", () => {
	it("calls endMission with publicId and default endedVia", async () => {
		const { result } = renderHook(() => useEndMission(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ publicId: "mission-1" });

		expect(endMission).toHaveBeenCalledWith("mission-1", undefined);
	});

	it("calls endMission with explicit endedVia", async () => {
		const { result } = renderHook(() => useEndMission(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ publicId: "mission-1", endedVia: "paused_app" });

		expect(endMission).toHaveBeenCalledWith("mission-1", "paused_app");
	});
});

describe("useRegenerateBriefing", () => {
	it("calls regenerateBriefing with publicId", async () => {
		const { result } = renderHook(() => useRegenerateBriefing(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ publicId: "mission-1" });

		expect(regenerateBriefing).toHaveBeenCalledWith("mission-1", undefined);
	});

	it("calls regenerateBriefing with currentPosition", async () => {
		const { result } = renderHook(() => useRegenerateBriefing(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			publicId: "mission-1",
			currentPosition: "Liurnia of the Lakes",
		});

		expect(regenerateBriefing).toHaveBeenCalledWith("mission-1", "Liurnia of the Lakes");
	});
});

describe("useRetroactiveDebrief", () => {
	it("calls submitRetroactiveDebrief with libraryEntryPublicId and debriefText", async () => {
		const { result } = renderHook(() => useRetroactiveDebrief(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			libraryEntryPublicId: "entry-1",
			debriefText: "Played for two hours, cleared a dungeon.",
		});

		expect(submitRetroactiveDebrief).toHaveBeenCalledWith(
			"entry-1",
			"Played for two hours, cleared a dungeon.",
		);
	});
});
