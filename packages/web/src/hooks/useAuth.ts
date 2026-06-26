import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	apiFetch,
	authFetch,
	clearTokens,
	getAccessToken,
	refreshSession,
	saveTokens,
} from "../lib/api";
import type { AuthTokens, User } from "../types/auth";

const USER_QUERY_KEY = ["auth", "me"] as const;
const BOOTSTRAP_QUERY_KEY = ["auth", "bootstrap"] as const;

export function useAuth() {
	const queryClient = useQueryClient();

	// ---- Bootstrap silent refresh ------------------------------------------
	// The access token lives only in memory, so it's gone after a page reload.
	// On mount, attempt a cookie-based silent refresh to restore the session
	// before deciding authenticated-vs-login. `isBootstrapping` keeps the app
	// in a loading state so it doesn't flash the login page.
	const { data: bootstrapped = false, isLoading: isBootstrapping } = useQuery<boolean>({
		queryKey: BOOTSTRAP_QUERY_KEY,
		queryFn: async () => {
			// Already have an in-memory token (e.g. right after login) → skip.
			if (getAccessToken()) return true;
			return refreshSession();
		},
		retry: false,
		staleTime: Number.POSITIVE_INFINITY,
		gcTime: Number.POSITIVE_INFINITY,
		refetchOnWindowFocus: false,
	});

	// ---- Current user query -------------------------------------------------
	const { data: user = null, isLoading: isUserLoading } = useQuery<User | null>({
		queryKey: USER_QUERY_KEY,
		queryFn: async () => {
			if (!getAccessToken()) return null;
			return apiFetch<User>("/v1/auth/me");
		},
		// Only fetch /me once bootstrap has resolved and produced a token.
		enabled: bootstrapped && !!getAccessToken(),
		retry: false,
		staleTime: 5 * 60 * 1000,
	});

	const isLoading = isBootstrapping || (bootstrapped && !!getAccessToken() && isUserLoading);

	// ---- Login mutation -----------------------------------------------------
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
			queryClient.invalidateQueries({ queryKey: USER_QUERY_KEY });
		},
	});

	// ---- Register mutation --------------------------------------------------
	const registerMutation = useMutation({
		mutationFn: async (vars: { email: string; password: string; displayName: string }) => {
			const data = await authFetch<AuthTokens>("/v1/auth/register", {
				email: vars.email,
				password: vars.password,
				display_name: vars.displayName,
			});
			saveTokens(data.access_token);
		},
		onSuccess: () => {
			queryClient.setQueryData(BOOTSTRAP_QUERY_KEY, true);
			queryClient.invalidateQueries({ queryKey: USER_QUERY_KEY });
		},
	});

	// ---- Logout mutation ----------------------------------------------------
	const logoutMutation = useMutation({
		mutationFn: async () => {
			try {
				// Hit the endpoint so the server revokes the token and clears the
				// httpOnly cookie. Best-effort: clear local state regardless.
				await authFetch("/v1/auth/logout", {});
			} catch {
				// ignore — we still drop the in-memory token below
			}
			clearTokens();
		},
		onSuccess: () => {
			queryClient.setQueryData(BOOTSTRAP_QUERY_KEY, false);
			queryClient.clear();
		},
	});

	// ---- Public API ---------------------------------------------------------
	const login = async (email: string, password: string) => {
		await loginMutation.mutateAsync({ email, password });
	};

	const register = async (email: string, password: string, displayName: string) => {
		await registerMutation.mutateAsync({ email, password, displayName });
	};

	const logout = async () => {
		await logoutMutation.mutateAsync();
	};

	return {
		user,
		isLoading,
		isAuthenticated: !!user,
		login,
		register,
		logout,
		loginError: loginMutation.error,
		registerError: registerMutation.error,
		isLoginPending: loginMutation.isPending,
		isRegisterPending: registerMutation.isPending,
	};
}
