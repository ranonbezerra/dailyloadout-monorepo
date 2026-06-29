import { Text, type TextProps } from "@mantine/core";
import type { ReactNode } from "react";

export interface RecapLabelProps extends TextProps {
	children: ReactNode;
}

/**
 * The recap label — "▸ PREVIOUSLY ON" (BRAND.md §8/§9). A play glyph plus an
 * uppercase, letter-spaced label in the display face. Editorial TV-recap, not a
 * code-terminal `//` comment. Use for "▸ PREVIOUSLY ON", "▸ TONIGHT'S PICK",
 * "▸ WHERE YOU LEFT OFF".
 */
export function RecapLabel({ children, style, ...rest }: RecapLabelProps) {
	return (
		<Text
			component="span"
			fw={600}
			tt="uppercase"
			c="violet.4"
			style={{
				fontFamily: "var(--mantine-font-family-headings, 'Outfit', sans-serif)",
				letterSpacing: "0.08em",
				fontSize: 12,
				...style,
			}}
			{...rest}
		>
			<span aria-hidden style={{ marginRight: 6 }}>
				▸
			</span>
			{children}
		</Text>
	);
}
