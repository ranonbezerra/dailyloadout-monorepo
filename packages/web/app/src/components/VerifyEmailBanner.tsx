import { Alert, Button, Group } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconMailExclamation } from "@tabler/icons-react";
import { useState } from "react";
import { useAuthContext } from "../contexts/AuthContext";

// Session-scoped dismissal: re-shows on a fresh tab/reload but stays hidden for
// the rest of this session once dismissed.
const DISMISS_KEY = "slate.verifyEmailBanner.dismissed";

function wasDismissed(): boolean {
	try {
		return sessionStorage.getItem(DISMISS_KEY) === "1";
	} catch {
		return false;
	}
}

// ---------------------------------------------------------------------------
// "Verify your email" banner.
//
// Shown in the AppShell when the user is authenticated AND not yet verified.
// Explains that AI features stay locked until they verify and offers a Resend
// action. Dismissible per session. In dev the server auto-verifies, so this
// won't appear locally — that's expected.
// ---------------------------------------------------------------------------

export function VerifyEmailBanner() {
	const { isAuthenticated, emailVerified, resendVerification, isResendPending } = useAuthContext();
	const [dismissed, setDismissed] = useState(wasDismissed);

	if (!isAuthenticated || emailVerified || dismissed) return null;

	const handleDismiss = () => {
		try {
			sessionStorage.setItem(DISMISS_KEY, "1");
		} catch {
			// sessionStorage unavailable — dismiss in-memory only for this mount.
		}
		setDismissed(true);
	};

	const handleResend = async () => {
		try {
			await resendVerification();
			notifications.show({
				title: "Verification email sent",
				message: "Check your inbox for a fresh verification link.",
				color: "green",
			});
		} catch {
			notifications.show({
				title: "Couldn't resend",
				message: "Please try again in a moment.",
				color: "red",
			});
		}
	};

	return (
		<Alert
			color="yellow"
			icon={<IconMailExclamation size={18} />}
			title="Verify your email"
			withCloseButton
			onClose={handleDismiss}
			closeButtonLabel="Dismiss"
			mb="md"
			data-testid="verify-email-banner"
		>
			<Group justify="space-between" wrap="nowrap" gap="md">
				<span>
					Verify your email to unlock AI features (picks, recaps, and the concierge). Check your
					inbox for the verification link.
				</span>
				<Button
					size="xs"
					variant="white"
					color="yellow"
					loading={isResendPending}
					onClick={handleResend}
				>
					Resend verification
				</Button>
			</Group>
		</Alert>
	);
}
