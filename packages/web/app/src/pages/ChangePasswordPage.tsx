import { Button, Card, PasswordInput, Stack, Text, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useAuthContext } from "../contexts/AuthContext";
import { validatePasswordComplexity, validatePasswordMatch } from "../lib/password";

interface ChangeFormValues {
	currentPassword: string;
	newPassword: string;
	confirmPassword: string;
}

// ---------------------------------------------------------------------------
// /account — change the signed-in user's password. A successful change cuts off
// every other session server-side but keeps this device signed in (the API
// reissues tokens). The form clears on success.
// ---------------------------------------------------------------------------

export function ChangePasswordPage() {
	const { changePassword, isChangePasswordPending } = useAuthContext();

	const form = useForm<ChangeFormValues>({
		initialValues: { currentPassword: "", newPassword: "", confirmPassword: "" },
		validate: {
			newPassword: (v) => validatePasswordComplexity(v),
			confirmPassword: (v, values) => validatePasswordMatch(values.newPassword, v),
		},
	});

	const handleSubmit = async (values: ChangeFormValues) => {
		try {
			await changePassword(values.currentPassword, values.newPassword);
			form.reset();
			notifications.show({
				title: "Password changed",
				message: "Your password was updated and other sessions were signed out.",
				color: "green",
			});
		} catch (err) {
			notifications.show({
				title: "Couldn't change password",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	return (
		<Card shadow="sm" padding="xl" radius="md" maw={460}>
			<Title order={3} mb="xs">
				Change password
			</Title>
			<Text c="dimmed" size="sm" mb="lg">
				Changing your password signs out every other device.
			</Text>

			<form onSubmit={form.onSubmit(handleSubmit)}>
				<Stack>
					<PasswordInput
						label="Current password"
						placeholder="Your current password"
						required
						{...form.getInputProps("currentPassword")}
					/>
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
					<Button type="submit" loading={isChangePasswordPending}>
						Update password
					</Button>
				</Stack>
			</form>
		</Card>
	);
}
