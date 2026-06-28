import {
	Badge,
	Button,
	Card,
	Center,
	Group,
	PasswordInput,
	Stack,
	Text,
	TextInput,
	Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconShieldLock } from "@tabler/icons-react";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuthContext } from "../contexts/AuthContext";

interface LoginFormValues {
	email: string;
	password: string;
}

export function LoginPage() {
	const { login, isAuthenticated, isLoading } = useAuthContext();
	const [submitting, setSubmitting] = useState(false);

	const form = useForm<LoginFormValues>({
		initialValues: { email: "", password: "" },
		validate: {
			email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Invalid email"),
			password: (v) => (v.length >= 6 ? null : "Password must be at least 6 characters"),
		},
	});

	if (!isLoading && isAuthenticated) {
		return <Navigate to="/" replace />;
	}

	const handleSubmit = async (values: LoginFormValues) => {
		setSubmitting(true);
		try {
			await login(values.email, values.password);
		} catch (err) {
			notifications.show({
				title: "Sign-in failed",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		} finally {
			setSubmitting(false);
		}
	};

	return (
		<Center h="100vh" px="md">
			<Card shadow="md" padding="xl" radius="md" w={420}>
				<Group justify="center" gap="xs" mb="xs">
					<IconShieldLock size={26} color="var(--mantine-color-violet-4)" />
					<Title order={3} ff="monospace" style={{ letterSpacing: "0.04em" }}>
						BACKOFFICE
					</Title>
					<Badge color="violet" variant="light" size="xs" radius="sm">
						INTERNAL
					</Badge>
				</Group>
				<Text c="dimmed" size="sm" ta="center" mb="lg">
					Sign in with an admin account
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
						<Button type="submit" color="violet" fullWidth loading={submitting}>
							Sign in
						</Button>
					</Stack>
				</form>
			</Card>
		</Center>
	);
}
