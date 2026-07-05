import { create } from "zustand";

type AppState = {
  token: string;
  userId?: number;
  email?: string;
  role: "admin" | "user" | "";
  theme: "light" | "dark";
  activeSessionId?: number;
  setToken: (token: string) => void;
  setProfile: (profile: { userId: number; email: string; role: "admin" | "user" | string }) => void;
  clearProfile: () => void;
  setTheme: (theme: "light" | "dark") => void;
  toggleTheme: () => void;
  setActiveSessionId: (id?: number) => void;
  hydrate: () => void;
};

function applyTheme(theme: "light" | "dark") {
  document.documentElement.setAttribute("data-theme", theme);
}

export const useAppStore = create<AppState>((set) => ({
  token: "",
  userId: undefined,
  email: "",
  role: "",
  theme: "light",
  activeSessionId: undefined,
  setToken: (token) => set({ token }),
  setProfile: ({ userId, email, role }) =>
    set({ userId, email, role: role === "admin" ? "admin" : "user" }),
  clearProfile: () => set({ userId: undefined, email: "", role: "" }),
  setTheme: (theme) => {
    localStorage.setItem("ui_theme", theme);
    applyTheme(theme);
    set({ theme });
  },
  toggleTheme: () =>
    set((state) => {
      const theme: "light" | "dark" = state.theme === "dark" ? "light" : "dark";
      localStorage.setItem("ui_theme", theme);
      applyTheme(theme);
      return { theme };
    }),
  setActiveSessionId: (id) => set({ activeSessionId: id }),
  hydrate: () => {
    const saved = localStorage.getItem("auth_token") || "";
    const role = (localStorage.getItem("auth_role") || "") as "admin" | "user" | "";
    const email = localStorage.getItem("auth_email") || "";
    const userIdRaw = localStorage.getItem("auth_user_id") || "";
    const userId = userIdRaw ? Number(userIdRaw) : undefined;
    const savedTheme = (localStorage.getItem("ui_theme") || "light") as "light" | "dark";
    applyTheme(savedTheme);
    set({ token: saved, role, email, userId, theme: savedTheme });
  },
}));
