# recipe_manager.py

# A simple, hardcoded dictionary for recipe data.
# For a production app, this would be loaded from a database, CSV, or external API.
# You can expand this list with more dishes as needed for your demo.
RECIPES_DATA = {
    "pasta": [
        "pasta",
        "tomato sauce",
        "garlic",
        "onion",
        "ground beef (optional)", # Can include notes within the item name for clarity
        "oregano",
        "parmesan cheese"
    ],
    "biryani": [
        "basmati rice",
        "chicken",
        "onions",
        "yogurt",
        "ginger-garlic paste",
        "biryani masala",
        "tomatoes",
        "fresh mint",
        "fresh cilantro"
    ],
    "chili": [
        "ground beef",
        "kidney beans",
        "diced tomatoes",
        "onion",
        "chili powder",
        "cumin",
        "bell pepper"
    ],
    "pancakes": [
        "all-purpose flour",
        "milk",
        "egg",
        "baking powder",
        "sugar",
        "salt",
        "butter"
    ],
    "omelette": [
        "eggs",
        "milk (optional)",
        "butter",
        "salt",
        "pepper",
        "cheese (optional)",
        "onion (optional)",
        "bell pepper (optional)"
    ],
    "pizza": [
        "pizza dough",
        "pizza sauce",
        "mozzarella cheese",
        "pepperoni (optional)",
        "mushrooms (optional)",
        "bell peppers (optional)"
    ],
    # --- 100 South Indian Dishes ---
    "dosa": ["rice", "urad dal", "fenugreek seeds", "salt", "oil"],
    "idli": ["rice", "urad dal", "fenugreek seeds", "salt"],
    "vada": ["urad dal", "onions", "green chillies", "ginger", "curry leaves", "salt", "oil"],
    "sambar": ["toor dal", "tamarind", "sambar powder", "vegetables", "mustard seeds", "curry leaves", "asafoetida"],
    "rasam": ["tamarind", "tomatoes", "rasam powder", "garlic", "mustard seeds", "curry leaves", "cilantro"],
    "uttapam": ["rice", "urad dal", "onions", "tomatoes", "green chillies", "cilantro", "salt", "oil"],
    "pongal": ["rice", "moong dal", "ghee", "cashews", "pepper", "cumin", "ginger"],
    "poori": ["wheat flour", "salt", "oil"],
    "upma": ["rava (semolina)", "onions", "green chillies", "mustard seeds", "curry leaves", "ghee"],
    "avial": ["mixed vegetables", "coconut", "yogurt", "green chillies", "cumin", "curry leaves"],
    "appam": ["rice flour", "coconut milk", "sugar", "yeast"],
    "puttu": ["rice flour", "grated coconut", "salt"],
    "kadala curry": ["black chickpeas", "coconut", "onions", "ginger", "garlic", "spices"],
    "porotta": ["maida (all-purpose flour)", "egg", "oil", "salt"],
    "fish moilee": ["fish", "coconut milk", "ginger", "garlic", "green chillies", "curry leaves"],
    "alleppey fish curry": ["fish", "raw mango", "coconut milk", "green chillies", "ginger", "curry leaves"],
    "malabar parotta": ["maida (all-purpose flour)", "egg", "oil", "salt"],
    "chemmeen curry": ["shrimp", "coconut milk", "ginger", "garlic", "green chillies", "spices"],
    "kerala style beef fry": ["beef", "onions", "ginger", "garlic", "curry leaves", "spices"],
    "ghee rice": ["basmati rice", "ghee", "onions", "cashews", "raisins", "spices"],
    "kozhi porichathu": ["chicken", "ginger", "garlic", "chilli powder", "turmeric", "curry leaves", "oil"],
    "kothu parotta": ["shredded parotta", "egg", "chicken/vegetables", "onions", "spices"],
    "paniyarappam": ["rice", "urad dal", "onions", "green chillies", "oil"],
    "adai": ["rice", "chana dal", "toor dal", "urad dal", "red chillies", "ginger", "curry leaves"],
    "set dosa": ["rice", "urad dal", "poha", "fenugreek seeds", "salt", "oil"],
    "masala dosa": ["dosa batter", "potatoes", "onions", "mustard seeds", "curry leaves", "turmeric"],
    "raagi mudde": ["ragi flour", "water"],
    "bisi bele bath": ["rice", "toor dal", "mixed vegetables", "bisi bele bath powder", "tamarind", "ghee"],
    "akki roti": ["rice flour", "onions", "green chillies", "dill leaves", "salt", "oil"],
    "ragi rotti": ["ragi flour", "onions", "green chillies", "dill leaves", "salt", "oil"],
    "ragi roti": ["ragi flour", "onions", "green chillies", "dill leaves", "salt", "oil"],
    "mysore pak": ["besan (gram flour)", "ghee", "sugar"],
    "obbattu_holige": ["maida", "chana dal", "jaggery", "cardamom"], # Corrected: Replaced '/' with '_'
    "kesari bath": ["rava (semolina)", "sugar", "ghee", "pineapple/banana", "cashews", "raisins", "saffron"],
    "chitranna": ["cooked rice", "lemon juice", "mustard seeds", "curry leaves", "peanuts", "turmeric"],
    "puliyogare": ["cooked rice", "tamarind", "jaggery", "peanuts", "mustard seeds", "curry leaves", "spices"],
    "kadubu": ["rice flour", "grated coconut", "jaggery"],
    "thatte idli": ["rice", "urad dal", "fenugreek seeds", "salt", "soda"],
    "benne dosa": ["dosa batter", "butter", "poha"],
    "chow chow bath": ["rava (semolina)", "sugar", "ghee", "salt", "mustard seeds", "curry leaves", "onions", "green chillies"],
    "neer dosa": ["rice", "salt", "oil"],
    "goli bajji": ["maida", "yogurt", "green chillies", "ginger", "cumin", "oil"],
    "mangalore bonda": ["maida", "yogurt", "green chillies", "ginger", "cumin", "oil"],
    "rava dosa": ["rava (semolina)", "rice flour", "maida", "onions", "green chillies", "cumin"],
    "vegetable kurma": ["mixed vegetables", "coconut", "cashews", "poppy seeds", "spices"],
    "vegetable kuruma": ["mixed vegetables", "coconut", "cashews", "poppy seeds", "spices"], # Alias
    "veg kurma": ["mixed vegetables", "coconut", "cashews", "poppy seeds", "spices"], # Alias
    "wheat dosa": ["whole wheat flour", "salt", "oil"],
    "adai dosa": ["rice", "mixed lentils", "red chillies", "ginger", "garlic"],
    "kuzhi paniyaram": ["rice", "urad dal", "onions", "green chillies", "oil"],
    "kozhukattai": ["rice flour", "grated coconut", "jaggery", "cardamom"],
    "semiya upma": ["vermicelli", "onions", "green chillies", "mustard seeds", "curry leaves"],
    "pulav": ["basmati rice", "mixed vegetables", "onions", "ginger", "garlic", "spices"],
    "veg stew": ["mixed vegetables", "coconut milk", "green chillies", "ginger", "curry leaves"],
    "chicken stew": ["chicken", "coconut milk", "potatoes", "carrots", "green chillies", "ginger", "curry leaves"],
    "veg biryani": ["basmati rice", "mixed vegetables", "onions", "yogurt", "spices"],
    "chicken biryani": ["basmati rice", "chicken", "onions", "yogurt", "spices"],
    "egg curry": ["eggs", "onions", "tomatoes", "ginger", "garlic", "spices"],
    "fish curry": ["fish", "onions", "tomatoes", "tamarind", "spices"],
    "parippu curry": ["moong dal", "coconut", "cumin", "green chillies"],
    "erissery": ["pumpkin", "black eyed peas", "coconut", "cumin", "green chillies"],
    "thoran": ["vegetable (e.g., beans, cabbage)", "grated coconut", "mustard seeds", "curry leaves"],
    "kalan": ["yam", "raw banana", "yogurt", "coconut", "cumin", "green chillies"],
    "olan": ["ash gourd", "black eyed peas", "coconut milk", "curry leaves"],
    "payasam": ["rice/vermicelli/dal", "milk", "sugar/jaggery", "ghee", "cashews", "raisins", "cardamom"],
    "unniyappam": ["rice flour", "jaggery", "banana", "cardamom", "ghee"],
    "bombay chutney": ["besan (gram flour)", "onions", "green chillies", "ginger", "turmeric"],
    "podi": ["roasted lentils", "red chillies", "garlic", "asafoetida", "salt"],
    "coconut chutney": ["grated coconut", "roasted chana dal", "green chillies", "ginger", "mustard seeds", "curry leaves"],
    "tomato chutney": ["tomatoes", "onions", "garlic", "red chillies", "tamarind"],
    "mint chutney": ["mint leaves", "cilantro", "green chillies", "ginger", "lemon juice"],
    "peanut chutney": ["roasted peanuts", "red chillies", "tamarind", "garlic"],
    "ginger chutney": ["ginger", "red chillies", "tamarind", "jaggery"],
    "gongura pachadi": ["gongura leaves", "red chillies", "coriander seeds", "cumin seeds"],
    "pesarattu": ["green gram (moong dal)", "rice", "ginger", "green chillies"],
    "mirchi bajji": ["large green chillies", "besan (gram flour)", "rice flour", "spices"],
    "punugulu": ["rice", "urad dal", "idli batter", "onions", "green chillies"],
    "uggani": ["puffed rice", "onions", "green chillies", "peanuts", "curry leaves"],
    "pesarattu upma": ["pesarattu", "upma"],
    "mysore bonda": ["maida", "yogurt", "green chillies", "ginger", "cumin", "oil"],
    "sundal": ["chickpeas/lentils", "mustard seeds", "curry leaves", "grated coconut"],
    "kuzhambu": ["tamarind", "toor dal", "vegetables", "sambar powder", "onions"],
    "moru curry": ["sour yogurt", "coconut", "cumin", "green chillies"],
    "theeyal": ["shallots", "coconut", "coriander powder", "chilli powder", "tamarind"],
    "kozhambu kulambu": ["vegetables", "tamarind", "sambar powder", "onions"], # Typo in list, assumed for clarity
    "kootu": ["lentils", "vegetables", "coconut", "cumin"],
    "poriyal": ["vegetable", "mustard seeds", "curry leaves", "grated coconut"],
    "rasavangi": ["brinjal", "toor dal", "tamarind", "sambar powder"],
    "kozhukattai sweet": ["rice flour", "coconut", "jaggery"],
    "modak": ["rice flour", "jaggery", "coconut", "cardamom"],
    "adai aval": ["poha", "jaggery", "coconut", "cardamom"],
    "ulundu vadai": ["urad dal", "onions", "green chillies", "ginger"],
    "paruppu vadai": ["chana dal", "onions", "green chillies", "fennel seeds"],
    "pazham pori": ["ripe plantains", "maida", "sugar", "cardamom"],
    "ullivada": ["onions", "besan (gram flour)", "rice flour", "spices"],
    "chakka appam": ["jackfruit", "rice flour", "jaggery", "coconut"],
    "idiappam": ["rice flour", "water", "salt"],
    "paneer butter masala": ["paneer", "tomatoes", "cream", "butter", "cashews", "spices"],
    "paneer": ["paneer"], # Added for general "paneer" command, can be refined.
    "dal makhani": ["black urad dal", "rajma (kidney beans)", "butter", "cream", "spices"],
    "gobhi manchurian": ["cauliflower", "maida", "corn flour", "soy sauce", "ginger", "garlic", "chillies"],
    "chicken 65": ["chicken", "curry leaves", "green chillies", "ginger", "garlic", "yogurt", "spices"],
    "chilli chicken": ["chicken", "bell peppers", "onions", "soy sauce", "chilli sauce", "ginger", "garlic"],
    "palak paneer": ["paneer", "spinach", "onions", "tomatoes", "cream", "spices"],
    "aloo gobi": ["potatoes", "cauliflower", "onions", "tomatoes", "spices"],
    "matar paneer": ["paneer", "peas", "onions", "tomatoes", "cream", "spices"],
    "bhindi masala": ["okra", "onions", "tomatoes", "spices"],
    "chana masala": ["chickpeas", "onions", "tomatoes", "spices"],
    "rajma chawal": ["kidney beans", "rice", "onions", "tomatoes", "spices"],
    "baingan bharta": ["eggplant", "onions", "tomatoes", "spices"],
    "lauki kofta": ["bottle gourd", "besan", "onions", "tomatoes", "spices"],
    "malai kofta": ["paneer", "potatoes", "cream", "cashews", "spices"],
    "navratan kurma": ["mixed vegetables", "paneer", "cream", "dry fruits", "spices"],
    "dum aloo": ["potatoes", "yogurt", "spices"],
    "shahi paneer": ["paneer", "cream", "cashews", "tomatoes", "spices"],
    "dal tadka": ["toor dal", "ghee", "garlic", "ginger", "chilli", "cumin"],
    "veg kolhapuri": ["mixed vegetables", "spicy kolhapuri masala", "coconut"],
    "paneer tikka masala": ["paneer tikka", "tomato gravy", "cream", "spices"],
    # --- 10 Italian Dishes ---
    "lasagna": ["lasagna noodles", "ground beef", "ricotta cheese", "mozzarella cheese", "marinara sauce", "parmesan cheese", "onions", "garlic"],
    "spaghetti carbonara": ["spaghetti", "eggs", "pecorino romano cheese", "guanciale/pancetta", "black pepper"],
    "risotto ai funghi": ["arborio rice", "mushrooms", "vegetable broth", "parmesan cheese", "onion", "garlic", "white wine"],
    "gnocchi with pesto": ["potatoes", "flour", "eggs", "basil", "pine nuts", "parmesan cheese", "garlic", "olive oil"],
    "focaccia bread": ["flour", "yeast", "olive oil", "rosemary", "salt"],
    "minestrone soup": ["mixed vegetables", "pasta/rice", "beans", "tomato broth", "herbs"],
    "tiramisu": ["espresso", "ladyfingers", "mascarpone cheese", "eggs", "sugar", "cocoa powder"],
    "arancini": ["risotto", "mozzarella cheese", "breadcrumbs", "oil for frying"],
    "osso buco": ["veal shanks", "vegetables", "white wine", "broth", "gremolata"],
    "caprese salad": ["fresh mozzarella", "tomatoes", "fresh basil", "balsamic glaze", "olive oil"]
}

def get_ingredients_for_dish(dish_name):
    """
    Retrieves a list of ingredients for a given dish name from the RECIPES_DATA.
    Performs a simple, case-insensitive lookup.
    """
    normalized_dish_name = dish_name.lower().strip()
    return RECIPES_DATA.get(normalized_dish_name, [])

# This function is no longer called directly from app.py as recipe population is integrated directly there.
# It's kept here as a reference if you were to use a different database setup.
def populate_recipes_db(app, db, Recipe, RecipeIngredient):
    """
    (Deprecated for current Firestore app.py) Populates the Recipe and RecipeIngredient tables from RECIPES_DATA.
    This function should typically be called once during application startup
    or when migrating/initializing your database.
    """
    pass # This function is a placeholder now, as Firestore population logic is in app.py

# Example Usage (for testing this module directly via `python recipe_manager.py`)
if __name__ == "__main__":
    print("--- Testing Recipe Manager ---")
    print(f"Ingredients for Pasta: {get_ingredients_for_dish('Pasta')}")
    print(f"Ingredients for Biryani: {get_ingredients_for_dish('Biryani')}")
    print(f"Ingredients for Pizza: {get_ingredients_for_dish('Pizza')}")
    print(f"Ingredients for Dosa: {get_ingredients_for_dish('Dosa')}")
    print(f"Ingredients for Lasagna: {get_ingredients_for_dish('Lasagna')}")
    print(f"Ingredients for Puliyogare: {get_ingredients_for_dish('Puliyogare')}")
    print(f"Ingredients for Vegetable Kurma: {get_ingredients_for_dish('Vegetable Kurma')}")
    print(f"Ingredients for Veg Kurma: {get_ingredients_for_dish('Veg Kurma')}")
    print(f"Ingredients for Paneer: {get_ingredients_for_dish('Paneer')}")
    print(f"Ingredients for Obbattu Holige: {get_ingredients_for_dish('Obbattu Holige')}") # Test the corrected name
    print(f"Ingredients for Unknown Dish: {get_ingredients_for_dish('Unknown Dish')}") # Should return empty
