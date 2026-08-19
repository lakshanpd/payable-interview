import AsyncStorage from '@react-native-async-storage/async-storage';

import { User } from '../types';

const ACCESS_TOKEN_KEY = 'circlefund.access_token';
const REFRESH_TOKEN_KEY = 'circlefund.refresh_token';
const LAST_CIRCLE_ID_KEY = 'circlefund.last_circle_id';
const USER_KEY = 'circlefund.user';

export const TokenStorage = {
  async getAccessToken(): Promise<string | null> {
    return AsyncStorage.getItem(ACCESS_TOKEN_KEY);
  },
  async getRefreshToken(): Promise<string | null> {
    return AsyncStorage.getItem(REFRESH_TOKEN_KEY);
  },
  async setTokens(access: string, refresh: string): Promise<void> {
    await AsyncStorage.multiSet([
      [ACCESS_TOKEN_KEY, access],
      [REFRESH_TOKEN_KEY, refresh],
    ]);
  },
  async setAccessToken(access: string): Promise<void> {
    await AsyncStorage.setItem(ACCESS_TOKEN_KEY, access);
  },
  async clear(): Promise<void> {
    await AsyncStorage.multiRemove([ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY]);
  },
};

export const UserStorage = {
  async getUser(): Promise<User | null> {
    const raw = await AsyncStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  },
  async setUser(user: User): Promise<void> {
    await AsyncStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  async clear(): Promise<void> {
    await AsyncStorage.removeItem(USER_KEY);
  },
};

export const CircleStorage = {
  async getLastCircleId(): Promise<number | null> {
    const value = await AsyncStorage.getItem(LAST_CIRCLE_ID_KEY);
    return value ? Number(value) : null;
  },
  async setLastCircleId(id: number): Promise<void> {
    await AsyncStorage.setItem(LAST_CIRCLE_ID_KEY, String(id));
  },
  async clear(): Promise<void> {
    await AsyncStorage.removeItem(LAST_CIRCLE_ID_KEY);
  },
};
