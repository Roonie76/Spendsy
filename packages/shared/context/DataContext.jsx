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

  // --- HELPER: GET AUTH HEADERS (Django Token Version) ---
  const getAuthHeaders = useCallback(() => {
    const token = localStorage.getItem("token"); // Get Django Token
    if (!token) return null;
    return {
      headers: { 
        'Authorization': `Token ${token}`, // Use Django 'Token' or 'Bearer'
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
      const transRes = await axios.get(`${API_BASE_URL}/finance/transactions/`, config);
      setTransactions(transRes.data);

      // Fetch Profile/Settings
      const profileRes = await axios.get(`${API_BASE_URL}/finance/profile/`, config);
      if (profileRes.data) {
        setSettings({
          monthlyIncome: profileRes.data.monthly_income || '',
          monthlyBudget: profileRes.data.monthly_budget || '',
          dailyBudget: profileRes.data.daily_budget || '',
          isBusiness: profileRes.data.is_business || false
        });
        if (profileRes.data.tax_profile) setTaxProfile(profileRes.data.tax_profile);
      }
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
      await axios.delete(`${API_BASE_URL}/finance/transactions/${id}/`, config);
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
      await axios.patch(`${API_BASE_URL}/finance/transactions/${id}/`, data, config);
      refreshData();
    } catch (e) {
      console.error("Update failed", e);
    }
  };

  const updateSettings = async (newSettings) => {
    const config = getAuthHeaders();
    if (!config) return;

    try {
      const djangoPayload = {
        monthly_income: parseFloat(newSettings.monthlyIncome) || 0,
        monthly_budget: parseFloat(newSettings.monthlyBudget) || 0,
        daily_budget: parseFloat(newSettings.dailyBudget) || 0,
        is_business: newSettings.isBusiness || false,
      };

      const res = await axios.patch(`${API_BASE_URL}/finance/profile/`, djangoPayload, config);
      
      if (res.data) {
        setSettings({
          monthlyIncome: res.data.monthly_income,
          monthlyBudget: res.data.monthly_budget,
          dailyBudget: res.data.daily_budget,
          isBusiness: res.data.is_business
        });
      }
    } catch (e) {
      console.error("Settings update failed:", e);
      refreshData(); 
    }
  };

  const updateTaxProfile = async (newProfile) => {
    const config = getAuthHeaders();
    if (!config) return;

    try {
      await axios.patch(`${API_BASE_URL}/finance/profile/`, { tax_profile: newProfile }, config);
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