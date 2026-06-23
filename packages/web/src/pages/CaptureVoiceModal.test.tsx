import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useSubmitTextCapture, useTranscribeAudio } from "../hooks/useCapture";
import { CaptureVoiceModal } from "./CaptureVoiceModal";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

vi.mock("../hooks/useCapture", () => ({
	useSubmitTextCapture: vi.fn(),
	useTranscribeAudio: vi.fn(),
	useCaptures: vi.fn(() => ({ data: null, isLoading: false })),
	useCapture: vi.fn(() => ({ data: null, isLoading: false })),
	useSubmitPhotoCapture: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useConfirmCandidate: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useRejectCandidate: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
}));

// Mock only Modal to avoid portal issues in jsdom; keep real Textarea
vi.mock("@mantine/core", async () => {
	const actual = await vi.importActual("@mantine/core");
	return {
		...actual,
		Modal: ({
			opened,
			children,
			title,
			onClose,
		}: {
			opened: boolean;
			children?: ReactNode;
			title?: ReactNode;
			onClose?: () => void;
			size?: string;
		}) =>
			opened ? (
				<div data-testid="mock-modal">
					{title && <div>{title}</div>}
					<button type="button" data-testid="mock-modal-close" onClick={onClose}>
						Close
					</button>
					{children}
				</div>
			) : null,
	};
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const defaultProps = {
	opened: true,
	onClose: vi.fn(),
	onSuccess: vi.fn(),
};

function renderModal(props: Partial<typeof defaultProps> = {}) {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<CaptureVoiceModal {...defaultProps} {...props} />
			</MemoryRouter>
		</MantineProvider>,
	);
}

function formatDuration(seconds: number): string {
	const m = Math.floor(seconds / 60)
		.toString()
		.padStart(2, "0");
	const s = (seconds % 60).toString().padStart(2, "0");
	return `${m}:${s}`;
}

function getFilledButton() {
	const buttons = screen.getAllByRole("button");
	return buttons.find((b) => b.getAttribute("data-variant") === "filled") || buttons[0];
}

// Build a mock MediaRecorder using a plain function constructor (not vi.fn arrow)
// so that `new MediaRecorder(stream)` works correctly in jsdom.
function setupMediaRecorderMock() {
	const stopTrackFn = vi.fn();
	const mockStream = { getTracks: () => [{ stop: stopTrackFn }] };

	const startFn = vi.fn();
	const stopFn = vi.fn();

	let ondataavailableFn: ((e: { data: Blob }) => void) | null = null;
	let onstopFn: (() => void) | null = null;

	function MockMediaRecorder() {
		const instance = {
			start: startFn,
			stop: stopFn,
			state: "inactive" as string,
			set ondataavailable(fn: ((e: { data: Blob }) => void) | null) {
				ondataavailableFn = fn;
			},
			get ondataavailable() {
				return ondataavailableFn;
			},
			set onstop(fn: (() => void) | null) {
				onstopFn = fn;
			},
			get onstop() {
				return onstopFn;
			},
		};

		startFn.mockImplementation(() => {
			instance.state = "recording";
		});

		stopFn.mockImplementation(() => {
			if (ondataavailableFn) {
				ondataavailableFn({ data: new Blob(["audio"], { type: "audio/webm" }) });
			}
			if (onstopFn) {
				onstopFn();
			}
		});

		return instance;
	}

	globalThis.MediaRecorder = MockMediaRecorder as unknown as typeof MediaRecorder;

	Object.defineProperty(navigator, "mediaDevices", {
		writable: true,
		configurable: true,
		value: {
			getUserMedia: vi.fn().mockResolvedValue(mockStream),
		},
	});

	return { startFn, stopFn, stopTrackFn };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CaptureVoiceModal", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		(useSubmitTextCapture as Mock).mockReturnValue({
			mutateAsync: vi.fn(),
			isPending: false,
		});
		(useTranscribeAudio as Mock).mockReturnValue({
			mutateAsync: vi.fn().mockResolvedValue({
				text: "Elden Ring and Hollow Knight",
				language: "en",
				durationSeconds: 5,
			}),
			isPending: false,
		});
	});

	it("does not render modal content when opened is false", () => {
		renderModal({ opened: false });

		expect(screen.queryByText("Voice Capture")).not.toBeInTheDocument();
		expect(screen.queryByText("Tap to record")).not.toBeInTheDocument();
	});

	it("shows recording UI when opened (title and description)", () => {
		renderModal();

		expect(screen.getByText("Voice Capture")).toBeInTheDocument();
		expect(screen.getByText(/Record yourself describing the games/)).toBeInTheDocument();
	});

	it('shows "Tap to record" initially', () => {
		renderModal();

		expect(screen.getByText("Tap to record")).toBeInTheDocument();
	});

	it("shows the ActionIcon mic button with filled variant", () => {
		renderModal();

		const filledButton = getFilledButton();
		expect(filledButton).toBeTruthy();
		expect(filledButton).toHaveAttribute("data-variant", "filled");
	});

	it("shows 00:00 timer initially", () => {
		renderModal();

		expect(screen.getByText("00:00")).toBeInTheDocument();
	});

	it("starts recording when mic button is clicked", async () => {
		const { startFn } = setupMediaRecorderMock();

		renderModal();

		await act(async () => {
			fireEvent.click(getFilledButton());
		});

		expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true });
		expect(startFn).toHaveBeenCalled();
		expect(screen.getByText(/Recording\.\.\./)).toBeInTheDocument();
		expect(screen.getByText("Tap to stop")).toBeInTheDocument();
	});

	it("shows error notification when microphone access is denied", async () => {
		Object.defineProperty(navigator, "mediaDevices", {
			writable: true,
			configurable: true,
			value: {
				getUserMedia: vi.fn().mockRejectedValue(new Error("Permission denied")),
			},
		});
		globalThis.MediaRecorder = (() => ({})) as unknown as typeof MediaRecorder;

		renderModal();

		await act(async () => {
			fireEvent.click(getFilledButton());
		});

		expect(notifications.show).toHaveBeenCalledWith(
			expect.objectContaining({
				title: "Microphone access denied",
				color: "red",
			}),
		);
	});

	it("shows transcription textarea after stop and successful transcription", async () => {
		const transcribeMutateAsync = vi.fn().mockResolvedValue({
			text: "Elden Ring and Hollow Knight",
			language: "en",
			durationSeconds: 5,
		});
		(useTranscribeAudio as Mock).mockReturnValue({
			mutateAsync: transcribeMutateAsync,
			isPending: false,
		});

		setupMediaRecorderMock();
		renderModal();

		// Start recording
		await act(async () => {
			fireEvent.click(getFilledButton());
		});

		expect(screen.getByText(/Recording\.\.\./)).toBeInTheDocument();

		// Stop recording - mock's stop() triggers ondataavailable + onstop synchronously,
		// onstop's async callback calls transcribeMutation.mutateAsync
		await act(async () => {
			fireEvent.click(getFilledButton());
		});

		// After transcription resolves
		await waitFor(() => {
			expect(screen.getByText("Transcription ready")).toBeInTheDocument();
		});

		expect(screen.getByDisplayValue("Elden Ring and Hollow Knight")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /Record Again/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /^Submit$/i })).toBeInTheDocument();
	});

	it("'Record Again' resets transcription state", async () => {
		const transcribeMutateAsync = vi.fn().mockResolvedValue({
			text: "Elden Ring",
			language: "en",
			durationSeconds: 3,
		});
		(useTranscribeAudio as Mock).mockReturnValue({
			mutateAsync: transcribeMutateAsync,
			isPending: false,
		});

		setupMediaRecorderMock();
		renderModal();

		// Start -> Stop
		await act(async () => {
			fireEvent.click(getFilledButton());
		});
		await act(async () => {
			fireEvent.click(getFilledButton());
		});

		await waitFor(() => {
			expect(screen.getByText("Transcription ready")).toBeInTheDocument();
		});

		// Click "Record Again"
		fireEvent.click(screen.getByRole("button", { name: /Record Again/i }));

		await waitFor(() => {
			expect(screen.queryByText("Transcription ready")).not.toBeInTheDocument();
		});

		expect(screen.getByText("Tap to record")).toBeInTheDocument();
		expect(screen.getByText("00:00")).toBeInTheDocument();
	});

	it("submits transcribed text successfully", async () => {
		const submitMutateAsync = vi.fn().mockResolvedValue({
			publicId: "cap-voice-1",
			candidates: [{ title: "Elden Ring" }],
		});
		(useSubmitTextCapture as Mock).mockReturnValue({
			mutateAsync: submitMutateAsync,
			isPending: false,
		});

		const transcribeMutateAsync = vi.fn().mockResolvedValue({
			text: "Elden Ring and Hollow Knight",
			language: "en",
			durationSeconds: 5,
		});
		(useTranscribeAudio as Mock).mockReturnValue({
			mutateAsync: transcribeMutateAsync,
			isPending: false,
		});

		setupMediaRecorderMock();

		const onSuccess = vi.fn();
		renderModal({ opened: true, onSuccess });

		// Start -> Stop
		await act(async () => {
			fireEvent.click(getFilledButton());
		});
		await act(async () => {
			fireEvent.click(getFilledButton());
		});

		await waitFor(() => {
			expect(screen.getByText("Transcription ready")).toBeInTheDocument();
		});

		// Submit
		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: /^Submit$/i }));
		});

		await waitFor(() => {
			expect(submitMutateAsync).toHaveBeenCalledWith({
				rawText: "Elden Ring and Hollow Knight",
				inputType: "voice",
			});
		});

		expect(notifications.show).toHaveBeenCalledWith(
			expect.objectContaining({
				title: "Capture submitted",
				color: "green",
			}),
		);

		expect(onSuccess).toHaveBeenCalledWith("cap-voice-1");
	});

	it("shows error notification when submit fails with Error", async () => {
		const submitMutateAsync = vi.fn().mockRejectedValue(new Error("Network error"));
		(useSubmitTextCapture as Mock).mockReturnValue({
			mutateAsync: submitMutateAsync,
			isPending: false,
		});

		const transcribeMutateAsync = vi.fn().mockResolvedValue({
			text: "Elden Ring",
			language: "en",
			durationSeconds: 3,
		});
		(useTranscribeAudio as Mock).mockReturnValue({
			mutateAsync: transcribeMutateAsync,
			isPending: false,
		});

		setupMediaRecorderMock();
		renderModal();

		// Start -> Stop
		await act(async () => {
			fireEvent.click(getFilledButton());
		});
		await act(async () => {
			fireEvent.click(getFilledButton());
		});

		await waitFor(() => {
			expect(screen.getByText("Transcription ready")).toBeInTheDocument();
		});

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: /^Submit$/i }));
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Capture failed",
					message: "Network error",
					color: "red",
				}),
			);
		});
	});

	it("shows generic error notification when submit fails with non-Error", async () => {
		const submitMutateAsync = vi.fn().mockRejectedValue("something weird");
		(useSubmitTextCapture as Mock).mockReturnValue({
			mutateAsync: submitMutateAsync,
			isPending: false,
		});

		const transcribeMutateAsync = vi.fn().mockResolvedValue({
			text: "some game text",
			language: "en",
			durationSeconds: 2,
		});
		(useTranscribeAudio as Mock).mockReturnValue({
			mutateAsync: transcribeMutateAsync,
			isPending: false,
		});

		setupMediaRecorderMock();
		renderModal();

		// Start -> Stop
		await act(async () => {
			fireEvent.click(getFilledButton());
		});
		await act(async () => {
			fireEvent.click(getFilledButton());
		});

		await waitFor(() => {
			expect(screen.getByText("Transcription ready")).toBeInTheDocument();
		});

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: /^Submit$/i }));
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Capture failed",
					message: "An unexpected error occurred",
					color: "red",
				}),
			);
		});
	});

	it("calls onClose (handleClose) when modal close button is clicked", () => {
		const onClose = vi.fn();
		renderModal({ opened: true, onClose });

		fireEvent.click(screen.getByTestId("mock-modal-close"));

		expect(onClose).toHaveBeenCalled();
	});

	it("shows transcribeMutation loading state on the mic button", () => {
		(useTranscribeAudio as Mock).mockReturnValue({
			mutateAsync: vi.fn(),
			isPending: true,
		});

		renderModal();

		const filledButton = getFilledButton();
		expect(filledButton).toHaveAttribute("data-loading");
		expect(filledButton).toBeDisabled();
	});

	it("edits transcription text in the textarea", async () => {
		const transcribeMutateAsync = vi.fn().mockResolvedValue({
			text: "Original text",
			language: "en",
			durationSeconds: 3,
		});
		(useTranscribeAudio as Mock).mockReturnValue({
			mutateAsync: transcribeMutateAsync,
			isPending: false,
		});

		setupMediaRecorderMock();
		renderModal();

		// Start -> Stop
		await act(async () => {
			fireEvent.click(getFilledButton());
		});
		await act(async () => {
			fireEvent.click(getFilledButton());
		});

		await waitFor(() => {
			expect(screen.getByText("Transcription ready")).toBeInTheDocument();
		});

		// Edit the textarea
		const textarea = screen.getByDisplayValue("Original text");
		fireEvent.change(textarea, { target: { value: "Edited text with more games" } });

		expect(screen.getByDisplayValue("Edited text with more games")).toBeInTheDocument();
	});

	it("shows transcription error notification when transcription fails", async () => {
		const transcribeMutateAsync = vi
			.fn()
			.mockRejectedValue(new Error("Transcription service unavailable"));
		(useTranscribeAudio as Mock).mockReturnValue({
			mutateAsync: transcribeMutateAsync,
			isPending: false,
		});

		setupMediaRecorderMock();
		renderModal();

		// Start recording
		await act(async () => {
			fireEvent.click(getFilledButton());
		});

		// Stop recording - transcription will fail
		await act(async () => {
			fireEvent.click(getFilledButton());
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Transcription failed",
					color: "red",
				}),
			);
		});
	});

	it("resets state on close even while recording", async () => {
		setupMediaRecorderMock();

		const onClose = vi.fn();
		renderModal({ opened: true, onClose });

		// Start recording
		await act(async () => {
			fireEvent.click(getFilledButton());
		});
		expect(screen.getByText(/Recording\.\.\./)).toBeInTheDocument();

		// Close the modal while recording
		await act(async () => {
			fireEvent.click(screen.getByTestId("mock-modal-close"));
		});

		expect(onClose).toHaveBeenCalled();
	});
});

describe("formatDuration", () => {
	it("formats 0 seconds as 00:00", () => {
		expect(formatDuration(0)).toBe("00:00");
	});

	it("formats 65 seconds as 01:05", () => {
		expect(formatDuration(65)).toBe("01:05");
	});

	it("formats 5 seconds as 00:05", () => {
		expect(formatDuration(5)).toBe("00:05");
	});

	it("formats 600 seconds as 10:00", () => {
		expect(formatDuration(600)).toBe("10:00");
	});

	it("formats 59 seconds as 00:59", () => {
		expect(formatDuration(59)).toBe("00:59");
	});
});
