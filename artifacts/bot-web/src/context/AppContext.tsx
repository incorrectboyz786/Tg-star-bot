import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api, UserProfile } from '../lib/api';
import { initTelegramApp, isInTelegram } from '../lib/telegram';

interface AppContextValue {
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  refetchUser: () => Promise<void>;
}

const AppContext = createContext<AppContextValue>({
  user: null,
  loading: true,
  error: null,
  refetchUser: async () => {},
});

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUser = async () => {
    try {
      setError(null);
      const data = await api.me();
      setUser(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load user');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initTelegramApp();
    fetchUser();
  }, []);

  return (
    <AppContext.Provider value={{ user, loading, error, refetchUser: fetchUser }}>
      {children}
    </AppContext.Provider>
  );
}

export const useApp = () => useContext(AppContext);
