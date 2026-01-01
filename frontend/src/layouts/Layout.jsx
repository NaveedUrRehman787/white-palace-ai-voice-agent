import { Link, Outlet, useLocation } from 'react-router-dom';
import { ChefHat, Phone, Calendar, Menu as MenuIcon, X, ShoppingCart, Settings } from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Layout() {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const location = useLocation();

    const navLinks = [
        { name: 'Home', path: '/', icon: <ChefHat size={18} /> },
        { name: 'Menu', path: '/menu', icon: <MenuIcon size={18} /> },
        { name: 'Order', path: '/order', icon: <ShoppingCart size={18} /> },
        { name: 'Reservations', path: '/reservations', icon: <Calendar size={18} /> },
        { name: 'Voice Agent', path: '/voice-agent', icon: <Phone size={18} /> },
        // Admin is intentionally hidden - staff access via /admin with password
    ];

    return (
        <div className="layout">
            {/* Navigation */}
            <nav className="navbar">
                <div className="container nav-container">
                    <Link to="/" className="logo">
                        <span className="logo-icon">🍔</span>
                        <span className="logo-text">White Palace Grill</span>
                    </Link>

                    {/* Desktop Nav */}
                    <div className="nav-links desktop-only">
                        {navLinks.map((link) => (
                            <Link
                                key={link.path}
                                to={link.path}
                                className={`nav-link ${location.pathname === link.path ? 'active' : ''}`}
                            >
                                {link.icon}
                                {link.name}
                            </Link>
                        ))}
                    </div>

                    {/* Mobile Menu Button */}
                    <button
                        className="mobile-menu-btn mobile-only"
                        onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                    >
                        {isMobileMenuOpen ? <X /> : <MenuIcon />}
                    </button>
                </div>
            </nav>

            {/* Mobile Nav Overlay */}
            <AnimatePresence>
                {isMobileMenuOpen && (
                    <motion.div
                        className="mobile-nav"
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                    >
                        {navLinks.map((link) => (
                            <Link
                                key={link.path}
                                to={link.path}
                                className={`mobile-nav-link ${location.pathname === link.path ? 'active' : ''}`}
                                onClick={() => setIsMobileMenuOpen(false)}
                            >
                                {link.icon}
                                {link.name}
                            </Link>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Main Content */}
            <main className="main-content">
                <Outlet />
            </main>

            {/* Footer */}
            <footer className="footer">
                <div className="container">
                    <p>&copy; {new Date().getFullYear()} White Palace Grill. Open 24/7 in Chicago.</p>
                </div>
            </footer>
        </div>
    );
}
