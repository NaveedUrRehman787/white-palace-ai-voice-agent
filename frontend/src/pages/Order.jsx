import { useState, useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShoppingCart, Plus, Minus, Trash2, Loader2, CheckCircle, CreditCard, Lock } from 'lucide-react';
import axios from 'axios';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { useAuth } from '../contexts/AuthContext';

// Initialize Stripe
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || 'pk_test_...');

export default function Order() {
    const { isAuthenticated, loading: authLoading } = useAuth();
    const location = useLocation();

    const [menuItems, setMenuItems] = useState([]);
    const [cart, setCart] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [currentStep, setCurrentStep] = useState('cart'); // cart, details, payment, success
    const [orderData, setOrderData] = useState(null);
    const [paymentIntent, setPaymentIntent] = useState(null);
    const [formData, setFormData] = useState({
        customerName: '',
        customerPhone: '',
        orderType: 'pickup',
        deliveryAddress: '',
        specialRequests: ''
    });

    // Authentication guard - redirect to login if not authenticated
    if (!authLoading && !isAuthenticated) {
        return (
            <Navigate
                to="/login"
                state={{ from: location }}
                replace
            />
        );
    }

    // Show loading while checking authentication
    if (authLoading) {
        return (
            <div className="min-h-screen bg-bg-dark flex items-center justify-center">
                <div className="loading-state">
                    <Loader2 className="animate-spin" size={24} />
                    <span>Loading...</span>
                </div>
            </div>
        );
    }

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

    const proceedToDetails = () => {
        if (cart.length === 0) {
            alert("Please add items to your order first.");
            return;
        }
        setCurrentStep('details');
    };

    const proceedToPayment = async () => {
        // Validate form
        if (!formData.customerName || !formData.customerPhone) {
            alert("Please fill in your name and phone number.");
            return;
        }

        if (formData.orderType === 'delivery' && !formData.deliveryAddress) {
            alert("Please provide a delivery address.");
            return;
        }

        setSubmitting(true);

        try {
            // Create the order first
            const payload = {
                items: cart,
                orderType: formData.orderType,
                customerName: formData.customerName,
                customerPhone: formData.customerPhone,
                deliveryAddress: formData.orderType === 'delivery' ? formData.deliveryAddress : null,
                specialRequests: formData.specialRequests || null
            };

            const orderRes = await axios.post('/api/orders', payload);

            if (orderRes.data.status === 'success') {
                setOrderData(orderRes.data.data);

                // Create payment intent
                const paymentPayload = {
                    orderId: orderRes.data.data.id,
                    amount: getTotal(),
                    currency: 'USD',
                    customerEmail: `${formData.customerName.replace(' ', '.').toLowerCase()}@example.com`,
                    metadata: { order_number: orderRes.data.data.orderNumber }
                };

                const paymentRes = await axios.post('/api/payments/create-intent', paymentPayload);

                if (paymentRes.data.status === 'success') {
                    setPaymentIntent(paymentRes.data.data);
                    setCurrentStep('payment');
                } else {
                    alert("Failed to set up payment. Please try again.");
                }
            } else {
                alert("Failed to create order. Please try again.");
            }
        } catch (error) {
            console.error("Error in checkout process:", error);
            alert("Failed to process your order. Please try again.");
        } finally {
            setSubmitting(false);
        }
    };

    const handlePaymentSuccess = () => {
        setCurrentStep('success');
        setCart([]);
    };

    const goBack = () => {
        if (currentStep === 'details') setCurrentStep('cart');
        else if (currentStep === 'payment') setCurrentStep('details');
    };

    const handleChange = (e) => {
        setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
    };

    // Success step
    if (currentStep === 'success') {
        return (
            <div className="container page-padding">
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="card success-card"
                >
                    <CheckCircle size={64} className="text-success" />
                    <h2>Order Confirmed!</h2>
                    <p>Thank you for your payment. Your order has been confirmed.</p>
                    <p>Your order number is:</p>
                    <p className="order-number">{orderData?.orderNumber}</p>
                    <button
                        onClick={() => {
                            setCurrentStep('cart');
                            setOrderData(null);
                            setPaymentIntent(null);
                            setFormData({
                                customerName: '',
                                customerPhone: '',
                                orderType: 'pickup',
                                deliveryAddress: '',
                                specialRequests: ''
                            });
                        }}
                        className="btn btn-primary"
                    >
                        Place Another Order
                    </button>
                </motion.div>
            </div>
        );
    }

    // Payment step
    if (currentStep === 'payment' && paymentIntent) {
        return (
            <div className="container page-padding">
                <div className="page-header">
                    <h1>Complete Payment</h1>
                    <p>Secure payment for your order</p>
                </div>

                <div className="checkout-layout">
                    {/* Order Summary */}
                    <div className="order-summary card">
                        <h2>Order Summary</h2>
                        <p><strong>Order #{orderData?.orderNumber}</strong></p>
                        {cart.map(item => (
                            <div key={item.menuItemId} className="summary-item">
                                <span>{item.name} x{item.quantity}</span>
                                <span>${(item.price * item.quantity).toFixed(2)}</span>
                            </div>
                        ))}
                        <div className="summary-total">
                            <strong>Total: ${getTotal().toFixed(2)}</strong>
                        </div>
                    </div>

                    {/* Payment Form */}
                    <div className="payment-section card">
                        <h2><CreditCard size={24} /> Payment Details</h2>
                        <Elements stripe={stripePromise}>
                            <CheckoutForm
                                paymentIntent={paymentIntent}
                                onSuccess={handlePaymentSuccess}
                                onBack={goBack}
                            />
                        </Elements>
                    </div>
                </div>
            </div>
        );
    }

    // Details step
    if (currentStep === 'details') {
        return (
            <div className="container page-padding">
                <div className="page-header">
                    <h1>Customer Details</h1>
                    <p>Please provide your information to continue</p>
                </div>

                <div className="checkout-layout">
                    {/* Order Summary */}
                    <div className="order-summary card">
                        <h2>Order Summary</h2>
                        {cart.map(item => (
                            <div key={item.menuItemId} className="summary-item">
                                <span>{item.name} x{item.quantity}</span>
                                <span>${(item.price * item.quantity).toFixed(2)}</span>
                            </div>
                        ))}
                        <div className="summary-total">
                            <strong>Total: ${getTotal().toFixed(2)}</strong>
                        </div>
                    </div>

                    {/* Customer Details Form */}
                    <div className="details-section card">
                        <h2>Customer Information</h2>
                        <form onSubmit={(e) => { e.preventDefault(); proceedToPayment(); }}>
                            <div className="form-group">
                                <label>Name *</label>
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
                                <label>Phone *</label>
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
                                    <label>Delivery Address *</label>
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

                            <div className="form-buttons">
                                <button
                                    type="button"
                                    onClick={goBack}
                                    className="btn btn-secondary"
                                >
                                    Back to Cart
                                </button>
                                <button
                                    type="submit"
                                    className="btn btn-primary"
                                    disabled={submitting}
                                >
                                    {submitting ? <Loader2 className="animate-spin" /> : 'Continue to Payment'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        );
    }

    // Cart step (default)
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

                {/* Cart Section */}
                <div className="cart-section">
                    <div className="card cart-card">
                        <h2><ShoppingCart size={24} /> Your Order</h2>

                        {cart.length === 0 ? (
                            <p className="empty-cart">Your cart is empty. Add items from the menu.</p>
                        ) : (
                            <>
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
                                </div>

                                <div className="cart-total">
                                    <strong>Subtotal</strong>
                                    <strong>${getTotal().toFixed(2)}</strong>
                                </div>

                                <button
                                    onClick={proceedToDetails}
                                    className="btn btn-primary btn-block"
                                >
                                    Proceed to Checkout
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

// Stripe Checkout Form Component
function CheckoutForm({ paymentIntent, onSuccess, onBack }) {
    const stripe = useStripe();
    const elements = useElements();
    const [processing, setProcessing] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (event) => {
        event.preventDefault();

        if (!stripe || !elements) {
            return;
        }

        setProcessing(true);
        setError(null);

        const cardElement = elements.getElement(CardElement);

        try {
            const { error, paymentIntent: confirmedPaymentIntent } = await stripe.confirmCardPayment(
                paymentIntent.clientSecret,
                {
                    payment_method: {
                        card: cardElement,
                    }
                }
            );

            if (error) {
                setError(error.message);
            } else if (confirmedPaymentIntent.status === 'succeeded') {
                onSuccess();
            }
        } catch (err) {
            setError('Payment failed. Please try again.');
        }

        setProcessing(false);
    };

    const cardStyle = {
        style: {
            base: {
                fontSize: '16px',
                color: '#424770',
                '::placeholder': {
                    color: '#aab7c4',
                },
            },
            invalid: {
                color: '#9e2146',
            },
        },
    };

    return (
        <form onSubmit={handleSubmit} className="payment-form">
            <div className="form-group">
                <label>Card Information</label>
                <div className="card-element-container">
                    <CardElement options={cardStyle} />
                </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="form-buttons">
                <button
                    type="button"
                    onClick={onBack}
                    className="btn btn-secondary"
                    disabled={processing}
                >
                    Back
                </button>
                <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={!stripe || processing}
                >
                    {processing ? <Loader2 className="animate-spin" /> : `Pay $${(paymentIntent.amount / 100).toFixed(2)}`}
                </button>
            </div>
        </form>
    );
}
