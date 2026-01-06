import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export function useAuth() {
    return useContext(AuthContext);
}

export function AuthProvider({ children }) {
    const [customer, setCustomer] = useState(null);
    const [token, setToken] = useState(localStorage.getItem('customerToken'));
    const [loading, setLoading] = useState(true);

    // Verify token on mount
    useEffect(() => {
        if (token) {
            verifyToken();
        } else {
            setLoading(false);
        }
    }, [token]);

    const verifyToken = async () => {
        try {
            const res = await axios.post('/api/customer/verify', { token });
            if (res.data.valid) {
                setCustomer(res.data.customer);
            } else {
                // Token invalid, clear it
                localStorage.removeItem('customerToken');
                setToken(null);
            }
        } catch (error) {
            // Token verification failed, clear it
            localStorage.removeItem('customerToken');
            setToken(null);
        } finally {
            setLoading(false);
        }
    };

    const login = async (loginData) => {
        const res = await axios.post('/api/customer/login', loginData);
        const { token: newToken, customer: customerData } = res.data;

        localStorage.setItem('customerToken', newToken);
        setToken(newToken);
        setCustomer(customerData);

        return customerData;
    };

    const register = async (registerData) => {
        const res = await axios.post('/api/customer/register', registerData);
        return res.data;
    };

    const logout = async () => {
        if (token) {
            try {
                await axios.post('/api/customer/logout', { token });
            } catch (error) {
                console.error('Logout error:', error);
            }
        }

        localStorage.removeItem('customerToken');
        setToken(null);
        setCustomer(null);
    };

    const value = {
        customer,
        token,
        login,
        register,
        logout,
        loading,
        isAuthenticated: !!customer
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}
