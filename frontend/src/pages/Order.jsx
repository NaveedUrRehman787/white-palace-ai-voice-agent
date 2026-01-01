import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ShoppingCart, Plus, Minus, Trash2, Loader2, CheckCircle } from 'lucide-react';
import axios from 'axios';

export default function Order() {
    const [menuItems, setMenuItems] = useState([]);
    const [cart, setCart] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [success, setSuccess] = useState(false);
    const [orderNumber, setOrderNumber] = useState('');
    const [formData, setFormData] = useState({
        customerName: '',
        customerPhone: '',
        orderType: 'pickup',
        deliveryAddress: '',
        specialRequests: ''
    });

    useEffect(() => {
        fetchMenu();
    }, []);

    const fetchMenu = async () => {
        try {
            const res = await axios.get('/api/menu');
            setMenuItems(res.data.data.items || []);
        } catch (error) {
            console.error("Error fetching menu:", error);
        } finally {
            setLoading(false);
        }
    };

    const addToCart = (item) => {
        const exists = cart.find(c => c.menuItemId === item.id);
        if (exists) {
            setCart(cart.map(c =>
                c.menuItemId === item.id
                    ? { ...c, quantity: c.quantity + 1 }
                    : c
            ));
        } else {
            setCart([...cart, {
                menuItemId: item.id,
                name: item.name,
                price: item.price,
                quantity: 1
            }]);
        }
    };

    const updateQuantity = (menuItemId, delta) => {
        setCart(cart.map(item => {
            if (item.menuItemId === menuItemId) {
                const newQty = item.quantity + delta;
                return newQty > 0 ? { ...item, quantity: newQty } : null;
            }
            return item;
        }).filter(Boolean));
    };

    const removeFromCart = (menuItemId) => {
        setCart(cart.filter(item => item.menuItemId !== menuItemId));
    };

    const getTotal = () => {
        return cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (cart.length === 0) {
            alert("Please add items to your order.");
            return;
        }

        setSubmitting(true);

        try {
            const payload = {
                items: cart,
                orderType: formData.orderType,
                customerName: formData.customerName,
                customerPhone: formData.customerPhone,
                deliveryAddress: formData.orderType === 'delivery' ? formData.deliveryAddress : null,
                specialRequests: formData.specialRequests || null
            };

            const res = await axios.post('/api/orders', payload);

            if (res.data.status === 'success') {
                setSuccess(true);
                setOrderNumber(res.data.data.orderNumber);
                setCart([]);
            }
        } catch (error) {
            console.error("Error creating order:", error);
            alert("Failed to create order. Please try again.");
        } finally {
            setSubmitting(false);
        }
    };

    const handleChange = (e) => {
        setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
    };

    if (success) {
        return (
            <div className="container page-padding">
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="card success-card"
                >
                    <CheckCircle size={64} className="text-success" />
                    <h2>Order Placed!</h2>
                    <p>Your order number is:</p>
                    <p className="order-number">{orderNumber}</p>
                    <button onClick={() => { setSuccess(false); setFormData({ customerName: '', customerPhone: '', orderType: 'pickup', deliveryAddress: '', specialRequests: '' }); }} className="btn btn-primary">
                        Place Another Order
                    </button>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="container page-padding">
            <div className="page-header">
                <h1>Order Online</h1>
                <p>Build your order and we'll have it ready for you.</p>
            </div>

            <div className="order-layout">
                {/* Menu Section */}
                <div className="menu-section">
                    <h2>Menu</h2>
                    {loading ? (
                        <div className="loading-state">
                            <Loader2 className="animate-spin" /> Loading menu...
                        </div>
                    ) : (
                        <div className="menu-items-list">
                            {menuItems.map(item => (
                                <div key={item.id} className="menu-item-row card">
                                    <div className="item-info">
                                        <h4>{item.name}</h4>
                                        <p className="description">{item.description}</p>
                                        <span className="price">${item.price.toFixed(2)}</span>
                                    </div>
                                    <button
                                        className="btn btn-sm btn-primary add-btn"
                                        onClick={() => addToCart(item)}
                                    >
                                        <Plus size={16} /> Add
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Cart & Checkout Section */}
                <div className="cart-section">
                    <div className="card cart-card">
                        <h2><ShoppingCart size={24} /> Your Order</h2>

                        {cart.length === 0 ? (
                            <p className="empty-cart">Your cart is empty. Add items from the menu.</p>
                        ) : (
                            <div className="cart-items">
                                {cart.map(item => (
                                    <div key={item.menuItemId} className="cart-item">
                                        <div className="cart-item-info">
                                            <span className="item-name">{item.name}</span>
                                            <span className="item-price">${(item.price * item.quantity).toFixed(2)}</span>
                                        </div>
                                        <div className="cart-item-controls">
                                            <button className="qty-btn" onClick={() => updateQuantity(item.menuItemId, -1)}>
                                                <Minus size={14} />
                                            </button>
                                            <span className="qty">{item.quantity}</span>
                                            <button className="qty-btn" onClick={() => updateQuantity(item.menuItemId, 1)}>
                                                <Plus size={14} />
                                            </button>
                                            <button className="remove-btn" onClick={() => removeFromCart(item.menuItemId)}>
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    </div>
                                ))}

                                <div className="cart-total">
                                    <strong>Subtotal</strong>
                                    <strong>${getTotal().toFixed(2)}</strong>
                                </div>
                            </div>
                        )}

                        {/* Customer Info Form */}
                        <form onSubmit={handleSubmit} className="checkout-form">
                            <div className="form-group">
                                <label>Name</label>
                                <input
                                    type="text"
                                    name="customerName"
                                    className="input"
                                    placeholder="Your Name"
                                    value={formData.customerName}
                                    onChange={handleChange}
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label>Phone</label>
                                <input
                                    type="tel"
                                    name="customerPhone"
                                    className="input"
                                    placeholder="(555) 555-5555"
                                    value={formData.customerPhone}
                                    onChange={handleChange}
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label>Order Type</label>
                                <select
                                    name="orderType"
                                    className="input"
                                    value={formData.orderType}
                                    onChange={handleChange}
                                >
                                    <option value="pickup">Pickup</option>
                                    <option value="dine-in">Dine-In</option>
                                    <option value="delivery">Delivery</option>
                                </select>
                            </div>

                            {formData.orderType === 'delivery' && (
                                <div className="form-group">
                                    <label>Delivery Address</label>
                                    <textarea
                                        name="deliveryAddress"
                                        className="input"
                                        placeholder="Enter your delivery address"
                                        value={formData.deliveryAddress}
                                        onChange={handleChange}
                                        required
                                    />
                                </div>
                            )}

                            <div className="form-group">
                                <label>Special Requests (optional)</label>
                                <textarea
                                    name="specialRequests"
                                    className="input"
                                    placeholder="Any special instructions?"
                                    value={formData.specialRequests}
                                    onChange={handleChange}
                                    rows="2"
                                />
                            </div>

                            <button
                                type="submit"
                                className="btn btn-primary btn-block"
                                disabled={submitting || cart.length === 0}
                            >
                                {submitting ? <Loader2 className="animate-spin" /> : 'Place Order'}
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
}
