import addon_manager
from logger import log
from i18n import tr, translator

def update_gameinfo(gameinfo_path, addons_with_paths):
    """
    Adds addon paths to gameinfo.txt file between markers
    Returns tuple (success, message)
    """
    try:
        log.info(tr("Updating gameinfo.txt..."))
        
        # Check markers
        marker_status = addon_manager.validate_addon_markers(gameinfo_path)
        
        if marker_status == "missing_start":
            return False, tr("Missing start marker of addons block! Add //mounted_addons_start to the beginning of addons list in gameinfo.txt.")
        elif marker_status == "missing_end":
            return False, tr("Missing end marker of addons block! Add //mounted_addons_end to the end of addons list in gameinfo.txt.")
        elif marker_status == "no_markers":
            # Add markers on first use
            success, message = addon_manager.add_addon_markers(gameinfo_path)
            if not success:
                return False, tr("Failed to add markers: {}").format(message)
        
        with open(gameinfo_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Find marker positions
        start_index = -1
        end_index = -1
        
        for i, line in enumerate(lines):
            if "//mounted_addons_start" in line:
                start_index = i
            if "//mounted_addons_end" in line:
                end_index = i
        
        if start_index == -1 or end_index == -1:
            return False, tr("Failed to find addons block markers.")
        
        # Get current addons
        current_addons = addon_manager.read_addons_from_gameinfo(gameinfo_path)
        
        # Create dictionary of existing addons by ID for quick search
        existing_addons_by_id = {addon['id']: addon for addon in current_addons}
        
        # Form complete addons list: first new, then existing
        all_addons_with_paths = []
        
        # Add new addons from collection
        for vpk_path, title in addons_with_paths:
            # Extract ID from path to search in existing addons
            addon_id = addon_manager.extract_addon_id(vpk_path)
            
            # If this addon already exists, use its data, otherwise add new
            if addon_id in existing_addons_by_id:
                existing_addon = existing_addons_by_id[addon_id]
                all_addons_with_paths.append((existing_addon['path'], existing_addon['title']))
                # Remove from dictionary to avoid duplicate addition
                del existing_addons_by_id[addon_id]
            else:
                all_addons_with_paths.append((vpk_path, title))
        
        # Add remaining existing addons (which were not in collection)
        for addon_id, addon in existing_addons_by_id.items():
            all_addons_with_paths.append((addon['path'], addon['title']))
        
        # Create lines to insert between markers
        insert_lines = []
        for vpk_path, title in all_addons_with_paths:
            insert_lines.append(f'\t\t// {title}\n')
            insert_lines.append(f'\t\tgame+mod\t\t"{vpk_path}"\n')
            insert_lines.append('\n')
        
        # Replace content between markers
        new_lines = lines[:start_index + 1] + insert_lines + lines[end_index:]
        
        # Write modified file
        with open(gameinfo_path, 'w', encoding='utf-8') as file:
            file.writelines(new_lines)
        
        log.info(tr("Gameinfo.txt updated: {} new addons").format(len(addons_with_paths)))
        return True, tr("Added addons: {}").format(len(addons_with_paths))
        
    except Exception as e:
        log.error(f"Error updating gameinfo.txt: {str(e)}")
        return False, f"Error updating gameinfo.txt: {str(e)}"

def update_gameinfo_order(gameinfo_path, addons_with_paths):
    """
    Updates addons order in gameinfo.txt between markers
    Returns tuple (success, message)
    """
    try:
        # Check markers
        marker_status = addon_manager.validate_addon_markers(gameinfo_path)
        
        if marker_status != "ok":
            return False, tr("Addons block markers corrupted.")
        
        with open(gameinfo_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Find marker positions
        start_index = -1
        end_index = -1
        
        for i, line in enumerate(lines):
            if "//mounted_addons_start" in line:
                start_index = i
            if "//mounted_addons_end" in line:
                end_index = i
        
        if start_index == -1 or end_index == -1:
            return False, tr("Failed to find addons block markers.")
        
        # Create lines to insert between markers
        insert_lines = []
        for vpk_path, title in addons_with_paths:
            insert_lines.append(f'\t\t// {title}\n')
            insert_lines.append(f'\t\tgame+mod\t\t"{vpk_path}"\n')
            insert_lines.append('\n')
        
        # Replace content between markers
        new_lines = lines[:start_index + 1] + insert_lines + lines[end_index:]
        
        # Write modified file
        with open(gameinfo_path, 'w', encoding='utf-8') as file:
            file.writelines(new_lines)
        

        return True, tr("Addons order updated")
        
    except Exception as e:
        log.error(f"Error updating addons order: {str(e)}")
        return False, f"Error updating addons order: {str(e)}"

def remove_existing_addons(lines):
    """
    Removes existing addons from list of strings (only between markers)
    """
    # Find indices of marker lines
    start_index = -1
    end_index = -1
    
    for i, line in enumerate(lines):
        if "//mounted_addons_start" in line:
            start_index = i
        if "//mounted_addons_end" in line:
            end_index = i
    
    # If markers found, remove only between them
    if start_index != -1 and end_index != -1:
        indices_to_remove = set()
        i = start_index + 1
        
        while i < end_index:
            line = lines[i]
            # Look for addon comment lines
            if line.strip().startswith('//') and i + 1 < len(lines) and 'game+mod' in lines[i + 1]:
                indices_to_remove.add(i)    # Comment line
                indices_to_remove.add(i + 1)  # Path line
                # Check if there's an empty line after
                if i + 2 < len(lines) and lines[i + 2].strip() == '':
                    indices_to_remove.add(i + 2)
            i += 1
        
        # Create new list without removed lines
        return [line for i, line in enumerate(lines) if i not in indices_to_remove]
    else:
        # Old logic if no markers found
        indices_to_remove = set()
        i = 0
        
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('//') and i + 1 < len(lines) and 'game+mod' in lines[i + 1]:
                indices_to_remove.add(i)
                indices_to_remove.add(i + 1)
                if i + 2 < len(lines) and lines[i + 2].strip() == '':
                    indices_to_remove.add(i + 2)
            i += 1
        
        return [line for i, line in enumerate(lines) if i not in indices_to_remove]