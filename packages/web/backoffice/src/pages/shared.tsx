import { Badge } from "@mantine/core";

/** Human-friendly relative time (e.g. "3h ago"); falls back to the date. */
export function relativeTime(iso: string): string {
	const then = new Date(iso).getTime();
	if (Number.isNaN(then)) return iso;
	const diff = Date.now() - then;
	const sec = Math.round(diff / 1000);
	if (sec < 60) return "just now";
	const min = Math.round(sec / 60);
	if (min < 60) return `${min}m ago`;
	const hr = Math.round(min / 60);
	if (hr < 24) return `${hr}h ago`;
	const day = Math.round(hr / 24);
	if (day < 30) return `${day}d ago`;
	return new Date(iso).toLocaleDateString();
}

const ACTION_META: Record<string, { color: string; label: string }> = {
	"user.ban": { color: "red", label: "Ban" },
	"user.unban": { color: "green", label: "Unban" },
	"user.verify": { color: "blue", label: "Verify" },
	"config.set": { color: "violet", label: "Config set" },
	"config.clear": { color: "gray", label: "Config clear" },
	"capture.reprocess": { color: "cyan", label: "Reprocess" },
	"capture.purge": { color: "red", label: "Purge" },
	"play_session.clamp": { color: "orange", label: "Clamp" },
};

/** Render a backoffice audit action as a colored badge. */
export function ActionLabel({ action }: { action: string }) {
	const meta = ACTION_META[action] ?? { color: "gray", label: action };
	return (
		<Badge color={meta.color} variant="light" radius="sm" size="sm">
			{meta.label}
		</Badge>
	);
}
