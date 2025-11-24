import os
from i18n import tr, translator

def get_workshop_path(hl2_path):
    normalized_path = os.path.normpath(hl2_path)
    
    common_hl2 = os.path.join("common", "Half-Life 2")
    if common_hl2 in normalized_path:
        workshop_path = normalized_path.replace(common_hl2, os.path.join("workshop", "content", "220"))
        return workshop_path
    
    parts = normalized_path.split(os.sep)
    if "steamapps" in parts:
        steamapps_index = parts.index("steamapps")
        base_path = os.sep.join(parts[:steamapps_index + 1])
        workshop_path = os.path.join(base_path, "workshop", "content", "220")
        return workshop_path
    
    return None

def validate_paths(hl2vr_path, hl2_path):
    """Checks path correctness and returns (success, error_message)"""
    if not hl2vr_path:
        return False, tr("Select Half-Life 2 VR folder")
    
    if not hl2_path:
        return False, tr("Select Half-Life 2 folder")
    
    # Check that HL2 VR path ends with correct folder name
    normalized_hl2vr = os.path.normpath(hl2vr_path)
    if not normalized_hl2vr.endswith("Half-Life 2 VR"):
        return False, tr("Wrong path selected for Half-Life 2 VR folder")
    
    # Check that HL2 path ends with correct folder name
    normalized_hl2 = os.path.normpath(hl2_path)
    if not normalized_hl2.endswith("Half-Life 2"):
        return False, tr("Wrong path selected for Half-Life 2 folder")
    
    gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
    if not os.path.exists(gameinfo_path):
        return False, tr("gameinfo.txt not found, check file integrity")
    
    workshop_path = get_workshop_path(hl2_path)
    if not workshop_path or not os.path.exists(workshop_path):
        return False, tr("Failed to find workshop folder")
    
    return True, ""