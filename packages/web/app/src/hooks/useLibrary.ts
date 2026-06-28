import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	addToLibrary,
	createGame,
	deleteEntry,
	fetchGameGenres,
	fetchLibrary,
	fetchLibraryEntry,
	fetchPlatforms,
	searchGames,
	updateEntry,
} from "../lib/library-api";
import type { GameCreate, LibraryEntryCreate, LibraryEntryUpdate } from "../types/library";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

const PLATFORMS_KEY = ["platforms"] as const;
const GAMES_SEARCH_KEY = ["games", "search"] as const;
const GAME_GENRES_KEY = ["games", "genres"] as const;
const LIBRARY_KEY = ["library"] as const;
const STATS_KEY = ["stats"] as const;

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function usePlatforms() {
	return useQuery({
		queryKey: PLATFORMS_KEY,
		queryFn: fetchPlatforms,
		staleTime: Number.POSITIVE_INFINITY,
	});
}

export function useSearchGames(query: string) {
	return useQuery({
		queryKey: [...GAMES_SEARCH_KEY, query],
		queryFn: () => searchGames(query),
		enabled: query.length >= 2,
		staleTime: 30_000,
	});
}

export function useGameGenres() {
	return useQuery({
		queryKey: GAME_GENRES_KEY,
		queryFn: fetchGameGenres,
		staleTime: 60_000,
	});
}

export function useLibrary(params?: { status?: string; limit?: number; offset?: number }) {
	return useQuery({
		queryKey: [...LIBRARY_KEY, params],
		queryFn: () => fetchLibrary(params),
	});
}

export function useLibraryEntry(publicId: string | null) {
	return useQuery({
		queryKey: [...LIBRARY_KEY, "entry", publicId],
		queryFn: () => fetchLibraryEntry(publicId as string),
		enabled: publicId !== null,
	});
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useAddToLibrary() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (data: LibraryEntryCreate) => addToLibrary(data),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useUpdateEntry() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { publicId: string; data: LibraryEntryUpdate }) =>
			updateEntry(vars.publicId, vars.data),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useDeleteEntry() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (publicId: string) => deleteEntry(publicId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useCreateGame() {
	return useMutation({
		mutationFn: (data: GameCreate) => createGame(data),
	});
}
