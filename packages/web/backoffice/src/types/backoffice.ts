/**
 * Backoffice (Epic 21) types. The API serves these under `/internal/v1` in
 * snake_case; the api layer runs them through `snakeToCamel`, so the shapes here
 * are camelCase.
 */

export interface AdminMe {
	publicId: string;
	email: string;
	displayName: string;
}

export interface AuditEntry {
	action: string;
	detail: string | null;
	createdAt: string;
	adminPublicId: string | null;
	adminEmail: string | null;
	targetPublicId: string | null;
	targetEmail: string | null;
}

export interface AuditList {
	items: AuditEntry[];
	total: number;
	limit: number;
	offset: number;
}

export interface DashboardSummary {
	usersTotal: number;
	usersBanned: number;
	usersUnverified: number;
	admins: number;
	missionsActive: number;
	catalogueSize: number;
	configOverrides: number;
	recentActions: AuditEntry[];
}

export interface AdminUserSummary {
	publicId: string;
	email: string;
	displayName: string;
	emailVerified: boolean;
	isBanned: boolean;
	createdAt: string;
}

export interface AdminUserList {
	items: AdminUserSummary[];
	total: number;
	limit: number;
	offset: number;
}

export interface AdminUserDetail extends AdminUserSummary {
	avatarUrl: string | null;
	locale: string;
	timezone: string;
	isAdmin: boolean;
	hasPassword: boolean;
	activeSessions: number;
}

/** A curated operational knob is either a boolean toggle or a bounded integer. */
export type ConfigValue = boolean | number;

export interface ConfigEntry {
	key: string;
	kind: "bool" | "int";
	category: string;
	description: string;
	effectiveValue: ConfigValue;
	overrideValue: ConfigValue | null;
	baselineValue: ConfigValue;
	isOverridden: boolean;
	minValue: number | null;
	maxValue: number | null;
	updatedAt: string | null;
	updatedBy: string | null;
}

export interface ConfigList {
	items: ConfigEntry[];
}

export interface UserListParams {
	q?: string;
	banned?: boolean;
	verified?: boolean;
	limit?: number;
	offset?: number;
}

// ── Games / catalogue ──────────────────────────────────────────────────

export type GameSource = "igdb" | "manual";

export interface AdminGameSummary {
	publicId: string;
	slug: string;
	title: string;
	igdbId: number | null;
	source: GameSource;
	isShared: boolean;
	coverUrl: string | null;
	ownerCount: number;
	createdAt: string;
}

export interface AdminGameList {
	items: AdminGameSummary[];
	total: number;
	limit: number;
	offset: number;
	catalogueTotal: number;
	catalogueIgdb: number;
	catalogueManual: number;
}

export interface AdminGameDetail extends AdminGameSummary {
	summary: string | null;
	genres: string[] | null;
	firstReleaseDate: string | null;
	metadataSource: string;
	createdByEmail: string | null;
	updatedAt: string;
}

export interface GameListParams {
	q?: string;
	shared?: boolean;
	source?: GameSource;
	limit?: number;
	offset?: number;
}

export interface GameEdit {
	title?: string;
	summary?: string;
}

// ── Captures (moderation) ──────────────────────────────────────────────

export interface AdminCaptureSummary {
	publicId: string;
	userEmail: string | null;
	inputType: string;
	status: string;
	candidateCount: number;
	errorMessage: string | null;
	createdAt: string;
	updatedAt: string;
}

export interface CaptureStatusCount {
	status: string;
	count: number;
}

export interface AdminCaptureList {
	items: AdminCaptureSummary[];
	total: number;
	limit: number;
	offset: number;
	statusCounts: CaptureStatusCount[];
}

export interface AdminCaptureCandidate {
	publicId: string;
	title: string;
	status: string;
	confidence: number | null;
	igdbId: number | null;
	matchedGameTitle: string | null;
}

export interface AdminCaptureDetail extends AdminCaptureSummary {
	rawText: string | null;
	reprocessable: boolean;
	candidates: AdminCaptureCandidate[];
}

export interface CaptureListParams {
	q?: string;
	status?: string;
	limit?: number;
	offset?: number;
}
