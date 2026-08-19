import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { AuthService } from '../services/auth';
import { TokenStorage, UserStorage } from '../services/storage';
import { User } from '../types';

interface AuthContextValue {
  user: User | null;
  isBootstrapping: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  useEffect(() => {
    (async () => {
      const [token, storedUser] = await Promise.all([TokenStorage.getAccessToken(), UserStorage.getUser()]);
      if (token && storedUser) {
        setUser(storedUser);
      }
      setIsBootstrapping(false);
    })();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isBootstrapping,
      async login(email, password) {
        const loggedInUser = await AuthService.login(email, password);
        setUser(loggedInUser);
      },
      async register(username, email, password) {
        await AuthService.register(username, email, password);
        await AuthService.login(email, password);
        setUser(await UserStorage.getUser());
      },
      async logout() {
        await AuthService.logout();
        setUser(null);
      },
    }),
    [user, isBootstrapping]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
