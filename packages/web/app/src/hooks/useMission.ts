import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	type BriefingMode,
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

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

const MISSIONS_KEY = ["missions"] as const;
const LIBRARY_KEY = ["library"] as const;
const STATS_KEY = ["stats"] as const;

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function useMissions(params?: { limit?: number; offset?: number }) {
	return useQuery({
		queryKey: [...MISSIONS_KEY, params],
		queryFn: () => listMissions(params),
	});
}

export function useMission(publicId: string) {
	return useQuery({
		queryKey: [...MISSIONS_KEY, publicId],
		queryFn: () => getMission(publicId),
		enabled: !!publicId,
	});
}

export function useActiveMission() {
	return useQuery({
		queryKey: [...MISSIONS_KEY, "active"],
		queryFn: () => getActiveMission(),
	});
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function usePreviewBriefing() {
	return useMutation({
		mutationFn: (vars: {
			libraryEntryPublicId: string;
			positionOverride?: string;
			mode?: BriefingMode;
			signal?: AbortSignal;
		}) =>
			previewBriefing(vars.libraryEntryPublicId, vars.positionOverride, vars.mode, vars.signal),
	});
}

export function useRetroactiveDebrief() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { libraryEntryPublicId: string; debriefText: string }) =>
			submitRetroactiveDebrief(vars.libraryEntryPublicId, vars.debriefText),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: MISSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useStartMission() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: {
			libraryEntryPublicId: string;
			briefingText?: string;
			skipBriefing?: boolean;
		}) => startMission(vars.libraryEntryPublicId, vars.briefingText, vars.skipBriefing),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: MISSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useSubmitDebrief() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { publicId: string; debriefText: string }) =>
			submitDebrief(vars.publicId, vars.debriefText),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: MISSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useEndMission() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { publicId: string; endedVia?: string }) =>
			endMission(vars.publicId, vars.endedVia),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: MISSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useRegenerateBriefing() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { publicId: string; currentPosition?: string }) =>
			regenerateBriefing(vars.publicId, vars.currentPosition),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: MISSIONS_KEY });
		},
	});
}
