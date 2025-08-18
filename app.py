import os
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, render_template, request, jsonify

# --- Firebase Initialization ---
# IMPORTANT: DO NOT commit this file to GitHub! Add it to .gitignore.
# For Vercel deployment, you will set GOOGLE_APPLICATION_CREDENTIALS_JSON
# as an environment variable in Vercel, containing the JSON string content.
SERVICE_ACCOUNT_KEY_PATH_LOCAL = 'firebase-service-account.json'

cred = None
if 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in os.environ:
    try:
        cred_json_str = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        cred_json = json.loads(cred_json_str)
        cred = credentials.Certificate(cred_json)
        print("Firebase credentials loaded from environment variable.")
    except json.JSONDecodeError as e:
        print(f"Error decoding GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
        print("Ensure the environment variable contains valid JSON.")
    except Exception as e:
        print(f"Error creating Firebase credentials from environment variable: {e}")
elif os.path.exists(SERVICE_ACCOUNT_KEY_PATH_LOCAL):
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH_LOCAL)
    print(f"Firebase credentials loaded from local file: {SERVICE_ACCOUNT_KEY_PATH_LOCAL}")
else:
    print("Warning: Firebase service account credentials JSON file not found locally, and GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set or invalid.")
    print("App may not function correctly without Firebase credentials.")

if cred:
    try:
        # Check if app is already initialized to avoid ValueError in Flask's debug mode restarts
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase Admin SDK initialized successfully.")
    except ValueError as e:
        print(f"Firebase Admin SDK already initialized or invalid options: {e}")
        # If it's already initialized, just get the client
        db = firestore.client()
else:
    print("Firebase Admin SDK could not be initialized due to missing/invalid credentials. Exiting.")
    exit()

app = Flask(__name__)

# --- Database Initialization and Recipe Population (Adapted for Firestore) ---
with app.app_context():
    setup_doc_ref = db.collection('app_meta').document('setup')
    setup_doc = setup_doc_ref.get()

    if not setup_doc.exists or not setup_doc.to_dict().get('recipes_populated'):
        print("Populating recipe database for Firestore...")
        # Import RECIPES_DATA locally within this function or ensure it's globally available
        from recipe_manager import RECIPES_DATA
        
        default_list_doc_ref = db.collection('shopping_lists').document('my_shopping_list')
        if not default_list_doc_ref.get().exists:
            default_list_doc_ref.set({"name": "My Shopping List"})
            print("Created default shopping list document in Firestore.")

        for dish_name, ingredients_list in RECIPES_DATA.items():
            recipe_doc_ref = db.collection('recipes').document(dish_name.lower())
            
            if not recipe_doc_ref.get().exists:
                recipe_doc_ref.set({"name": dish_name})
                
                for ingredient_name in ingredients_list:
                    recipe_doc_ref.collection('ingredients').add({"name": ingredient_name})
                print(f"Added recipe: {dish_name} and its ingredients to Firestore.")
            else:
                print(f"Recipe '{dish_name}' already exists in Firestore. Skipping population.")
        
        setup_doc_ref.set({'recipes_populated': True, 'last_populated': firestore.SERVER_TIMESTAMP})
        print("Recipe database population complete for Firestore.")
    else:
        print("Firestore recipes already populated. Skipping initial recipe population.")

@app.route('/')
def index():
    current_list_doc_ref = db.collection('shopping_lists').document('my_shopping_list')
    current_list_doc = current_list_doc_ref.get()
    items = []
    recommendations = []

    if current_list_doc.exists:
        items_query = db.collection('list_items').where('list_id', '==', current_list_doc.id).where('is_bought', '==', False).order_by('added_timestamp', direction=firestore.Query.DESCENDING).stream()
        
        for item_doc in items_query:
            item_data = item_doc.to_dict()
            item_data['id'] = item_doc.id
            
            display_name = item_data.get('item_name', '')
            quantity = item_data.get('quantity', '1')
            unit = item_data.get('unit', '')

            if quantity and quantity != '1':
                display_name = f"{quantity} {unit} {display_name}".strip()
            elif unit:
                display_name = f"{unit} {display_name}".strip()
            item_data['name'] = display_name

            items.append(item_data)

        from recommender import get_smart_recommendations
        # Pass the Firestore 'db' instance to the recommender function
        recommendations = get_smart_recommendations(db, current_list_doc.id) 

    return render_template('index.html', items=items, recommendations=recommendations)

# --- API Routes - Moved Outside of index() Function ---

@app.route('/api/process_voice_command', methods=['POST'])
def process_voice_command_api():
    print("--- process_voice_command_api route hit! ---") # Debugging print
    data = request.json
    command_text = data.get('command')

    if not command_text:
        return jsonify({"status": "error", "message": "No command provided."}), 400

    print(f"\n--- Received Command Text: '{command_text}' ---")
    # Import process_command locally within this function
    from nlp_model import process_command 
    nlp_output = process_command(command_text)
    intent = nlp_output['intent']
    print(f"--- NLP Output: {nlp_output} ---\n")
    
    current_list_doc_ref = db.collection('shopping_lists').document('my_shopping_list')
    current_list_doc = current_list_doc_ref.get()

    if not current_list_doc.exists:
        return jsonify({"status": "error", "message": "Shopping list not found."}), 404

    current_list_id = current_list_doc.id

    response_message = "I'm not sure how to handle that. Can you try rephrasing?"
    status_type = "info"
    
    if intent == 'add_item':
        added_count = 0
        added_item_names = []
        for item_obj in nlp_output['items']:
            item_name = item_obj['name']
            quantity = item_obj.get('quantity', '1')
            unit = item_obj.get('unit', '')

            existing_items_query = db.collection('list_items').where('list_id', '==', current_list_id)\
                                    .where('item_name', '==', item_name).where('quantity', '==', quantity)\
                                    .where('unit', '==', unit).where('is_bought', '==', False).limit(1).stream()
            existing_item_doc = next(existing_items_query, None)

            if not existing_item_doc:
                new_item_data = {
                    "list_id": current_list_id,
                    "item_name": item_name,
                    "quantity": quantity,
                    "unit": unit,
                    "added_timestamp": firestore.SERVER_TIMESTAMP,
                    "is_bought": False,
                    "note": nlp_output['note']
                }
                new_item_ref = db.collection('list_items').add(new_item_data)[1]
                
                user_history_data = {
                    "item_name": item_name,
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "action_type": 'added',
                    "list_item_id": new_item_ref.id
                }
                db.collection('user_history').add(user_history_data)
                
                added_count += 1
                display_name = f"{quantity} {unit} {item_name}".strip()
                if quantity == "1" and not unit:
                    display_name = item_name
                added_item_names.append(display_name)
            
            if added_count > 0:
                response_message = f"Added {', '.join(added_item_names)} to your list."
                status_type = "success"
            else:
                response_message = "Those items are already on your list or no new items detected."
                status_type = "info"

    elif intent == 'remove_item':
        removed_count = 0
        deleted_item_names = []
        items_to_delete_refs = []

        if nlp_output['dish_name']: # If a dish name is provided (e.g., "delete biryani items")
            dish_name_lower = nlp_output['dish_name'].lower()
            
            # Retrieve all unbought items for the current list
            all_unbought_items_query = db.collection('list_items').where('list_id', '==', current_list_id)\
                                        .where('is_bought', '==', False).stream()
            
            items_to_consider_for_deletion = []
            for doc in all_unbought_items_query:
                item_data = doc.to_dict()
                item_data['id'] = doc.id # Add ID for reference
                items_to_consider_for_deletion.append(item_data)

            # 1. Match items by dish name in their note (e.g., "for chitranna")
            for item_data in items_to_consider_for_deletion:
                note_content = item_data.get('note', '').lower()
                if f"for {dish_name_lower}" in note_content:
                    items_to_delete_refs.append(db.collection('list_items').document(item_data['id']))
                    deleted_item_names.append(f"{item_data.get('quantity', '')} {item_data.get('unit', '')} {item_data.get('item_name', '')}".strip())
            
            # 2. Match items by ingredient name for the given dish
            from recipe_manager import RECIPES_DATA
            recipe_ingredients = RECIPES_DATA.get(dish_name_lower, [])
            
            if recipe_ingredients:
                for ingredient_name in recipe_ingredients:
                    for item_data in items_to_consider_for_deletion:
                        # Check if item name matches an ingredient and hasn't been marked for deletion yet
                        if item_data['item_name'].lower() == ingredient_name.lower() and \
                           db.collection('list_items').document(item_data['id']) not in items_to_delete_refs:
                            
                            items_to_delete_refs.append(db.collection('list_items').document(item_data['id']))
                            deleted_item_names.append(f"{item_data.get('quantity', '')} {item_data.get('unit', '')} {item_data.get('item_name', '')}".strip())
            
            # Remove duplicates from deleted_item_names (if an item matched by note AND ingredient)
            deleted_item_names = list(dict.fromkeys(deleted_item_names))

            if not items_to_delete_refs:
                response_message = f"No items related to '{nlp_output['dish_name']}' found on your list to remove."
                status_type = "info"

        else: # Regular item removal (e.g., "remove bread" - items array populated by NLP)
            # Iterate through the structured item objects from NLP
            for item_obj in nlp_output['items']:
                item_name_nlp = item_obj['name']
                quantity_nlp = item_obj.get('quantity', '1')
                unit_nlp = item_obj.get('unit', '')

                # Query for a specific item, matching quantity and unit if provided by NLP
                query = db.collection('list_items').where('list_id', '==', current_list_id)\
                          .where('item_name', '==', item_name_nlp).where('is_bought', '==', False)
                if quantity_nlp and quantity_nlp != '1':
                    query = query.where('quantity', '==', quantity_nlp)
                if unit_nlp:
                    query = query.where('unit', '==', unit_nlp)
                
                item_to_remove_doc = next(query.limit(1).stream(), None)

                if item_to_remove_doc:
                    items_to_delete_refs.append(item_to_remove_doc.reference)
                    item_data = item_to_remove_doc.to_dict()
                    deleted_item_names.append(f"{item_data.get('quantity', '')} {item_data.get('unit', '')} {item_data.get('item_name', '')}".strip())
            
            if not items_to_delete_refs: 
                response_message = "Could not find those items on your list to remove."
                status_type = "info"

        # Perform deletion for all collected item references
        for item_ref in items_to_delete_refs:
            item_data = item_ref.get().to_dict() # Re-fetch to log correct item_name before deletion
            item_ref.delete() # Delete from Firestore
            user_history_data = {
                "item_name": item_data.get('item_name', 'Unknown Item'),
                "timestamp": firestore.SERVER_TIMESTAMP,
                "action_type": 'removed',
                "list_item_id": item_ref.id # Store the ID of the removed item
            }
            db.collection('user_history').add(user_history_data)
            removed_count += 1

        if removed_count > 0:
            response_message = f"Removed {', '.join(deleted_item_names)} from your list."
            status_type = "success"
        elif status_type != "info": 
            pass # Keep previous info message if set
        else: 
            response_message = "No items found to remove."
            status_type = "info"

    elif intent == 'mark_bought':
        bought_count = 0
        bought_item_names = []

        for item_obj in nlp_output['items']:
            item_name_nlp = item_obj['name']
            quantity_nlp = item_obj.get('quantity', '1')
            unit_nlp = item_obj.get('unit', '')

            query = db.collection('list_items').where('list_id', '==', current_list_id)\
                      .where('item_name', '==', item_name_nlp).where('is_bought', '==', False)
            if quantity_nlp and quantity_nlp != '1':
                query = query.where('quantity', '==', quantity_nlp)
            if unit_nlp:
                query = query.where('unit', '==', unit_nlp)
            
            item_to_mark_doc = next(query.limit(1).stream(), None)

            if item_to_mark_doc:
                item_to_mark_doc.reference.update({'is_bought': True})
                item_data = item_to_mark_doc.to_dict()
                
                user_history_data = {
                    "item_name": item_data.get('item_name', 'Unknown Item'),
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "action_type": 'bought',
                    "list_item_id": item_to_mark_doc.id
                }
                db.collection('user_history').add(user_history_data)
                
                bought_count += 1
                display_name = f"{item_data.get('quantity', '')} {item_data.get('unit', '')} {item_data.get('item_name', '')}".strip()
                if item_data.get('quantity', '1') == "1" and not item_data.get('unit'):
                    display_name = item_data.get('item_name', '')
                bought_item_names.append(display_name)
        
        if bought_count > 0:
            response_message = f"Marked {', '.join(bought_item_names)} as bought."
            status_type = "success"
        else:
            response_message = "Could not find those items on your list to mark as bought."
            status_type = "info"

    elif intent == 'get_recipe_ingredients':
        dish_name = nlp_output.get('dish_name')
        if dish_name:
            recipe_doc_ref = db.collection('recipes').document(dish_name.lower())
            recipe_doc = recipe_doc_ref.get()

            if recipe_doc.exists:
                ingredients_query = recipe_doc_ref.collection('ingredients').stream()
                ingredients = [doc.to_dict()['name'] for doc in ingredients_query]
                
                added_recipe_items = []
                for ingredient_name in ingredients:
                    existing_item_query = db.collection('list_items').where('list_id', '==', current_list_id)\
                                        .where('item_name', '==', ingredient_name).where('is_bought', '==', False).limit(1).stream()
                    existing_item_doc = next(existing_item_query, None)
                    
                    if not existing_item_doc:
                        item_note_text = f"for {dish_name}"
                        if nlp_output['note']:
                            item_note_text += f" ({nlp_output['note']})"

                        new_item_data = {
                            "list_id": current_list_id,
                            "item_name": ingredient_name,
                            "quantity": "1",
                            "unit": "",
                            "added_timestamp": firestore.SERVER_TIMESTAMP,
                            "is_bought": False,
                            "note": item_note_text
                        }
                        new_item_ref = db.collection('list_items').add(new_item_data)[1]
                        
                        user_history_data = {
                            "item_name": ingredient_name,
                            "timestamp": firestore.SERVER_TIMESTAMP,
                            "action_type": f'added_for_recipe_{dish_name}',
                            "list_item_id": new_item_ref.id
                        }
                        db.collection('user_history').add(user_history_data)
                        added_recipe_items.append(ingredient_name)
                
                if added_recipe_items:
                    response_message = f"Added ingredients for {dish_name}: {', '.join(added_recipe_items)}."
                    status_type = "success"
                else:
                    response_message = f"All ingredients for {dish_name} are already on your list."
                    status_type = "info"
            else:
                response_message = f"Sorry, I don't have ingredients for '{dish_name}' in my recipe book."
                status_type = "warning"
        else:
            response_message = "Please tell me which dish you want ingredients for."
            status_type = "warning"
        
        # This return handles 'get_recipe_ingredients' specific responses, so it should stay inside
        return jsonify({"status": status_type, "message": response_message})

    # --- DEFAULT RETURN FOR UNHANDLED INTENTS ---
    # This ensures a response is always returned if none of the above intents are matched.
    return jsonify({"status": status_type, "message": response_message})


@app.route('/api/get_list_items', methods=['GET'])
def get_list_items_api():
    current_list_doc_ref = db.collection('shopping_lists').document('my_shopping_list')
    current_list_doc = current_list_doc_ref.get()
    
    if not current_list_doc.exists:
        return jsonify([]), 200

    items_for_display = []
    items_query = db.collection('list_items').where('list_id', '==', current_list_doc.id).where('is_bought', '==', False).order_by('added_timestamp', direction=firestore.Query.DESCENDING).stream()
    
    for item_doc in items_query:
        item_data = item_doc.to_dict()
        item_data['id'] = item_doc.id
        
        display_name = item_data.get('item_name', '')
        quantity = item_data.get('quantity', '1')
        unit = item_data.get('unit', '')

        if quantity and quantity != '1':
            display_name = f"{quantity} {unit} {display_name}".strip()
        elif unit:
            display_name = f"{unit} {display_name}".strip()
        
        item_data['name'] = display_name
        items_for_display.append(item_data)

    return jsonify(items_for_display), 200

@app.route('/api/get_recommendations', methods=['GET'])
def get_recommendations_api():
    current_list_doc_ref = db.collection('shopping_lists').document('my_shopping_list')
    current_list_doc = current_list_doc_ref.get()

    if not current_list_doc.exists:
        return jsonify(["Milk", "Eggs", "Bread", "Coffee"]), 200

    # Import get_smart_recommendations locally within this function
    from recommender import get_smart_recommendations
    recommendations = get_smart_recommendations(db, current_list_doc.id) 

    return jsonify(recommendations), 200

@app.route('/api/edit_item', methods=['POST'])
def edit_item():
    data = request.json
    item_id = data.get('item_id')
    new_item_name = data.get('item_name')
    new_quantity = data.get('quantity')
    new_unit = data.get('unit')
    new_note = data.get('note')

    if not item_id or not new_item_name:
        return jsonify({"status": "error", "message": "Missing item ID or new item name."}), 400

    item_doc_ref = db.collection('list_items').document(item_id)
    item_doc = item_doc_ref.get()

    if item_doc.exists:
        item_doc_ref.update({
            'item_name': new_item_name,
            'quantity': new_quantity,
            'unit': new_unit,
            'note': new_note
        })
        
        display_name = f"{new_quantity or ''} {new_unit or ''} {new_item_name}".strip()
        if new_quantity == "1" and not new_unit:
            display_name = new_item_name

        return jsonify({"status": "success", "message": f"Item '{display_name}' updated."}), 200
    return jsonify({"status": "error", "message": "Item not found."}), 404

@app.route('/api/toggle_item_bought', methods=['POST'])
def toggle_item_bought():
    item_id = request.json.get('item_id')
    
    item_doc_ref = db.collection('list_items').document(item_id)
    item_doc = item_doc_ref.get()

    if item_doc.exists:
        current_is_bought = item_doc.to_dict().get('is_bought', False)
        new_is_bought = not current_is_bought
        item_doc_ref.update({'is_bought': new_is_bought})
        
        action = 'bought' if new_is_bought else 'unmarked_bought'
        item_data = item_doc.to_dict()

        user_history_data = {
            "item_name": item_data.get('item_name', 'Unknown Item'),
            "timestamp": firestore.SERVER_TIMESTAMP,
            "action_type": action,
            "list_item_id": item_to_mark_doc.id
        }
        db.collection('user_history').add(user_history_data)
        
        display_name = f"{item_data.get('quantity', '')} {item_data.get('unit', '')} {item_data.get('item_name', '')}".strip()
        if item_data.get('quantity', '1') == "1" and not item_data.get('unit'):
            display_name = item_data.get('item_name', '')

        return jsonify({"status": "success", "message": f"Item '{display_name}' status toggled."}), 200
    return jsonify({"status": "error", "message": "Item not found."}), 404

@app.route('/api/delete_item', methods=['POST'])
def delete_item_api():
    item_id = request.json.get('item_id')

    item_doc_ref = db.collection('list_items').document(item_id)
    item_doc = item_doc_ref.get()

    if item_doc.exists:
        item_data = item_doc.to_dict()
        item_doc_ref.delete()
        
        user_history_data = {
            "item_name": item_data.get('item_name', 'Unknown Item'),
            "timestamp": firestore.SERVER_TIMESTAMP,
            "action_type": 'deleted',
            "list_item_id": item_id
        }
        db.collection('user_history').add(user_history_data)

        display_name = f"{item_data.get('quantity', '')} {item_data.get('unit', '')} {item_data.get('item_name', '')}".strip()
        if item_data.get('quantity', '1') == "1" and not item_data.get('unit'):
            display_name = item_data.get('item_name', '')

        return jsonify({"status": "success", "message": f"Item '{display_name}' deleted."}), 200
    return jsonify({"status": "error", "message": "Item not found."}), 404

if __name__ == '__main__':
    print("Attempting to run Flask app...")
    app.run(host='0.0.0.0', debug=True, port=5000)
