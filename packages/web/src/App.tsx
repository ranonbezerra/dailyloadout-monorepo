import { Anchor, AppShell, Button, NavLink, Stack, Text } from "@mantine/core";
import {
	IconBooks,
	IconChartBar,
	IconDeviceGamepad2,
	IconHistory,
	IconLogout,
} from "@tabler/icons-react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { useAuthContext } from "./contexts/AuthContext";
import { FEATURES } from "./lib/features";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { CapturesPage } from "./pages/CapturesPage";
import { ConciergePage } from "./pages/ConciergePage";
import { LibraryImportPage } from "./pages/LibraryImportPage";
import { LibraryPage } from "./pages/LibraryPage";
import { LoadoutPage } from "./pages/LoadoutPage";
import { LoginPage } from "./pages/LoginPage";
import { MissionsPage } from "./pages/MissionsPage";
import { PlayPage } from "./pages/PlayPage";
import { RegisterPage } from "./pages/RegisterPage";

function AppLayout() {
	const { logout } = useAuthContext();
	const location = useLocation();
	const navigate = useNavigate();

	return (
		<AppShell navbar={{ width: 250, breakpoint: "sm" }} padding="md">
			<AppShell.Navbar p="md">
				<Stack justify="space-between" h="100%">
					<Stack gap="xs">
						<Text fw={700} mb="sm">
							DailyLoadout
						</Text>
						<NavLink
							label="Play"
							leftSection={<IconDeviceGamepad2 size={18} />}
							active={location.pathname.startsWith("/play")}
							onClick={() => navigate("/play")}
						/>
						<NavLink
							label="Library"
							leftSection={<IconBooks size={18} />}
							active={location.pathname.startsWith("/library")}
							onClick={() => navigate("/library")}
						/>
						<NavLink
							label="History"
							leftSection={<IconHistory size={18} />}
							active={location.pathname.startsWith("/history")}
							onClick={() => navigate("/history")}
						/>
						<NavLink
							label="Stats"
							leftSection={<IconChartBar size={18} />}
							active={location.pathname.startsWith("/analytics")}
							onClick={() => navigate("/analytics")}
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
			</AppShell.Main>
		</AppShell>
	);
}

function App() {
	return (
		<Routes>
			<Route path="/login" element={<LoginPage />} />
			<Route path="/register" element={<RegisterPage />} />
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
