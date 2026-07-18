import { getInitData } from './telegram';

// In dev (Replit/local), Vite proxies /api → Python bot.
// In production (Railway), same origin serves /api.
const BASE = '';

function authHeaders(): Record<string, string> {
  return {
    'Authorization': `tma ${getInitData()}`,
    'Content-Type': 'application/json',
  };
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options?.headers || {}) },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error || `HTTP ${res.status}`);
  return data as T;
}

// ── Types ──────────────────────────────────────────────────────────────────────

export interface UserProfile {
  id: number;
  telegram_id: number;
  first_name: string;
  username: string | null;
  balance: number;
  total_earned: number;
  referral_earnings: number;
  daily_earnings: number;
  streak: number;
  last_claimed: string | null;
  rank_emoji: string;
  rank_title: string;
  rank_next: number | null;
  leaderboard_rank: number;
  referral_count: number;
  can_claim_daily: boolean;
  daily_cooldown_seconds: number;
  device_verified: boolean;
  created_at: string;
}

export interface DailyStatus {
  can_claim: boolean;
  streak: number;
  next_streak: number;
  preview_amount: number;
  cooldown_seconds: number;
  last_claimed: string | null;
  streak_milestones: { days: number; multiplier: string; bonus: number }[];
}

export interface ReferralInfo {
  total_referrals: number;
  referral_earnings: number;
  referral_link: string;
  points_per_referral: number;
  referrals: {
    first_name: string;
    username: string | null;
    points_awarded: number;
    joined_at: string;
  }[];
}

export interface StarTier {
  stars: number;
  cost: number;
  icon: string;
  can_afford: boolean;
  shortfall: number;
}

export interface StarTiers {
  balance: number;
  tiers: StarTier[];
}

export interface Withdrawal {
  id: number;
  stars_amount: number;
  points_spent: number;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  processed_at: string | null;
}

export interface LeaderboardEntry {
  position: number;
  first_name: string;
  username: string | null;
  total_earned: number;
  balance: number;
  rank_emoji: string;
  rank_title: string;
  is_me: boolean;
}

export interface Leaderboard {
  entries: LeaderboardEntry[];
  my_rank: number;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export const api = {
  me: () => request<UserProfile>('/api/me'),

  dailyStatus: () => request<DailyStatus>('/api/daily/status'),

  claimDaily: () =>
    request<{ claimed: boolean; amount: number; streak: number; next_claim_in: number }>(
      '/api/daily/claim',
      { method: 'POST' }
    ),

  referrals: () => request<ReferralInfo>('/api/referrals'),

  starTiers: () => request<StarTiers>('/api/stars/tiers'),

  withdrawStars: (stars: number) =>
    request<{ success: boolean; withdrawal_id: number; stars: number; cost: number; message: string }>(
      '/api/stars/withdraw',
      { method: 'POST', body: JSON.stringify({ stars }) }
    ),

  starsHistory: () => request<{ history: Withdrawal[] }>('/api/stars/history'),

  leaderboard: () => request<Leaderboard>('/api/leaderboard'),
};
