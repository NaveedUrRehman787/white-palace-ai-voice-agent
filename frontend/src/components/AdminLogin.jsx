import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Lock, Loader2, AlertCircle } from 'lucide-react';
import axios from 'axios';

export default function AdminLogin({ onLoginSuccess }) {
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const res = await axios.post('/api/admin/login', { password });

            if (res.data.status === 'success') {
                // Store token securely
                localStorage.setItem('adminToken', res.data.token);
                localStorage.setItem('adminTokenExpiry', Date.now() + (res.data.expiresIn * 1000));
                onLoginSuccess();
            }
        } catch (err) {
            if (err.response?.status === 401) {
                setError('Invalid password. Please try again.');
            } else {
                setError('Login failed. Please check your connection.');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="card login-card"
            >
                <div className="login-icon">
                    <Lock size={48} />
                </div>

                <h2>Admin Access</h2>
                <p className="login-subtitle">Enter your staff password to continue.</p>

                {error && (
                    <div className="login-error">
                        <AlertCircle size={16} />
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <input
                            type="password"
                            className="input"
                            placeholder="Enter password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            autoFocus
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className="btn btn-primary btn-block"
                        disabled={loading}
                    >
                        {loading ? <Loader2 className="animate-spin" /> : 'Login'}
                    </button>
                </form>
            </motion.div>
        </div>
    );
}
