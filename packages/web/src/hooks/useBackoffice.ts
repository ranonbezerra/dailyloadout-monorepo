/**
 * TanStack Query hooks for the backoffice. Queries are admin-only; mutations
 * (ban/verify/config) invalidate the touched lists so the UI reflects the new
 * server state and the audit trail stays in sync.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	banUser,
	clearConfig,
	fetchAdminMe,
	fetchAudit,
	fetchConfig,
	fetchDashboard,
	fetchUser,
	fetchUsers,
	setConfig,
	unbanUser,
	verifyUser,
} from "../lib/backoffice-api";
import type { ConfigValue, UserListParams } from "../types/backoffice";

const BO = ["backoffice"] as const;

export function useAdminMe() {
	return useQuery({
		queryKey: [...BO, "me"],
		queryFn: fetchAdminMe,
		retry: false,
		staleTime: 5 * 60 * 1000,
	});
}

export function useDashboard() {
	return useQuery({ queryKey: [...BO, "dashboard"], queryFn: fetchDashboard });
}

export function useUsers(params: UserListParams) {
	return useQuery({
		queryKey: [...BO, "users", params],
		queryFn: () => fetchUsers(params),
	});
}

export function useUser(publicId: string | null) {
	return useQuery({
		queryKey: [...BO, "user", publicId],
		queryFn: () => fetchUser(publicId as string),
		enabled: !!publicId,
	});
}

export function useConfig() {
	return useQuery({ queryKey: [...BO, "config"], queryFn: fetchConfig });
}

export function useAudit(params: { limit?: number; offset?: number }) {
	return useQuery({
		queryKey: [...BO, "audit", params],
		queryFn: () => fetchAudit(params),
	});
}

/** Ban / unban / verify, all invalidating the user lists + dashboard + audit. */
export function useUserActions() {
	const qc = useQueryClient();
	const invalidate = () => {
		qc.invalidateQueries({ queryKey: [...BO, "users"] });
		qc.invalidateQueries({ queryKey: [...BO, "user"] });
		qc.invalidateQueries({ queryKey: [...BO, "dashboard"] });
		qc.invalidateQueries({ queryKey: [...BO, "audit"] });
	};

	const ban = useMutation({
		mutationFn: (vars: { publicId: string; reason?: string }) =>
			banUser(vars.publicId, vars.reason),
		onSuccess: invalidate,
	});
	const unban = useMutation({
		mutationFn: (publicId: string) => unbanUser(publicId),
		onSuccess: invalidate,
	});
	const verify = useMutation({
		mutationFn: (publicId: string) => verifyUser(publicId),
		onSuccess: invalidate,
	});

	return { ban, unban, verify };
}

/** Set / clear a config override, invalidating the config list + audit. */
export function useConfigActions() {
	const qc = useQueryClient();
	const invalidate = () => {
		qc.invalidateQueries({ queryKey: [...BO, "config"] });
		qc.invalidateQueries({ queryKey: [...BO, "dashboard"] });
		qc.invalidateQueries({ queryKey: [...BO, "audit"] });
	};

	const set = useMutation({
		mutationFn: (vars: { key: string; value: ConfigValue }) => setConfig(vars.key, vars.value),
		onSuccess: invalidate,
	});
	const clear = useMutation({
		mutationFn: (key: string) => clearConfig(key),
		onSuccess: invalidate,
	});

	return { set, clear };
}
