import { Box, type BoxProps } from "@mantine/core";
import type { ReactNode } from "react";

export interface SpotlightProps extends BoxProps {
	/** The single coral focal point per screen. Set false to dim the glow. */
	active?: boolean;
	children: ReactNode;
}

/**
 * The spotlight — a soft coral glow behind tonight's pick (BRAND.md §9). Warmth
 * and focus, used ONCE per screen, on the thing that matters. More than one and
 * nothing is lit.
 */
export function Spotlight({ active = true, children, style, ...rest }: SpotlightProps) {
	return (
		<Box pos="relative" style={style} {...rest}>
			{active && (
				<Box
					aria-hidden
					pos="absolute"
					style={{
						inset: "-20%",
						background:
							"radial-gradient(closest-side, rgba(255, 90, 77, 0.28), rgba(255, 90, 77, 0) 70%)",
						pointerEvents: "none",
						zIndex: 0,
					}}
				/>
			)}
			<Box pos="relative" style={{ zIndex: 1 }}>
				{children}
			</Box>
		</Box>
	);
}
