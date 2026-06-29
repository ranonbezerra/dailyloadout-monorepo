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
import { useEffect, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { SocialLoginButtons } from "../components/SocialLoginButtons";
import { useAuthContext } from "../contexts/AuthContext";
import { oauthErrorMessage } from "../lib/oauth";

interface LoginFormValues {
	email: string;
	password: string;
}

export function LoginPage() {
	const { login, isAuthenticated, isLoading } = useAuthContext();
	const [submitting, setSubmitting] = useState(false);
	const [searchParams, setSearchParams] = useSearchParams();

	// A failed social-login flow redirects the browser back here with an
	// `?error=<reason>` param. Surface a human message once, then clear the param
	// so a reload/back-nav doesn't re-toast.
	useEffect(() => {
		const error = searchParams.get("error");
		if (!error) return;
		notifications.show({
			title: "Sign-in failed",
			message: oauthErrorMessage(error),
			color: "red",
		});
		setSearchParams({}, { replace: true });
	}, [searchParams, setSearchParams]);

	const form = useForm<LoginFormValues>({
		initialValues: { email: "", password: "" },
		validate: {
			email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Invalid email"),
			password: (v) => (v.length >= 6 ? null : "Password must be at least 6 characters"),
		},
	});

	if (!isLoading && isAuthenticated) {
		return <Navigate to="/library" replace />;
	}

	const handleSubmit = async (values: LoginFormValues) => {
		setSubmitting(true);
		try {
			await login(values.email, values.password);
		} catch (err) {
			notifications.show({
				title: "Login failed",
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
					Welcome back
				</Title>
				<Text c="dimmed" size="sm" ta="center" mb="lg">
					Sign in to Slate
				</Text>

				<form onSubmit={form.onSubmit(handleSubmit)}>
					<Stack>
						<TextInput
							label="Email"
							placeholder="you@example.com"
							required
							{...form.getInputProps("email")}
						/>
						<PasswordInput
							label="Password"
							placeholder="Your password"
							required
							{...form.getInputProps("password")}
						/>
						<Button type="submit" fullWidth loading={submitting}>
							Sign in
						</Button>
						<SocialLoginButtons />
					</Stack>
				</form>

				<Text ta="center" mt="md" size="sm">
					Don&apos;t have an account?{" "}
					<Anchor component={Link} to="/register">
						Register
					</Anchor>
				</Text>
			</Card>
		</Center>
	);
}
