import os
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

from flask import Flask, render_template, request, jsonify

# 1. Initialize Flask app IMMEDIATELY after imports
app = Flask(__name__)

# 2. Initialize Firebase Admin SDK and Firestore client (db)
SERVICE_ACCOUNT_KEY_PATH_LOCAL = 'firebase-service-account.json'
db = None

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
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase Admin SDK initialized successfully.")
    except ValueError as e:
        print(f"Firebase Admin SDK already initialized or invalid options: {e}")
        db = firestore.client()
else:
    print("Firebase Admin SDK could not be initialized. `db` client will be None.")

# 3. Database Initialization and Recipe Population (uses app_context and 'db')
with app.app_context():
    if db:
        setup_doc_ref = db.collection('app_meta').document('setup')
        setup_doc = setup_doc_ref.get()

        # --- TEMPORARY CHANGE: FORCE RE-POPULATION ---
        # Set this to True for ONE deployment to force your Firestore recipes to sync
        # with your local recipe_manager.py.
        # After one successful deploy, set this back to False and redeploy.
        force_repopulation = True # <<< CRITICAL: Change this back to False AFTER THIS DEPLOYMENT!

        if force_repopulation or not setup_doc.exists or not setup_doc.to_dict().get('recipes_populated'):
            print("Populating recipe database for Firestore (forced re-population)...")
            from recipe_manager import RECIPES_DATA
            
            default_list_doc_ref = db.collection('shopping_lists').document('my_shopping_list')
            if not default_list_doc_ref.get().exists:
                default_list_doc_ref.set({"name": "My Shopping List"})
                print("Created default shopping list document in Firestore.")

            # IMPORTANT: Delete existing recipes and their ingredients to avoid duplicates during re-population
            print("Deleting existing recipes and their ingredients before re-population...")
            
            # Fetch all recipe documents
            existing_recipes_stream = db.collection('recipes').stream()
            
            # Use a batch to perform deletions efficiently
            batch = db.batch()
            recipes_deleted_count = 0
            
            for recipe_doc in existing_recipes_stream:
                # Delete ingredients subcollection for each recipe
                ingredients_stream = recipe_doc.reference.collection('ingredients').stream()
                for ing_doc in ingredients_stream:
                    batch.delete(ing_doc.reference) # Add ingredient doc to batch for deletion
                
                batch.delete(recipe_doc.reference) # Add recipe doc to batch for deletion
                recipes_deleted_count += 1
            
            if recipes_deleted_count > 0:
                batch.commit() # Execute all deletions in one go
                print(f"Successfully deleted {recipes_deleted_count} existing recipes and their ingredients.")
            else:
                print("No existing recipes found to delete.")


            # Now, add all recipes from RECIPES_DATA
            for dish_name, ingredients_list in RECIPES_DATA.items():
                recipe_doc_ref = db.collection('recipes').document(dish_name.lower())
                
                # Double-check existence (unlikely after batch delete, but robust)
                if not recipe_doc_ref.get().exists:
                    recipe_doc_ref.set({"name": dish_name})
                    
                    # Add ingredients to a subcollection for this recipe
                    for ingredient_name in ingredients_list:
                        recipe_doc_ref.collection('ingredients').add({"name": ingredient_name})
                    print(f"Added recipe: {dish_name} and its ingredients to Firestore.")
                else:
                    print(f"Recipe '{dish_name}' unexpectedly exists after re-check. Skipping population.")
            
            # Update the setup document to mark population as complete
            setup_doc_ref.set({'recipes_populated': True, 'last_populated': firestore.SERVER_TIMESTAMP})
            print("Recipe database population complete for Firestore.")
        else:
            print("Firestore recipes already populated. Skipping initial recipe population.")
    else:
        print("Skipping Firestore database population due to uninitialized Firebase Admin SDK.")


# --- Frontend Route ---
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
            item_data['id'] = item_doc.id # Add document ID for frontend use
            
            display_name = item_data.get('item_name', '')
            quantity = item_data.get('quantity', '1')
            unit = item_data.get('unit', '')

            # Format item name for display with quantity and unit
            if quantity and quantity != '1':
                display_name = f"{quantity} {unit} {display_name}".strip()
            elif unit: # If unit exists but quantity is 1 or empty
                 display_name = f"{unit} {display_name}".strip()
            
            item_data['name'] = display_name # Update 'name' key for display purposes

            items.append(item_data)

        from recommender import get_smart_recommendations
        # Pass the Firestore 'db' instance to the recommender function
        recommendations = get_smart_recommendations(db, current_list_doc.id) 

    return render_template('index.html', items=items, recommendations=recommendations)

# --- API Endpoints for Voice Commands and List Management ---

@app.route('/api/process_voice_command', methods=['POST'])
def process_voice_command_api():
    """
    API endpoint to receive transcribed voice commands from the frontend.
    It uses the NLP model to interpret the command and performs Firestore actions.
    """
    print("--- process_voice_command_api route hit! ---") # Debugging print
    data = request.json
    command_text = data.get('command')

    if not command_text:
        return jsonify({"status": "error", "message": "No command provided."}), 400

    print(f"\n--- Received Command Text: '{command_text}' ---")
    # Import process_command locally within this function to avoid circular imports if nlp_model depends on app
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
    
    # --- Handle Different Intents ---
    if intent == 'add_item':
        added_count = 0
        added_item_names = [] # To store names of actually added items for the response message

        # nlp_output['items'] is now a list of dictionaries: [{'name': 'milk', 'quantity': '2', 'unit': 'liters'}]
        for item_obj in nlp_output['items']:
            item_name = item_obj['name']
            quantity = item_obj.get('quantity', '1') # Default to '1' if not provided by NLP
            unit = item_obj.get('unit', '')           # Default to '' if not provided by NLP

            # When checking for existing items, query Firestore for precise duplicates
            existing_items_query = db.collection('list_items').where('list_id', '==', current_list_id)\
                                    .where('item_name', '==', item_name)\
                                    .where('quantity', '==', quantity)\
                                    .where('unit', '==', unit)\
                                    .where('is_bought', '==', False).limit(1).stream()
            existing_item_doc = next(existing_items_query, None) # Get the first matching document or None

            if not existing_item_doc:
                new_item_data = {
                    "list_id": current_list_id,
                    "item_name": item_name,
                    "quantity": quantity, # Save quantity
                    "unit": unit,         # Save unit
                    "added_timestamp": firestore.SERVER_TIMESTAMP, # Use server timestamp
                    "is_bought": False,
                    "note": nlp_output['note'] # Use the extracted general note
                }
                new_item_ref = db.collection('list_items').add(new_item_data)[1] # Add document to Firestore
                
                # Log to user history
                user_history_data = {
                    "item_name": item_name,
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "action_type": 'added',
                    "list_item_id": new_item_ref.id # Store the ID of the newly added list item
                }
                db.collection('user_history').add(user_history_data)
                
                added_count += 1
                # Format for response message: "2 liters milk" or "milk"
                display_name = f"{quantity} {unit} {item_name}".strip()
                if quantity == "1" and not unit: # For items like "milk" (quantity 1, no unit)
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
        deleted_item_names = [] # To collect names of items actually removed
        items_to_delete_refs = [] # Collect document references to delete

        if nlp_output['dish_name']: # If a dish name is provided (e.g., "delete biryani items")
            dish_name_lower = nlp_output['dish_name'].lower()
            
            # Find items with a note referring to the dish
            dish_note_items_query = db.collection('list_items').where('list_id', '==', current_list_id)\
                                    .where('is_bought', '==', False).stream()
            for doc in dish_note_items_query:
                item_data = doc.to_dict()
                # Check if 'note' field exists and if dish_name_lower is in the note
                if item_data.get('note') and dish_name_lower in item_data['note'].lower():
                    items_to_delete_refs.append(doc.reference)
                    # Format for response message
                    deleted_item_names.append(f"{item_data.get('quantity', '')} {item_data.get('unit', '')} {item_data.get('item_name', '')}".strip())

            # Import RECIPES_DATA from recipe_manager for recipe-based removal
            from recipe_manager import RECIPES_DATA
            recipe_ingredients = RECIPES_DATA.get(dish_name_lower, [])
            
            if recipe_ingredients:
                for ingredient_name in recipe_ingredients:
                    matching_items_by_name_query = db.collection('list_items').where('list_id', '==', current_list_id)\
                                                    .where('item_name', '==', ingredient_name).where('is_bought', '==', False).stream()
                    for doc in matching_items_by_name_query:
                        if doc.reference not in items_to_delete_refs: # Avoid adding duplicates
                            items_to_delete_refs.append(doc.reference)
                            item_data = doc.to_dict()
                            deleted_item_names.append(f"{item_data.get('quantity', '')} {item_data.get('unit', '')} {item_data.get('item_name', '')}".strip())
            
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
        bought_item_names = [] # To collect names of items actually marked

        # Iterate through structured item objects from NLP
        for item_obj in nlp_output['items']:
            item_name_nlp = item_obj['name']
            quantity_nlp = item_obj.get('quantity', '1')
            unit_nlp = item_obj.get('unit', '')

            # When searching to mark bought, match by name, quantity, and unit if provided by NLP
            query = db.collection('list_items').where('list_id', '==', current_list_id)\
                      .where('item_name', '==', item_name_nlp).where('is_bought', '==', False)
            if quantity_nlp and quantity_nlp != '1':
                query = query.where('quantity', '==', quantity_nlp)
            if unit_nlp:
                query = query.where('unit', '==', unit_nlp)
            
            item_to_mark_doc = next(query.limit(1).stream(), None)

            if item_to_mark_doc:
                item_to_mark_doc.reference.update({'is_bought': True}) # Update Firestore document
                item_data = item_to_mark_doc.to_dict() # Get updated data for history logging
                
                user_history_data = {
                    "item_name": item_data.get('item_name', 'Unknown Item'),
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "action_type": 'bought',
                    "list_item_id": item_to_mark_doc.id
                }
                db.collection('user_history').add(user_history_data)
                
                bought_count += 1
                # Format the name for the response message
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
            # Import get_ingredients_for_dish locally
            from recipe_manager import get_ingredients_for_dish
            ingredients = get_ingredients_for_dish(dish_name)
            if ingredients:
                added_recipe_items = []
                for ingredient_name in ingredients:
                    # For recipe ingredients, we assume quantity '1' and no unit unless specified in recipe_manager's data
                    # Check if item (case-insensitive) already exists and is not bought
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
                            "quantity": "1", # Default quantity for recipe items
                            "unit": "",      # Default unit for recipe items
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
    """Returns all unbought items for the default shopping list as JSON from Firestore."""
    current_list_doc_ref = db.collection('shopping_lists').document('my_shopping_list')
    current_list_doc = current_list_doc_ref.get()
    
    if not current_list_doc.exists:
        return jsonify([]), 200

    items_for_display = []
    items_query = db.collection('list_items').where('list_id', '==', current_list_doc.id).where('is_bought', '==', False).order_by('added_timestamp', direction=firestore.Query.DESCENDING).stream()
    
    for item_doc in items_query:
        item_data = item_doc.to_dict()
        item_data['id'] = item_doc.id # Add document ID for frontend use
        
        display_name = item_data.get('item_name', '')
        quantity = item_data.get('quantity', '1')
        unit = item_data.get('unit', '')

        # Format item name for display with quantity and unit
        if quantity and quantity != '1':
            display_name = f"{quantity} {unit} {display_name}".strip()
        elif unit: # If unit exists but quantity is 1 or empty
             display_name = f"{unit} {display_name}".strip()
        
        item_data['name'] = display_name # Update 'name' key for display purposes
        items_for_display.append(item_data)

    return jsonify(items_for_display), 200

@app.route('/api/get_recommendations', methods=['GET'])
def get_recommendations_api():
    """Returns smart recommendations as JSON from Firestore."""
    current_list_doc_ref = db.collection('shopping_lists').document('my_shopping_list')
    current_list_doc = current_list_doc_ref.get()

    if not current_list_doc.exists:
        return jsonify(["Milk", "Eggs", "Bread", "Coffee"]), 200 # Default recommendations if no list exists

    from recommender import get_smart_recommendations
    recommendations = get_smart_recommendations(db, current_list_doc.id) 
    return jsonify(recommendations), 200

@app.route('/api/edit_item', methods=['POST'])
def edit_item():
    """
    API endpoint to edit an existing list item's name, quantity, unit, and note in Firestore.
    """
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
        # Update specific fields in the Firestore document
        item_doc_ref.update({
            'item_name': new_item_name,
            'quantity': new_quantity,
            'unit': new_unit,
            'note': new_note
        })
        
        # Format for response message
        display_name = f"{new_quantity or ''} {new_unit or ''} {new_item_name}".strip()
        if new_quantity == "1" and not new_unit:
            display_name = new_item_name

        return jsonify({"status": "success", "message": f"Item '{display_name}' updated."}), 200
    return jsonify({"status": "error", "message": "Item not found."}), 404


@app.route('/api/toggle_item_bought', methods=['POST'])
def toggle_item_bought():
    """Toggles the 'is_bought' status of a list item in Firestore."""
    item_id = request.json.get('item_id')
    
    item_doc_ref = db.collection('list_items').document(item_id)
    item_doc = item_doc_ref.get()

    if item_doc.exists:
        current_is_bought = item_doc.to_dict().get('is_bought', False)
        new_is_bought = not current_is_bought
        item_doc_ref.update({'is_bought': new_is_bought}) # Update Firestore document
        
        action = 'bought' if new_is_bought else 'unmarked_bought'
        item_data = item_doc.to_dict() # Get data for history logging

        user_history_data = {
            "item_name": item_data.get('item_name', 'Unknown Item'),
            "timestamp": firestore.SERVER_TIMESTAMP,
            "action_type": action,
            "list_item_id": item_id
        }
        db.collection('user_history').add(user_history_data) # Add to history collection
        
        display_name = f"{item_data.get('quantity', '')} {item_data.get('unit', '')} {item_data.get('item_name', '')}".strip()
        if item_data.get('quantity', '1') == "1" and not item_data.get('unit'):
            display_name = item_data.get('item_name', '')

        return jsonify({"status": "success", "message": f"Item '{display_name}' status toggled."}), 200
    return jsonify({"status": "error", "message": "Item not found."}), 404

@app.route('/api/delete_item', methods=['POST'])
def delete_item_api():
    """Deletes a list item permanently from Firestore."""
    item_id = request.json.get('item_id')

    item_doc_ref = db.collection('list_items').document(item_id)
    item_doc = item_doc_ref.get()

    if item_doc.exists:
        item_data = item_doc.to_dict()
        item_doc_ref.delete() # Delete from Firestore
        
        user_history_data = {
            "item_name": item_data.get('item_name', 'Unknown Item'),
            "timestamp": firestore.SERVER_TIMESTAMP,
            "action_type": 'deleted',
            "list_item_id": item_id
        }
        db.collection('user_history').add(user_history_data) # Add to history collection

        display_name = f"{item_data.get('quantity', '')} {item_data.get('unit', '')} {item_data.get('item_name', '')}".strip()
        if item_data.get('quantity', '1') == "1" and not item_data.get('unit'):
            display_name = item_data.get('item_name', '')

        return jsonify({"status": "success", "message": f"Item '{display_name}' deleted."}), 200
    return jsonify({"status": "error", "message": "Item not found."}), 404

if __name__ == '__main__':
    # Get the port from the environment variable (e.g., set by Render) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', debug=True, port=port)
