import axios from 'axios';
import { API_BASE_URL } from '../config/constants';

/**
 * HELPER: GET AUTH HEADERS
 * Pulls the Django REST Framework token from localStorage.
 */
const getAuthHeaders = () => {
    const token = localStorage.getItem("token");
    if (!token) throw new Error("No authentication token found. Please log in.");
    
    return {
        headers: { 
            // Standard Django DRF Token format
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json'
        }
    };
};

export const financeAPI = {
    // SAVE TRANSACTION
    saveTransaction: async (data) => {
        try {
            const config = getAuthHeaders();
            const response = await axios.post(`${API_BASE_URL}/finance/transactions/`, data, config);
            return response.data;
        } catch (error) {
            console.error("API Save Error:", error.response?.data || error.message);
            throw error;
        }
    },

    // FETCH TRANSACTIONS
    getTransactions: async () => {
        try {
            const config = getAuthHeaders();
            const response = await axios.get(`${API_BASE_URL}/finance/transactions/`, config);
            return response.data;
        } catch (error) {
            console.error("API Fetch Error:", error.response?.data || error.message);
            throw error;
        }
    },

    // DELETE TRANSACTION
    deleteTransaction: async (id) => {
        try {
            const config = getAuthHeaders();
            await axios.delete(`${API_BASE_URL}/finance/transactions/${id}/`, config);
            return true;
        } catch (error) {
            console.error("API Delete Error:", error.response?.data || error.message);
            throw error;
        }
    }
};