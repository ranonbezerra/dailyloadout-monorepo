import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, clearTokens, getAccessToken, getRefreshToken, saveTokens } from "../lib/api";
import type { AuthTokens, User } from "../types/auth";

const USER_QUERY_KEY = ["auth", "me"] as const;

export function useAuth() {
	const queryClient = useQueryClient();

	// ---- Current user query -------------------------------------------------
	const {
		data: user = null,
		isLoading,
		isFetching,
	} = useQuery<User | null>({
		queryKey: USER_QUERY_KEY,
		queryFn: async () => {
			if (!getAccessToken()) return null;
			return apiFetch<User>("/v1/auth/me");
		},
		enabled: !!getAccessToken(),
		retry: false,
		staleTime: 5 * 60 * 1000,
	});

	// ---- Login mutation -----------------------------------------------------
	const loginMutation = useMutation({
		mutationFn: async (vars: { email: string; password: string }) => {
			const data = await apiFetch<AuthTokens>("/v1/auth/login", {
				method: "POST",
				body: JSON.stringify({
					email: vars.email,
					password: vars.password,
				}),
			});
			saveTokens(data.access_token, data.refresh_token);
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: USER_QUERY_KEY });
		},
	});

	// ---- Register mutation --------------------------------------------------
	const registerMutation = useMutation({
		mutationFn: async (vars: { email: string; password: string; displayName: string }) => {
			const data = await apiFetch<AuthTokens>("/v1/auth/register", {
				method: "POST",
				body: JSON.stringify({
					email: vars.email,
					password: vars.password,
					display_name: vars.displayName,
				}),
			});
			saveTokens(data.access_token, data.refresh_token);
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: USER_QUERY_KEY });
		},
	});

	// ---- Logout mutation ----------------------------------------------------
	const logoutMutation = useMutation({
		mutationFn: async () => {
			const refreshToken = getRefreshToken();
			if (refreshToken) {
				try {
					await apiFetch("/v1/auth/logout", {
						method: "POST",
						body: JSON.stringify({ refresh_token: refreshToken }),
					});
				} catch {
					// Best-effort; clear local state regardless
				}
			}
			clearTokens();
		},
		onSuccess: () => {
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
		isLoading: isLoading || isFetching,
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
