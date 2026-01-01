import { useState } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Users, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import axios from 'axios';

export default function Reservations() {
    const [formData, setFormData] = useState({
        partySize: 2,
        reservationDate: new Date().toISOString().split('T')[0],
        reservationTime: '19:00',
        customerName: '',
        customerPhone: '',
        specialRequests: ''
    });

    const [availability, setAvailability] = useState(null); // null, 'checking', 'available', 'unavailable'
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);

    const checkAvailability = async (e) => {
        e.preventDefault();
        setAvailability('checking');
        try {
            const res = await axios.post('/api/reservations/availability', {
                reservationDate: formData.reservationDate,
                reservationTime: formData.reservationTime,
                partySize: formData.partySize
            });

            if (res.data.available) {
                setAvailability('available');
                setMessage(res.data.message);
            } else {
                setAvailability('unavailable');
                setMessage(res.data.message);
            }
        } catch (error) {
            setAvailability('error');
            setMessage("Could not check availability. Please try again.");
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            const res = await axios.post('/api/reservations', formData);
            if (res.data.status === 'success') {
                setSuccess(true);
                setMessage(`Reservation confirmed! Your confirmation number is ${res.data.data.reservationNumber}`);
            }
        } catch (error) {
            setMessage("Error creating reservation. Please try calling us.");
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e) => {
        setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
        // Reset availability check if critical fields change
        if (['reservationDate', 'reservationTime', 'partySize'].includes(e.target.name)) {
            setAvailability(null);
            setMessage('');
        }
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
                    <h2>Table Booked!</h2>
                    <p>{message}</p>
                    <div className="reservation-details">
                        <div className="detail-item">
                            <Calendar size={20} />
                            <span>{formData.reservationDate} at {formData.reservationTime}</span>
                        </div>
                        <div className="detail-item">
                            <Users size={20} />
                            <span>Party of {formData.partySize}</span>
                        </div>
                    </div>
                    <button onClick={() => setSuccess(false)} className="btn btn-primary">Make Another</button>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="container page-padding">
            <div className="page-header">
                <h1>Reservations</h1>
                <p>Join us for an unforgettable dining experience.</p>
            </div>

            <div className="reservation-container">
                <motion.div
                    className="card reservation-form-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <form onSubmit={availability === 'available' ? handleSubmit : checkAvailability}>

                        {/* Step 1: Details */}
                        <div className="form-group">
                            <label>Party Size</label>
                            <div className="input-with-icon">
                                <Users size={18} />
                                <input
                                    type="number"
                                    name="partySize"
                                    min="1"
                                    max="20"
                                    className="input"
                                    value={formData.partySize}
                                    onChange={handleChange}
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label>Date</label>
                                <div className="input-with-icon">
                                    <Calendar size={18} />
                                    <input
                                        type="date"
                                        name="reservationDate"
                                        className="input"
                                        value={formData.reservationDate}
                                        onChange={handleChange}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Time</label>
                                <div className="input-with-icon">
                                    <Clock size={18} />
                                    <input
                                        type="time"
                                        name="reservationTime"
                                        className="input"
                                        value={formData.reservationTime}
                                        onChange={handleChange}
                                        required
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Availability Status Message */}
                        {message && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                className={`status-message ${availability}`}
                            >
                                {availability === 'unavailable' && <AlertCircle size={18} />}
                                {availability === 'available' && <CheckCircle size={18} />}
                                <span>{message}</span>
                            </motion.div>
                        )}

                        {/* Step 2: Contact Info (Only show if available) */}
                        {availability === 'available' && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="contact-fields"
                            >
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
                                    <label>Special Requests</label>
                                    <textarea
                                        name="specialRequests"
                                        className="input"
                                        rows="3"
                                        value={formData.specialRequests}
                                        onChange={handleChange}
                                    />
                                </div>
                            </motion.div>
                        )}

                        <button
                            type="submit"
                            className={`btn btn-block ${availability === 'available' ? 'btn-primary' : 'btn-secondary'}`}
                            disabled={loading || availability === 'checking'}
                        >
                            {loading || availability === 'checking' ? (
                                <Loader2 className="animate-spin" />
                            ) : availability === 'available' ? (
                                'Confirm Booking'
                            ) : (
                                'Check Availability'
                            )}
                        </button>
                    </form>
                </motion.div>
            </div>
        </div>
    );
}
