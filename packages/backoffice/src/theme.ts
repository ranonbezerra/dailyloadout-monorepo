import { createTheme, type MantineColorsTuple } from "@mantine/core";

/// Backoffice Mantine theme — the dark "Night Den" surfaces shared with the
/// player app, but a VIOLET primary (the app uses coral) so the admin tool reads
/// as a distinct, internal product at a glance.

// Primary — violet
const violet: MantineColorsTuple = [
	"#F0EDFE",
	"#DCD6FB",
	"#C3BAF9",
	"#AD9FF7",
	"#9A8CF5",
	"#8576E8", // 5
	"#6E5FD6", // 6 — deep
	"#5C4FBE",
	"#4A3F9C",
	"#392F7A",
];

// Neutrals — the Night Den surfaces (same as the app, for visual kinship).
const dark: MantineColorsTuple = [
	"#F0EDF5", // 0 — text
	"#CFCBD9",
	"#A39FB2", // 2 — muted text
	"#7E7A8C",
	"#322E3F", // 4 — borders
	"#272433", // 5 — raised / hover
	"#1E1C28", // 6 — cards / panels
	"#121119", // 7 — app background
	"#0E0D14", // 8
	"#0A0910", // 9
];

export const theme = createTheme({
	primaryColor: "violet",
	primaryShade: { light: 6, dark: 5 },
	autoContrast: true,
	luminanceThreshold: 0.45,
	white: "#F0EDF5",
	black: "#121119",
	colors: { violet, dark },

	fontFamily: "Inter, system-ui, sans-serif",
	fontFamilyMonospace: "'JetBrains Mono', ui-monospace, monospace",
	headings: {
		fontFamily: "Outfit, system-ui, sans-serif",
		fontWeight: "700",
	},

	defaultRadius: "md",
	radius: { sm: "8px", md: "12px", lg: "16px", xl: "20px" },

	components: {
		Button: {
			defaultProps: { radius: "md" },
			styles: { label: { fontFamily: "Outfit, system-ui, sans-serif", fontWeight: 700 } },
		},
		Card: { defaultProps: { radius: "lg", withBorder: true } },
		Paper: { defaultProps: { radius: "lg" } },
		Badge: { defaultProps: { radius: "sm" } },
	},
});
