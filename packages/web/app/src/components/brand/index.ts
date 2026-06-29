/**
 * Brand devices (BRAND.md §9) — reusable elements that make any screen feel like
 * Slate.
 *
 * **The one-coral rule:** use a SINGLE coral focal point per screen. Coral is a
 * spotlight; more than one and nothing is lit. A `Slot lit`, the lit slot in a
 * `Lineup`, and a `Spotlight` glow all count as the coral focus — don't stack
 * them on the same screen.
 */
export { Lineup, type LineupProps } from "./Lineup";
export { RecapLabel, type RecapLabelProps } from "./RecapLabel";
export { Slot, type SlotProps } from "./Slot";
export { Spotlight, type SpotlightProps } from "./Spotlight";
