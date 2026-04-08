import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: { email: string; role?: string } | null;
  setSession: (payload: {
    accessToken: string;
    refreshToken?: string;
    user?: { email: string; role?: string };
  }) => void;
  clear: () => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setSession: ({ accessToken, refreshToken, user }) =>
        set({
          accessToken,
          refreshToken: refreshToken || null,
          user: user || null,
        }),
      clear: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    {
      name: "ai-agent-auth",
      storage: createJSONStorage(() => localStorage),
    }
  )
);
