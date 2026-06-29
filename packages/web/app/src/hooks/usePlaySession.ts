import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	endPlaySession,
	getActivePlaySession,
	getPlaySession,
	listPlaySessions,
	previewRecap,
	type RecapMode,
	regenerateRecap,
	startPlaySession,
	submitRetroactiveWrapUp,
	submitWrapUp,
} from "../lib/play-session-api";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

const PLAY_SESSIONS_KEY = ["playSessions"] as const;
const LIBRARY_KEY = ["library"] as const;
const STATS_KEY = ["stats"] as const;

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function usePlaySessions(params?: { limit?: number; offset?: number }) {
	return useQuery({
		queryKey: [...PLAY_SESSIONS_KEY, params],
		queryFn: () => listPlaySessions(params),
	});
}

export function usePlaySession(publicId: string) {
	return useQuery({
		queryKey: [...PLAY_SESSIONS_KEY, publicId],
		queryFn: () => getPlaySession(publicId),
		enabled: !!publicId,
	});
}

export function useActivePlaySession() {
	return useQuery({
		queryKey: [...PLAY_SESSIONS_KEY, "active"],
		queryFn: () => getActivePlaySession(),
	});
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function usePreviewRecap() {
	return useMutation({
		mutationFn: (vars: {
			libraryEntryPublicId: string;
			positionOverride?: string;
			mode?: RecapMode;
			signal?: AbortSignal;
		}) => previewRecap(vars.libraryEntryPublicId, vars.positionOverride, vars.mode, vars.signal),
	});
}

export function useRetroactiveWrapUp() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { libraryEntryPublicId: string; wrapUpText: string }) =>
			submitRetroactiveWrapUp(vars.libraryEntryPublicId, vars.wrapUpText),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: PLAY_SESSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useStartPlaySession() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: {
			libraryEntryPublicId: string;
			recapText?: string;
			skipRecap?: boolean;
		}) => startPlaySession(vars.libraryEntryPublicId, vars.recapText, vars.skipRecap),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: PLAY_SESSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useSubmitWrapUp() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { publicId: string; wrapUpText: string }) =>
			submitWrapUp(vars.publicId, vars.wrapUpText),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: PLAY_SESSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useEndPlaySession() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { publicId: string; endedVia?: string }) =>
			endPlaySession(vars.publicId, vars.endedVia),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: PLAY_SESSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useRegenerateRecap() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { publicId: string; currentPosition?: string }) =>
			regenerateRecap(vars.publicId, vars.currentPosition),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: PLAY_SESSIONS_KEY });
		},
	});
}
