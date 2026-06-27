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
