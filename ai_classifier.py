# AI Classifier Module
# Interfaces with Google Gemini API to categorize bookmarks intelligently.

import google.generativeai as genai
import time
import json
import logging

# Set up logging to track batch progress and errors
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def configure_gemini(api_key):
    """
    Initializes the Gemini library with the provided API key.
    
    Args:
        api_key (str): The user's Gemini API key.
    """
    if not api_key:
        raise ValueError("API Key is required to use AI features.")
    genai.configure(api_key=api_key)

def verify_gemini_connection(api_key, model_name='gemini-1.5-flash'):
    """
    Verifies that the API key is valid by making a lightweight API call.
    
    Args:
        api_key (str): The user's Gemini API key.
        model_name (str): The specific model to test.
        
    Returns:
        bool: True if connection is successful.
    Raises:
        Exception: If connection fails, with the specific error message.
    """
    try:
        configure_gemini(api_key)
        # Attempt to list models as a lightweight check
        # or verify by generating a simple 'hello'
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("test", generation_config={'max_output_tokens': 1})
        return True
    except Exception as e:
        # Re-raise nicely formatted error
        if "403" in str(e) or "API_KEY_INVALID" in str(e):
             raise ValueError("Invalid API Key. Please check your credentials.")
        raise e

def categorize_batch(model, batch, existing_categories=None):
    """
    Sends a batch of bookmarks to the LLM for categorization.
    
    Args:
        model: Connected GenAI model instance.
        batch (list): List of dicts [{'title':..., 'url':...}].
        existing_categories (list, optional): List of already created categories to encourage reuse.
        
    Returns:
        list: The same bookmarks with a new 'category' field.
    """
    if existing_categories is None:
        existing_categories = []
        
    # We provide the AI with existing categories to prevent it from creating synonyms
    # (e.g., using "Tech" when "Technology" already exists).
    prompt = f"""
    You are an intelligent bookmark organizer. Your task is to categorize the following bookmarks into logical, hierarchical folders.
    
    Here is the list of bookmarks to categorize:
    {json.dumps(batch, indent=2)}
    
    EXISTING CATEGORIES (Reuse these if they fit well!):
    {json.dumps(existing_categories, indent=2)}
    
    Instructions:
    1. Organize these into intuitive categories (e.g., "Development", "News", "Entertainment", "Shopping > Tech", etc.).
    2. PREFER using specific EXISTING CATEGORIES if they fit the bookmark well to maintain consistency.
    3. You can use nested categories if appropriate (use ' > ' as separator, e.g., "Dev > Python").
    4. If a bookmark doesn't fit any existing category, create a NEW high-quality generic category. Avoid creating highly specific categories for single websites unless necessary.
    5. Return ONLY a JSON array where each object has:
       - "title": The original title
       - "url": The original url
       - "category": The assigned category
    
    Ensure the output is valid JSON. Do not include markdown formatting like ```json.
    """
    
    try:
        # Call the API
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        
        # Clean up potential markdown formatting often returned by LLMs
        if text_response.startswith("```"):
            text_response = text_response.strip("`").replace("json\n", "").strip()
            
        categorized_data = json.loads(text_response)
        return categorized_data
    except Exception as e:
        # Catch errors (like JSON parsing or API 500s) and return the error message in the category
        # This helps the user see exactly what went wrong for specific items.
        error_msg = str(e)
        logging.error(f"Error categorizing batch: {error_msg}")
        return [{"title": b["title"], "url": b["url"], "category": f"Error: {error_msg[:50]}..."} for b in batch]

def categorize_bookmarks(bookmarks, api_key, model_name="gemini-2.5-flash", batch_size=50, progress_callback=None, status_callback=None):
    """
    Orchestrator function to categorize a full list of bookmarks.
    Handles batching, rate limiting, and status updates.
    
    Args:
        bookmarks (list): Full list of bookmarks.
        api_key (str): Gemini API Key.
        model_name (str): Model to use (default: gemini-2.5-flash).
        batch_size (int): items per request.
        progress_callback (func): Function to update a progress bar (0.0 to 1.0).
        status_callback (func): Function to update a text status message.
        
    Returns:
        list: Fully categorized list of bookmarks.
    """
    configure_gemini(api_key)
    model = genai.GenerativeModel(model_name)
    
    categorized_bookmarks = []
    unique_categories = set()
    total_bookmarks = len(bookmarks)
    
    logging.info(f"Starting classification for {total_bookmarks} bookmarks with model {model_name}...")
    
    for i in range(0, total_bookmarks, batch_size):
        # Status Update
        current_batch_num = i // batch_size + 1
        total_batches = (total_bookmarks + batch_size - 1) // batch_size
        
        msg = f"Processing batch {current_batch_num} of {total_batches} ({min(i+batch_size, total_bookmarks)}/{total_bookmarks})..."
        logging.info(msg)
        
        if status_callback:
            status_callback(msg)
            
        # Create Batch
        batch = bookmarks[i : i + batch_size]
        
        # Minify batch data to save tokens (send only title and url not dates)
        minified_batch = [{"title": b.get("title", ""), "url": b.get("url", "")} for b in batch]
        
        # Call AI
        current_cats_list = list(unique_categories)
        results = categorize_batch(model, minified_batch, existing_categories=current_cats_list)
        
        # Merge Results
        for res in results:
             cat = res.get("category", "Uncategorized")
             # Track unique categories to feed back into the next batch
             if not str(cat).startswith("Error"):
                 unique_categories.add(cat)
             categorized_bookmarks.append(res)
             
        # Progress Update
        if progress_callback:
            progress_callback((min(i + batch_size, total_bookmarks) / total_bookmarks))
            
        time.sleep(1) # Rate limit politeness
        
    return categorized_bookmarks
