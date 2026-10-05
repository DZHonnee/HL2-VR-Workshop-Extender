import addon_manager
from logger import log
from i18n import tr, translator

def _block_lines(addon):
    """
    Builds the gameinfo.txt lines for one addon entry.
    'addon' is a dict with 'path', 'title' and 'is_map' keys; extra keys
    such as 'number' or 'is_unpacked' are ignored.
    A map addon gets a //@map marker line between the title and the path,
    which the Source engine ignores because it is a comment.
    """
    path = addon.get('path', '')
    title = addon.get('title', '')
    is_map = bool(addon.get('is_map', False))

    normalized_path = path.replace('\\', '/')
    lines = ['\t\t// {}\n'.format(title)]
    if is_map:
        lines.append('\t\t//@map\n')
    lines.append('\t\tgame+mod\t\t"{}"\n'.format(normalized_path))
    lines.append('\n')
    return lines


def _find_markers(lines):
    """
    Returns (start_index, end_index) of the mounted addons block, or None
    when a marker is missing.
    """
    start_index = -1
    end_index = -1

    for i, line in enumerate(lines):
        if "//mounted_addons_start" in line:
            start_index = i
        if "//mounted_addons_end" in line:
            end_index = i

    if start_index == -1 or end_index == -1:
        return None

    return start_index, end_index


def _replace_addons_block(lines, addons_with_paths):
    """
    Returns a new line list with the addons block replaced by the given
    entries, or None when the block markers are missing.
    """
    markers = _find_markers(lines)
    if markers is None:
        return None
    start_index, end_index = markers

    insert_lines = []
    for entry in addons_with_paths:
        insert_lines.extend(_block_lines(entry))

    return lines[:start_index + 1] + insert_lines + lines[end_index:]


def rewrite_addons_block_if_changed(gameinfo_path, addons_with_paths):
    """
    Rewrites the addons block only when the stored text differs from what
    the given entries produce, so a file that is already in sync is not
    touched at all.
    Used to bring gameinfo.txt in line with the list the user sees: a map
    stored as a .vpk, or one carrying the legacy MAP prefix, is fixed on the
    next refresh instead of waiting for the next mount.
    Returns tuple (rewritten, message)
    """
    try:
        if addon_manager.validate_addon_markers(gameinfo_path) != "ok":
            return False, tr("Addons block markers corrupted.")

        with open(gameinfo_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        new_lines = _replace_addons_block(lines, addons_with_paths)
        if new_lines is None:
            return False, tr("Failed to find addons block markers.")

        if new_lines == lines:
            return False, tr("Addons block already up to date")

        markers = _find_markers(lines)
        start_index, end_index = markers
        stored_entries = sum(1 for line in lines[start_index + 1:end_index]
                             if 'game+mod' in line)
        if stored_entries != len(addons_with_paths):
            # Something in the block was not parsed as an addon, a hand
            # written entry without a title comment for instance. Rebuilding
            # the block would drop it, so the file is left untouched.
            log.warning(tr("gameinfo.txt addons block was not rewritten: {} entries stored, {} addons parsed").format(
                stored_entries, len(addons_with_paths)))
            return False, tr("Addons block left unchanged")

        with open(gameinfo_path, 'w', encoding='utf-8') as file:
            file.writelines(new_lines)

        log.info(tr("gameinfo.txt addons block updated to match the list"))
        return True, tr("Addons block updated")

    except Exception as e:
        log.error(f"Error rewriting addons block: {str(e)}")
        return False, f"Error rewriting addons block: {str(e)}"


def update_gameinfo(gameinfo_path, addons_with_paths):
    """
    Adds addon paths to gameinfo.txt file between markers
    addons_with_paths: list of dicts with 'path', 'title', 'is_map'
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
        for entry in addons_with_paths:
            vpk_path = entry['path']
            # Extract ID from path to search in existing addons
            addon_id = addon_manager.extract_addon_id(vpk_path)
            
            # If this addon already exists, use its stored data (including
            # is_map), otherwise add the new entry
            if addon_id in existing_addons_by_id:
                all_addons_with_paths.append(existing_addons_by_id[addon_id])
                # Remove from dictionary to avoid duplicate addition
                del existing_addons_by_id[addon_id]
            else:
                all_addons_with_paths.append(entry)
        
        # Add remaining existing addons (which were not in collection)
        for addon_id, addon in existing_addons_by_id.items():
            all_addons_with_paths.append(addon)
        
        # Create lines to insert between markers
        insert_lines = []
        for entry in all_addons_with_paths:
            insert_lines.extend(_block_lines(entry))
        
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
    addons_with_paths: list of dicts with 'path', 'title', 'is_map'
    Returns tuple (success, message)
    """
    try:
        # Check markers
        marker_status = addon_manager.validate_addon_markers(gameinfo_path)
        
        if marker_status != "ok":
            return False, tr("Addons block markers corrupted.")
        
        with open(gameinfo_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # Replace content between markers
        new_lines = _replace_addons_block(lines, addons_with_paths)
        if new_lines is None:
            return False, tr("Failed to find addons block markers.")
        
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