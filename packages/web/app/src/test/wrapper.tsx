/**
 * Reusable test wrapper providing all required React context providers.
 *
 * Usage:
 *   render(<MyComponent />, { wrapper: createWrapper() })
 */
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AuthProvider } from "../contexts/AuthContext";
import type { useAuth } from "../hooks/useAuth";

type AuthContextValue = ReturnType<typeof useAuth>;

/**
 * Build a fully-typed `useAuthContext()` return value for tests, with sane
 * defaults (unauthenticated, verified). Pass `overrides` to tailor a scenario.
 */
export function makeAuthContext(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
	return {
		user: null,
		isLoading: false,
		isAuthenticated: false,
		emailVerified: true,
		login: vi.fn(),
		register: vi.fn(),
		logout: vi.fn(),
		completeOAuth: vi.fn(),
		verify: vi.fn(),
		resendVerification: vi.fn(),
		forgotPassword: vi.fn(),
		resetPassword: vi.fn(),
		changePassword: vi.fn(),
		refetchUser: vi.fn(),
		loginError: null,
		registerError: null,
		verifyError: null,
		changePasswordError: null,
		isLoginPending: false,
		isRegisterPending: false,
		isVerifyPending: false,
		isResendPending: false,
		isForgotPasswordPending: false,
		isResetPasswordPending: false,
		isChangePasswordPending: false,
		...overrides,
	};
}

interface WrapperOptions {
	/** Initial route entries for MemoryRouter (default: ["/"]) */
	initialEntries?: string[];
	/** Custom QueryClient (creates a fresh one per call when omitted) */
	queryClient?: QueryClient;
}

function makeQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			queries: { retry: false },
			mutations: { retry: false },
		},
	});
}

export function createWrapper(opts: WrapperOptions = {}) {
	const qc = opts.queryClient ?? makeQueryClient();
	const entries = opts.initialEntries ?? ["/"];

	return function Wrapper({ children }: { children: ReactNode }) {
		return (
			<QueryClientProvider client={qc}>
				<MantineProvider>
					<MemoryRouter initialEntries={entries}>
						<AuthProvider>{children}</AuthProvider>
					</MemoryRouter>
				</MantineProvider>
			</QueryClientProvider>
		);
	};
}
