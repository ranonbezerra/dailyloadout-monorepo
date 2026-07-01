import {
	apiFetch,
	authFetch,
	clearTokens,
	getAccessToken,
	refreshSession,
	saveTokens,
	TURNSTILE_HEADER,
} from "@slate/shared/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import {
	changePassword as changePasswordApi,
	forgotPassword as forgotPasswordApi,
	resendVerification as resendVerificationApi,
	resetPassword as resetPasswordApi,
	verifyEmail,
} from "../lib/auth-api";
import { mfaLogin as mfaLoginApi } from "../lib/mfa-api";
import type { AuthTokens, LoginResponse, User } from "../types/auth";

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
	// When the account has MFA enabled the server returns `mfa_required` with a
	// short-lived challenge token instead of session tokens — we hold off on
	// saving anything and let the caller drive the second step.
	const loginMutation = useMutation({
		mutationFn: async (vars: { email: string; password: string; turnstileToken?: string }) => {
			// After repeated failures the server demands a CAPTCHA (403). The re-submit
			// then carries the solved token in the `cf-turnstile-response` header.
			const headers = vars.turnstileToken
				? { [TURNSTILE_HEADER]: vars.turnstileToken }
				: undefined;
			const data = await authFetch<LoginResponse>(
				"/v1/auth/login",
				{ email: vars.email, password: vars.password },
				headers,
			);
			if (!data.mfa_required) saveTokens(data.access_token);
			return data;
		},
		onSuccess: (data) => {
			if (!data.mfa_required) {
				queryClient.setQueryData(BOOTSTRAP_QUERY_KEY, true);
				queryClient.invalidateQueries({ queryKey: USER_QUERY_KEY });
			}
		},
	});

	// ---- MFA login (second factor) -----------------------------------------
	const mfaLoginMutation = useMutation({
		mutationFn: async (vars: { mfaToken: string; code: string }) => {
			const data = await mfaLoginApi(vars.mfaToken, vars.code);
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

	// ---- Password-recovery mutations ---------------------------------------
	const forgotPasswordMutation = useMutation({
		mutationFn: (email: string) => forgotPasswordApi(email),
	});

	const resetPasswordMutation = useMutation({
		mutationFn: (vars: { token: string; newPassword: string }) =>
			resetPasswordApi(vars.token, vars.newPassword),
	});

	// Change-password reissues tokens: store the fresh access token so this
	// device stays signed in, then refetch /me (other sessions were cut off).
	const changePasswordMutation = useMutation({
		mutationFn: async (vars: { currentPassword: string; newPassword: string }) => {
			const data = await changePasswordApi(vars.currentPassword, vars.newPassword);
			saveTokens(data.access_token);
		},
		onSuccess: () => {
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
	const login = async (
		email: string,
		password: string,
		turnstileToken?: string,
	): Promise<{ mfaRequired: boolean; mfaToken: string }> => {
		const data = await loginMutation.mutateAsync({ email, password, turnstileToken });
		return { mfaRequired: data.mfa_required, mfaToken: data.mfa_token };
	};

	const completeMfaLogin = async (mfaToken: string, code: string): Promise<void> => {
		await mfaLoginMutation.mutateAsync({ mfaToken, code });
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

	const forgotPassword = async (email: string): Promise<void> => {
		await forgotPasswordMutation.mutateAsync(email);
	};

	const resetPassword = async (token: string, newPassword: string): Promise<void> => {
		await resetPasswordMutation.mutateAsync({ token, newPassword });
	};

	const changePassword = async (currentPassword: string, newPassword: string): Promise<void> => {
		await changePasswordMutation.mutateAsync({ currentPassword, newPassword });
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
		completeMfaLogin,
		register,
		logout,
		completeOAuth,
		verify,
		resendVerification,
		forgotPassword,
		resetPassword,
		changePassword,
		refetchUser,
		loginError: loginMutation.error,
		registerError: registerMutation.error,
		verifyError: verifyEmailMutation.error,
		changePasswordError: changePasswordMutation.error,
		isLoginPending: loginMutation.isPending,
		isMfaLoginPending: mfaLoginMutation.isPending,
		isRegisterPending: registerMutation.isPending,
		isVerifyPending: verifyEmailMutation.isPending,
		isResendPending: resendVerificationMutation.isPending,
		isForgotPasswordPending: forgotPasswordMutation.isPending,
		isResetPasswordPending: resetPasswordMutation.isPending,
		isChangePasswordPending: changePasswordMutation.isPending,
	};
}
