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
import { ApiError } from "@slate/shared/api";
import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { SocialLoginButtons } from "../components/SocialLoginButtons";
import { type TurnstileHandle, TurnstileWidget } from "../components/TurnstileWidget";
import { useAuthContext } from "../contexts/AuthContext";
import { oauthErrorMessage } from "../lib/oauth";

/** The server flags step-up with a 403 whose detail mentions CAPTCHA. */
function isCaptchaRequired(err: unknown): boolean {
	return err instanceof ApiError && err.status === 403 && /captcha/i.test(err.message);
}

interface LoginFormValues {
	email: string;
	password: string;
}

export function LoginPage() {
	const { login, completeMfaLogin, isMfaLoginPending, isAuthenticated, isLoading } =
		useAuthContext();
	const [submitting, setSubmitting] = useState(false);
	// Holds the short-lived challenge token once the password step reports that a
	// second factor is required; presence of it switches the card to the code step.
	const [mfaToken, setMfaToken] = useState<string | null>(null);
	// Flipped once the server demands a CAPTCHA (after repeated failures); it
	// reveals the Turnstile widget whose solved token is sent on the next submit.
	const [captchaRequired, setCaptchaRequired] = useState(false);
	const turnstileTokenRef = useRef<string | null>(null);
	const turnstileRef = useRef<TurnstileHandle>(null);
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

	const mfaForm = useForm<{ code: string }>({
		initialValues: { code: "" },
		validate: { code: (v) => (v.trim().length >= 6 ? null : "Enter your 6-digit code") },
	});

	if (!isLoading && isAuthenticated) {
		return <Navigate to="/library" replace />;
	}

	const handleSubmit = async (values: LoginFormValues) => {
		setSubmitting(true);
		try {
			const result = await login(
				values.email,
				values.password,
				turnstileTokenRef.current ?? undefined,
			);
			if (result?.mfaRequired) {
				setMfaToken(result.mfaToken);
			}
		} catch (err) {
			// Turnstile tokens are single-use — re-arm the widget so a retry sends a
			// fresh token instead of replaying a consumed one.
			turnstileTokenRef.current = null;
			turnstileRef.current?.reset();
			if (isCaptchaRequired(err)) {
				setCaptchaRequired(true);
				notifications.show({
					title: "Verification required",
					message: "Please complete the challenge below and sign in again.",
					color: "yellow",
				});
			} else {
				notifications.show({
					title: "Login failed",
					message: err instanceof Error ? err.message : "An unexpected error occurred",
					color: "red",
				});
			}
		} finally {
			setSubmitting(false);
		}
	};

	const handleMfaSubmit = async (values: { code: string }) => {
		if (!mfaToken) return;
		try {
			await completeMfaLogin(mfaToken, values.code.trim());
		} catch (err) {
			notifications.show({
				title: "Verification failed",
				message: err instanceof Error ? err.message : "Invalid or expired code",
				color: "red",
			});
		}
	};

	return (
		<Center h="100vh">
			<Card shadow="md" padding="xl" radius="md" w={420}>
				<Title order={2} ta="center" mb="md">
					Welcome back
				</Title>
				<Text c="dimmed" size="sm" ta="center" mb="lg">
					{mfaToken ? "Enter your two-factor code" : "Sign in to Slate"}
				</Text>

				{mfaToken ? (
					<form onSubmit={mfaForm.onSubmit(handleMfaSubmit)}>
						<Stack>
							<TextInput
								label="Authentication code"
								placeholder="123456 or a recovery code"
								autoFocus
								required
								{...mfaForm.getInputProps("code")}
							/>
							<Button type="submit" fullWidth loading={isMfaLoginPending}>
								Verify
							</Button>
							<Anchor
								component="button"
								type="button"
								size="sm"
								ta="center"
								onClick={() => setMfaToken(null)}
							>
								Back to sign in
							</Anchor>
						</Stack>
					</form>
				) : (
					<>
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
								<Anchor component={Link} to="/forgot-password" size="sm" ta="right">
									Forgot password?
								</Anchor>
								{captchaRequired && (
									<TurnstileWidget
										ref={turnstileRef}
										onToken={(token) => {
											turnstileTokenRef.current = token;
										}}
									/>
								)}
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
					</>
				)}
			</Card>
		</Center>
	);
}
