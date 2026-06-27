import { Navigate, Route, Routes } from "react-router-dom";
import { BackofficeGuard } from "../../components/backoffice/BackofficeGuard";
import { BackofficeShell } from "../../components/backoffice/BackofficeShell";
import { AuditPage } from "./AuditPage";
import { ConfigPage } from "./ConfigPage";
import { DashboardPage } from "./DashboardPage";
import { UsersPage } from "./UsersPage";

/**
 * The backoffice entry point: admin guard → distinct shell → nested admin
 * routes. Lazy-loaded as one chunk from `App`, so none of the admin code ships
 * to non-admin users until they navigate to `/backoffice`.
 */
export function BackofficeRoot() {
	return (
		<BackofficeGuard>
			<BackofficeShell>
				<Routes>
					<Route index element={<DashboardPage />} />
					<Route path="users" element={<UsersPage />} />
					<Route path="config" element={<ConfigPage />} />
					<Route path="audit" element={<AuditPage />} />
					<Route path="*" element={<Navigate to="/backoffice" replace />} />
				</Routes>
			</BackofficeShell>
		</BackofficeGuard>
	);
}

export default BackofficeRoot;
