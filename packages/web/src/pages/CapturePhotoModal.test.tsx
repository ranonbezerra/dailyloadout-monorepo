import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useSubmitPhotoCapture } from "../hooks/useCapture";
import { CapturePhotoModal } from "./CapturePhotoModal";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../hooks/useCapture", () => ({
	useSubmitPhotoCapture: vi.fn(),
	useCaptures: vi.fn(() => ({ data: null, isLoading: false })),
	useCapture: vi.fn(() => ({ data: null, isLoading: false })),
	useSubmitTextCapture: vi.fn(() => ({
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
	useTranscribeAudio: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
}));

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

// Mock only Modal to avoid portal issues in jsdom
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
				<CapturePhotoModal {...defaultProps} {...props} />
			</MemoryRouter>
		</MantineProvider>,
	);
}

// Stub URL.createObjectURL / revokeObjectURL for jsdom
const mockCreateObjectURL = vi.fn(() => "blob:http://localhost/fake-url");
const mockRevokeObjectURL = vi.fn();

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CapturePhotoModal", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		(useSubmitPhotoCapture as Mock).mockReturnValue({
			mutateAsync: vi.fn(),
			isPending: false,
		});
		globalThis.URL.createObjectURL = mockCreateObjectURL;
		globalThis.URL.revokeObjectURL = mockRevokeObjectURL;
	});

	it("renders modal content when opened is true", () => {
		renderModal({ opened: true });

		expect(screen.getByText("Photo Capture")).toBeInTheDocument();
	});

	it("does not render modal content when opened is false", () => {
		renderModal({ opened: false });

		expect(screen.queryByText("Photo Capture")).not.toBeInTheDocument();
	});

	it("shows description text about photo capture", () => {
		renderModal({ opened: true });

		expect(screen.getByText(/Take a photo of a game cover or your shelf/)).toBeInTheDocument();
	});

	it("shows 'Choose File' and 'Take Photo' buttons", () => {
		renderModal({ opened: true });

		expect(screen.getByRole("button", { name: /Choose File/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /Take Photo/i })).toBeInTheDocument();
	});

	it("does not show submit button initially (no file selected)", () => {
		renderModal({ opened: true });

		expect(screen.queryByRole("button", { name: /^Submit$/i })).not.toBeInTheDocument();
	});

	it("shows supported formats text", () => {
		renderModal({ opened: true });

		expect(screen.getByText(/Supports JPG, PNG, WebP/)).toBeInTheDocument();
	});

	it("has hidden file inputs in the DOM", () => {
		renderModal({ opened: true });

		const fileInputs = document.body.querySelectorAll('input[type="file"]');
		expect(fileInputs.length).toBe(2);
	});

	it("the camera input has capture attribute", () => {
		renderModal({ opened: true });

		const cameraInput = document.body.querySelector('input[type="file"][capture]');
		expect(cameraInput).toBeInTheDocument();
		expect(cameraInput).toHaveAttribute("capture", "environment");
	});

	it("shows preview image and submit button after selecting a file", async () => {
		renderModal({ opened: true });

		const fileInput = document.body.querySelector(
			'input[type="file"]:not([capture])',
		) as HTMLInputElement;
		const file = new File(["pixels"], "test.png", { type: "image/png" });

		fireEvent.change(fileInput, { target: { files: [file] } });

		await waitFor(() => {
			expect(screen.getByAltText("Selected image preview")).toBeInTheDocument();
		});

		expect(screen.getByText("test.png")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /^Submit$/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /Choose Different Image/i })).toBeInTheDocument();
	});

	it("resets file selection when 'Choose Different Image' is clicked", async () => {
		renderModal({ opened: true });

		const fileInput = document.body.querySelector(
			'input[type="file"]:not([capture])',
		) as HTMLInputElement;
		const file = new File(["pixels"], "test.png", { type: "image/png" });

		fireEvent.change(fileInput, { target: { files: [file] } });

		await waitFor(() => {
			expect(screen.getByAltText("Selected image preview")).toBeInTheDocument();
		});

		const resetButton = screen.getByRole("button", { name: /Choose Different Image/i });
		fireEvent.click(resetButton);

		await waitFor(() => {
			expect(screen.queryByAltText("Selected image preview")).not.toBeInTheDocument();
		});

		// Should be back to initial state with "Choose File" button
		expect(screen.getByRole("button", { name: /Choose File/i })).toBeInTheDocument();
	});

	it("calls mutateAsync on successful submission and shows success notification", async () => {
		const mutateAsyncFn = vi.fn().mockResolvedValueOnce({
			publicId: "cap-photo-1",
			candidates: [{ title: "Hollow Knight" }],
		});
		(useSubmitPhotoCapture as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		const onSuccess = vi.fn();
		renderModal({ opened: true, onSuccess });

		const fileInput = document.body.querySelector(
			'input[type="file"]:not([capture])',
		) as HTMLInputElement;
		const file = new File(["pixels"], "test.png", { type: "image/png" });

		fireEvent.change(fileInput, { target: { files: [file] } });

		await waitFor(() => {
			expect(screen.getByRole("button", { name: /^Submit$/i })).toBeInTheDocument();
		});

		const submitButton = screen.getByRole("button", { name: /^Submit$/i });
		fireEvent.click(submitButton);

		await waitFor(() => {
			expect(mutateAsyncFn).toHaveBeenCalledWith(file);
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Photo capture submitted",
					color: "green",
				}),
			);
		});

		await waitFor(() => {
			expect(onSuccess).toHaveBeenCalledWith("cap-photo-1");
		});
	});

	it("shows error notification when photo submission fails with Error", async () => {
		const mutateAsyncFn = vi.fn().mockRejectedValueOnce(new Error("Upload failed"));
		(useSubmitPhotoCapture as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		renderModal({ opened: true });

		const fileInput = document.body.querySelector(
			'input[type="file"]:not([capture])',
		) as HTMLInputElement;
		const file = new File(["pixels"], "test.png", { type: "image/png" });

		fireEvent.change(fileInput, { target: { files: [file] } });

		await waitFor(() => {
			expect(screen.getByRole("button", { name: /^Submit$/i })).toBeInTheDocument();
		});

		const submitButton = screen.getByRole("button", { name: /^Submit$/i });
		fireEvent.click(submitButton);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Photo capture failed",
					message: "Upload failed",
					color: "red",
				}),
			);
		});
	});

	it("shows generic error notification when photo submission fails with non-Error", async () => {
		const mutateAsyncFn = vi.fn().mockRejectedValueOnce("something");
		(useSubmitPhotoCapture as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		renderModal({ opened: true });

		const fileInput = document.body.querySelector(
			'input[type="file"]:not([capture])',
		) as HTMLInputElement;
		const file = new File(["pixels"], "test.png", { type: "image/png" });

		fireEvent.change(fileInput, { target: { files: [file] } });

		await waitFor(() => {
			expect(screen.getByRole("button", { name: /^Submit$/i })).toBeInTheDocument();
		});

		const submitButton = screen.getByRole("button", { name: /^Submit$/i });
		fireEvent.click(submitButton);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Photo capture failed",
					message: "An unexpected error occurred",
					color: "red",
				}),
			);
		});
	});

	it("handles null file gracefully in handleFileChange", () => {
		renderModal({ opened: true });

		const fileInput = document.body.querySelector(
			'input[type="file"]:not([capture])',
		) as HTMLInputElement;

		// Simulate change with no files (e.g. user cancelled file picker)
		fireEvent.change(fileInput, { target: { files: [] } });

		// Should still show the initial buttons
		expect(screen.getByRole("button", { name: /Choose File/i })).toBeInTheDocument();
		expect(screen.queryByAltText("Selected image preview")).not.toBeInTheDocument();
	});

	it("revokes old preview URL when selecting a new file", async () => {
		renderModal({ opened: true });

		const fileInput = document.body.querySelector(
			'input[type="file"]:not([capture])',
		) as HTMLInputElement;
		const file1 = new File(["pixels1"], "first.png", { type: "image/png" });
		const file2 = new File(["pixels2"], "second.png", { type: "image/png" });

		fireEvent.change(fileInput, { target: { files: [file1] } });

		await waitFor(() => {
			expect(screen.getByAltText("Selected image preview")).toBeInTheDocument();
		});

		// Select a second file - should revoke the first URL
		fireEvent.change(fileInput, { target: { files: [file2] } });

		await waitFor(() => {
			expect(mockRevokeObjectURL).toHaveBeenCalled();
		});
	});

	it("calls onClose and resets state when modal close button is clicked", async () => {
		const onClose = vi.fn();
		renderModal({ opened: true, onClose });

		// Select a file first
		const fileInput = document.body.querySelector(
			'input[type="file"]:not([capture])',
		) as HTMLInputElement;
		const file = new File(["pixels"], "test.png", { type: "image/png" });

		fireEvent.change(fileInput, { target: { files: [file] } });

		await waitFor(() => {
			expect(screen.getByAltText("Selected image preview")).toBeInTheDocument();
		});

		// Click the mock modal close button which triggers handleClose
		fireEvent.click(screen.getByTestId("mock-modal-close"));

		expect(onClose).toHaveBeenCalled();
		expect(mockRevokeObjectURL).toHaveBeenCalled();
	});

	it("handles camera input file selection", async () => {
		renderModal({ opened: true });

		const cameraInput = document.body.querySelector(
			'input[type="file"][capture]',
		) as HTMLInputElement;
		const file = new File(["pixels"], "camera.jpg", { type: "image/jpeg" });

		fireEvent.change(cameraInput, { target: { files: [file] } });

		await waitFor(() => {
			expect(screen.getByAltText("Selected image preview")).toBeInTheDocument();
		});

		expect(screen.getByText("camera.jpg")).toBeInTheDocument();
	});

	it("does not call mutateAsync when no file is selected (handleSubmit guard)", async () => {
		const mutateAsyncFn = vi.fn();
		(useSubmitPhotoCapture as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		renderModal({ opened: true });

		// No file selected, so submit button should not exist
		expect(screen.queryByRole("button", { name: /^Submit$/i })).not.toBeInTheDocument();

		// mutateAsync should not have been called
		expect(mutateAsyncFn).not.toHaveBeenCalled();
	});
});
