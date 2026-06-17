import { AppShell, Text, Title } from "@mantine/core";
import { Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";

function Dashboard() {
	return (
		<AppShell navbar={{ width: 250, breakpoint: "sm" }} padding="md">
			<AppShell.Navbar p="md">
				<Text fw={700}>Navigation</Text>
			</AppShell.Navbar>

			<AppShell.Main>
				<Title order={1}>DailyLoadout</Title>
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
						<Dashboard />
					</ProtectedRoute>
				}
			/>
		</Routes>
	);
}

export default App;
