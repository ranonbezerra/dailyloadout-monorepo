import { Group } from "@mantine/core";
import { Slot } from "./Slot";

export interface LineupProps {
	/** Number of slots in the row. */
	count?: number;
	/** Index of the single lit slot (defaults to the middle). */
	litIndex?: number;
	size?: number;
	gap?: number;
}

/**
 * The lineup — a row of slots, one lit (BRAND.md §9): the literal picture of
 * "one chosen from many". Use for empty states, loading, splash, and the
 * pick reveal. Exactly one slot is lit (the single coral focal point).
 */
export function Lineup({ count = 5, litIndex, size = 40, gap = 10 }: LineupProps) {
	const lit = litIndex ?? Math.floor(count / 2);
	return (
		<Group gap={gap} wrap="nowrap" justify="center" aria-hidden>
			{Array.from({ length: count }, (_, i) => (
				// biome-ignore lint/suspicious/noArrayIndexKey: fixed decorative row
				<Slot key={i} lit={i === lit} size={size} />
			))}
		</Group>
	);
}
