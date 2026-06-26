import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import "@mantine/notifications/styles.css";
import "mantine-datatable/styles.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.tsx";
import { ErrorBoundary } from "./components/ErrorBoundary.tsx";
import { AuthProvider } from "./contexts/AuthContext.tsx";
import { theme } from "./theme.ts";

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 30_000,
			refetchOnWindowFocus: false,
		},
	},
});

// biome-ignore lint/style/noNonNullAssertion: root element guaranteed by index.html
createRoot(document.getElementById("root")!).render(
	<StrictMode>
		<QueryClientProvider client={queryClient}>
			<MantineProvider theme={theme} defaultColorScheme="dark">
				<Notifications position="top-right" />
				<ModalsProvider>
					<ErrorBoundary>
						<BrowserRouter>
							<AuthProvider>
								<App />
							</AuthProvider>
						</BrowserRouter>
					</ErrorBoundary>
				</ModalsProvider>
			</MantineProvider>
		</QueryClientProvider>
	</StrictMode>,
);
