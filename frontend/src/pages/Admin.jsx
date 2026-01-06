import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ClipboardList, Calendar, CheckCircle, Clock, XCircle,
    ChevronRight, Utensils, Users, RefreshCw, AlertCircle, LogOut
} from 'lucide-react';
import AdminLogin from '../components/AdminLogin';

export default function Admin() {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [checkingAuth, setCheckingAuth] = useState(true);
    const [activeTab, setActiveTab] = useState('orders');
    const [orders, setOrders] = useState([]);
    const [reservations, setReservations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshTrigger, setRefreshTrigger] = useState(0);

    // Check if user is already logged in
    useEffect(() => {
        checkAuthStatus();
    }, []);

    const checkAuthStatus = async () => {
        const token = localStorage.getItem('adminToken');
        const expiry = localStorage.getItem('adminTokenExpiry');

        if (!token || !expiry || Date.now() > parseInt(expiry)) {
            // Token missing or expired
            localStorage.removeItem('adminToken');
            localStorage.removeItem('adminTokenExpiry');
            setIsAuthenticated(false);
            setCheckingAuth(false);
            return;
        }

        try {
            // Verify token with backend
            const res = await axios.post('/api/admin/verify', { token });
            if (res.data.valid) {
                setIsAuthenticated(true);
            } else {
                localStorage.removeItem('adminToken');
                localStorage.removeItem('adminTokenExpiry');
                setIsAuthenticated(false);
            }
        } catch {
            setIsAuthenticated(false);
        } finally {
            setCheckingAuth(false);
        }
    };

    const handleLogout = async () => {
        const token = localStorage.getItem('adminToken');
        try {
            await axios.post('/api/admin/logout', { token });
        } catch { }
        localStorage.removeItem('adminToken');
        localStorage.removeItem('adminTokenExpiry');
        setIsAuthenticated(false);
    };

    useEffect(() => {
        fetchData();
    }, [activeTab, refreshTrigger]);

    const fetchData = async () => {
        setLoading(true);
        try {
            if (activeTab === 'orders') {
                const res = await axios.get('/api/orders?limit=50');
                setOrders(res.data.data.orders);
            } else {
                const res = await axios.get('/api/reservations?limit=50');
                setReservations(res.data.data.reservations);
            }
        } catch (error) {
            console.error("Failed to fetch data", error);
        } finally {
            setLoading(false);
        }
    };

    const updateOrderStatus = async (id, newStatus) => {
        try {
            await axios.put(`/api/orders/${id}/status`, { status: newStatus });
            setRefreshTrigger(prev => prev + 1);
        } catch (error) {
            alert("Failed to update status");
        }
    };

    const updateReservationStatus = async (id, newStatus) => {
        try {
            await axios.put(`/api/reservations/${id}/status`, { status: newStatus });
            setRefreshTrigger(prev => prev + 1);
        } catch (error) {
            alert("Failed to update status");
        }
    };

    // Show loading while checking auth
    if (checkingAuth) {
        return (
            <div className="container page-padding">
                <div className="loading-state">
                    <RefreshCw className="animate-spin" /> Verifying access...
                </div>
            </div>
        );
    }

    // Show login if not authenticated
    if (!isAuthenticated) {
        return <AdminLogin onLoginSuccess={() => setIsAuthenticated(true)} />;
    }

    return (
        <div className="container page-padding">
            <div className="admin-header">
                <h1>Dashboard</h1>
                <div className="header-actions">
                    <button className="btn btn-secondary icon-btn" onClick={() => setRefreshTrigger(prev => prev + 1)}>
                        <RefreshCw size={18} /> Refresh
                    </button>
                    <button className="btn btn-danger-outline icon-btn" onClick={handleLogout}>
                        <LogOut size={18} /> Logout
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="admin-tabs">
                <button
                    className={`tab-btn ${activeTab === 'orders' ? 'active' : ''}`}
                    onClick={() => setActiveTab('orders')}
                >
                    <ClipboardList size={20} /> Orders
                </button>
                <button
                    className={`tab-btn ${activeTab === 'reservations' ? 'active' : ''}`}
                    onClick={() => setActiveTab('reservations')}
                >
                    <Calendar size={20} /> Reservations
                </button>
            </div>

            {/* Content */}
            <div className="admin-content">
                {loading ? (
                    <div className="loading-state">
                        <RefreshCw className="animate-spin" /> Loading...
                    </div>
                ) : (
                    <AnimatePresence mode='wait'>
                        <motion.div
                            key={activeTab}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                        >
                            {activeTab === 'orders' ? (
                                <OrdersList orders={orders} onUpdateStatus={updateOrderStatus} />
                            ) : (
                                <ReservationsList reservations={reservations} onUpdateStatus={updateReservationStatus} />
                            )}
                        </motion.div>
                    </AnimatePresence>
                )}
            </div>
        </div>
    );
}

// Sub-components for cleaner code
function OrdersList({ orders, onUpdateStatus }) {
    if (orders.length === 0) return <EmptyState message="No active orders found." />;

    return (
        <div className="list-grid">
            {orders.map(order => (
                <div key={order.id} className="card admin-card">
                    <div className="card-header">
                        <div className="header-left">
                            <span className="id-badge">#{order.orderNumber}</span>
                            <span className={`status-badge ${order.status}`}>{order.status}</span>
                        </div>
                        <span className="time">{new Date(order.createdAt).toLocaleTimeString()}</span>
                    </div>

                    <div className="card-body">
                        <h3>{order.customerName}</h3>
                        <p className="contact">{order.customerPhone}</p>
                        <div className="items-list">
                            {order.orderItems.map((item, idx) => (
                                <div key={idx} className="order-item-row">
                                    <span>{item.quantity}x {item.name}</span>
                                    <span className="price">${item.price}</span>
                                </div>
                            ))}
                        </div>
                        <div className="total-row">
                            <strong>Total</strong>
                            <strong>${order.totalPrice.toFixed(2)}</strong>
                        </div>
                    </div>

                    <div className="card-actions">
                        {order.status === 'pending' && (
                            <button
                                className="btn btn-sm btn-primary"
                                onClick={() => onUpdateStatus(order.id, 'preparing')}
                            >
                                Mark Preparing
                            </button>
                        )}
                        {order.status === 'preparing' && (
                            <button
                                className="btn btn-sm btn-success"
                                onClick={() => onUpdateStatus(order.id, 'ready')}
                            >
                                Mark Ready
                            </button>
                        )}
                        {order.status === 'ready' && (
                            <button
                                className="btn btn-sm btn-secondary"
                                onClick={() => onUpdateStatus(order.id, 'completed')}
                            >
                                Complete
                            </button>
                        )}
                        {order.status !== 'cancelled' && order.status !== 'completed' && (
                            <button
                                className="btn btn-sm btn-danger-outline"
                                onClick={() => onUpdateStatus(order.id, 'cancelled')}
                            >
                                Cancel
                            </button>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}

function ReservationsList({ reservations, onUpdateStatus }) {
    if (reservations.length === 0) return <EmptyState message="No reservations found." />;

    return (
        <div className="list-grid">
            {reservations.map(res => (
                <div key={res.id} className="card admin-card">
                    <div className="card-header">
                        <div className="header-left">
                            <span className="id-badge">#{res.reservationNumber}</span>
                            <span className={`status-badge ${res.status}`}>{res.status.replace('_', ' ')}</span>
                        </div>
                        <div className="date-time">
                            <Calendar size={14} /> {res.reservationDate} <Clock size={14} /> {res.reservationTime}
                        </div>
                    </div>

                    <div className="card-body">
                        <div className="customer-info">
                            <Users size={16} /> <strong>{res.partySize} Guests</strong>
                        </div>
                        <h3>{res.customerName}</h3>
                        <p className="contact">{res.customerPhone}</p>
                        {res.specialRequests && (
                            <p className="notes">"{res.specialRequests}"</p>
                        )}
                    </div>

                    <div className="card-actions">
                        {res.status === 'pending' && (
                            <>
                                <button
                                    className="btn btn-sm btn-primary"
                                    onClick={() => onUpdateStatus(res.id, 'confirmed')}
                                >
                                    Confirm
                                </button>
                                <button
                                    className="btn btn-sm btn-danger-outline"
                                    onClick={() => onUpdateStatus(res.id, 'cancelled')}
                                >
                                    Cancel
                                </button>
                            </>
                        )}
                        {res.status === 'confirmed' && (
                            <>
                                <button
                                    className="btn btn-sm btn-success"
                                    onClick={() => onUpdateStatus(res.id, 'arrived')}
                                >
                                    Guest Arrived
                                </button>
                                <button
                                    className="btn btn-sm btn-warning"
                                    onClick={() => onUpdateStatus(res.id, 'no_show')}
                                >
                                    No Show
                                </button>
                                <button
                                    className="btn btn-sm btn-danger-outline"
                                    onClick={() => onUpdateStatus(res.id, 'cancelled')}
                                >
                                    Cancel
                                </button>
                            </>
                        )}
                        {res.status === 'arrived' && (
                            <>
                                <button
                                    className="btn btn-sm btn-primary"
                                    onClick={() => onUpdateStatus(res.id, 'seated')}
                                >
                                    Seat Guest
                                </button>
                                <button
                                    className="btn btn-sm btn-danger-outline"
                                    onClick={() => onUpdateStatus(res.id, 'cancelled')}
                                >
                                    Cancel
                                </button>
                            </>
                        )}
                        {res.status === 'seated' && (
                            <button
                                className="btn btn-sm btn-success"
                                onClick={() => onUpdateStatus(res.id, 'completed')}
                            >
                                Complete
                            </button>
                        )}
                        {res.status === 'no_show' && (
                            <button
                                className="btn btn-sm btn-secondary"
                                onClick={() => onUpdateStatus(res.id, 'cancelled')}
                            >
                                Cancel
                            </button>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}

function EmptyState({ message }) {
    return (
        <div className="empty-state">
            <AlertCircle size={48} className="text-muted" />
            <p>{message}</p>
        </div>
    );
}
