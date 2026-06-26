import {
	ActionIcon,
	Box,
	Button,
	Card,
	Group,
	Paper,
	ScrollArea,
	Stack,
	Text,
	TextInput,
	Title,
} from "@mantine/core";
import {
	IconPlayerPlay,
	IconPlayerStop,
	IconSearch,
	IconSend,
	IconSparkles,
} from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useConcierge } from "../hooks/useConcierge";
import { useLibraryEntry } from "../hooks/useLibrary";
import type { ChatMessage } from "../types/concierge";
import { MissionBriefingModal } from "./MissionBriefingModal";

const TYPING_DOTS = ["dot-0", "dot-1", "dot-2"];

// Friendly labels for the tool affordance shown while the agent works.
const TOOL_LABELS: Record<string, string> = {
	search_library: "searching your library",
	get_mission_history: "recalling your last session",
	get_play_stats: "checking your stats",
	estimate_session_fit: "sizing up the session",
	start_mission: "starting your mission",
	generate_briefing: "writing a briefing",
	submit_retroactive_debrief: "logging your session",
	set_status: "updating your library",
};

function TypingDots() {
	return (
		<Group gap={5} py={4} aria-label="Concierge is thinking">
			{TYPING_DOTS.map((id, i) => (
				<Box
					key={id}
					w={7}
					h={7}
					style={{
						borderRadius: "50%",
						backgroundColor: "var(--mantine-color-gray-5)",
						animation: "conciergeBlink 1.2s infinite ease-in-out",
						animationDelay: `${i * 0.16}s`,
					}}
				/>
			))}
		</Group>
	);
}

function MessageBubble({ message, onPlay }: { message: ChatMessage; onPlay: () => void }) {
	const isUser = message.role === "user";
	const isPending = message.role === "assistant" && message.text === "" && !message.recommendation;
	return (
		<Group justify={isUser ? "flex-end" : "flex-start"} align="flex-start" wrap="nowrap">
			<Card withBorder radius="lg" py="xs" px="md" maw="80%" bg={isUser ? "blue.9" : undefined}>
				{isPending ? (
					<TypingDots />
				) : (
					<Stack gap="xs">
						{message.text && (
							<Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
								{message.text}
							</Text>
						)}
						{message.recommendation && (
							<Button
								size="xs"
								radius="md"
								leftSection={<IconPlayerPlay size={14} />}
								onClick={onPlay}
							>
								Play {message.recommendation.title}
							</Button>
						)}
					</Stack>
				)}
			</Card>
		</Group>
	);
}

export function ConciergePage() {
	// Errors surface inline as an assistant bubble (see useConcierge); we
	// deliberately don't also render a separate banner to avoid showing the
	// same failure twice.
	const { messages, isStreaming, activeTool, send, cancel } = useConcierge();
	const [input, setInput] = useState("");
	// The recommended library entry the user tapped "Play" on — opens the
	// briefing-choice dialog once the full entry loads.
	const [playEntryId, setPlayEntryId] = useState<string | null>(null);
	const { data: playEntry } = useLibraryEntry(playEntryId);
	const navigate = useNavigate();
	const viewport = useRef<HTMLDivElement>(null);

	// Keep the latest message in view as the reply streams in. `messages` is the
	// intended trigger even though the body only reads the viewport ref.
	// biome-ignore lint/correctness/useExhaustiveDependencies: scroll on new messages
	useEffect(() => {
		viewport.current?.scrollTo?.({ top: viewport.current.scrollHeight, behavior: "smooth" });
	}, [messages]);

	const submit = () => {
		const text = input.trim();
		if (!text || isStreaming) return;
		setInput("");
		void send(text);
	};

	return (
		<Stack h="calc(100vh - 32px)" gap="md">
			<div>
				<Title order={2}>Backlog Concierge</Title>
				<Text c="dimmed" size="sm">
					Ask what to play — grounded in your library, sessions, and the time you have.
				</Text>
			</div>

			<ScrollArea style={{ flex: 1 }} viewportRef={viewport} type="auto">
				<Stack gap="sm" p="xs">
					{messages.length === 0 && (
						<Paper withBorder radius="lg" p="xl">
							<Stack align="center" gap="xs">
								<IconSparkles size={28} />
								<Text fw={600}>What should you play tonight?</Text>
								<Text c="dimmed" size="sm" ta="center">
									Try “I have 30 minutes and want something chill” or “What was I doing in my last
									RPG?”
								</Text>
							</Stack>
						</Paper>
					)}
					{messages.map((message, i) => (
						<MessageBubble
							// Order-stable, append-only chat log — index key is safe here.
							// biome-ignore lint/suspicious/noArrayIndexKey: append-only chat log
							key={i}
							message={message}
							onPlay={() => setPlayEntryId(message.recommendation?.id ?? null)}
						/>
					))}
					{activeTool && (
						<Group gap={6} c="dimmed" px="xs" aria-label="Concierge tool activity">
							<IconSearch size={14} />
							<Text size="xs">{TOOL_LABELS[activeTool] ?? activeTool}…</Text>
						</Group>
					)}
				</Stack>
			</ScrollArea>

			<Box>
				<TextInput
					placeholder="Ask the concierge…"
					value={input}
					onChange={(e) => setInput(e.currentTarget.value)}
					onKeyDown={(e) => {
						if (e.key === "Enter" && !e.shiftKey) {
							e.preventDefault();
							submit();
						}
					}}
					disabled={isStreaming}
					rightSection={
						isStreaming ? (
							<ActionIcon
								variant="subtle"
								color="red"
								onClick={cancel}
								aria-label="Stop generating"
							>
								<IconPlayerStop size={18} />
							</ActionIcon>
						) : (
							<ActionIcon
								variant="subtle"
								onClick={submit}
								disabled={!input.trim()}
								aria-label="Send message"
							>
								<IconSend size={18} />
							</ActionIcon>
						)
					}
				/>
			</Box>

			{playEntryId && playEntry && (
				<MissionBriefingModal
					mode="preview"
					libraryEntry={playEntry}
					libraryEntryPublicId={playEntryId}
					onConfirm={() => {
						setPlayEntryId(null);
						navigate("/play"); // land on the now-active mission
					}}
					onClose={() => setPlayEntryId(null)}
				/>
			)}
		</Stack>
	);
}
