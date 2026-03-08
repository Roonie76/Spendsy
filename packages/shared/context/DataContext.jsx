import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';
import { API_BASE_URL } from '../config/constants'; // Use the shared constant

const DataContext = createContext();
export function useData() { return useContext(DataContext); }

export function DataProvider({ children }) {
  const { user } = useAuth();
  
  const [transactions, setTransactions] = useState([]);
  const [wealthItems, setWealthItems] = useState([]);
  const [settings, setSettings] = useState({ monthlyIncome: '', monthlyBudget: '', dailyBudget: '', isBusiness: false });
  const [taxProfile, setTaxProfile] = useState({ 
    annualRent: '', annualEPF: '', healthInsuranceSelf: '', 
    healthInsuranceParents: '', npsContribution: '', isBusiness: false 
  });
  const [loading, setLoading] = useState(false);

  // --- HELPER: GET AUTH HEADERS (JWT Bearer) ---
  const getAuthHeaders = useCallback(() => {
    const token =
      localStorage.getItem("access_token") ||
      localStorage.getItem("auth_token") ||
      localStorage.getItem("token");
    if (!token) return null;
    return {
      headers: { 
        'Authorization': token.startsWith("Bearer ") ? token : `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    };
  }, []);

  // --- 1. FETCH ALL DATA FROM DJANGO ---
  const refreshData = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const config = getAuthHeaders();
      if (!config) return;

      // Fetch Transactions
      const transRes = await axios.get(`${API_BASE_URL}/transactions`, config);
      const transactionsPayload = transRes.data?.data || transRes.data || [];
      setTransactions(transactionsPayload);

      const wealthRes = await axios.get(`${API_BASE_URL}/wealth`, config);
      const wealthPayload = wealthRes.data?.data || wealthRes.data || [];
      setWealthItems(Array.isArray(wealthPayload) ? wealthPayload : []);

      // Fetch Profile/Settings
      const profileRes = await axios.get(`${API_BASE_URL}/profile/${user.id}`, config);
      const profilePayload = profileRes.data?.data || profileRes.data;
      if (profilePayload) {
        setSettings({
          monthlyIncome: profilePayload.monthlyIncome || '',
          monthlyBudget: profilePayload.monthlyBudget || '',
          dailyBudget: profilePayload.dailyBudget || '',
          isBusiness: profilePayload.is_business || false
        });
      }

      const taxRes = await axios.get(`${API_BASE_URL}/tax-profile/${user.id}`, config);
      const taxPayload = taxRes.data?.data || taxRes.data;
      if (taxPayload) setTaxProfile(taxPayload);
    } catch (e) {
      console.error("Django Fetch Error:", e);
    } finally {
      setLoading(false);
    }
  }, [user, getAuthHeaders]);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // --- 2. ACTIONS ---

  const deleteTransaction = async (id) => {
    const config = getAuthHeaders();
    if (!config) return;

    setTransactions(prev => prev.filter(t => t.id !== id));
    try {
      await axios.delete(`${API_BASE_URL}/transactions/${id}`, config);
    } catch (e) {
      console.error("Delete failed", e);
      refreshData(); 
    }
  };

  const updateTransaction = async (updatedTx) => {
    const config = getAuthHeaders();
    if (!config) return;

    try {
      const { id, ...data } = updatedTx;
      await axios.patch(`${API_BASE_URL}/transactions/${id}`, data, config);
      refreshData();
    } catch (e) {
      console.error("Update failed", e);
    }
  };

  const updateSettings = async (newSettings) => {
    if (!user) return;
    const config = getAuthHeaders();
    if (!config) return;

    try {
      const djangoPayload = {
        monthly_income: parseFloat(newSettings.monthlyIncome) || 0,
        monthly_budget: parseFloat(newSettings.monthlyBudget) || 0,
        daily_budget: parseFloat(newSettings.dailyBudget) || 0,
        is_business: newSettings.isBusiness || false,
      };

      const res = await axios.post(`${API_BASE_URL}/profile/${user.id}`, djangoPayload, config);
      const payload = res.data?.data || res.data;
      if (payload) {
        setSettings({
          monthlyIncome: payload.monthlyIncome,
          monthlyBudget: payload.monthlyBudget,
          dailyBudget: payload.dailyBudget,
          isBusiness: payload.is_business
        });
      }
    } catch (e) {
      console.error("Settings update failed:", e);
      refreshData(); 
    }
  };

  const updateTaxProfile = async (newProfile) => {
    if (!user) return;
    const config = getAuthHeaders();
    if (!config) return;

    try {
      await axios.post(`${API_BASE_URL}/tax-profile/${user.id}`, newProfile, config);
      setTaxProfile(newProfile);
    } catch (e) {
      console.error("Tax profile update failed", e);
    }
  };

  const value = {
    transactions, wealthItems, settings, taxProfile, loading,
    deleteTransaction, updateTransaction, updateSettings, updateTaxProfile, refreshData
  };

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}
