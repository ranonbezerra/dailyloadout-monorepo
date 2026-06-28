import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

interface WrapperOptions {
	initialEntries?: string[];
	queryClient?: QueryClient;
}

export function makeQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			queries: { retry: false },
			mutations: { retry: false },
		},
	});
}

/** Providers for hooks/components under test (Query + Mantine + Router). */
export function createWrapper(opts: WrapperOptions = {}) {
	const qc = opts.queryClient ?? makeQueryClient();
	const entries = opts.initialEntries ?? ["/"];

	return function Wrapper({ children }: { children: ReactNode }) {
		return (
			<QueryClientProvider client={qc}>
				<MantineProvider>
					<MemoryRouter initialEntries={entries}>{children}</MemoryRouter>
				</MantineProvider>
			</QueryClientProvider>
		);
	};
}
