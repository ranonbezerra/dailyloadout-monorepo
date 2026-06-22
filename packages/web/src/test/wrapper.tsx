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
import { AuthProvider } from "../contexts/AuthContext";

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
