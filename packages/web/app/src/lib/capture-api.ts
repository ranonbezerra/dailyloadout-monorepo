import { apiFetch, fetchWithAuthRetry } from "@dl/shared/api";
import { snakeToCamel } from "@dl/shared/case-convert";
import type { Capture, CaptureListResponse } from "../types/capture";
import type { LibraryEntry, LibraryStatus } from "../types/library";

// ---------------------------------------------------------------------------
// Text capture
// ---------------------------------------------------------------------------

export async function submitTextCapture(rawText: string, inputType = "text"): Promise<Capture> {
	const raw = await apiFetch<unknown>("/v1/captures/text", {
		method: "POST",
		body: JSON.stringify({ raw_text: rawText, input_type: inputType }),
	});
	return snakeToCamel<Capture>(raw);
}

// ---------------------------------------------------------------------------
// Voice transcription
// ---------------------------------------------------------------------------

export interface TranscribeResult {
	text: string;
	language: string | null;
	durationSeconds: number | null;
}

export async function transcribeAudio(audioBlob: Blob): Promise<TranscribeResult> {
	const formData = new FormData();
	formData.append("file", audioBlob, "recording.webm");

	const res = await fetchWithAuthRetry("/v1/captures/transcribe", {
		method: "POST",
		body: formData,
	});

	if (!res.ok) {
		const errBody = await res.text();
		throw new Error(errBody || `Transcription failed: ${res.status}`);
	}

	const raw = await res.json();
	return snakeToCamel<TranscribeResult>(raw);
}

// ---------------------------------------------------------------------------
// Photo capture
// ---------------------------------------------------------------------------

export async function submitPhotoCapture(imageFile: File): Promise<Capture> {
	const formData = new FormData();
	formData.append("file", imageFile);

	const res = await fetchWithAuthRetry("/v1/captures/photo", {
		method: "POST",
		body: formData,
	});

	if (!res.ok) {
		const errBody = await res.text();
		throw new Error(errBody || `Photo capture failed: ${res.status}`);
	}

	const raw = await res.json();
	return snakeToCamel<Capture>(raw);
}

// ---------------------------------------------------------------------------
// Bulk library import (multipart, multiple images)
// ---------------------------------------------------------------------------

export async function submitLibraryImport(files: File[]): Promise<Capture> {
	const formData = new FormData();
	for (const file of files) {
		formData.append("files", file);
	}

	const res = await fetchWithAuthRetry("/v1/captures/library-import", {
		method: "POST",
		body: formData,
	});

	if (!res.ok) {
		const errBody = await res.text();
		throw new Error(errBody || `Library import failed: ${res.status}`);
	}

	const raw = await res.json();
	return snakeToCamel<Capture>(raw);
}

export async function bulkConfirmCandidates(
	captureId: string,
	confirmPublicIds: string[],
	platformId: number,
	status: LibraryStatus = "backlog",
	titleOverrides: Record<string, string> = {},
): Promise<{ confirmed: number; rejected: number }> {
	const raw = await apiFetch<unknown>(`/v1/captures/${captureId}/candidates/bulk-confirm`, {
		method: "POST",
		body: JSON.stringify({
			confirm_public_ids: confirmPublicIds,
			platform_id: platformId,
			status,
			title_overrides: titleOverrides,
		}),
	});
	return snakeToCamel<{ confirmed: number; rejected: number }>(raw);
}

/** Candidate public_ids already in the library for the given platform. */
export async function checkCandidateDuplicates(
	captureId: string,
	platformId: number,
): Promise<string[]> {
	const raw = await apiFetch<unknown>(
		`/v1/captures/${captureId}/candidates/duplicates?platform_id=${platformId}`,
	);
	const parsed = snakeToCamel<{ duplicatePublicIds: string[] }>(raw);
	return parsed.duplicatePublicIds;
}

// ---------------------------------------------------------------------------
// Capture listing and detail
// ---------------------------------------------------------------------------

export async function listCaptures(params?: {
	status?: string;
	limit?: number;
	offset?: number;
}): Promise<CaptureListResponse> {
	const searchParams = new URLSearchParams();
	if (params?.status) searchParams.set("status", params.status);
	if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
	if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));

	const qs = searchParams.toString();
	const path = qs ? `/v1/captures?${qs}` : "/v1/captures";

	const raw = await apiFetch<unknown>(path);
	return snakeToCamel<CaptureListResponse>(raw);
}

export async function getCapture(publicId: string): Promise<Capture> {
	const raw = await apiFetch<unknown>(`/v1/captures/${publicId}`);
	return snakeToCamel<Capture>(raw);
}

// ---------------------------------------------------------------------------
// Candidate actions
// ---------------------------------------------------------------------------

export async function confirmCandidate(
	captureId: string,
	candidateId: string,
	platformId: number,
	status: LibraryStatus = "backlog",
): Promise<LibraryEntry> {
	const raw = await apiFetch<unknown>(
		`/v1/captures/${captureId}/candidates/${candidateId}/confirm`,
		{
			method: "POST",
			body: JSON.stringify({ platform_id: platformId, status }),
		},
	);
	return snakeToCamel<LibraryEntry>(raw);
}

export async function rejectCandidate(captureId: string, candidateId: string): Promise<void> {
	await apiFetch<void>(`/v1/captures/${captureId}/candidates/${candidateId}/reject`, {
		method: "POST",
	});
}
