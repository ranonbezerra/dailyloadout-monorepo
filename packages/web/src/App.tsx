import { AppShell, Button, NavLink, Stack, Text } from "@mantine/core";
import { IconBooks, IconDice3, IconHistory, IconLogout, IconSwords } from "@tabler/icons-react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { useAuthContext } from "./contexts/AuthContext";
import { CapturesPage } from "./pages/CapturesPage";
import { LibraryPage } from "./pages/LibraryPage";
import { LoadoutPage } from "./pages/LoadoutPage";
import { LoginPage } from "./pages/LoginPage";
import { MissionsPage } from "./pages/MissionsPage";
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
							label="Library"
							leftSection={<IconBooks size={18} />}
							active={location.pathname.startsWith("/library")}
							onClick={() => navigate("/library")}
						/>
						<NavLink
							label="Daily Loadout"
							leftSection={<IconDice3 size={18} />}
							active={location.pathname.startsWith("/loadout")}
							onClick={() => navigate("/loadout")}
						/>
						<NavLink
							label="Missions"
							leftSection={<IconSwords size={18} />}
							active={location.pathname.startsWith("/missions")}
							onClick={() => navigate("/missions")}
						/>
						<NavLink
							label="Capture History"
							leftSection={<IconHistory size={18} />}
							active={location.pathname.startsWith("/captures")}
							onClick={() => navigate("/captures")}
						/>
					</Stack>
					<Button
						variant="subtle"
						color="gray"
						leftSection={<IconLogout size={16} />}
						onClick={() => logout()}
						justify="flex-start"
					>
						Sign out
					</Button>
				</Stack>
			</AppShell.Navbar>

			<AppShell.Main>
				<Routes>
					<Route path="/library" element={<LibraryPage />} />
					<Route path="/loadout" element={<LoadoutPage />} />
					<Route path="/missions" element={<MissionsPage />} />
					<Route path="/captures" element={<CapturesPage />} />
					<Route path="*" element={<Navigate to="/library" replace />} />
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
