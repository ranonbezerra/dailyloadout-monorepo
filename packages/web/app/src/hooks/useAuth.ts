import {
	apiFetch,
	authFetch,
	clearTokens,
	getAccessToken,
	refreshSession,
	saveTokens,
	TURNSTILE_HEADER,
} from "@dl/shared/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { resendVerification as resendVerificationApi, verifyEmail } from "../lib/auth-api";
import type { AuthTokens, User } from "../types/auth";

/**
 * Normalize the API's `UserResponse` so UI code can read a camel-case
 * `emailVerified` field. The API only returns `email_verified`; we mirror it.
 */
function normalizeUser(raw: User): User {
	return { ...raw, emailVerified: raw.email_verified };
}

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
			return normalizeUser(await apiFetch<User>("/v1/auth/me"));
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
	// When a Turnstile site key is configured the form supplies a solved-challenge
	// token; we forward it as the `cf-turnstile-response` header. With no key the
	// token is undefined and the header is omitted — the server treats it as a
	// no-op, so registration still works in dev / when CAPTCHA is disabled.
	const registerMutation = useMutation({
		mutationFn: async (vars: {
			email: string;
			password: string;
			displayName: string;
			turnstileToken?: string;
		}) => {
			const headers = vars.turnstileToken
				? { [TURNSTILE_HEADER]: vars.turnstileToken }
				: undefined;
			const data = await authFetch<AuthTokens>(
				"/v1/auth/register",
				{
					email: vars.email,
					password: vars.password,
					display_name: vars.displayName,
				},
				headers,
			);
			saveTokens(data.access_token);
		},
		onSuccess: () => {
			queryClient.setQueryData(BOOTSTRAP_QUERY_KEY, true);
			queryClient.invalidateQueries({ queryKey: USER_QUERY_KEY });
		},
	});

	// ---- Email-verification mutations --------------------------------------
	const verifyEmailMutation = useMutation({
		mutationFn: (token: string) => verifyEmail(token),
		onSuccess: () => {
			// The flag just flipped server-side — refetch /me so the banner clears.
			queryClient.invalidateQueries({ queryKey: USER_QUERY_KEY });
		},
	});

	const resendVerificationMutation = useMutation({
		mutationFn: () => resendVerificationApi(),
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

	// ---- OAuth completion ---------------------------------------------------
	// Called by /oauth/callback after a social login redirect. The browser holds
	// only the refresh cookie at this point, so a silent refresh exchanges it for
	// an in-memory access token; we then invalidate bootstrap + /me so the app
	// re-derives authenticated state and loads the user.
	const completeOAuth = useCallback(async () => {
		const ok = await refreshSession();
		await queryClient.invalidateQueries({ queryKey: BOOTSTRAP_QUERY_KEY });
		if (ok) await queryClient.invalidateQueries({ queryKey: USER_QUERY_KEY });
		return ok;
	}, [queryClient]);

	// ---- Public API ---------------------------------------------------------
	const login = async (email: string, password: string) => {
		await loginMutation.mutateAsync({ email, password });
	};

	const register = async (
		email: string,
		password: string,
		displayName: string,
		turnstileToken?: string,
	) => {
		await registerMutation.mutateAsync({ email, password, displayName, turnstileToken });
	};

	const verify = async (token: string): Promise<void> => {
		await verifyEmailMutation.mutateAsync(token);
	};

	const resendVerification = async (): Promise<void> => {
		await resendVerificationMutation.mutateAsync();
	};

	/** Force a refetch of /me (e.g. after verifying via the email link). */
	const refetchUser = () => queryClient.invalidateQueries({ queryKey: USER_QUERY_KEY });

	const logout = async () => {
		await logoutMutation.mutateAsync();
	};

	return {
		user,
		isLoading,
		isAuthenticated: !!user,
		emailVerified: user?.emailVerified ?? false,
		login,
		register,
		logout,
		completeOAuth,
		verify,
		resendVerification,
		refetchUser,
		loginError: loginMutation.error,
		registerError: registerMutation.error,
		verifyError: verifyEmailMutation.error,
		isLoginPending: loginMutation.isPending,
		isRegisterPending: registerMutation.isPending,
		isVerifyPending: verifyEmailMutation.isPending,
		isResendPending: resendVerificationMutation.isPending,
	};
}
