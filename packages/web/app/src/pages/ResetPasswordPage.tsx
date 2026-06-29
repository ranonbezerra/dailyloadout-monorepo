import { Alert, Button, Card, Center, PasswordInput, Stack, Text, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconMailExclamation } from "@tabler/icons-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuthContext } from "../contexts/AuthContext";
import { validatePasswordComplexity, validatePasswordMatch } from "../lib/password";

interface ResetFormValues {
	newPassword: string;
	confirmPassword: string;
}

// ---------------------------------------------------------------------------
// /reset-password — landing page for the emailed reset link. Reads `?token=`,
// collects a new password (with confirmation), and POSTs both. On success every
// session is cut off server-side, so we send the user to /login to sign in with
// the new password. A missing/invalid token surfaces an error.
// ---------------------------------------------------------------------------

export function ResetPasswordPage() {
	const [searchParams] = useSearchParams();
	const token = searchParams.get("token");
	const { resetPassword, isResetPasswordPending } = useAuthContext();
	const navigate = useNavigate();

	const form = useForm<ResetFormValues>({
		initialValues: { newPassword: "", confirmPassword: "" },
		validate: {
			newPassword: (v) => validatePasswordComplexity(v),
			confirmPassword: (v, values) => validatePasswordMatch(values.newPassword, v),
		},
	});

	if (!token) {
		return (
			<Center h="100vh">
				<Card shadow="md" padding="xl" radius="md" w={440}>
					<Stack>
						<Title order={2} ta="center">
							Reset password
						</Title>
						<Alert color="yellow" icon={<IconMailExclamation size={18} />} title="Missing token">
							This link is missing its reset token. Request a fresh link from the forgot-password
							page.
						</Alert>
						<Button component={Link} to="/forgot-password" variant="light" fullWidth>
							Request a new link
						</Button>
					</Stack>
				</Card>
			</Center>
		);
	}

	const handleSubmit = async (values: ResetFormValues) => {
		try {
			await resetPassword(token, values.newPassword);
			notifications.show({
				title: "Password reset",
				message: "Sign in with your new password.",
				color: "green",
			});
			navigate("/login", { replace: true });
		} catch (err) {
			notifications.show({
				title: "Reset failed",
				message:
					err instanceof Error
						? err.message
						: "This reset link is invalid or has expired. Request a new one.",
				color: "red",
			});
		}
	};

	return (
		<Center h="100vh">
			<Card shadow="md" padding="xl" radius="md" w={440}>
				<Title order={2} ta="center" mb="md">
					Choose a new password
				</Title>
				<Text c="dimmed" size="sm" ta="center" mb="lg">
					Set a new password for your account.
				</Text>

				<form onSubmit={form.onSubmit(handleSubmit)}>
					<Stack>
						<PasswordInput
							label="New password"
							placeholder="Choose a new password"
							required
							{...form.getInputProps("newPassword")}
						/>
						<PasswordInput
							label="Confirm new password"
							placeholder="Repeat the new password"
							required
							{...form.getInputProps("confirmPassword")}
						/>
						<Button type="submit" fullWidth loading={isResetPasswordPending}>
							Reset password
						</Button>
					</Stack>
				</form>

				<Text ta="center" mt="md" size="sm">
					<Link to="/login">Back to sign in</Link>
				</Text>
			</Card>
		</Center>
	);
}
