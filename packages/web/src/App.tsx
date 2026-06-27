import {
	Anchor,
	AppShell,
	Burger,
	Button,
	Group,
	Loader,
	NavLink,
	Stack,
	Text,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
	IconBooks,
	IconChartBar,
	IconDeviceGamepad2,
	IconHistory,
	IconLogout,
} from "@tabler/icons-react";
import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { VerifyEmailBanner } from "./components/VerifyEmailBanner";
import { useAuthContext } from "./contexts/AuthContext";
import { FEATURES } from "./lib/features";
import { LoginPage } from "./pages/LoginPage";
import { OAuthCallbackPage } from "./pages/OAuthCallbackPage";
import { RegisterPage } from "./pages/RegisterPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";

// Route-level code-splitting: each page (and its heavy chart/datatable deps)
// loads on demand rather than shipping in one >1MB bundle. The shell stays eager.
const AnalyticsPage = lazy(() =>
	import("./pages/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })),
);
const CapturesPage = lazy(() =>
	import("./pages/CapturesPage").then((m) => ({ default: m.CapturesPage })),
);
const ConciergePage = lazy(() =>
	import("./pages/ConciergePage").then((m) => ({ default: m.ConciergePage })),
);
const LibraryImportPage = lazy(() =>
	import("./pages/LibraryImportPage").then((m) => ({ default: m.LibraryImportPage })),
);
const LibraryPage = lazy(() =>
	import("./pages/LibraryPage").then((m) => ({ default: m.LibraryPage })),
);
const LoadoutPage = lazy(() =>
	import("./pages/LoadoutPage").then((m) => ({ default: m.LoadoutPage })),
);
const MissionsPage = lazy(() =>
	import("./pages/MissionsPage").then((m) => ({ default: m.MissionsPage })),
);
const PlayPage = lazy(() => import("./pages/PlayPage").then((m) => ({ default: m.PlayPage })));
const BackofficeRoot = lazy(() =>
	import("./pages/backoffice/BackofficeRoot").then((m) => ({ default: m.BackofficeRoot })),
);

function RouteFallback() {
	return (
		<Group justify="center" py="xl">
			<Loader />
		</Group>
	);
}

function AppLayout() {
	const { logout } = useAuthContext();
	const location = useLocation();
	const navigate = useNavigate();
	const [opened, { toggle, close }] = useDisclosure();

	// Collapse the mobile navbar after navigating to a new section.
	const go = (path: string) => {
		navigate(path);
		close();
	};

	return (
		<AppShell
			header={{ height: 56 }}
			navbar={{ width: 250, breakpoint: "sm", collapsed: { mobile: !opened } }}
			padding="md"
		>
			<AppShell.Header>
				<Group h="100%" px="md" gap="sm">
					<Burger
						opened={opened}
						onClick={toggle}
						hiddenFrom="sm"
						size="sm"
						aria-label="Toggle navigation"
					/>
					<Text fw={700}>DailyLoadout</Text>
				</Group>
			</AppShell.Header>

			<AppShell.Navbar p="md">
				<Stack justify="space-between" h="100%">
					<Stack gap="xs">
						<NavLink
							label="Play"
							leftSection={<IconDeviceGamepad2 size={18} />}
							active={location.pathname.startsWith("/play")}
							onClick={() => go("/play")}
						/>
						<NavLink
							label="Library"
							leftSection={<IconBooks size={18} />}
							active={location.pathname.startsWith("/library")}
							onClick={() => go("/library")}
						/>
						<NavLink
							label="History"
							leftSection={<IconHistory size={18} />}
							active={location.pathname.startsWith("/history")}
							onClick={() => go("/history")}
						/>
						<NavLink
							label="Stats"
							leftSection={<IconChartBar size={18} />}
							active={location.pathname.startsWith("/analytics")}
							onClick={() => go("/analytics")}
						/>
					</Stack>
					<Stack gap="xs">
						<Button
							variant="subtle"
							color="gray"
							leftSection={<IconLogout size={16} />}
							onClick={() => logout()}
							justify="flex-start"
						>
							Sign out
						</Button>
						{/* IGDB requires visible, static attribution wherever its data is used. */}
						<Text size="xs" c="dimmed">
							Game data from{" "}
							<Anchor
								href="https://www.igdb.com"
								target="_blank"
								rel="noopener noreferrer"
								c="dimmed"
								underline="always"
								inherit
							>
								IGDB.com
							</Anchor>
						</Text>
					</Stack>
				</Stack>
			</AppShell.Navbar>

			<AppShell.Main>
				<VerifyEmailBanner />
				<Suspense fallback={<RouteFallback />}>
					<Routes>
						<Route path="/play" element={<PlayPage />} />
						<Route path="/play/loadout" element={<LoadoutPage />} />
						{FEATURES.backlogConcierge && (
							<Route path="/play/concierge" element={<ConciergePage />} />
						)}
						<Route path="/library" element={<LibraryPage />} />
						<Route path="/library/import" element={<LibraryImportPage />} />
						<Route path="/history" element={<MissionsPage />} />
						<Route path="/captures" element={<CapturesPage />} />
						<Route path="/analytics" element={<AnalyticsPage />} />
						{/* Backward-compatible redirects from the old flat / nested routes. */}
						<Route path="/loadout" element={<Navigate to="/play/loadout" replace />} />
						<Route path="/missions" element={<Navigate to="/history" replace />} />
						<Route path="/play/missions" element={<Navigate to="/history" replace />} />
						<Route path="/concierge" element={<Navigate to="/play/concierge" replace />} />
						<Route path="*" element={<Navigate to="/play" replace />} />
					</Routes>
				</Suspense>
			</AppShell.Main>
		</AppShell>
	);
}

function App() {
	return (
		<Routes>
			<Route path="/login" element={<LoginPage />} />
			<Route path="/register" element={<RegisterPage />} />
			{/* Public: the verification link is opened straight from the email,
			    possibly while signed out. */}
			<Route path="/verify-email" element={<VerifyEmailPage />} />
			{/* Public: the API redirects the browser here after a social login;
			    the page completes the cookie→session bootstrap. */}
			<Route path="/oauth/callback" element={<OAuthCallbackPage />} />
			{/* Backoffice: a separate admin area with its own shell, gated by an
			    admin check on top of the auth guard. Lazy so its bundle never ships
			    to non-admins until they navigate here. */}
			<Route
				path="/backoffice/*"
				element={
					<ProtectedRoute>
						<Suspense fallback={<RouteFallback />}>
							<BackofficeRoot />
						</Suspense>
					</ProtectedRoute>
				}
			/>
			<Route
				path="/*"
				element={
					<ProtectedRoute>
						<AppLayout />
					</ProtectedRoute>
				}
			/>
		</Routes>
	);
}

export default App;
