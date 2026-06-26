import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	bulkConfirmCandidates,
	checkCandidateDuplicates,
	confirmCandidate,
	getCapture,
	listCaptures,
	rejectCandidate,
	submitLibraryImport,
	submitPhotoCapture,
	submitTextCapture,
	transcribeAudio,
} from "../lib/capture-api";
import type { LibraryStatus } from "../types/library";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

const CAPTURES_KEY = ["captures"] as const;
const LIBRARY_KEY = ["library"] as const;
const STATS_KEY = ["stats"] as const;

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function useCaptures(status?: string) {
	return useQuery({
		queryKey: [...CAPTURES_KEY, { status }],
		queryFn: () => listCaptures(status ? { status } : undefined),
	});
}

export function useCapture(publicId: string) {
	return useQuery({
		queryKey: [...CAPTURES_KEY, publicId],
		queryFn: () => getCapture(publicId),
		enabled: !!publicId,
	});
}

/** Which candidates are already in the library for a platform (import warning). */
export function useCandidateDuplicates(captureId: string | null, platformId: number | null) {
	return useQuery({
		queryKey: [...CAPTURES_KEY, captureId, "duplicates", platformId],
		queryFn: () => checkCandidateDuplicates(captureId as string, platformId as number),
		enabled: !!captureId && platformId != null,
	});
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useSubmitTextCapture() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { rawText: string; inputType?: string }) =>
			submitTextCapture(vars.rawText, vars.inputType),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: CAPTURES_KEY });
		},
	});
}

export function useSubmitPhotoCapture() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (imageFile: File) => submitPhotoCapture(imageFile),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: CAPTURES_KEY });
		},
	});
}

export function useSubmitLibraryImport() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (files: File[]) => submitLibraryImport(files),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: CAPTURES_KEY });
		},
	});
}

export function useBulkConfirmCandidates() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: {
			captureId: string;
			confirmPublicIds: string[];
			platformId: number;
			status?: LibraryStatus;
			titleOverrides?: Record<string, string>;
		}) =>
			bulkConfirmCandidates(
				vars.captureId,
				vars.confirmPublicIds,
				vars.platformId,
				vars.status,
				vars.titleOverrides,
			),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: CAPTURES_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useTranscribeAudio() {
	return useMutation({
		mutationFn: (audioBlob: Blob) => transcribeAudio(audioBlob),
	});
}

export function useConfirmCandidate() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: {
			captureId: string;
			candidateId: string;
			platformId: number;
			status?: LibraryStatus;
		}) => confirmCandidate(vars.captureId, vars.candidateId, vars.platformId, vars.status),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: CAPTURES_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useRejectCandidate() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { captureId: string; candidateId: string }) =>
			rejectCandidate(vars.captureId, vars.candidateId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: CAPTURES_KEY });
		},
	});
}
