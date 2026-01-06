import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { User, Lock, Mail, Phone, Loader2, AlertCircle, ArrowLeft, CheckCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function SignUp() {
    const [formData, setFormData] = useState({
        name: '',
        phone: '',
        email: '',
        password: '',
        confirmPassword: ''
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const { register } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        // Validate passwords match
        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match');
            setLoading(false);
            return;
        }

        // Validate password length
        if (formData.password.length < 6) {
            setError('Password must be at least 6 characters long');
            setLoading(false);
            return;
        }

        try {
            const { data } = await register({
                name: formData.name,
                phone: formData.phone,
                email: formData.email,
                password: formData.password
            });

            setSuccess(true);

            // Redirect to login after 2 seconds
            setTimeout(() => {
                navigate('/login');
            }, 2000);

        } catch (err) {
            if (err.response?.status === 409) {
                setError('Phone number or email already registered');
            } else if (err.response?.status === 400) {
                setError(err.response.data.message || 'Invalid registration data');
            } else {
                setError('Registration failed. Please try again.');
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

    if (success) {
        return (
            <div className="auth-page">
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="auth-card auth-success"
                >
                    <Link to="/" className="auth-back-link">
                        <ArrowLeft size={16} />
                        Back to Home
                    </Link>

                    <div className="auth-success-icon">✅</div>
                    <h1 className="auth-success-title">Account Created!</h1>
                    <p className="auth-success-message">
                        Your account has been successfully created. You can now sign in with your credentials.
                    </p>
                    <p className="auth-success-note">
                        Redirecting to login page...
                    </p>
                </motion.div>
            </div>
        );
    }

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
                    <h1 className="auth-title">Join White Palace</h1>
                    <p className="auth-subtitle">Create your account to get started</p>
                </div>

                {error && (
                    <div className="auth-error">
                        <AlertCircle size={16} className="auth-error-icon" />
                        <span>{error}</span>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="auth-field">
                        <label>Full Name</label>
                        <div className="auth-input-group">
                            <User size={18} className="auth-input-icon" />
                            <input
                                type="text"
                                name="name"
                                className="auth-input"
                                placeholder="Enter your full name"
                                value={formData.name}
                                onChange={handleChange}
                                required
                            />
                        </div>
                    </div>

                    <div className="auth-field">
                        <label>Phone Number</label>
                        <div className="auth-input-group">
                            <Phone size={18} className="auth-input-icon" />
                            <input
                                type="tel"
                                name="phone"
                                className="auth-input"
                                placeholder="+1 (312) 555-0123"
                                value={formData.phone}
                                onChange={handleChange}
                                required
                            />
                        </div>
                    </div>

                    <div className="auth-field">
                        <label>Email Address</label>
                        <div className="auth-input-group">
                            <Mail size={18} className="auth-input-icon" />
                            <input
                                type="email"
                                name="email"
                                className="auth-input"
                                placeholder="your@email.com"
                                value={formData.email}
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
                                placeholder="Create a password (min 6 characters)"
                                value={formData.password}
                                onChange={handleChange}
                                required
                            />
                        </div>
                    </div>

                    <div className="auth-field">
                        <label>Confirm Password</label>
                        <div className="auth-input-group">
                            <Lock size={18} className="auth-input-icon" />
                            <input
                                type="password"
                                name="confirmPassword"
                                className="auth-input"
                                placeholder="Confirm your password"
                                value={formData.confirmPassword}
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
                                Creating Account...
                            </>
                        ) : (
                            'Create Account'
                        )}
                    </button>
                </form>

                <div className="auth-links">
                    <p>
                        Already have an account?{' '}
                        <Link to="/login" className="auth-link">
                            Sign in here
                        </Link>
                    </p>
                </div>
            </motion.div>
        </div>
    );
}
