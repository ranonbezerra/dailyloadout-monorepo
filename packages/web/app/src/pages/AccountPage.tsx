import { Stack, Title } from "@mantine/core";
import { ChangePasswordPage } from "./ChangePasswordPage";
import { MfaSection } from "./MfaSection";

// ---------------------------------------------------------------------------
// /account — security settings: change password + two-factor authentication.
// ---------------------------------------------------------------------------

export function AccountPage() {
	return (
		<Stack gap="lg">
			<Title order={2}>Account security</Title>
			<ChangePasswordPage />
			<MfaSection />
		</Stack>
	);
}
