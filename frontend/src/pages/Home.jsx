import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

export default function Home() {
    return (
        <div className="home-page">
            {/* Hero Section */}
            <section className="hero">
                <div className="container hero-content">
                    <motion.h1
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="hero-title"
                    >
                        Taste the Legend <br />
                        <span className="text-primary">Open 24/7 in Chicago</span>
                    </motion.h1>

                    <motion.p
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="hero-subtitle"
                    >
                        Serving classic diner favorites since 1939. Experience the nostalgia,
                        taste the quality, anytime you want.
                    </motion.p>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="hero-actions"
                    >
                        <Link to="/menu" className="btn btn-primary">View Menu</Link>
                        <Link to="/reservations" className="btn btn-secondary">Book a Table</Link>
                    </motion.div>
                </div>
            </section>

            {/* Features Grid */}
            <section className="features container">
                <div className="feature-card">
                    <div className="feature-icon">🍳</div>
                    <h3>All Day Breakfast</h3>
                    <p>Pancakes, omelets, and skillets served anytime you crave them.</p>
                </div>
                <div className="feature-card">
                    <div className="feature-icon">🍔</div>
                    <h3>Classic Burgers</h3>
                    <p>Juicy, hand-packed burgers made fresh to order.</p>
                </div>
                <div className="feature-card">
                    <div className="feature-icon">🎙️</div>
                    <h3>AI Voice Ordering</h3>
                    <p>Experience the future with our AI voice assistant for quick orders.</p>
                    <Link to="/voice-agent" className="text-primary">Try it now &rarr;</Link>
                </div>
            </section>
        </div>
    );
}
