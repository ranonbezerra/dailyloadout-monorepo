import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	acceptLoadout,
	createLoadout,
	getLatestLoadout,
	listLoadouts,
	rejectLoadout,
} from "../lib/loadout-api";
import type { LoadoutMood, MentalEnergy } from "../types/loadout";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

const LOADOUTS_KEY = ["loadouts"] as const;
const MISSIONS_KEY = ["missions"] as const;

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function useLoadouts(params?: { limit?: number; offset?: number }) {
	return useQuery({
		queryKey: [...LOADOUTS_KEY, params],
		queryFn: () => listLoadouts(params),
	});
}

export function useLatestLoadout() {
	return useQuery({
		queryKey: [...LOADOUTS_KEY, "latest"],
		queryFn: () => getLatestLoadout(),
	});
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useCreateLoadout() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: {
			mood: LoadoutMood;
			availableMinutes: number;
			mentalEnergy: MentalEnergy;
			count?: number;
			context?: string;
		}) =>
			createLoadout(vars.mood, vars.availableMinutes, vars.mentalEnergy, vars.count, vars.context),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: LOADOUTS_KEY });
		},
	});
}

export function useAcceptLoadout() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (publicId: string) => acceptLoadout(publicId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: LOADOUTS_KEY });
			queryClient.invalidateQueries({ queryKey: MISSIONS_KEY });
		},
	});
}

export function useRejectLoadout() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (publicId: string) => rejectLoadout(publicId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: LOADOUTS_KEY });
		},
	});
}
