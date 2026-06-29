import { Box, type BoxProps } from "@mantine/core";
import type { ReactNode } from "react";

export interface SlotProps extends BoxProps {
	/** Lit (coral) = the chosen pick; otherwise an outlined "waiting" slot. */
	lit?: boolean;
	/** Square edge length, in px. */
	size?: number;
	children?: ReactNode;
}

/**
 * The slot — the rounded-square brand cell (BRAND.md §9). Lit (coral) marks the
 * selected pick / active session; outlined (muted) is a waiting slot.
 */
export function Slot({ lit = false, size = 56, children, style, ...rest }: SlotProps) {
	return (
		<Box
			data-lit={lit || undefined}
			style={{
				width: size,
				height: size,
				borderRadius: 14,
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				border: lit
					? "2px solid var(--mantine-color-coral-5)"
					: "2px solid var(--mantine-color-dark-4)",
				background: lit ? "rgba(255, 90, 77, 0.13)" : "transparent",
				boxShadow: lit ? "0 0 16px rgba(255, 90, 77, 0.45)" : "none",
				transition: "border-color 150ms ease, box-shadow 150ms ease",
				...style,
			}}
			{...rest}
		>
			{children}
		</Box>
	);
}
