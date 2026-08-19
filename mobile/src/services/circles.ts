import { Circle, CircleDetail, CircleMember } from '../types';
import { api } from './api';

export const CircleService = {
  async create(name: string, contributionAmount: number): Promise<Circle> {
    const response = await api.post<Circle>('/circles', {
      name,
      contribution_amount: contributionAmount,
    });
    return response.data;
  },

  async join(inviteCode: string): Promise<CircleMember> {
    const response = await api.post<CircleMember>('/circles/join', { invite_code: inviteCode });
    return response.data;
  },

  async getDetail(circleId: number): Promise<CircleDetail> {
    const response = await api.get<CircleDetail>(`/circles/${circleId}`);
    return response.data;
  },
};
