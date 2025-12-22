import os
import json
import sqlite3
import glob
from datetime import datetime, timedelta

def get_db_path(browser="chrome"):
    """
    Constructs the default path to the bookmark file for supported browsers.
    
    Args:
        browser (str): 'chrome', 'edge', 'brave', or 'firefox'.
        
    Returns:
        str or None: Absolute path to the file if it exists, else None.
    """
    user_home = os.path.expanduser("~")
    local_app_data = os.path.join(user_home, "AppData", "Local")
    roaming_app_data = os.path.join(user_home, "AppData", "Roaming")
    
    if browser.lower() == "chrome":
        return os.path.join(local_app_data, "Google", "Chrome", "User Data", "Default", "Bookmarks")
        
    elif browser.lower() == "edge":
        return os.path.join(local_app_data, "Microsoft", "Edge", "User Data", "Default", "Bookmarks")
        
    elif browser.lower() == "brave":
        return os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "User Data", "Default", "Bookmarks")
        
    elif browser.lower() == "firefox":
        # Firefox profiles are dynamic. We search for the default release profile.
        profile_root = os.path.join(roaming_app_data, "Mozilla", "Firefox", "Profiles")
        if os.path.exists(profile_root):
            # Look for folders ending in .default-release or just .default
            # We prefer .default-release if multiple exist
            patterns = [
                os.path.join(profile_root, "*.default-release", "places.sqlite"),
                os.path.join(profile_root, "*.default", "places.sqlite"),
                os.path.join(profile_root, "*", "places.sqlite") # Fallback to any profile
            ]
            
            for pattern in patterns:
                matches = glob.glob(pattern)
                if matches:
                    return matches[0] # Return the first found match
    return None

def get_browser_path(browser_name):
    """Wrapper to find browser bookmarks."""
    path = get_db_path(browser_name)
    if path and os.path.exists(path):
        return path
    return None

def format_timestamp(timestamp_str, source_type="chromium"):
    """
    Converts browser timestamps to human-readable strings.
    """
    if not timestamp_str:
        return ""
        
    try:
        timestamp_int = int(timestamp_str)
        if source_type == "chromium":
            # WebKit timestamp: Microseconds since Jan 1, 1601 UTC
            epoch = datetime(1601, 1, 1)
            dt = epoch + timedelta(microseconds=timestamp_int)
        elif source_type == "firefox":
            # Unix timestamp: Microseconds since Jan 1, 1970 UTC
            epoch = datetime(1970, 1, 1)
            dt = epoch + timedelta(microseconds=timestamp_int)
        else:
            return timestamp_str
            
        # Basic conversion to local time (naive)
        # For a pure "ISD/IST" we might need pytz, but system local time is usually what users expect "normal way"
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(timestamp_str)

def parse_bookmarks(node, bookmarks_list=None):
    """
    Recursively navigates the Chromium (Chrome/Edge/Brave) bookmark JSON tree.
    """
    if bookmarks_list is None:
        bookmarks_list = []

    if isinstance(node, dict):
        node_type = node.get("type")
        
        # Leaf node: It's a bookmark
        if node_type == "url":
            bookmarks_list.append({
                "title": node.get("name"),
                "url": node.get("url"),
                "date_added": format_timestamp(node.get("date_added"), "chromium"),
                "source": "Chromium" # Generic source, specific browser tracked in caller
            })
        # Folder node: It has children
        elif node_type == "folder":
            children = node.get("children", [])
            for child in children:
                parse_bookmarks(child, bookmarks_list)
        else:
            # Root level handling
            if "roots" in node:
                for root_key in node["roots"]:
                    parse_bookmarks(node["roots"][root_key], bookmarks_list)
            elif "children" in node:
                for child in node["children"]:
                    parse_bookmarks(child, bookmarks_list)
                    
    elif isinstance(node, list):
        for item in node:
            parse_bookmarks(item, bookmarks_list)
            
    return bookmarks_list

def load_and_parse_json(file_path):
    """Safe helper to load Chromium JSON and parse it."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return parse_bookmarks(data)
    except Exception as e:
        print(f"Error reading JSON {file_path}: {e}")
        return []

def extract_firefox_bookmarks(db_path):
    """
    Extracts bookmarks from Firefox 'places.sqlite' database.
    Requires reading 'moz_bookmarks' (structure) and 'moz_places' (urls).
    """
    bookmarks = []
    try:
        # Connect to the database
        # Open in read-only mode to prevent locking issues if Firefox is open
        # We use URI syntax for read-only
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        # Query: join bookmarks with places to get URL
        # type=1 is bookmark (2 is folder, 3 is separator)
        query = """
        SELECT b.title, p.url, b.dateAdded
        FROM moz_bookmarks b
        JOIN moz_places p ON b.fk = p.id
        WHERE b.type = 1 AND p.url IS NOT NULL
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        for row in rows:
            title, url, date_added = row
            if url and not url.startswith("place:"): # Ignore smart bookmarks
                bookmarks.append({
                    "title": title if title else "Untitled",
                    "url": url,
                    "date_added": format_timestamp(date_added, "firefox"),
                    "source": "Firefox"
                })
                
        conn.close()
    except Exception as e:
        print(f"Error reading Firefox SQLite {db_path}: {e}")
        
    return bookmarks

def consolidate_bookmarks(chrome_path, edge_path, brave_path=None, firefox_path=None):
    """
    Reads bookmarks from multiple sources and removes duplicates.
    """
    all_bookmarks = []
    
    # Chromium Browsers
    for path, name in [(chrome_path, "Chrome"), (edge_path, "Edge"), (brave_path, "Brave")]:
        if path:
            print(f"Reading {name} bookmarks from {path}...")
            bms = load_and_parse_json(path)
            # Tag source for debugging if needed
            for b in bms: b["source"] = name 
            all_bookmarks.extend(bms)
            
    # Firefox
    if firefox_path:
        print(f"Reading Firefox bookmarks from {firefox_path}...")
        bms = extract_firefox_bookmarks(firefox_path)
        all_bookmarks.extend(bms)
        
    # Deduplicate by URL
    unique_bookmarks = {}
    for bm in all_bookmarks:
        if bm["url"] not in unique_bookmarks:
            unique_bookmarks[bm["url"]] = bm
            
    return list(unique_bookmarks.values())
