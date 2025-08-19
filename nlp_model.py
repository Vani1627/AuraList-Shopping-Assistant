import spacy
import string
import re

# Load a small English language model.
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("SpaCy model 'en_core_web_sm' not found. Downloading it...")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Define common command-related words to filter out from item names
COMMAND_WORDS = set([
    "add", "put", "get", "remove", "delete", "mark", "check", "off", "my", "the",
    "list", "shopping", "item", "items", "dish", "dishes", "recipe", "recipes",
    "make", "cook", "prepare", "help", "with", "i", "want", "to", "need", "some",
    "thought", "of", "doing", "for", "on", "at", # Added prepositions that might start notes
    "next", "last", "this" # Time-related keywords
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
    "mysore pak", "obbattu_holige", # Updated from "obbattu / holige"
    "kesari bath", "chitranna",
    "puliyogare", "kadubu", "thatte idli", "benne dosa", "chow chow bath",
    "neer dosa", "goli bajji", "mangalore bonda", "rava dosa", "vegetable kurma", "vegetable kuruma",
    "veg kurma", # Alias
    "wheat dosa", "adai dosa", "kuzhi paniyaram", "kozhukattai", "semiya upma",
    "pulav", "veg stew", "chicken stew", "veg biryani", "chicken biryani",
    "egg curry", "fish curry", "parippu curry", "erissery", "thoran",
    "kalan", "olan", "payasam", "unniyappam", "bombay chutney", "podi",
    "coconut chutney", "tomato chutney", "mint chutney", "peanut chutney",
    "ginger chutney", "gongura pachadi", "pesarattu", "mirchi bajji",
    "punugulu", "uggani", "pesarattu upma", "mysore bonda", "sundal",
    "kuzhambu", "moru curry", "theeyal", "kozhambu kulambu",
    "kootu", "poriyal", "rasavangi", "kozhukattai sweet", "modak", "adai aval",
    "ulundu vadai", "paruppu vadai", "pazham pori", "ullivada", "chakka appam",
    "idiappam",
    # --- North Indian/General Indian Dishes ---
    "paneer butter masala", "paneer", # Alias
    "dal makhani", "gobhi manchurian", "chicken 65", "chilli chicken",
    "palak paneer", "aloo gobi", "matar paneer", "bhindi masala", "chana masala",
    "rajma chawal", "baingan bharta", "lauki kofta", "malai kofta",
    "navratan kurma", "dum aloo", "shahi paneer", "dal tadka", "veg kolhapuri",
    "paneer tikka masala",
    # --- 10 Italian Dishes ---
    "lasagna", "spaghetti carbonara", "risotto ai funghi", "gnocchi with pesto",
    "focaccia bread", "minestrone soup", "tiramisu", "arancini", "osso buco", "caprese salad"
]

# Sort KNOWN_DISHES by length in descending order to prioritize longer, more specific matches
KNOWN_DISHES = sorted(KNOWN_DISHES, key=len, reverse=True)


# --- Regex for Quantity and Units (Simplified for common cases) ---
# Matches patterns like "2 kg", "500 grams", "one liter", "a dozen"
QUANTITY_UNIT_PATTERN = re.compile(
    r'(?:^|\s)(?P<quantity>\d+(?:\.\d+)?|one|two|a dozen|half(?: a)?|a couple of|a few)' # e.g., "2", "1.5", "one", "a dozen", "half a"
    r'(?:\s(?P<unit>(?:kg|kilogram(?:s)?|g|gram(?:s)?|lb|pound(?:s)?|oz|ounce(?:s)?|l|liter(?:s)?|ml|milliliter(?:s)?|pc|piece(?:s)?|dozen|cup(?:s)?|tsp|teaspoon(?:s)?|tbsp|tablespoon(?:s)?|pack(?:s)?|bottle(?:s)?|can(?:s)?)))?' # e.g., "kg", "grams", "liter"
    , re.IGNORECASE
)
# Note: This is a basic pattern. Advanced parsing needs more robust grammar rules.


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
    items = [] # Will now store tuples like (item_name, quantity, unit) or just item_name
    dish_name = None
    note = None
    
    # --- Pre-scan for dish_name and primary note (DATE/TIME entities) ---
    # Use the pre-sorted KNOWN_DISHES
    for dish_candidate in KNOWN_DISHES:
        # Check if the exact dish_candidate string is present in the document's text
        if dish_candidate in doc.text:
            dish_name = dish_candidate
            break # Found the longest/most specific match, so break
    
    # Prioritize SpaCy's NER for date/time notes ("next Friday")
    for ent in doc.ents:
        if ent.label_ in ["DATE", "TIME"]:
            note = ent.text.strip().rstrip(string.punctuation)
            break

    # --- Intent Recognition ---

    # 1. Recipe Ingredient Addition Intent
    cooking_keywords = ["make", "cook", "prepare", "recipe", "ingredients", "doing"]
    if dish_name and any(token.text in cooking_keywords for token in doc):
        intent = "get_recipe_ingredients"
        # If NER didn't find a note, try prepositional phrases like "for dinner"
        if not note:
            for i, token in enumerate(doc):
                if token.text in ["for", "on", "at"] and i + 1 < len(doc) and doc[i+1].text not in KNOWN_DISHES:
                    extracted_note = extract_note(doc, i + 1)
                    if extracted_note:
                        note = f"{token.text} {extracted_note}"
                        break
    
    # 2. Remove/Delete Intent
    elif any(word in doc.text for word in ["remove", "delete"]):
        intent = "remove_item"

    # 3. Mark Bought Intent
    elif any(word in doc.text for word in ["bought", "check off"]):
        intent = "mark_bought"

    # 4. Add Item Intent (general items)
    elif any(word in doc.text for word in ["add", "put", "get", "need"]):
        # Exclude if it's clearly a recipe ingredient command
        if not (dish_name and any(k in doc.text for k in ["ingredients", "recipe", "make", "cook", "prepare", "doing"])):
            intent = "add_item"

    # --- Item Extraction with Quantity/Unit/Detailed Note ---
    if intent in ["add_item", "remove_item", "mark_bought"]:
        
        # Capture the original text to remove parts as we extract them
        temp_text = text.lower().strip()
        
        # First, try to extract items with quantity and unit
        extracted_structured_items = []
        # Find all matches of QUANTITY_UNIT_PATTERN
        matches = list(QUANTITY_UNIT_PATTERN.finditer(temp_text))
        
        # Iterate matches in reverse to remove them from text without affecting earlier indices
        for match in reversed(matches):
            quantity_text = match.group('quantity')
            unit_text = match.group('unit')
            
            # Remove the matched quantity and unit from the text to isolate the item name
            temp_text = temp_text[:match.start()] + temp_text[match.end():]

            # Find the actual item name around the quantity/unit, usually the following noun chunk
            # This part is highly heuristic and can be improved with dependency parsing
            # For simplicity, we'll try to find a noun chunk directly after where the quantity/unit was
            # Or assume the main noun chunk in the remaining text is the item
            
            # Re-process the remaining text with NLP to find noun chunks
            temp_doc_for_item = nlp(temp_text.strip())
            found_item_name = None
            for chunk in temp_doc_for_item.noun_chunks:
                # Ensure the chunk is not just command words or known dishes
                cleaned_chunk = " ".join([t.text for t in chunk if t.text not in COMMAND_WORDS]).strip()
                if cleaned_chunk and cleaned_chunk not in KNOWN_DISHES:
                    found_item_name = cleaned_chunk
                    break
            
            if found_item_name:
                item_obj = {
                    "name": found_item_name,
                    "quantity": quantity_text if quantity_text else "1", # Default to 1 if no quantity specified
                    "unit": unit_text if unit_text else "" # No unit if not specified
                }
                extracted_structured_items.append(item_obj)
                # Remove the found item name from temp_text for subsequent loops
                temp_text = temp_text.replace(found_item_name, "", 1) # Replace only first occurrence

        # If no structured items found, or there's remaining text for simple items
        if not extracted_structured_items or temp_text.strip():
            # Process remaining text for simple items without explicit quantities/units
            remaining_doc = nlp(temp_text.strip())
            for chunk in remaining_doc.noun_chunks:
                cleaned_chunk = " ".join([token.text for token in chunk if token.text not in COMMAND_WORDS]).strip()
                if cleaned_chunk and cleaned_chunk not in KNOWN_DISHES:
                    # Check if this item was already captured by structured extraction
                    is_duplicate = False
                    for existing_item_obj in extracted_structured_items:
                        if existing_item_obj['name'].lower() == cleaned_chunk.lower():
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        extracted_structured_items.append({"name": cleaned_chunk, "quantity": "1", "unit": ""})
            # Fallback for single nouns not caught by noun_chunks
            if not extracted_structured_items:
                for token in remaining_doc:
                    if token.pos_ in ["NOUN", "PROPN"] and token.text not in COMMAND_WORDS and token.text not in KNOWN_DISHES:
                        extracted_structured_items.append({"name": token.text, "quantity": "1", "unit": ""})

        # Convert to a unique list of dictionaries based on name
        unique_items_map = {item["name"].lower(): item for item in extracted_structured_items}
        items = list(unique_items_map.values())
        
        # If a note was found by NER (DATE/TIME), it overrides previous note attempts for general items
        # If no NER note, and no recipe, try for general "for X" note
        if not note and intent == "add_item":
            for i, token in enumerate(doc):
                if token.text in ["for", "on", "at"] and i + 1 < len(doc):
                    extracted_note_temp = extract_note(doc, i + 1)
                    if extracted_note_temp:
                        # Ensure the note isn't just a part of the extracted item itself
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
        "items": items, # Now a list of dictionaries with 'name', 'quantity', 'unit'
        "dish_name": dish_name,
        "note": note
    }

# Example Usage (for testing in VS Code terminal)
if __name__ == "__main__":
    print("--- Testing NLP Model ---")
    print(f"'Add milk and eggs to my list': {process_command('Add milk and eggs to my list.')}")
    print(f"'Remove bread from the list': {process_command('Remove bread from the list.')}")
    print(f"'Mark apples as bought': {process_command('Mark apples as bought.')}")
    print(f"'Next Friday I want to make biryani': {process_command('Next Friday I want to make biryani.')}")
    print(f"'Can you add ingredients for pasta for dinner tonight?': {process_command('Can you add ingredients for pasta for dinner tonight?')}")
    print(f"'I need large milk': {process_command('I need large milk')}")
    print(f"'What's on my list?': {process_command('What\'s on my list?')}")
    print(f"'Help me with chili recipe': {process_command('Help me with chili recipe')}")
    print(f"'Add some small bananas': {process_command('Add some small bananas')}")
    print(f"'Delete biryani items from list.': {process_command('Delete biryani items from list.')}")
    print(f"'Remove pasta ingredients': {process_command('Remove pasta ingredients')}")
    print(f"'I thought of doing omelette next Friday': {process_command('I thought of doing omelette next Friday')}")
    
    # --- New Test Cases for Quantity and Units ---
    print(f"\n--- New Quantity/Unit Tests ---")
    print(f"'Add 2 liters of milk': {process_command('Add 2 liters of milk')}")
    print(f"'Put 500 grams of chicken on the list': {process_command('Put 500 grams of chicken on the list')}")
    print(f"'Need one dozen eggs': {process_command('Need one dozen eggs')}")
    print(f"'Get a pack of butter': {process_command('Get a pack of butter')}")
    print(f"'Add a few apples for the trip': {process_command('Add a few apples for the trip')}")
    print(f"'Remove 1.5 pounds of ground beef': {process_command('Remove 1.5 pounds of ground beef')}")
    # --- Test Cases for South Indian and Italian Dishes ---
    print(f"\n--- South Indian & Italian Dish Tests ---")
    print(f"'Add ingredients for dosa': {process_command('Add ingredients for dosa')}")
    print(f"'I want to cook sambar': {process_command('I want to cook sambar')}")
    print(f"'Prepare lasagna for dinner': {process_command('Prepare lasagna for dinner')}")
    print(f"'I thought of doing puliyogare': {process_command('I thought of doing puliyogare')}")
    print(f"'I thought of doing veg kurma': {process_command('I thought of doing veg kurma')}")
    print(f"'Add ingredients for obbattu holige': {process_command('Add ingredients for obbattu holige')}") # Test corrected name
