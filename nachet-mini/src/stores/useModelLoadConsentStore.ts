import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface PendingInferenceRequest {
  imageSrc: string;
  imageIndex: number;
}

interface ModelLoadConsentState {
  hasAcknowledgedModelLoadWarning: boolean;
  pendingInferenceRequest: PendingInferenceRequest | null;

  acknowledgeModelLoadWarning: () => void;
  setPendingInferenceRequest: (req: PendingInferenceRequest | null) => void;
}

export const useModelLoadConsentStore = create<ModelLoadConsentState>()(
  persist(
    (set) => ({
      hasAcknowledgedModelLoadWarning: false,
      pendingInferenceRequest: null,

      acknowledgeModelLoadWarning: () =>
        set({ hasAcknowledgedModelLoadWarning: true }),

      setPendingInferenceRequest: (req) =>
        set({ pendingInferenceRequest: req }),
    }),
    {
      name: "nachet-mini-model-load-consent",
      partialize: (state) => ({
        hasAcknowledgedModelLoadWarning: state.hasAcknowledgedModelLoadWarning,
      }),
    },
  ),
);
