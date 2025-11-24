import requests
from bs4 import BeautifulSoup
import re
from logger import log
from i18n import tr, translator

def get_page_type(url):
    """
    Determines page type by presence of specific substrings in HTML
    Returns: 'collection', 'addon' or 'unknown'
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        html_content = response.text
        
        # Check if page is a Half-Life 2 collection
        if 'myworkshopfiles/?section=collections&appid=220' in html_content:
            return 'collection'
        
        # Check if page is a Half-Life 2 addon
        if 'myworkshopfiles/?appid=220' in html_content:
            return 'addon'
        
        return 'unknown'
        
    except Exception as e:
        return 'unknown'

def get_collection_addons(collection_url):
    """
    Gets addons list from Steam Workshop collection
    Returns list of tuples (id, title)
    """
    try:
        log.info(tr("Getting addons from collection: {}").format(collection_url))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(collection_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        collection_items = soup.find_all('div', class_='collectionItem')
        
        addons = []
        seen_ids = set()
        
        for item in collection_items:
            addon_id = None
            
            # Extract ID from script
            script_tag = item.find('script')
            if script_tag and script_tag.string:
                match = re.search(r'"id":"(\d+)"', script_tag.string)
                if match:
                    addon_id = match.group(1)
            
            # Alternative method from link
            if not addon_id:
                link = item.find('a', href=re.compile(r'filedetails.*id=\d+'))
                if link and link.get('href'):
                    match = re.search(r'id=(\d+)', link['href'])
                    if match:
                        addon_id = match.group(1)
            
            if not addon_id or addon_id in seen_ids:
                continue
                
            seen_ids.add(addon_id)
            
            # Extract title
            title_element = item.find('div', class_='workshopItemTitle')
            title = title_element.get_text(strip=True) if title_element else tr("Unknown title")
            addons.append((addon_id, title))
        
        log.info(tr("Got {} addons from collection").format(len(addons)))
        return addons
        
    except Exception as e:
        log.error(f"Error getting addons from collection: {str(e)}")
        return []

def get_single_addon(addon_url):
    """
    Gets information about a single addon from Steam Workshop
    Returns tuple (id, title) or (None, None) on error
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(addon_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract ID from URL
        match = re.search(r'id=(\d+)', addon_url)
        if not match:
            return None, None
        addon_id = match.group(1)
        
        # Extract title
        title_element = soup.find('div', class_='workshopItemTitle')
        title = title_element.get_text(strip=True) if title_element else tr("Unknown title")
        return addon_id, title
        
    except Exception as e:
        return None, None

def validate_workshop_url(url, expected_type):
    """
    Checks Steam Workshop URL correctness by presence of specific substrings in HTML
    expected_type: 'collection' or 'addon'
    Returns tuple (is_valid, error_message)
    """
    if not url:
        return False, tr("Enter URL")
    
    if 'steamcommunity.com' not in url:
        return False, tr("Invalid URL")
    
    # Determine page type by specific substrings in HTML
    page_type = get_page_type(url)
    
    if page_type == 'unknown':
        return False, tr("Failed to determine page")
    
    if expected_type == 'collection' and page_type != 'collection':
        return False, tr("Page is not a collection")
    
    if expected_type == 'addon' and page_type != 'addon':
        return False, tr("Page is not an addon")
    
    return True, ""

def get_addon_by_id(addon_id):
    """
    Gets addon information by its ID
    Returns tuple (id, title) or (None, None) on error
    """
    try:
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={addon_id}"
        return get_single_addon(url)
    except Exception as e:
        return None, None
    
def is_addon_map(addon_url):
    """
    Checks if addon is a map by presence of specific substring in HTML
    Returns True or False
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(addon_url, headers=headers)
        response.raise_for_status()
        
        # Check for substring indicating a map
        map_indicator = "https://steamcommunity.com/workshop/browse/?appid=220&browsesort=toprated&section=readytouseitems&requiredtags%5B%5D=maps"
        return map_indicator in response.text
        
    except Exception as e:
        print(f"Error checking if addon is a map: {e}")
        return False