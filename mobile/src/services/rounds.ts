import { Round } from '../types';
import { api } from './api';

export const RoundService = {
  async contribute(roundId: number): Promise<Round> {
    const response = await api.post<Round>(`/rounds/${roundId}/contribute`);
    return response.data;
  },

  async approve(roundId: number): Promise<Round> {
    const response = await api.post<Round>(`/rounds/${roundId}/approve`);
    return response.data;
  },
};
