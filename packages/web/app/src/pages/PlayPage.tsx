import {
	Badge,
	Button,
	Card,
	Group,
	SimpleGrid,
	Stack,
	Text,
	Title,
	Tooltip,
	UnstyledButton,
} from "@mantine/core";
import {
	IconBook,
	IconDice3,
	IconFlagCheck,
	IconHandClick,
	IconMessageChatbot,
} from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useActiveMission } from "../hooks/useMission";
import { FEATURES } from "../lib/features";
import { MissionBriefingModal } from "./MissionBriefingModal";
import { MissionDebriefModal } from "./MissionDebriefModal";

interface DoorCardProps {
	title: string;
	subtitle: string;
	icon: React.ReactNode;
	accent?: boolean;
	disabled?: boolean;
	onClick: () => void;
}

const DISABLED_REASON = "Finish your active mission first";

function DoorCard({ title, subtitle, icon, accent, disabled, onClick }: DoorCardProps) {
	// Render as a real <button> (UnstyledButton) so the door is keyboard
	// focusable and fires on Enter/Space natively; the Card inside is purely
	// visual. For the disabled state we use aria-disabled (not the native
	// `disabled` attribute) so the element stays focusable/hoverable and its
	// Tooltip reason remains reachable by both keyboard and pointer.
	const card = (
		<UnstyledButton
			onClick={disabled ? undefined : onClick}
			aria-disabled={disabled}
			aria-label={disabled ? `${title} — ${DISABLED_REASON}` : title}
			style={{
				cursor: disabled ? "not-allowed" : "pointer",
				height: "100%",
				width: "100%",
				display: "block",
				textAlign: "left",
			}}
		>
			<Card
				withBorder
				p="lg"
				radius="md"
				h="100%"
				style={{ opacity: disabled ? 0.55 : 1 }}
				bg={accent && !disabled ? "var(--mantine-primary-color-light)" : undefined}
			>
				<Stack gap="sm" align="flex-start">
					{icon}
					<Title order={4}>{title}</Title>
					<Text size="sm" c="dimmed">
						{subtitle}
					</Text>
				</Stack>
			</Card>
		</UnstyledButton>
	);

	if (disabled) {
		return (
			<Tooltip label={DISABLED_REASON} withArrow>
				{card}
			</Tooltip>
		);
	}
	return card;
}

export function PlayPage() {
	const navigate = useNavigate();
	const { data: activeMission } = useActiveMission();
	const [showBriefing, setShowBriefing] = useState(false);
	const [showDebrief, setShowDebrief] = useState(false);
	const hasActiveMission = Boolean(activeMission);

	return (
		<Stack maw={720} mx="auto" mt="md">
			<Title order={2}>Play</Title>
			<Text c="dimmed" size="sm">
				Pick how you want to start your session.
			</Text>

			{activeMission ? (
				<Card withBorder p="lg" radius="md">
					<Stack gap="md">
						<Group gap="sm">
							<Badge color="teal" variant="dot" size="lg">
								Mission active
							</Badge>
							<Title order={3}>{activeMission.libraryEntry.game.title}</Title>
						</Group>

						{activeMission.briefingText && (
							<Card withBorder p="sm" radius="sm">
								<Text size="sm" c="dimmed" lineClamp={3}>
									{activeMission.briefingText}
								</Text>
							</Card>
						)}

						<Group>
							<Button
								leftSection={<IconBook size={18} />}
								variant="light"
								onClick={() => setShowBriefing(true)}
							>
								Briefing
							</Button>
							<Button
								leftSection={<IconFlagCheck size={18} />}
								color="teal"
								onClick={() => setShowDebrief(true)}
							>
								End / Debrief
							</Button>
						</Group>
					</Stack>
				</Card>
			) : (
				<Card withBorder p="lg" radius="md">
					<Text c="dimmed" ta="center" py="sm">
						No active mission. Choose a door below to get rolling.
					</Text>
				</Card>
			)}

			<SimpleGrid cols={{ base: 1, sm: FEATURES.backlogConcierge ? 3 : 2 }} mt="sm">
				<DoorCard
					title="What's the move?"
					subtitle="One tap — we pick, you play."
					icon={<IconDice3 size={28} />}
					accent
					disabled={hasActiveMission}
					onClick={() => navigate("/play/loadout")}
				/>
				<DoorCard
					title="I'll choose"
					subtitle="Pick a game yourself."
					icon={<IconHandClick size={28} />}
					disabled={hasActiveMission}
					onClick={() => navigate("/library")}
				/>
				{FEATURES.backlogConcierge && (
					<DoorCard
						title="Ask"
						subtitle="Chat about what to play."
						icon={<IconMessageChatbot size={28} />}
						onClick={() => navigate("/play/concierge")}
					/>
				)}
			</SimpleGrid>

			{showBriefing && activeMission && (
				<MissionBriefingModal
					mode="view"
					mission={activeMission}
					onClose={() => setShowBriefing(false)}
				/>
			)}
			<MissionDebriefModal
				mission={showDebrief ? (activeMission ?? null) : null}
				onClose={() => setShowDebrief(false)}
			/>
		</Stack>
	);
}
