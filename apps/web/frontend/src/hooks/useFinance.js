/**
 * hooks/useFinance.js
 *
 * React Query hooks for all finance data.
 * Replaces the sprawl of manual useEffect/fetch calls in App.jsx.
 */
import { useQuery, useMutation, useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { financeApi, authApi } from "../api";

export const QUERY_KEYS = {
  me: ["auth", "me"],
  summary: ["finance", "summary"],
  transactions: (search) => ["finance", "transactions", search],
  wealth: ["finance", "wealth"],
  profile: (uid) => ["finance", "profile", uid],
  taxProfile: (uid) => ["finance", "taxProfile", uid],
};

// ── Auth ────────────────────────────────────────────────────────────────────

export function useCurrentUser() {
  return useQuery({
    queryKey: QUERY_KEYS.me,
    queryFn: () => authApi.me().then((r) => r.data ?? r),
    staleTime: 1000 * 60 * 5,  // cache 5 min
    retry: false,              // don't retry 401s
  });
}

// ── Financial Summary ────────────────────────────────────────────────────────

export function useSummary(enabled = true) {
  return useQuery({
    queryKey: QUERY_KEYS.summary,
    queryFn: () => financeApi.summary().then((r) => r.data ?? r),
    enabled,
    staleTime: 1000 * 30,
  });
}

// ── Transactions (Infinite/Cursor Paginated) ─────────────────────────────────

export function useTransactions(search = "") {
  return useInfiniteQuery({
    queryKey: QUERY_KEYS.transactions(search),
    queryFn: ({ pageParam = undefined }) =>
      financeApi.transactions({ limit: 50, cursor: pageParam, search }).then((r) => r.data ?? r),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 1000 * 30,
  });
}

/** Returns flat array of all fetched transactions from all pages. */
export function useFlatTransactions(search = "") {
  const query = useTransactions(search);
  const all = query.data?.pages?.flatMap((page) => page.data ?? page) ?? [];
  return { ...query, transactions: all };
}

// ── Wealth ───────────────────────────────────────────────────────────────────

export function useWealth(enabled = true) {
  return useQuery({
    queryKey: QUERY_KEYS.wealth,
    queryFn: () => financeApi.wealth().then((r) => r.data ?? r),
    enabled,
    staleTime: 1000 * 60,
  });
}

// ── Profile ──────────────────────────────────────────────────────────────────

export function useProfile(userId) {
  return useQuery({
    queryKey: QUERY_KEYS.profile(userId),
    queryFn: () => financeApi.profile(userId).then((r) => r.data ?? r),
    enabled: !!userId,
    staleTime: 1000 * 60 * 5,
  });
}

// ── Tax Profile ──────────────────────────────────────────────────────────────

export function useTaxProfile(userId) {
  return useQuery({
    queryKey: QUERY_KEYS.taxProfile(userId),
    queryFn: () => financeApi.taxProfile(userId).then((r) => r.data ?? r),
    enabled: !!userId,
    staleTime: 1000 * 60 * 5,
  });
}

// ── Mutations ─────────────────────────────────────────────────────────────────

export function useAddTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body) => financeApi.addTransaction(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["finance", "transactions"] });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.summary });
    },
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => financeApi.deleteTransaction(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["finance", "transactions"] });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.summary });
    },
  });
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }) => financeApi.updateTransaction(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["finance", "transactions"] });
    },
  });
}

export function useAddWealth() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body) => financeApi.addWealth(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.wealth });
    },
  });
}

export function useDeleteWealth() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => financeApi.deleteWealth(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.wealth });
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, body }) => financeApi.updateProfile(userId, body),
    onSuccess: (_, { userId }) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.profile(userId) });
    },
  });
}

export function useUpdateTaxProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, body }) => financeApi.updateTaxProfile(userId, body),
    onSuccess: (_, { userId }) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.taxProfile(userId) });
    },
  });
}
