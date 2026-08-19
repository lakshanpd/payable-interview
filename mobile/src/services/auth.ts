import { User } from '../types';
import { api } from './api';
import { CircleStorage, TokenStorage, UserStorage } from './storage';

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export const AuthService = {
  async register(username: string, email: string, password: string): Promise<User> {
    const response = await api.post<User>('/auth/register', { username, email, password });
    return response.data;
  },

  async login(email: string, password: string): Promise<User> {
    const response = await api.post<LoginResponse>('/auth/login', { email, password });
    await TokenStorage.setTokens(response.data.access, response.data.refresh);
    await UserStorage.setUser(response.data.user);
    return response.data.user;
  },

  async logout(): Promise<void> {
    await TokenStorage.clear();
    await UserStorage.clear();
    // Otherwise the next account to log in on this device would get
    // auto-navigated straight into this account's last-viewed circle.
    await CircleStorage.clear();
  },
};
