import "@testing-library/jest-dom/vitest";

// Polyfill window.matchMedia for Mantine's color scheme detection in jsdom
Object.defineProperty(window, "matchMedia", {
	writable: true,
	value: (query: string) => ({
		matches: false,
		media: query,
		onchange: null,
		addListener: () => {},
		removeListener: () => {},
		addEventListener: () => {},
		removeEventListener: () => {},
		dispatchEvent: () => false,
	}),
});

// Polyfill ResizeObserver for mantine-datatable and Textarea autosize
if (typeof globalThis.ResizeObserver === "undefined") {
	globalThis.ResizeObserver = class ResizeObserver {
		observe() {}
		unobserve() {}
		disconnect() {}
	} as unknown as typeof ResizeObserver;
}

// Polyfill document.fonts for Mantine Textarea autosize
if (typeof document !== "undefined" && !document.fonts) {
	Object.defineProperty(document, "fonts", {
		value: { ready: Promise.resolve(), addEventListener: () => {}, removeEventListener: () => {} },
	});
}

// Polyfill Element.prototype.scrollIntoView
if (typeof Element.prototype.scrollIntoView === "undefined") {
	Element.prototype.scrollIntoView = () => {};
}

// Polyfill HTMLElement.prototype.hasPointerCapture
if (typeof HTMLElement.prototype.hasPointerCapture === "undefined") {
	HTMLElement.prototype.hasPointerCapture = () => false;
}

// Polyfill HTMLElement.prototype.setPointerCapture/releasePointerCapture
if (typeof HTMLElement.prototype.setPointerCapture === "undefined") {
	HTMLElement.prototype.setPointerCapture = () => {};
}
if (typeof HTMLElement.prototype.releasePointerCapture === "undefined") {
	HTMLElement.prototype.releasePointerCapture = () => {};
}
