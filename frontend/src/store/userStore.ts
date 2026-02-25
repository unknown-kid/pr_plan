import { create } from 'zustand';

interface UserState {
  user: any | null;
  token: string | null;
  darkMode: boolean;
  setUser: (user: any) => void;
  setToken: (token: string | null) => void;
  setDarkMode: (darkMode: boolean) => void;
  logout: () => void;
}

const useUserStore = create<UserState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  darkMode: localStorage.getItem('darkMode') === 'true',
  setUser: (user) => set({ user }),
  setToken: (token) => {
    if (token) localStorage.setItem('token', token);
    else localStorage.removeItem('token');
    set({ token });
  },
  setDarkMode: (darkMode) => {
    localStorage.setItem('darkMode', String(darkMode));
    set({ darkMode });
  },
  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null });
  },
}));

export default useUserStore;
