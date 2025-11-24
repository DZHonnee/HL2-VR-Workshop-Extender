import os
import json
from logger import log

CONFIG_FILE = "config.json"

def load_config():
    default_config = {
        "collection_url": "",
        "single_addon_url": "", 
        "hl2vr_path": "",
        "hl2_path": "",
        "check_addon_files": True,
        "auto_check_maps": True,
        "embed_into_episodes": True,
        "language": "en"
    }
    
    if not os.path.exists(CONFIG_FILE):
        return default_config
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            config = json.load(file)
        
        for key in default_config:
            if key not in config:
                config[key] = default_config[key]
        
        return config
    except Exception as e:
        log.error(f"Error loading configuration: {e}")
        return default_config

def save_config(collection_url, single_addon_url, hl2vr_path, hl2_path, 
                check_addon_files, auto_check_maps, embed_into_episodes, language="en"):
    config = {
        "collection_url": collection_url,
        "single_addon_url": single_addon_url, 
        "hl2vr_path": hl2vr_path,
        "hl2_path": hl2_path,
        "check_addon_files": check_addon_files,
        "auto_check_maps": auto_check_maps,
        "embed_into_episodes": embed_into_episodes,
        "language": language
    }
    
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as file:
            json.dump(config, file, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.error(f"Error saving configuration: {e}")
        return False