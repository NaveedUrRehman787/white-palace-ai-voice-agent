import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search, Loader2 } from 'lucide-react';
import axios from 'axios';

export default function Menu() {
    const [items, setItems] = useState([]);
    const [categories, setCategories] = useState({});
    const [loading, setLoading] = useState(true);
    const [activeCategory, setActiveCategory] = useState('all');
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        fetchMenu();
        fetchCategories();
    }, []);

    const fetchMenu = async () => {
        try {
            setLoading(true);
            const res = await axios.get('/api/menu');
            setItems(res.data.data.items);
        } catch (error) {
            console.error("Error fetching menu:", error);
        } finally {
            setLoading(false);
        }
    };

    const fetchCategories = async () => {
        try {
            const res = await axios.get('/api/menu/categories');
            setCategories(res.data.categories);
        } catch (error) {
            console.error("Error fetching categories:", error);
        }
    }

    const filteredItems = items.filter(item => {
        const matchesCategory = activeCategory === 'all' || item.category.toLowerCase() === activeCategory.toLowerCase();
        const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            item.description.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesCategory && matchesSearch;
    });

    const categoryList = ['all', ...Object.keys(categories)];

    return (
        <div className="menu-page container page-padding">
            <div className="page-header">
                <h1>Our Menu</h1>
                <p>Fresh ingredients, classic recipes, served 24/7.</p>
            </div>

            {/* Controls */}
            <div className="menu-controls">
                <div className="search-bar">
                    <Search size={20} className="search-icon" />
                    <input
                        type="text"
                        placeholder="Search menu..."
                        className="input search-input"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>

                <div className="category-scroll">
                    {categoryList.map(cat => (
                        <button
                            key={cat}
                            className={`btn btn-sm ${activeCategory === cat ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setActiveCategory(cat)}
                        >
                            {cat.charAt(0).toUpperCase() + cat.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            {/* Grid */}
            {loading ? (
                <div className="loading-state">
                    <Loader2 className="animate-spin" size={40} color="var(--color-primary)" />
                </div>
            ) : (
                <div className="menu-grid">
                    {filteredItems.map((item) => (
                        <motion.div
                            key={item.id}
                            layout
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="card menu-item-card"
                        >
                            <div className="menu-item-header">
                                <h3>{item.name}</h3>
                                <span className="price">${item.price.toFixed(2)}</span>
                            </div>
                            <p className="description">{item.description}</p>
                            <span className="badge">{item.category}</span>
                        </motion.div>
                    ))}
                </div>
            )}
        </div>
    );
}
