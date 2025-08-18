document.addEventListener('DOMContentLoaded', () => {
    // Get references to key HTML elements
    const startRecognitionBtn = document.getElementById('startRecognitionBtn');
    const transcriptOutput = document.getElementById('transcriptOutput');
    const statusMessage = document.getElementById('statusMessage');
    const shoppingListUl = document.getElementById('shoppingList');
    const recommendationsListUl = document.getElementById('recommendationsList');
    const refreshListBtn = document.getElementById('refreshListBtn');
    const loadingSpinner = document.getElementById('loadingSpinner'); // Reference to the loading spinner
    const clearListBtn = document.getElementById('clearListBtn'); // NEW: Reference to the clear list button

    let recognition; // Variable to hold the Web Speech API recognition object

    // --- Text-to-Speech (TTS) Functionality ---
    const synth = window.speechSynthesis; // Get the SpeechSynthesis object from the browser

    function speak(text) {
        if (synth.speaking) {
            // If already speaking, stop current utterance to prevent overlapping
            synth.cancel();
        }
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US'; // Set language for speech
        utterance.volume = 1; // Volume from 0 to 1
        utterance.rate = 1;   // Speech rate from 0.1 to 10
        utterance.pitch = 1;  // Pitch from 0 to 2

        // Optional: Choose a specific voice
        // let voices = synth.getVoices();
        // utterance.voice = voices.find(voice => voice.name === 'Google US English'); // Or another preferred voice

        synth.speak(utterance); // Speak the text
    }
    // --- End TTS Functionality ---


    // Initialize Web Speech API (Speech-to-Text - STT)
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        // Event handler for when speech recognition starts
        recognition.onstart = () => {
            transcriptOutput.textContent = 'Listening... Speak now.';
            statusMessage.textContent = 'Recording audio...';
            startRecognitionBtn.disabled = true;
            startRecognitionBtn.classList.add('opacity-50', 'cursor-not-allowed');
            loadingSpinner.classList.add('hidden'); // Hide spinner during listening
        };

        // Event handler when a speech result is obtained
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            transcriptOutput.textContent = `You said: "${transcript}"`;
            statusMessage.textContent = 'Processing command...';
            loadingSpinner.classList.remove('hidden'); // Show spinner during processing
            sendVoiceCommandToBackend(transcript); // Send transcribed text to Flask backend
        };

        // Event handler for errors during speech recognition
        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            transcriptOutput.textContent = 'Error during speech recognition. Try again.';
            statusMessage.textContent = `Error: ${event.error}. Please ensure microphone access is granted.`;
            startRecognitionBtn.disabled = false;
            startRecognitionBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            loadingSpinner.classList.add('hidden'); // Hide spinner on error
        };

        // Event handler when recognition ends
        recognition.onend = () => {
            statusMessage.textContent = 'Recognition ended.';
            startRecognitionBtn.disabled = false;
            startRecognitionBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            loadingSpinner.classList.add('hidden'); // Ensure spinner is hidden when recognition ends
        };

        // Add event listener to the "Start Speaking" button
        startRecognitionBtn.addEventListener('click', () => {
            if (synth.speaking) {
                synth.cancel(); // Stop any ongoing speech before starting recognition
            }
            recognition.start();
        });
    } else {
        // Fallback for browsers that do not support Web Speech API
        startRecognitionBtn.disabled = true;
        startRecognitionBtn.classList.add('opacity-50', 'cursor-not-allowed');
        transcriptOutput.textContent = 'Speech Recognition not supported in this browser.';
        statusMessage.textContent = 'Please use a Chrome-based browser (e.g., Chrome, Edge) for voice input.';
    }

    async function sendVoiceCommandToBackend(commandText) {
        statusMessage.textContent = 'Processing command...';
        statusMessage.className = 'status-message text-center text-sm mt-2 text-gray-600';
        loadingSpinner.classList.remove('hidden'); // Show spinner

        try {
            const response = await fetch('/api/process_voice_command', { // This endpoint handles all NLP
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command: commandText }),
            });
            const data = await response.json();

            // Update status message based on backend response
            statusMessage.className = `status-message text-center text-sm mt-2 ${data.status === 'error' ? 'text-red-600' : data.status === 'warning' ? 'text-yellow-600' : 'text-green-600'}`;
            statusMessage.textContent = data.message;
            speak(data.message); // Speak the response message

            await fetchAndRenderLists(); // Refresh lists after any command

        } catch (error) {
            console.error('Error sending command to backend:', error);
            statusMessage.className = 'status-message text-center text-sm mt-2 text-red-600';
            statusMessage.textContent = 'Error communicating with server. Please check the browser console for details.';
            speak('Error communicating with the server. Please check your internet connection.');
        } finally {
            loadingSpinner.classList.add('hidden'); // Hide spinner when processing is complete
        }
    }

    // Function to fetch and render both the shopping list and recommendations
    async function fetchAndRenderLists() {
        try {
            // --- Fetch and Render Shopping List ---
            const listResponse = await fetch('/api/get_list_items');
            const items = await listResponse.json();
            shoppingListUl.innerHTML = ''; // Clear current list content

            if (items.length > 0) {
                items.forEach(item => {
                    const li = document.createElement('li');
                    li.dataset.id = item.id;
                    li.className = 'flex items-center justify-between py-3 px-2 hover:bg-gray-100 transition duration-150 rounded-md';
                    
                    // Create the content span that will be editable
                    const itemContentSpan = document.createElement('span');
                    itemContentSpan.className = 'item-content text-lg text-gray-700 font-medium cursor-pointer flex-grow';
                    itemContentSpan.textContent = item.name; // item.name now includes quantity/unit for display
                    if (item.note) {
                        const noteSpan = document.createElement('span');
                        noteSpan.className = 'text-sm text-gray-500 italic';
                        noteSpan.textContent = ` (${item.note})`;
                        itemContentSpan.appendChild(noteSpan);
                    }
                    itemContentSpan.onclick = () => enableInlineEdit(li, item); // Enable editing on click

                    // Create action buttons (mark bought, delete)
                    const itemActionsDiv = document.createElement('div');
                    itemActionsDiv.className = 'item-actions flex space-x-2 flex-shrink-0';

                    const markBoughtBtn = document.createElement('button');
                    markBoughtBtn.className = 'mark-bought-btn bg-green-200 hover:bg-green-300 text-green-800 font-semibold py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-green-400';
                    markBoughtBtn.dataset.id = item.id;
                    markBoughtBtn.textContent = '✔️';
                    markBoughtBtn.onclick = (event) => toggleItemBought(event.target.dataset.id);

                    const deleteItemBtn = document.createElement('button');
                    deleteItemBtn.className = 'delete-item-btn bg-red-200 hover:bg-red-300 text-red-800 font-semibold py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-red-400';
                    deleteItemBtn.dataset.id = item.id;
                    deleteItemBtn.textContent = '🗑️';
                    deleteItemBtn.onclick = (event) => deleteItem(event.target.dataset.id);
                    
                    itemActionsDiv.appendChild(markBoughtBtn);
                    itemActionsDiv.appendChild(deleteItemBtn);

                    li.appendChild(itemContentSpan);
                    li.appendChild(itemActionsDiv);
                    shoppingListUl.appendChild(li);
                });
            } else {
                shoppingListUl.innerHTML = '<li class="py-3 text-gray-500 text-center italic">Your list is currently empty. Start adding items!</li>';
            }

            // --- Fetch and Render Recommendations ---
            const recResponse = await fetch('/api/get_recommendations');
            const recommendations = await recResponse.json();
            recommendationsListUl.innerHTML = ''; // Clear current recommendations content

            if (recommendations.length > 0) {
                recommendations.forEach(rec => {
                    const li = document.createElement('li');
                    li.className = 'py-3 text-lg text-gray-700 font-medium hover:bg-gray-100 transition duration-150 rounded-md px-2';
                    li.textContent = rec;
                    recommendationsListUl.appendChild(li);
                });
            } else {
                recommendationsListUl.innerHTML = '<li class="py-3 text-gray-500 text-center italic">No current suggestions. Add more items and use AuraList frequently for personalized recommendations!</li>';
            }

        } catch (error) {
            console.error('Error fetching lists:', error);
            statusMessage.textContent = 'Could not load lists. Please check the browser console.';
            statusMessage.className = 'status-message text-center text-sm mt-2 text-red-600';
            speak('I could not load your lists. Please try again.');
        }
    }

    // --- Inline Editing Functions ---
    function enableInlineEdit(listItem, itemData) {
        const itemContentSpan = listItem.querySelector('.item-content');
        // itemData.name currently holds the formatted name (e.g., "2 liters milk")
        const originalDisplayName = itemData.name; 
        const originalNote = itemData.note || '';

        // Create input for item name (which will parse quantity/unit back)
        const nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.value = originalDisplayName; // Populate with current display name
        nameInput.className = 'edit-input flex-grow mr-2';
        nameInput.placeholder = 'Item name (e.g., 2 liters milk)';

        // Create input for note
        const noteInput = document.createElement('input');
        noteInput.type = 'text';
        noteInput.value = originalNote;
        noteInput.className = 'edit-input flex-grow mr-2';
        noteInput.placeholder = 'Note (e.g., for Friday)';

        // Create Save button
        const saveBtn = document.createElement('button');
        saveBtn.className = 'bg-blue-500 hover:bg-blue-600 text-white font-bold py-1 px-2 rounded-md text-sm';
        saveBtn.textContent = 'Save';
        // When saving, send the raw input values; backend will handle parsing
        saveBtn.onclick = () => saveInlineEdit(listItem, itemData.id, nameInput.value, noteInput.value);

        // Create Cancel button
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'bg-gray-400 hover:bg-gray-500 text-white font-bold py-1 px-2 rounded-md text-sm';
        cancelBtn.textContent = 'Cancel';
        // On cancel, revert to original display and restore old buttons
        cancelBtn.onclick = () => cancelInlineEdit(listItem, originalDisplayName, originalNote);

        // Clear existing content and append inputs/buttons
        itemContentSpan.innerHTML = '';
        itemContentSpan.classList.remove('cursor-pointer');
        itemContentSpan.classList.add('flex', 'flex-col'); // Use flex column for stacking inputs

        const nameNoteContainer = document.createElement('div');
        nameNoteContainer.className = 'flex flex-col sm:flex-row gap-2 w-full'; // Responsive stacking
        nameNoteContainer.appendChild(nameInput);
        nameNoteContainer.appendChild(noteInput);
        
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'flex gap-2 mt-2 justify-end w-full'; // Align buttons to end
        buttonContainer.appendChild(saveBtn);
        buttonContainer.appendChild(cancelBtn);

        itemContentSpan.appendChild(nameNoteContainer);
        itemContentSpan.appendChild(buttonContainer);

        // Hide original action buttons while editing
        listItem.querySelector('.item-actions').classList.add('hidden');
    }

    async function saveInlineEdit(listItem, itemId, newNameDisplay, newNote) {
        // This regex attempts to separate quantity/unit from the item name for backend
        const QUANTITY_UNIT_REGEX = /^(?:(\d+(?:\.\d+)?|one|two|a dozen|half(?: a)?|a couple of|a few)\s*(?:(kg|kilogram(?:s)?|g|gram(?:s)?|lb|pound(?:s)?|oz|ounce(?:s)?|l|liter(?:s)?|ml|milliliter(?:s)?|pc|piece(?:s)?|dozen|cup(?:s)?|tsp|teaspoon(?:s)?|tbsp|tablespoon(?:s)?|pack(?:s)?|bottle(?:s)?|can(?:s)?)\s*)?)?(.*)$/i;
        
        const match = newNameDisplay.match(QUANTITY_UNIT_REGEX);
        let parsedQuantity = '1';
        let parsedUnit = '';
        let parsedItemName = newNameDisplay.trim(); // Default to full string if no match

        if (match) {
            parsedQuantity = match[1] || '1'; // First group is quantity, default to '1'
            parsedUnit = match[2] || '';       // Second group is unit, default to ''
            parsedItemName = (match[3] || '').trim(); // Third group is the rest, the item name

            // Edge case: if input was "one dozen" or "a few" with no explicit item name after,
            // we should treat the whole thing as the item name unless it was followed by a unit.
            if (['one', 'two', 'a dozen', 'half', 'half a', 'a couple of', 'a few'].includes(parsedQuantity.toLowerCase()) && !parsedUnit && !parsedItemName) {
                parsedItemName = newNameDisplay.trim();
                parsedQuantity = '1'; // Reset to '1' as the whole string is the item name
                parsedUnit = '';
            }
            // Another edge case: if only "1.5" was typed, it's not a quantity for an item, it IS the item.
            else if (parsedQuantity === newNameDisplay.trim() && !parsedUnit && !parsedItemName) {
                parsedItemName = newNameDisplay.trim();
                parsedQuantity = '1';
                parsedUnit = '';
            }
        }
        
        try {
            const response = await fetch('/api/edit_item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    item_id: itemId,
                    item_name: parsedItemName,
                    quantity: parsedQuantity,
                    unit: parsedUnit,
                    note: newNote
                })
            });
            const data = await response.json();
            statusMessage.textContent = data.message;
            statusMessage.className = `status-message text-center text-sm mt-2 ${data.status === 'success' ? 'text-green-600' : 'text-red-600'}`;
            speak(data.message);
            await fetchAndRenderLists(); // Refresh lists after successful edit
        } catch (error) {
            console.error('Error saving item:', error);
            statusMessage.textContent = 'Error saving item.';
            statusMessage.className = 'status-message text-center text-sm mt-2 text-red-600';
            speak('Error saving item.');
        }
    }

    function cancelInlineEdit(listItem, originalDisplayName, originalNote) {
        const itemContentSpan = listItem.querySelector('.item-content');
        // Reconstruct original display content
        itemContentSpan.innerHTML = `${originalDisplayName} ${originalNote ? `<span class="text-sm text-gray-500 italic">(${originalNote})</span>` : ''}`;
        itemContentSpan.classList.add('cursor-pointer');
        itemContentSpan.classList.remove('flex', 'flex-col'); // Remove flex styling
        listItem.querySelector('.item-actions').classList.remove('hidden'); // Show original buttons
    }


    // --- Event listener for "Mark Bought" and "Delete Item" buttons ---
    async function toggleItemBought(itemId) {
        try {
            const response = await fetch('/api/toggle_item_bought', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_id: itemId })
            });
            const data = await response.json();
            statusMessage.textContent = data.message;
            statusMessage.className = `status-message text-center text-sm mt-2 ${data.status === 'success' ? 'text-green-600' : 'text-red-600'}`;
            speak(data.message);
            await fetchAndRenderLists(); // Refresh lists
        } catch (error) {
            console.error('Error toggling item status:', error);
            statusMessage.textContent = 'Error toggling item status.';
            statusMessage.className = 'status-message text-center text-sm mt-2 text-red-600';
            speak('Error toggling item status.');
        }
    }

    async function deleteItem(itemId) {
        try {
            const response = await fetch('/api/delete_item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_id: itemId })
            });
            const data = await response.json();
            statusMessage.textContent = data.message;
            statusMessage.className = `status-message text-center text-sm mt-2 ${data.status === 'success' ? 'text-green-600' : 'text-red-600'}`;
            speak(data.message);
            await fetchAndRenderLists(); // Refresh lists
        } catch (error) {
            console.error('Error deleting item:', error);
            statusMessage.textContent = 'Error deleting item.';
            statusMessage.className = 'status-message text-center text-sm mt-2 text-red-600';
            speak('Error deleting item.');
        }
    }


    // Event listener for the manual "Refresh List" button
    refreshListBtn.addEventListener('click', async () => {
        statusMessage.textContent = 'Refreshing all lists...';
        await fetchAndRenderLists();
        statusMessage.textContent = 'All lists refreshed.';
        speak('Your lists have been refreshed.');
    });

    // NEW: Event listener for the "Clear All Items" button
    clearListBtn.addEventListener('click', async () => {
        // Show a confirmation dialog (replace with a custom modal in production)
        if (confirm("Are you sure you want to clear all items from your shopping list? This action cannot be undone.")) {
            statusMessage.textContent = 'Clearing shopping list...';
            loadingSpinner.classList.remove('hidden'); // Show spinner

            try {
                const response = await fetch('/api/clear_list', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                statusMessage.textContent = data.message;
                statusMessage.className = `status-message text-center text-sm mt-2 ${data.status === 'success' ? 'text-green-600' : 'text-red-600'}`;
                speak(data.message);
                await fetchAndRenderLists(); // Refresh the list after clearing
            } catch (error) {
                console.error('Error clearing list:', error);
                statusMessage.textContent = 'Error clearing list.';
                statusMessage.className = 'status-message text-center text-sm mt-2 text-red-600';
                speak('Error clearing your list.');
            } finally {
                loadingSpinner.classList.add('hidden'); // Hide spinner when processing is complete
            }
        }
    });

    // Initial call to fetch and render lists when the page first loads
    fetchAndRenderLists();
});
