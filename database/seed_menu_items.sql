-- Seed White Palace Grill Menu Items
-- All items with prices and categories

-- ============================================
-- BREAKFAST ITEMS (8 items)
-- ============================================
INSERT INTO menu_items (restaurant_id, name, description, price, category, availability, preparation_time) VALUES
(1, 'Two Eggs & Toast', 'Two eggs your way with buttered toast', 4.95, 'breakfast', true, 8),
(1, 'Three Egg Omelette', 'Three egg omelette with cheese and your choice of fillings', 7.95, 'breakfast', true, 12),
(1, 'Pancakes', 'Stack of fluffy pancakes with butter and syrup', 6.95, 'breakfast', true, 10),
(1, 'French Toast', 'Golden French toast with cinnamon and powdered sugar', 6.95, 'breakfast', true, 10),
(1, 'Breakfast Sandwich', 'Egg, cheese, and choice of bacon or sausage on toast', 5.95, 'breakfast', true, 9),
(1, 'Corned Beef Hash', 'Crispy corned beef hash with two eggs', 8.95, 'breakfast', true, 12),
(1, 'Waffle', 'Crispy waffle with butter and syrup', 5.95, 'breakfast', true, 10),
(1, 'Home Fries', 'Seasoned crispy home fried potatoes', 3.95, 'breakfast', true, 8);

-- ============================================
-- BURGERS (12 items)
-- ============================================
INSERT INTO menu_items (restaurant_id, name, description, price, category, availability, preparation_time) VALUES
(1, 'Classic Burger', 'Single patty with lettuce, tomato, onion, and pickle', 5.95, 'burgers', true, 10),
(1, 'Double Burger', 'Two beef patties with all the classics', 7.95, 'burgers', true, 12),
(1, 'Triple Burger', 'Three beef patties, perfect for the hungry', 9.95, 'burgers', true, 14),
(1, 'Cheese Burger', 'Classic burger topped with American cheese', 6.95, 'burgers', true, 11),
(1, 'Double Cheese Burger', 'Two patties with double cheese', 8.95, 'burgers', true, 13),
(1, 'Mushroom Burger', 'Burger with grilled mushrooms and Swiss cheese', 7.95, 'burgers', true, 12),
(1, 'Bacon Burger', 'Classic burger loaded with crispy bacon', 8.95, 'burgers', true, 12),
(1, 'Chili Burger', 'Burger topped with spicy White Palace chili', 7.95, 'burgers', true, 13),
(1, 'Fried Onion Burger', 'Patty topped with crispy fried onions', 6.95, 'burgers', true, 11),
(1, 'Deluxe Burger', 'Loaded burger with bacon, cheese, mushrooms', 9.95, 'burgers', true, 14),
(1, 'Western Burger', 'Burger with chili, cheese, and fried onions', 8.95, 'burgers', true, 13),
(1, 'Palace Burger', 'House specialty with special sauce and premium toppings', 10.95, 'burgers', true, 15);

-- ============================================
-- SANDWICHES (10 items)
-- ============================================
INSERT INTO menu_items (restaurant_id, name, description, price, category, availability, preparation_time) VALUES
(1, 'Hot Dog', 'Classic all-beef hot dog', 3.95, 'sandwiches', true, 6),
(1, 'Cheese Dog', 'Hot dog with melted cheese', 4.95, 'sandwiches', true, 7),
(1, 'Chili Dog', 'Hot dog topped with White Palace chili', 5.95, 'sandwiches', true, 9),
(1, 'Grilled Cheese', 'Melted cheese on buttered toast', 4.95, 'sandwiches', true, 8),
(1, 'Tuna Melt', 'Tuna salad with melted cheese on toast', 7.95, 'sandwiches', true, 11),
(1, 'Roast Beef Sandwich', 'Tender roast beef on a roll with gravy', 8.95, 'sandwiches', true, 12),
(1, 'Turkey Club', 'Turkey, bacon, lettuce, tomato on toast', 8.95, 'sandwiches', true, 11),
(1, 'Ham & Cheese Sandwich', 'Sliced ham with Swiss cheese on rye', 7.95, 'sandwiches', true, 10),
(1, 'Tuna Sandwich', 'Fresh tuna salad on toast', 7.95, 'sandwiches', true, 11),
(1, 'Chicken Salad Sandwich', 'Creamy chicken salad on toast', 7.95, 'sandwiches', true, 10);

-- ============================================
-- ENTREES (8 items)
-- ============================================
INSERT INTO menu_items (restaurant_id, name, description, price, category, availability, preparation_time) VALUES
(1, 'Meatloaf Dinner', 'Homemade meatloaf with mashed potatoes and gravy', 11.95, 'entrees', true, 20),
(1, 'Fried Chicken', 'Golden fried chicken with sides', 11.95, 'entrees', true, 18),
(1, 'Roast Turkey Dinner', 'Sliced turkey with dressing and gravy', 12.95, 'entrees', true, 20),
(1, 'Beef Stew', 'Hearty beef stew with vegetables', 10.95, 'entrees', true, 20),
(1, 'Grilled Fish', 'Fresh grilled fish with lemon butter sauce', 12.95, 'entrees', true, 18),
(1, 'Breaded Pork Chops', 'Tender pork chops with apple sauce', 11.95, 'entrees', true, 18),
(1, 'Liver & Onions', 'Sautéed calf liver with grilled onions', 10.95, 'entrees', true, 16),
(1, 'Baked Chicken', 'Herb-roasted chicken with sides', 11.95, 'entrees', true, 18);

-- ============================================
-- SIDES (8 items)
-- ============================================
INSERT INTO menu_items (restaurant_id, name, description, price, category, availability, preparation_time) VALUES
(1, 'Mashed Potatoes', 'Creamy mashed potatoes with gravy', 3.95, 'sides', true, 8),
(1, 'French Fries', 'Golden crispy French fries', 3.95, 'sides', true, 7),
(1, 'Sweet Potato Fries', 'Crispy sweet potato fries', 4.95, 'sides', true, 8),
(1, 'Onion Rings', 'Golden battered onion rings', 4.95, 'sides', true, 8),
(1, 'Coleslaw', 'Fresh crispy coleslaw', 2.95, 'sides', true, 5),
(1, 'Pickle Spear', 'Tangy dill pickle spear', 1.95, 'sides', true, 2),
(1, 'Corn', 'Fresh buttered corn on the cob', 3.95, 'sides', true, 8),
(1, 'Baked Beans', 'Slow-cooked baked beans', 3.95, 'sides', true, 10);

-- ============================================
-- SOUPS (5 items)
-- ============================================
INSERT INTO menu_items (restaurant_id, name, description, price, category, availability, preparation_time) VALUES
(1, 'Chicken Noodle Soup', 'Classic chicken noodle soup', 4.95, 'soups', true, 5),
(1, 'Vegetable Soup', 'Fresh vegetable soup with broth', 4.95, 'soups', true, 5),
(1, 'Tomato Soup', 'Creamy tomato soup', 4.95, 'soups', true, 5),
(1, 'Beef Barley Soup', 'Hearty beef and barley soup', 5.95, 'soups', true, 8),
(1, 'White Palace Chili', 'Famous White Palace chili', 5.95, 'soups', true, 10);

-- ============================================
-- SALADS (5 items)
-- ============================================
INSERT INTO menu_items (restaurant_id, name, description, price, category, availability, preparation_time) VALUES
(1, 'Garden Salad', 'Fresh mixed greens with vegetables', 6.95, 'salads', true, 7),
(1, 'Caesar Salad', 'Crisp romaine with parmesan and croutons', 7.95, 'salads', true, 8),
(1, 'Chicken Salad', 'Mixed greens with grilled chicken', 9.95, 'salads', true, 12),
(1, 'Tuna Salad', 'Mixed greens with tuna salad', 9.95, 'salads', true, 10),
(1, 'Cobb Salad', 'Mixed greens with bacon, egg, avocado, cheese', 10.95, 'salads', true, 12);

-- ============================================
-- DESSERTS (6 items)
-- ============================================
INSERT INTO menu_items (restaurant_id, name, description, price, category, availability, preparation_time) VALUES
(1, 'Apple Pie', 'Homemade apple pie with ice cream', 5.95, 'desserts', true, 8),
(1, 'Chocolate Cake', 'Rich chocolate cake with frosting', 5.95, 'desserts', true, 5),
(1, 'Cheesecake', 'New York style cheesecake', 6.95, 'desserts', true, 5),
(1, 'Pecan Pie', 'Sweet pecan pie with whipped cream', 6.95, 'desserts', true, 8),
(1, 'Ice Cream Sundae', 'Ice cream with toppings of your choice', 5.95, 'desserts', true, 5),
(1, 'Pie à la Mode', 'Your choice of pie with ice cream', 6.95, 'desserts', true, 8);

-- ============================================
-- BEVERAGES (6 items)
-- ============================================
INSERT INTO menu_items (restaurant_id, name, description, price, category, availability, preparation_time) VALUES
(1, 'Coffee', 'Fresh brewed coffee', 2.95, 'beverages', true, 3),
(1, 'Iced Coffee', 'Cold refreshing iced coffee', 3.95, 'beverages', true, 5),
(1, 'Soft Drink', 'Coca-Cola, Sprite, or other sodas (12 oz)', 2.95, 'beverages', true, 2),
(1, 'Orange Juice', 'Fresh squeezed orange juice', 3.95, 'beverages', true, 5),
(1, 'Milkshake', 'Classic milkshake - vanilla, chocolate, or strawberry', 4.95, 'beverages', true, 8),
(1, 'Iced Tea', 'Refreshing iced tea', 2.95, 'beverages', true, 3);
