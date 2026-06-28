import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import "@mantine/notifications/styles.css";
import "mantine-datatable/styles.css";
import "./styles/keyframes.css";
import { notifications } from "@mantine/notifications";
import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.tsx";
import { ErrorBoundary } from "./components/ErrorBoundary.tsx";
import { AuthProvider } from "./contexts/AuthContext.tsx";
import { isEmailNotVerifiedError } from "./lib/errors.ts";
import { theme } from "./theme.ts";

const queryClient = new QueryClient({
	// Defensive global handler: cost-bearing routes 403 with "Email not verified"
	// until the user verifies. Surface a toast pointing them at the banner so a
	// failed AI action doesn't fail silently.
	mutationCache: new MutationCache({
		onError: (error) => {
			if (isEmailNotVerifiedError(error)) {
				notifications.show({
					title: "Email not verified",
					message:
						"Verify your email to use AI features. Use the banner at the top to resend the link.",
					color: "yellow",
				});
			}
		},
	}),
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
