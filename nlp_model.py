import spacy
import string
import re

# Load a small English language model.
# The model should be downloaded as part of the deployment process on Render's build command.
# Removed the spacy.cli.download logic as it causes timeouts in production.
nlp = spacy.load("en_core_web_sm")

# Define common command-related words to filter out from item names
COMMAND_WORDS = set([
    "add", "put", "get", "remove", "delete", "mark", "check", "off", "my", "the",
    "list", "shopping", "item", "items", "dish", "dishes", "recipe", "recipes",
    "help", "with", "i", "want", "to", "need", "some", "thought", "of", "doing",
    "for", "on", "at", "next", "last", "this"
])

# Extend this list of dish names as you add more recipes to recipe_manager.py
# This list MUST be kept in sync with the keys in RECIPES_DATA in recipe_manager.py
KNOWN_DISHES = [
    "pasta", "biryani", "chili", "pancakes", "omelette", "pizza",
    # --- 100 South Indian Dishes ---
    "dosa", "idli", "vada", "sambar", "rasam", "uttapam", "pongal", "poori",
    "upma", "avial", "appam", "puttu", "kadala curry", "porotta", "fish moilee",
    "alleppey fish curry", "malabar parotta", "chemmeen curry", "kerala style beef fry",
    "ghee rice", "kozhi porichathu", "kothu parotta", "paniyarappam", "adai",
    "set dosa", "masala dosa", "raagi mudde", "bisi bele bath", "akki roti",
    "ragi rotti", "ragi roti",
    "mysore pak", "obbattu / holige", "kesari bath", "chitranna",
    "puliyogare", "kadubu", "thatte idli", "benne dosa", "chow chow bath",
    "neer dosa", "goli bajji", "mangalore bonda", "rava dosa", "vegetable kurma", "vegetable kuruma",
    "wheat dosa", "adai dosa", "kuzhi paniyaram", "kozhukattai", "semiya upma",
    "pulav", "veg stew", "chicken stew", "veg biryani", "chicken biryani",
    "egg curry", "fish curry", "parippu curry", "erissery", "thoran",
    "kalan", "olan", "payasam", "unniyappam", "bombay chutney", "podi",
    "coconut chutney", "tomato chutney", "mint chutney", "peanut chutney",
    "ginger chutney", "gongura pachadi", "pesarattu", "mirchi bajji",
    "punugulu", "uggani", "pesarattu upma", "mysore bonda", "sundal",
    "kuzhambu", "moru curry", "theeyal", "kozhambu kulambu", "kootu",
    "poriyal", "rasavangi", "kozhukattai sweet", "modak", "adai aval",
    "ulundu vadai", "paruppu vadai", "pazham pori", "ullivada", "chakka appam",
    "idiappam",
    # --- North Indian/General Indian Dishes (continued from above) ---
    "paneer butter masala", "paneer", # Added "paneer" as a dish candidate
    "dal makhani", "gobhi manchurian", "chicken 65", "chilli chicken",
    "palak paneer", "aloo gobi", "matar paneer", "bhindi masala", "chana masala",
    "rajma chawal", "baingan bharta", "lauki kofta", "malai kofta",
    "navratan kurma", "dum aloo", "shahi paneer", "dal tadka", "veg kolhapuri",
    "paneer tikka masala",
    "veg kurma", # Added "veg kurma" as a dish candidate
    # --- 10 Italian Dishes ---
    "lasagna", "spaghetti carbonara", "risotto ai funghi", "gnocchi with pesto",
    "focaccia bread", "minestrone soup", "tiramisu", "arancini", "osso buco", "caprese salad"
]

# --- Regex for Quantity and Units (Simplified for common cases) ---
QUANTITY_UNIT_PATTERN = re.compile(
    r'(?:^|\s)(?P<quantity>\d+(?:\.\d+)?|one|two|a dozen|half(?: a)?|a couple of|a few)'
    r'(?:\s(?P<unit>(?:kg|kilogram(?:s)?|g|gram(?:s)?|lb|pound(?:s)?|oz|ounce(?:s)?|l|liter(?:s)?|ml|milliliter(?:s)?|pc|piece(?:s)?|dozen|cup(?:s)?|tsp|teaspoon(?:s)?|tbsp|tablespoon(?:s)?|pack(?:s)?|bottle(?:s)?|can(?:s)?)))?'
    , re.IGNORECASE
)

def extract_note(doc, start_token_index, is_time_entity=False):
    """
    Helper function to extract a note from a doc.
    Can be used for general phrases or specific time entities.
    """
    if is_time_entity:
        note_text = " ".join([token.text for token in doc[start_token_index:] if token.pos_ not in ["PUNCT"]]).strip()
        return note_text.rstrip(string.punctuation)

    potential_note_tokens = []
    for j in range(start_token_index, len(doc)):
        token = doc[j]
        if token.pos_ in ["VERB", "CCONJ"] and token.text not in ["and", "or"]:
            break
        if token.text in KNOWN_DISHES or token.text in COMMAND_WORDS:
            break
        potential_note_tokens.append(token.text)
    
    note_text = " ".join(potential_note_tokens).strip()
    note_text = note_text.rstrip(string.punctuation)

    if note_text and note_text not in ["for", "on", "at", "by", "to"]:
        return note_text
    return None

def process_command(text):
    """
    Processes a natural language voice command to identify intent, items, dish names,
    quantities, units, and notes.
    """
    doc = nlp(text.lower().strip())
    
    intent = "unknown"
    items = []
    dish_name = None
    note = None
    
    # --- Pre-scan for dish_name and primary note (DATE/TIME entities) ---
    # Sort KNOWN_DISHES by length in descending order to prioritize longer, more specific matches
    sorted_known_dishes = sorted(KNOWN_DISHES, key=len, reverse=True)
    
    # Attempt to find the most specific dish name in the text
    found_dish_name_candidate = None
    for dish_candidate in sorted_known_dishes:
        # Check if the exact dish_candidate string is present in the document's text
        # This is a less strict check than \b, but combined with sorting, it should be more robust.
        if dish_candidate in doc.text:
            found_dish_name_candidate = dish_candidate
            break # Found the longest/most specific match, so break

    dish_name = found_dish_name_candidate
    
    # Prioritize SpaCy's NER for date/time notes ("next Friday")
    for ent in doc.ents:
        if ent.label_ in ["DATE", "TIME"]:
            note = ent.text.strip().rstrip(string.punctuation)
            break

    # --- Intent Recognition ---

    # 1. Recipe Ingredient Addition Intent
    # More flexible check: look for cooking keywords AND a known dish name anywhere in the text
    cooking_keywords = ["make", "making", "cook", "cooking", "prepare", "preparing", "recipe", "ingredients", "doing"]
    
    # Check if any cooking keyword is present in the document's text
    is_cooking_related = any(k in doc.text for k in cooking_keywords)

    if dish_name and is_cooking_related:
        intent = "get_recipe_ingredients"
        # If NER didn't find a note, try prepositional phrases like "for dinner"
        if not note:
            for i, token in enumerate(doc):
                # Ensure it's not part of a dish name itself or a command word
                if token.text in ["for", "on", "at"] and i + 1 < len(doc) and doc[i+1].text not in KNOWN_DISHES and doc[i+1].text not in COMMAND_WORDS:
                    extracted_note = extract_note(doc, i + 1)
                    if extracted_note:
                        note = f"{token.text} {extracted_note}"
                        break
    
    # 2. Remove/Delete Intent
    elif any(word in doc.text for word in ["remove", "delete", "clear"]): # Added 'clear' here for NLP
        intent = "remove_item"

    # 3. Mark Bought Intent
    elif any(word in doc.text for word in ["bought", "check off"]):
        intent = "mark_bought"

    # 4. Add Item Intent (general items)
    elif any(word in doc.text for word in ["add", "put", "get", "need"]):
        # Exclude if it's clearly a recipe ingredient command (to avoid "add biryani" adding biryani as an item)
        if not (dish_name and is_cooking_related):
            intent = "add_item"

    # --- Item Extraction with Quantity/Unit/Detailed Note ---
    if intent in ["add_item", "remove_item", "mark_bought"]:
        
        # Capture the original text to remove parts as we extract them
        temp_text = text.lower().strip()
        
        # First, try to extract items with quantity and unit
        extracted_structured_items = []
        matches = list(QUANTITY_UNIT_PATTERN.finditer(temp_text))
        
        for match in reversed(matches):
            quantity_text = match.group('quantity')
            unit_text = match.group('unit')
            
            temp_text = temp_text[:match.start()] + temp_text[match.end():]

            temp_doc_for_item = nlp(temp_text.strip())
            found_item_name = None
            for chunk in temp_doc_for_item.noun_chunks:
                cleaned_chunk = " ".join([t.text for t in chunk if t.text not in COMMAND_WORDS and t.text not in KNOWN_DISHES]).strip()
                if cleaned_chunk:
                    found_item_name = cleaned_chunk
                    break
            
            if found_item_name:
                item_obj = {
                    "name": found_item_name,
                    "quantity": quantity_text if quantity_text else "1",
                    "unit": unit_text if unit_text else ""
                }
                extracted_structured_items.append(item_obj)
                temp_text = temp_text.replace(found_item_name, "", 1)

        if not extracted_structured_items or temp_text.strip():
            remaining_doc = nlp(temp_text.strip())
            for chunk in remaining_doc.noun_chunks:
                cleaned_chunk = " ".join([token.text for token in chunk if token.text not in COMMAND_WORDS and token.text not in KNOWN_DISHES]).strip()
                if cleaned_chunk:
                    is_duplicate = False
                    for existing_item_obj in extracted_structured_items:
                        if existing_item_obj['name'].lower() == cleaned_chunk.lower():
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        extracted_structured_items.append({"name": cleaned_chunk, "quantity": "1", "unit": ""})
            
            if not extracted_structured_items:
                for token in remaining_doc:
                    if token.pos_ in ["NOUN", "PROPN"] and token.text not in COMMAND_WORDS and token.text not in KNOWN_DISHES:
                        extracted_structured_items.append({"name": token.text, "quantity": "1", "unit": ""})

        unique_items_map = {item["name"].lower(): item for item in extracted_structured_items}
        items = list(unique_items_map.values())
        
        if not note and intent == "add_item":
            for i, token in enumerate(doc):
                if token.text in ["for", "on", "at"] and i + 1 < len(doc):
                    extracted_note_temp = extract_note(doc, i + 1)
                    if extracted_note_temp:
                        is_part_of_item = False
                        for item_obj in items:
                            if extracted_note_temp.lower() in item_obj["name"].lower():
                                is_part_of_item = True
                                break
                        if not is_part_of_item:
                            note = f"{token.text} {extracted_note_temp}"
                            break

    return {
        "intent": intent,
        "items": items,
        "dish_name": dish_name,
        "note": note
    }
