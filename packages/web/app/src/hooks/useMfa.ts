import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	confirmMfa,
	disableMfa,
	enrollMfa,
	getMfaStatus,
	regenerateRecoveryCodes,
} from "../lib/mfa-api";
import type { MfaStatus } from "../types/auth";

const MFA_STATUS_KEY = ["mfa", "status"] as const;

/**
 * MFA management for the account page: status query plus enroll / confirm /
 * regenerate / disable mutations. Each mutation invalidates the status query so
 * the UI reflects the new enabled / recovery-code state.
 */
export function useMfa() {
	const queryClient = useQueryClient();

	const { data: status, isLoading: isStatusLoading } = useQuery<MfaStatus>({
		queryKey: MFA_STATUS_KEY,
		queryFn: getMfaStatus,
		staleTime: 30 * 1000,
	});

	const invalidateStatus = () => queryClient.invalidateQueries({ queryKey: MFA_STATUS_KEY });

	const enrollMutation = useMutation({ mutationFn: enrollMfa });
	const confirmMutation = useMutation({
		mutationFn: (code: string) => confirmMfa(code),
		onSuccess: invalidateStatus,
	});
	const regenerateMutation = useMutation({
		mutationFn: (code: string) => regenerateRecoveryCodes(code),
		onSuccess: invalidateStatus,
	});
	const disableMutation = useMutation({
		mutationFn: (code: string) => disableMfa(code),
		onSuccess: invalidateStatus,
	});

	return {
		status,
		isStatusLoading,
		enroll: () => enrollMutation.mutateAsync(),
		confirm: (code: string) => confirmMutation.mutateAsync(code),
		regenerate: (code: string) => regenerateMutation.mutateAsync(code),
		disable: (code: string) => disableMutation.mutateAsync(code),
		isEnrolling: enrollMutation.isPending,
		isConfirming: confirmMutation.isPending,
		isRegenerating: regenerateMutation.isPending,
		isDisabling: disableMutation.isPending,
	};
}
