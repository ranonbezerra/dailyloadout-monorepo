import { Alert, Anchor, Button, Card, Center, Stack, Text, TextInput, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconMailCheck } from "@tabler/icons-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuthContext } from "../contexts/AuthContext";

interface ForgotFormValues {
	email: string;
}

// ---------------------------------------------------------------------------
// /forgot-password — request a reset link. The response is intentionally
// neutral (the server never reveals whether the account exists), so the UI
// always shows the same "check your inbox" confirmation after a submit.
// ---------------------------------------------------------------------------

export function ForgotPasswordPage() {
	const { forgotPassword, isForgotPasswordPending } = useAuthContext();
	const [sent, setSent] = useState(false);

	const form = useForm<ForgotFormValues>({
		initialValues: { email: "" },
		validate: {
			email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Invalid email"),
		},
	});

	const handleSubmit = async (values: ForgotFormValues) => {
		// Neutral by design: even on a network/validation hiccup the server path is
		// the oracle-free one, so we flip to the confirmation regardless of outcome
		// and never surface an error that could hint at account state.
		try {
			await forgotPassword(values.email);
		} catch {
			// Swallow — the confirmation is identical whether or not it succeeded.
		} finally {
			setSent(true);
		}
	};

	return (
		<Center h="100vh">
			<Card shadow="md" padding="xl" radius="md" w={420}>
				<Title order={2} ta="center" mb="md">
					Forgot your password?
				</Title>
				<Text c="dimmed" size="sm" ta="center" mb="lg">
					Enter your email and we'll send you a reset link.
				</Text>

				{sent ? (
					<Stack>
						<Alert color="green" icon={<IconMailCheck size={18} />} title="Check your inbox">
							If an account exists for that email, a password-reset link is on its way. The link
							expires shortly, so use it soon.
						</Alert>
						<Button component={Link} to="/login" variant="light" fullWidth>
							Back to sign in
						</Button>
					</Stack>
				) : (
					<form onSubmit={form.onSubmit(handleSubmit)}>
						<Stack>
							<TextInput
								label="Email"
								placeholder="you@example.com"
								required
								{...form.getInputProps("email")}
							/>
							<Button type="submit" fullWidth loading={isForgotPasswordPending}>
								Send reset link
							</Button>
						</Stack>
					</form>
				)}

				<Text ta="center" mt="md" size="sm">
					Remembered it?{" "}
					<Anchor component={Link} to="/login">
						Sign in
					</Anchor>
				</Text>
			</Card>
		</Center>
	);
}
