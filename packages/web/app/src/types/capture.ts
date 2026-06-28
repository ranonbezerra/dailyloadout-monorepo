// ---------------------------------------------------------------------------
// Capture domain types (camelCase for TS, API returns snake_case)
// ---------------------------------------------------------------------------

import type { Game } from "./library";

export type CaptureStatus =
	| "queued"
	| "processing"
	| "review"
	| "committed"
	| "partially_committed"
	| "failed"
	| "cancelled";

export type CandidateStatus = "pending" | "confirmed" | "rejected";

export interface CaptureCandidate {
	publicId: string;
	title: string;
	platformHint: string | null;
	igdbTitle: string | null;
	igdbCoverUrl: string | null;
	igdbSummary: string | null;
	igdbGenres: string[] | null;
	confidence: number | null;
	status: CandidateStatus;
	matchedGame: Game | null;
}

export interface Capture {
	publicId: string;
	inputType: string;
	rawText: string | null;
	status: CaptureStatus;
	errorMessage: string | null;
	candidates: CaptureCandidate[];
	createdAt: string;
	updatedAt: string;
}

export interface CaptureListItem {
	publicId: string;
	inputType: string;
	rawText: string | null;
	status: CaptureStatus;
	errorMessage: string | null;
	candidateTitles: string[];
	createdAt: string;
	updatedAt: string;
}

export interface CaptureListResponse {
	items: CaptureListItem[];
	total: number;
}
