import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authFetch, clearTokens, getAccessToken, refreshSession, saveTokens } from "../lib/api";
import type { AuthTokens } from "../types/auth";

const BOOTSTRAP_QUERY_KEY = ["backoffice", "bootstrap"] as const;

/**
 * Backoffice auth: a minimal email/password sign-in over the SAME API the player
 * app uses (cookie-based refresh; the access token lives only in memory). Whether
 * the signed-in account is actually an admin is decided downstream by the
 * `BackofficeGuard` via `/internal/v1/me`.
 */
export function useAuth() {
	const queryClient = useQueryClient();

	// On reload the in-memory access token is gone; restore the session from the
	// httpOnly refresh cookie before deciding authenticated-vs-login.
	const { data: bootstrapped = false, isLoading: isBootstrapping } = useQuery<boolean>({
		queryKey: BOOTSTRAP_QUERY_KEY,
		queryFn: async () => {
			if (getAccessToken()) return true;
			return refreshSession();
		},
		retry: false,
		staleTime: Number.POSITIVE_INFINITY,
		gcTime: Number.POSITIVE_INFINITY,
		refetchOnWindowFocus: false,
	});

	const loginMutation = useMutation({
		mutationFn: async (vars: { email: string; password: string }) => {
			const data = await authFetch<AuthTokens>("/v1/auth/login", {
				email: vars.email,
				password: vars.password,
			});
			saveTokens(data.access_token);
		},
		onSuccess: () => {
			queryClient.setQueryData(BOOTSTRAP_QUERY_KEY, true);
			queryClient.invalidateQueries({ queryKey: ["backoffice", "me"] });
		},
	});

	const logoutMutation = useMutation({
		mutationFn: async () => {
			try {
				await authFetch("/v1/auth/logout", {});
			} catch {
				// best-effort — we still drop local state below
			}
			clearTokens();
		},
		onSuccess: () => {
			queryClient.setQueryData(BOOTSTRAP_QUERY_KEY, false);
			queryClient.clear();
		},
	});

	const login = async (email: string, password: string) => {
		await loginMutation.mutateAsync({ email, password });
	};

	const logout = async () => {
		await logoutMutation.mutateAsync();
	};

	return {
		isLoading: isBootstrapping,
		isAuthenticated: bootstrapped && !!getAccessToken(),
		login,
		logout,
		loginError: loginMutation.error,
		isLoginPending: loginMutation.isPending,
	};
}
