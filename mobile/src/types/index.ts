export interface User {
  id: number;
  username: string;
  email: string;
}

export interface CircleMember {
  id: number;
  user: User;
  position: number;
  joined_at: string;
  // Only present on the POST /circles/join response, used to route the
  // mobile app straight to the circle just joined.
  circle?: number;
}

export interface Circle {
  id: number;
  name: string;
  invite_code: string;
  admin: User;
  contribution_amount: number;
  penalty_rate: number;
  max_members: number;
  created_at: string;
}

export type RoundStatus = 'OPEN' | 'PENDING_APPROVAL' | 'COMPLETED';

export interface Contribution {
  id: number;
  member: CircleMember;
  amount: number;
  penalty: number;
  total_paid: number;
  is_late: boolean;
  created_at: string;
}

export interface Round {
  id: number;
  circle: number;
  payout_recipient: CircleMember;
  status: RoundStatus;
  contribution_amount: number;
  deadline: string;
  payout_amount: number | null;
  approved_at: string | null;
  created_at: string;
  contributions: Contribution[];
}

export interface CircleDetailMember {
  id: number;
  user: User;
  position: number;
  is_admin: boolean;
  is_current_recipient: boolean;
  has_contributed_current_round: boolean | null;
}

export interface CircleDetail {
  circle: Circle;
  members: CircleDetailMember[];
  current_round: Round | null;
}

export interface ApiErrorBody {
  detail?: string;
  code?: string;
  [field: string]: unknown;
}
