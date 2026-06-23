import type { Capture, CaptureListResponse } from "../types/capture";
import type { LibraryEntry, LibraryStatus } from "../types/library";
import { apiFetch, BASE_URL, getAccessToken } from "./api";
import { snakeToCamel } from "./case-convert";

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

	const headers: Record<string, string> = {};
	const accessToken = getAccessToken();
	if (accessToken) {
		headers.Authorization = `Bearer ${accessToken}`;
	}

	const res = await fetch(`${BASE_URL}/v1/captures/transcribe`, {
		method: "POST",
		headers,
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

	const headers: Record<string, string> = {};
	const accessToken = getAccessToken();
	if (accessToken) {
		headers.Authorization = `Bearer ${accessToken}`;
	}

	const res = await fetch(`${BASE_URL}/v1/captures/photo`, {
		method: "POST",
		headers,
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
