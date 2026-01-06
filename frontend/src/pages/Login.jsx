import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { User, Lock, Loader2, AlertCircle, ArrowLeft } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
    const [formData, setFormData] = useState({
        login: '',
        password: ''
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    const from = location.state?.from?.pathname || '/';

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            await login(formData);
            navigate(from, { replace: true });
        } catch (err) {
            if (err.response?.status === 401) {
                setError('Invalid login credentials. Please try again.');
            } else {
                setError('Login failed. Please check your connection.');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    return (
        <div className="auth-page">
            <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="auth-card"
            >
                <Link to="/" className="auth-back-link">
                    <ArrowLeft size={16} />
                    Back to Home
                </Link>

                <div className="auth-header">
                    <div className="auth-icon">
                        🍔
                    </div>
                    <h1 className="auth-title">Welcome Back</h1>
                    <p className="auth-subtitle">Sign in to your White Palace account</p>
                </div>

                {error && (
                    <div className="auth-error">
                        <AlertCircle size={16} className="auth-error-icon" />
                        <span>{error}</span>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="auth-field">
                        <label>Phone or Email</label>
                        <div className="auth-input-group">
                            <User size={18} className="auth-input-icon" />
                            <input
                                type="text"
                                name="login"
                                className="auth-input"
                                placeholder="Enter phone or email"
                                value={formData.login}
                                onChange={handleChange}
                                required
                            />
                        </div>
                    </div>

                    <div className="auth-field">
                        <label>Password</label>
                        <div className="auth-input-group">
                            <Lock size={18} className="auth-input-icon" />
                            <input
                                type="password"
                                name="password"
                                className="auth-input"
                                placeholder="Enter password"
                                value={formData.password}
                                onChange={handleChange}
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="auth-submit-btn"
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <Loader2 className="animate-spin" size={18} />
                                Signing in...
                            </>
                        ) : (
                            'Sign In'
                        )}
                    </button>
                </form>

                <div className="auth-links">
                    <p>
                        Don't have an account?{' '}
                        <Link to="/signup" className="auth-link">
                            Sign up here
                        </Link>
                    </p>
                </div>
            </motion.div>
        </div>
    );
}
