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
import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuthContext } from "../contexts/AuthContext";

interface RegisterFormValues {
	email: string;
	password: string;
	displayName: string;
}

export function RegisterPage() {
	const { register, isAuthenticated, isLoading } = useAuthContext();
	const [submitting, setSubmitting] = useState(false);

	const form = useForm<RegisterFormValues>({
		initialValues: { email: "", password: "", displayName: "" },
		validate: {
			email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Invalid email"),
			password: (v) => (v.length >= 8 ? null : "Password must be at least 8 characters"),
			displayName: (v) =>
				v.trim().length >= 2 ? null : "Display name must be at least 2 characters",
		},
	});

	if (!isLoading && isAuthenticated) {
		return <Navigate to="/" replace />;
	}

	const handleSubmit = async (values: RegisterFormValues) => {
		setSubmitting(true);
		try {
			await register(values.email, values.password, values.displayName);
		} catch (err) {
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
					Join DailyLoadout
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
						<Button type="submit" fullWidth loading={submitting}>
							Create account
						</Button>
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
