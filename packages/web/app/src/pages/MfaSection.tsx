import {
	Alert,
	Badge,
	Button,
	Card,
	Code,
	Group,
	List,
	Paper,
	Stack,
	Text,
	TextInput,
	Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconShieldCheck, IconShieldLock } from "@tabler/icons-react";
import { QRCodeSVG } from "qrcode.react";
import { useState } from "react";
import { useMfa } from "../hooks/useMfa";
import type { MfaEnroll } from "../types/auth";

// ---------------------------------------------------------------------------
// Two-factor (TOTP) management, rendered on the account page. Three states:
//   • disabled  → "Enable" starts enrollment (QR + confirm code).
//   • enrolling → scan the QR, confirm a code → one-time recovery codes shown.
//   • enabled   → status + a code-gated "regenerate codes" / "disable".
// The TOTP secret never persists in the UI beyond the enrollment step.
// ---------------------------------------------------------------------------

function RecoveryCodes({ codes }: { codes: string[] }) {
	return (
		<Alert color="yellow" title="Save your recovery codes" icon={<IconShieldLock size={18} />}>
			<Text size="sm" mb="xs">
				Each code works once. Store them somewhere safe — they're your way back in if you lose your
				authenticator. They won't be shown again.
			</Text>
			<Paper withBorder p="sm" radius="sm">
				<List spacing={2} listStyleType="none">
					{codes.map((code) => (
						<List.Item key={code}>
							<Code>{code}</Code>
						</List.Item>
					))}
				</List>
			</Paper>
		</Alert>
	);
}

export function MfaSection() {
	const mfa = useMfa();
	const [enrollData, setEnrollData] = useState<MfaEnroll | null>(null);
	const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);

	const confirmForm = useForm({
		initialValues: { code: "" },
		validate: { code: (v) => (v.trim().length >= 6 ? null : "Enter the 6-digit code") },
	});
	const manageForm = useForm({
		initialValues: { code: "" },
		validate: { code: (v) => (v.trim().length >= 6 ? null : "Enter a current code") },
	});

	const enabled = mfa.status?.enabled ?? false;

	const startEnroll = async () => {
		setRecoveryCodes(null);
		try {
			setEnrollData(await mfa.enroll());
		} catch (err) {
			notifications.show({
				title: "Couldn't start enrollment",
				message: err instanceof Error ? err.message : "Try again in a moment",
				color: "red",
			});
		}
	};

	const handleConfirm = async (values: { code: string }) => {
		try {
			const { recovery_codes } = await mfa.confirm(values.code.trim());
			setEnrollData(null);
			confirmForm.reset();
			setRecoveryCodes(recovery_codes);
			notifications.show({
				title: "Two-factor enabled",
				message: "MFA is now on.",
				color: "green",
			});
		} catch (err) {
			notifications.show({
				title: "Couldn't enable two-factor",
				message: err instanceof Error ? err.message : "Invalid code",
				color: "red",
			});
		}
	};

	const handleRegenerate = async () => {
		const code = manageForm.values.code.trim();
		if (manageForm.validate().hasErrors) return;
		try {
			const { recovery_codes } = await mfa.regenerate(code);
			manageForm.reset();
			setRecoveryCodes(recovery_codes);
		} catch (err) {
			notifications.show({
				title: "Couldn't regenerate codes",
				message: err instanceof Error ? err.message : "Invalid code",
				color: "red",
			});
		}
	};

	const handleDisable = async () => {
		const code = manageForm.values.code.trim();
		if (manageForm.validate().hasErrors) return;
		try {
			await mfa.disable(code);
			manageForm.reset();
			setRecoveryCodes(null);
			notifications.show({
				title: "Two-factor disabled",
				message: "MFA is now off.",
				color: "blue",
			});
		} catch (err) {
			notifications.show({
				title: "Couldn't disable two-factor",
				message: err instanceof Error ? err.message : "Invalid code",
				color: "red",
			});
		}
	};

	return (
		<Card shadow="sm" padding="xl" radius="md" maw={460}>
			<Group justify="space-between" mb="xs">
				<Title order={3}>Two-factor authentication</Title>
				<Badge
					color={enabled ? "green" : "gray"}
					leftSection={enabled ? <IconShieldCheck size={12} /> : null}
				>
					{enabled ? "On" : "Off"}
				</Badge>
			</Group>
			<Text c="dimmed" size="sm" mb="lg">
				Protect your account with a time-based code from an authenticator app.
			</Text>

			<Stack>
				{recoveryCodes && <RecoveryCodes codes={recoveryCodes} />}

				{/* Enrollment in progress: QR + confirm. */}
				{enrollData && (
					<Stack>
						<Text size="sm">
							Scan this QR in your authenticator app (or enter the key manually), then enter the
							6-digit code to finish.
						</Text>
						<Group justify="center">
							<QRCodeSVG value={enrollData.otpauth_uri} size={176} />
						</Group>
						<Text size="xs" ta="center" c="dimmed">
							Manual key: <Code>{enrollData.secret}</Code>
						</Text>
						<form onSubmit={confirmForm.onSubmit(handleConfirm)}>
							<Stack>
								<TextInput
									label="Verification code"
									placeholder="123456"
									autoFocus
									{...confirmForm.getInputProps("code")}
								/>
								<Group justify="flex-end">
									<Button variant="default" onClick={() => setEnrollData(null)}>
										Cancel
									</Button>
									<Button type="submit" loading={mfa.isConfirming}>
										Confirm
									</Button>
								</Group>
							</Stack>
						</form>
					</Stack>
				)}

				{/* Disabled and not enrolling → offer to enable. */}
				{!enabled && !enrollData && (
					<Button onClick={startEnroll} loading={mfa.isEnrolling}>
						Enable two-factor
					</Button>
				)}

				{/* Enabled → manage (regenerate codes / disable), code-gated. */}
				{enabled && !enrollData && (
					<Stack>
						<Text size="sm">
							{mfa.status?.recovery_codes_remaining ?? 0} recovery code(s) remaining.
						</Text>
						<TextInput
							label="Current code"
							description="A 6-digit code or a recovery code, required to make changes."
							placeholder="123456"
							{...manageForm.getInputProps("code")}
						/>
						<Group justify="flex-end">
							<Button variant="default" onClick={handleRegenerate} loading={mfa.isRegenerating}>
								Regenerate codes
							</Button>
							<Button color="red" onClick={handleDisable} loading={mfa.isDisabling}>
								Disable
							</Button>
						</Group>
					</Stack>
				)}
			</Stack>
		</Card>
	);
}
