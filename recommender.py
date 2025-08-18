# recommender.py
import pandas as pd
from firebase_admin import firestore
from datetime import datetime, timedelta, timezone # Import timezone

def get_smart_recommendations(db_client, current_list_id, num_recommendations=5):
    """
    Provides smart recommendations for shopping list items based on user history in Firestore.
    It identifies frequently bought/added items that are not currently on the active list.
    
    Args:
        db_client: The Firestore client instance.
        current_list_id: The ID of the current shopping list to check against.
        num_recommendations: The maximum number of recommendations to return.
    
    Returns:
        A list of recommended item names (strings).
    """
    
    # 1. Fetch user history (recently bought/added items)
    # Get all 'bought' and 'added' history items for frequency analysis.
    # In Firestore, direct range queries on timestamps can require composite indexes.
    # For a simpler approach here, we fetch all relevant history and filter by date in Python.
    
    history_items_data = []
    # Fetch all user history documents with 'bought' or 'added' action types
    history_query = db_client.collection('user_history').where('action_type', 'in', ['bought', 'added']).stream()

    for doc in history_query:
        history_data = doc.to_dict()
        # Firestore SERVER_TIMESTAMP fields become Python datetime objects when retrieved.
        # If timestamp is missing or not a datetime, skip.
        if isinstance(history_data.get('timestamp'), datetime):
             history_items_data.append(history_data)

    # Convert to DataFrame for easier aggregation and filtering
    history_df = pd.DataFrame(history_items_data)

    frequently_interacted_items = []
    if not history_df.empty:
        # Filter for items within a recent period (e.g., last 90 days) for "fresh" recommendations
        # FIX: Make ninety_days_ago timezone-aware (UTC) to match Firestore timestamps
        ninety_days_ago = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=90)
        recent_history_df = history_df[history_df['timestamp'] >= ninety_days_ago]
        
        # Count frequencies of item names from recent history
        item_frequency = recent_history_df['item_name'].value_counts()
        
        # Get top N frequently interacted items
        # Fetch more candidates initially to ensure enough after filtering out current list items
        frequently_interacted_items = item_frequency.head(num_recommendations * 3).index.tolist()

    # 2. Fetch current list items to avoid recommending already existing items
    current_list_items = set()
    list_items_query = db_client.collection('list_items').where('list_id', '==', current_list_id).where('is_bought', '==', False).stream()
    for doc in list_items_query:
        current_list_items.add(doc.to_dict()['item_name'].lower())

    # 3. Generate final recommendations
    recommendations = []
    for item in frequently_interacted_items:
        if item.lower() not in current_list_items:
            recommendations.append(item)
        if len(recommendations) >= num_recommendations:
            break
            
    # Fallback recommendations if not enough from history or no history exists
    if len(recommendations) < num_recommendations:
        fallback_items = ["Milk", "Eggs", "Bread", "Coffee", "Sugar", "Rice", "Apples", "Bananas", "Potatoes"]
        for item in fallback_items:
            if item.lower() not in current_list_items and item not in recommendations:
                recommendations.append(item)
            if len(recommendations) >= num_recommendations:
                break

    return recommendations

# Example Usage (for direct testing, requires Firebase setup and some data in Firestore)
if __name__ == "__main__":
    # This block would require a mock Firestore client or actual Firebase setup
    # to run directly. It's primarily designed to be imported by app.py.
    print("--- Testing Recommender (Requires live Firestore DB connection) ---")
    print("This module is typically run via app.py and needs an active Firestore client.")
    print("To test, ensure your Firebase environment is set up and app.py is running.")
