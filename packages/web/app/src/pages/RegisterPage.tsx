import {
	Anchor,
	Button,
	Card,
	Center,
	PasswordInput,
	Stack,
	Text,
	TextInput,
	Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { SocialLoginButtons } from "../components/SocialLoginButtons";
import { type TurnstileHandle, TurnstileWidget } from "../components/TurnstileWidget";
import { useAuthContext } from "../contexts/AuthContext";
import { validatePasswordMatch } from "../lib/password";

interface RegisterFormValues {
	email: string;
	password: string;
	confirmPassword: string;
	displayName: string;
}

export function RegisterPage() {
	const { register, isAuthenticated, isLoading } = useAuthContext();
	const [submitting, setSubmitting] = useState(false);
	// Solved Turnstile token (null when no site key is configured or before the
	// challenge resolves). Held in a ref so it doesn't trigger re-renders.
	const turnstileTokenRef = useRef<string | null>(null);
	const turnstileRef = useRef<TurnstileHandle>(null);

	const form = useForm<RegisterFormValues>({
		initialValues: { email: "", password: "", confirmPassword: "", displayName: "" },
		validate: {
			email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Invalid email"),
			password: (v) => (v.length >= 8 ? null : "Password must be at least 8 characters"),
			confirmPassword: (v, values) => validatePasswordMatch(values.password, v),
			displayName: (v) =>
				v.trim().length >= 2 ? null : "Display name must be at least 2 characters",
		},
	});

	if (!isLoading && isAuthenticated) {
		return <Navigate to="/library" replace />;
	}

	const handleSubmit = async (values: RegisterFormValues) => {
		setSubmitting(true);
		try {
			await register(
				values.email,
				values.password,
				values.displayName,
				turnstileTokenRef.current ?? undefined,
			);
		} catch (err) {
			// Turnstile tokens are single-use — re-arm the widget so a retry gets a
			// fresh token instead of replaying a consumed one.
			turnstileTokenRef.current = null;
			turnstileRef.current?.reset();
			notifications.show({
				title: "Registration failed",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		} finally {
			setSubmitting(false);
		}
	};

	return (
		<Center h="100vh">
			<Card shadow="md" padding="xl" radius="md" w={420}>
				<Title order={2} ta="center" mb="md">
					Create an account
				</Title>
				<Text c="dimmed" size="sm" ta="center" mb="lg">
					Join Slate
				</Text>

				<form onSubmit={form.onSubmit(handleSubmit)}>
					<Stack>
						<TextInput
							label="Display name"
							placeholder="Your name"
							required
							{...form.getInputProps("displayName")}
						/>
						<TextInput
							label="Email"
							placeholder="you@example.com"
							required
							{...form.getInputProps("email")}
						/>
						<PasswordInput
							label="Password"
							placeholder="Choose a password"
							required
							{...form.getInputProps("password")}
						/>
						<PasswordInput
							label="Confirm password"
							placeholder="Repeat your password"
							required
							{...form.getInputProps("confirmPassword")}
						/>
						<TurnstileWidget
							ref={turnstileRef}
							onToken={(token) => {
								turnstileTokenRef.current = token;
							}}
						/>
						<Button type="submit" fullWidth loading={submitting}>
							Create account
						</Button>
						<SocialLoginButtons label="or sign up with" />
					</Stack>
				</form>

				<Text ta="center" mt="md" size="sm">
					Already have an account?{" "}
					<Anchor component={Link} to="/login">
						Sign in
					</Anchor>
				</Text>
			</Card>
		</Center>
	);
}
