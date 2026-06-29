import { createTheme, type MantineColorsTuple } from "@mantine/core";

/// Slate Mantine theme — "Night Den" (dark-first), coral spotlight +
/// violet secondary. Mirrors brand/BRAND.md §14.
///
/// Wired in main.tsx: <MantineProvider theme={theme} defaultColorScheme="dark">

// Hero — coral (primary)
const coral: MantineColorsTuple = [
	"#FFEDEB",
	"#FFD6D1",
	"#FFB3AB",
	"#FF8F84",
	"#FF7264",
	"#FF5A4D", // 5 — brand base
	"#F0463A",
	"#E03E2F", // 7 — pressed
	"#C0331F",
	"#9E2718",
];

// Secondary — violet
const violet: MantineColorsTuple = [
	"#F0EDFE",
	"#DCD6FB",
	"#C3BAF9",
	"#AD9FF7",
	"#9A8CF5", // 4 — brand base
	"#8576E8",
	"#6E5FD6", // 6 — deep
	"#5C4FBE",
	"#4A3F9C",
	"#392F7A",
];

// Completed / success
const green: MantineColorsTuple = [
	"#E4F6EF",
	"#C2EBDA",
	"#94DCC0",
	"#67CDA6",
	"#52C699",
	"#46C28A", // 5 — brand base
	"#37A576",
	"#2C8862",
	"#236E4F",
	"#1A543C",
];

// Neutrals — overrides Mantine's dark scheme to the Night Den surfaces.
// dark[7] = body bg, dark[6] = Paper/Card, dark[5] = hover, dark[4] = borders,
// dark[2] = muted text, dark[0] = primary text.
const dark: MantineColorsTuple = [
	"#F0EDF5", // 0 — text
	"#CFCBD9", // 1
	"#A39FB2", // 2 — muted text
	"#7E7A8C", // 3
	"#322E3F", // 4 — borders (--line)
	"#272433", // 5 — raised / hover (--surface-2)
	"#1E1C28", // 6 — cards / panels (--surface)
	"#121119", // 7 — app background (--bg)
	"#0E0D14", // 8
	"#0A0910", // 9
];

export const theme = createTheme({
	primaryColor: "coral",
	primaryShade: { light: 6, dark: 5 },
	autoContrast: true,
	luminanceThreshold: 0.45,
	white: "#F0EDF5",
	black: "#121119",
	colors: { coral, violet, green, dark },

	fontFamily: "Inter, system-ui, sans-serif",
	fontFamilyMonospace: "'JetBrains Mono', ui-monospace, monospace",
	headings: {
		fontFamily: "Outfit, system-ui, sans-serif",
		fontWeight: "700",
	},

	defaultRadius: "md",
	radius: { sm: "8px", md: "12px", lg: "16px", xl: "20px" },

	// Raw brand tokens for direct use: theme.other.coral, etc.
	other: {
		bg: "#121119",
		bg2: "#17161F",
		surface: "#1E1C28",
		surface2: "#272433",
		line: "#322E3F",
		text: "#F0EDF5",
		textMuted: "#A39FB2",
		textDim: "#6B6679",
		coral: "#FF5A4D",
		coralBright: "#FF7A6E",
		coralDeep: "#E03E2F",
		violet: "#9A8CF5",
		violetDeep: "#6E5FD6",
		green: "#46C28A",
		red: "#E5484D",
		statusBacklog: "#8A8699",
		statusPlaying: "#FF5A4D",
		statusPaused: "#9A8CF5",
		statusCompleted: "#46C28A",
		statusSetAside: "#6B6679",
	},

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
