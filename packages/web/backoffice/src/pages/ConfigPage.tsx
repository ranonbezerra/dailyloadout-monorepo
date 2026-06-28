import {
	ActionIcon,
	Alert,
	Badge,
	Button,
	Card,
	Center,
	Group,
	Loader,
	NumberInput,
	Stack,
	Switch,
	Text,
	Title,
	Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertTriangle, IconBolt, IconRestore } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useConfig, useConfigActions } from "../hooks/useBackoffice";
import type { ConfigEntry } from "../types/backoffice";

const CATEGORY_LABELS: Record<string, string> = {
	kill_switch: "Kill-switches",
	cap: "Abuse caps",
	product: "Product rules",
};

const CATEGORY_ORDER = ["kill_switch", "cap", "product"];

function notify(msg: string, color = "violet") {
	notifications.show({ message: msg, color });
}

export function ConfigPage() {
	const { data, isLoading, isError } = useConfig();

	if (isLoading) {
		return (
			<Center py="xl">
				<Loader color="violet" />
			</Center>
		);
	}

	if (isError || !data) {
		return (
			<Alert color="red" icon={<IconAlertTriangle size={18} />} title="Couldn't load config">
				The config endpoint failed to respond.
			</Alert>
		);
	}

	const byCategory = new Map<string, ConfigEntry[]>();
	for (const entry of data.items) {
		const list = byCategory.get(entry.category) ?? [];
		list.push(entry);
		byCategory.set(entry.category, list);
	}
	const categories = [...byCategory.keys()].sort(
		(a, b) => CATEGORY_ORDER.indexOf(a) - CATEGORY_ORDER.indexOf(b),
	);

	return (
		<Stack gap="lg">
			<div>
				<Title order={2}>Operational config</Title>
				<Text c="dimmed" size="sm">
					Curated knobs editable live — no redeploy. Precedence: override &gt; env &gt; default.
				</Text>
			</div>

			{categories.map((cat) => (
				<Stack key={cat} gap="xs">
					<Text fw={700} size="sm" tt="uppercase" c="dimmed">
						{CATEGORY_LABELS[cat] ?? cat}
					</Text>
					<Card padding={0}>
						<Stack gap={0}>
							{(byCategory.get(cat) ?? []).map((entry, idx) => (
								<ConfigRow key={entry.key} entry={entry} divider={idx > 0} />
							))}
						</Stack>
					</Card>
				</Stack>
			))}
		</Stack>
	);
}

function ConfigRow({ entry, divider }: { entry: ConfigEntry; divider: boolean }) {
	const { set, clear } = useConfigActions();
	const busy = set.isPending || clear.isPending;

	return (
		<Group
			justify="space-between"
			align="flex-start"
			wrap="nowrap"
			p="md"
			style={divider ? { borderTop: "1px solid var(--mantine-color-dark-4)" } : undefined}
		>
			<Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
				<Group gap="xs">
					<Text ff="monospace" size="sm" fw={600}>
						{entry.key}
					</Text>
					{entry.isOverridden && (
						<Badge color="violet" variant="light" radius="sm" size="xs">
							override
						</Badge>
					)}
				</Group>
				<Text size="xs" c="dimmed">
					{entry.description}
				</Text>
				<Text size="xs" c="dimmed">
					baseline: <b>{String(entry.baselineValue)}</b>
				</Text>
			</Stack>

			<Group gap="xs" wrap="nowrap">
				{entry.kind === "bool" ? (
					<Switch
						color="violet"
						checked={Boolean(entry.effectiveValue)}
						disabled={busy}
						onChange={(e) =>
							set.mutate(
								{ key: entry.key, value: e.currentTarget.checked },
								{ onSuccess: () => notify(`${entry.key} updated`) },
							)
						}
						aria-label={`Toggle ${entry.key}`}
					/>
				) : (
					<IntEditor
						entry={entry}
						busy={busy}
						onSave={(value) =>
							set.mutate(
								{ key: entry.key, value },
								{ onSuccess: () => notify(`${entry.key} updated`) },
							)
						}
					/>
				)}
				{entry.isOverridden && (
					<Tooltip label="Reset to baseline">
						<ActionIcon
							variant="subtle"
							color="gray"
							loading={clear.isPending}
							onClick={() =>
								clear.mutate(entry.key, { onSuccess: () => notify(`${entry.key} reset`) })
							}
							aria-label={`Reset ${entry.key}`}
						>
							<IconRestore size={16} />
						</ActionIcon>
					</Tooltip>
				)}
			</Group>
		</Group>
	);
}

function IntEditor({
	entry,
	busy,
	onSave,
}: {
	entry: ConfigEntry;
	busy: boolean;
	onSave: (value: number) => void;
}) {
	const [value, setValue] = useState<number | string>(Number(entry.effectiveValue));
	// Keep the field in sync when the server value changes (e.g. after a reset).
	useEffect(() => {
		setValue(Number(entry.effectiveValue));
	}, [entry.effectiveValue]);

	const num = typeof value === "number" ? value : Number(value);
	const dirty = num !== Number(entry.effectiveValue);

	return (
		<Group gap={6} wrap="nowrap">
			<NumberInput
				size="xs"
				w={120}
				value={value}
				min={entry.minValue ?? undefined}
				max={entry.maxValue ?? undefined}
				disabled={busy}
				onChange={setValue}
				aria-label={entry.key}
			/>
			<Button
				size="xs"
				variant="light"
				color="violet"
				leftSection={<IconBolt size={14} />}
				disabled={!dirty || Number.isNaN(num)}
				loading={busy}
				onClick={() => onSave(num)}
			>
				Save
			</Button>
		</Group>
	);
}
