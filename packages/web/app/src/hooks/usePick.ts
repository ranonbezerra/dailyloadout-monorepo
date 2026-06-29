import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { acceptPick, createPick, getLatestPick, listPicks, rejectPick } from "../lib/pick-api";
import type { MentalEnergy, PickMood } from "../types/pick";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

const PICKS_KEY = ["picks"] as const;
const PLAY_SESSIONS_KEY = ["playSessions"] as const;
const STATS_KEY = ["stats"] as const;

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function usePicks(params?: { limit?: number; offset?: number }) {
	return useQuery({
		queryKey: [...PICKS_KEY, params],
		queryFn: () => listPicks(params),
	});
}

export function useLatestPick() {
	return useQuery({
		queryKey: [...PICKS_KEY, "latest"],
		queryFn: () => getLatestPick(),
	});
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useCreatePick() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: {
			mood: PickMood;
			availableMinutes: number;
			mentalEnergy: MentalEnergy;
			count?: number;
			context?: string;
		}) =>
			createPick(vars.mood, vars.availableMinutes, vars.mentalEnergy, vars.count, vars.context),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: PICKS_KEY });
		},
	});
}

export function useAcceptPick() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { publicId: string; recapText?: string }) =>
			acceptPick(vars.publicId, vars.recapText),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: PICKS_KEY });
			queryClient.invalidateQueries({ queryKey: PLAY_SESSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useRejectPick() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (publicId: string) => rejectPick(publicId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: PICKS_KEY });
		},
	});
}
