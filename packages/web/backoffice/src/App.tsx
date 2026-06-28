import { Navigate, Route, Routes } from "react-router-dom";
import { BackofficeGuard } from "./components/BackofficeGuard";
import { BackofficeShell } from "./components/BackofficeShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuditPage } from "./pages/AuditPage";
import { CapturesPage } from "./pages/CapturesPage";
import { ConfigPage } from "./pages/ConfigPage";
import { DashboardPage } from "./pages/DashboardPage";
import { GamesPage } from "./pages/GamesPage";
import { LoginPage } from "./pages/LoginPage";
import { MissionsPage } from "./pages/MissionsPage";
import { UsersPage } from "./pages/UsersPage";

/** Authenticated + admin-gated area, wrapped in the distinct backoffice shell. */
function BackofficeApp() {
	return (
		<BackofficeGuard>
			<BackofficeShell>
				<Routes>
					<Route index element={<DashboardPage />} />
					<Route path="users" element={<UsersPage />} />
					<Route path="games" element={<GamesPage />} />
					<Route path="captures" element={<CapturesPage />} />
					<Route path="missions" element={<MissionsPage />} />
					<Route path="config" element={<ConfigPage />} />
					<Route path="audit" element={<AuditPage />} />
					<Route path="*" element={<Navigate to="/" replace />} />
				</Routes>
			</BackofficeShell>
		</BackofficeGuard>
	);
}

export default function App() {
	return (
		<Routes>
			<Route path="/login" element={<LoginPage />} />
			<Route
				path="/*"
				element={
					<ProtectedRoute>
						<BackofficeApp />
					</ProtectedRoute>
				}
			/>
		</Routes>
	);
}
