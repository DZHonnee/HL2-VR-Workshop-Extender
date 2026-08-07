import os
import re
import workshop
import vpk
import shutil
from logger import log
import concurrent.futures
from i18n import tr, translator
import gameinfo
import requests

def read_addons_from_gameinfo(gameinfo_path):
    """
    Reads addons list from gameinfo.txt between markers
    Returns list of dictionaries with addon information
    """
    if not os.path.exists(gameinfo_path):
        log.warning(tr("gameinfo.txt file not found at path: {}").format(gameinfo_path))
        return []
    
    try:
        
        with open(gameinfo_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        addons = []
        
        # Check for markers presence
        start_marker = "//mounted_addons_start"
        end_marker = "//mounted_addons_end"
        
        start_index = content.find(start_marker)
        end_index = content.find(end_marker)
        
        # If markers found, search for addons only between them
        if start_index != -1 and end_index != -1 and start_index < end_index:
            addon_content = content[start_index:end_index]
        else:
            # Otherwise search in entire SearchPaths block
            log.info(tr("Addon markers not found, searching in entire SearchPaths block"))
            searchpaths_match = re.search(r'SearchPaths\s*\{([^}]+)\}', content, re.DOTALL)
            if not searchpaths_match:
                log.warning(tr("SearchPaths block not found in gameinfo.txt"))
                return []
            addon_content = searchpaths_match.group(1)
        
        # Search for addon blocks
        pattern = r'//\s*([^\n]+?)\s*\n\s*game\+mod\s+"(.+?)"'
        matches = re.findall(pattern, addon_content, re.DOTALL)
        
        
        for i, (title, path) in enumerate(matches, 1):
            clean_title = title.strip()
            addon_id = extract_addon_id(path)
            
            addons.append({
                'number': i,
                'title': clean_title,
                'id': addon_id,
                'path': path
            })
        return addons
    
    except Exception as e:
        log.error(tr("Error reading gameinfo.txt: {}").format(e))
        return []

def extract_addon_id(path):
    """Extracts addon ID from path"""
    # Search for ID in path (format /workshop/content/220/ID/workshop_dir.vpk or /workshop/content/220/ID/workshop_dir)
    match = re.search(r'[/\\]workshop[/\\]content[/\\]220[/\\](\d+)[/\\](?:workshop_dir\.vpk|workshop_dir)', path)
    if match:
        return match.group(1)
    
    # Alternative path format
    match = re.search(r'[/\\](\d+)[/\\](?:workshop_dir\.vpk|workshop_dir)', path)
    if match:
        return match.group(1)
    
    # For VPK files, use the filename without extension
    if path.lower().endswith('.vpk'):
        return os.path.splitext(os.path.basename(path))[0]
    
    # For folder mods, extract the folder name from the path string as ID (regardless of whether it exists)
    # Get the folder name from the path string
    return os.path.basename(path)

def remove_addons_from_gameinfo(gameinfo_path, addon_ids):
    """
    Removes addons from gameinfo.txt by their IDs
    Returns tuple (success, message)
    """
    try:
        log.info(tr("Removing addons from gameinfo.txt..."))
        
        with open(gameinfo_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Get current addons
        current_addons = read_addons_from_gameinfo(gameinfo_path)
        ids_to_remove = set(addon_ids)
        
        # Find line indices to remove
        lines_to_remove = set()
        removed_titles = []
        
        for addon in current_addons:
            if addon['id'] in ids_to_remove:
                # Find lines of this addon by ID (more reliable than by title)
                for i, line in enumerate(lines):
                    clean_line = line.strip()
                    # Find comment line containing addon title (with or without prefix)
                    if clean_line.startswith('//') and (addon['title'] in clean_line or addon['title'].replace("MAP   |   ", "") in clean_line):
                        # Check next line for path - enhanced to handle all types of paths properly
                        if i + 1 < len(lines):
                            next_line = lines[i + 1]
                            
                            # Check if addon path is in the next line - multiple strategies
                            path_found = False
                            
                            # Strategy 1: Direct inclusion check
                            if addon['path'] in next_line:
                                path_found = True
                            
                            # Strategy 2: Standard workshop path conversions
                            elif (addon['path'].replace('workshop_dir', 'workshop_dir.vpk') in next_line or
                                  addon['path'].replace('workshop_dir.vpk', 'workshop_dir') in next_line):
                                path_found = True
                            
                            # Strategy 3: Normalize path separators (forward/backward slashes)
                            elif addon['path'].replace('\\', '/') in next_line.replace('\\', '/'):
                                path_found = True
                            elif addon['path'].replace('/', '\\') in next_line.replace('/', '\\'):
                                path_found = True
                            
                            # Strategy 4: Check for basename if path is complex
                            elif os.path.basename(addon['path']) in next_line:
                                # Extra validation to make sure it's the right path
                                path_found = True
                            
                            if path_found:
                                lines_to_remove.add(i)    # Comment
                                lines_to_remove.add(i + 1)  # Path
                                # Check if there's empty line after
                                if i + 2 < len(lines) and lines[i + 2].strip() == '':
                                    lines_to_remove.add(i + 2)
                                
                                removed_titles.append(addon['title'])
                        break
        
        # Remove lines and create new list
        new_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]
        
        # Write modified file
        with open(gameinfo_path, 'w', encoding='utf-8') as file:
            file.writelines(new_lines)
        
        removed_count = len(ids_to_remove)
            
        log.info(tr("Successfully removed {} addons").format(removed_count))
        return True, tr("Removed {} addons").format(removed_count)
    
    except Exception as e:
        log.error(f"Error removing addons: {str(e)}")
        return False, f"Error removing addons: {str(e)}"

def filter_duplicate_addons(gameinfo_path, addons):
    """
    Filters duplicate addons
    Returns tuple (unique addons, duplicates)
    """
    existing_addons = read_addons_from_gameinfo(gameinfo_path)
    
    # Create set of existing addon IDs (ignoring path)
    existing_ids = {addon['id'] for addon in existing_addons}
    
    unique_addons = []
    duplicates = []
    
    for addon_id, title in addons:
        if addon_id in existing_ids:
            duplicates.append((addon_id, title))
        else:
            unique_addons.append((addon_id, title))
    log.info(tr("Filtering duplicates"))
    return unique_addons, duplicates

def has_addon_markers(gameinfo_path):
    """Checks for the presence of start and end tags of the addons block"""
    if not os.path.exists(gameinfo_path):
        return False, False
    
    try:
        with open(gameinfo_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        start_marker = "//mounted_addons_start"
        end_marker = "//mounted_addons_end"
        
        has_start = start_marker in content
        has_end = end_marker in content
        
        return has_start, has_end
    
    except Exception as e:
        print(f"Error checking markers: {e}")
        return False, False

def validate_addon_markers(gameinfo_path):
    """Checks marker integrity and returns status"""
    has_start, has_end = has_addon_markers(gameinfo_path)
    
    if has_start and has_end:
        return "ok"
    elif has_start and not has_end:
        return "missing_end"
    elif not has_start and has_end:
        return "missing_start"
    else:
        return "no_markers"


def _copy_file_if_changed(src_path, dst_path):
    """Copy file if source exists and is different from destination.
    Returns True if file was copied, False otherwise."""
    if not os.path.exists(src_path):
        return False
    
    # If destination doesn't exist -> copy
    if not os.path.exists(dst_path):
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy2(src_path, dst_path)
        return True
    
    # Compare by size and modification time (fast)
    src_stat = os.stat(src_path)
    dst_stat = os.stat(dst_path)
    
    if src_stat.st_size != dst_stat.st_size or src_stat.st_mtime != dst_stat.st_mtime:
        shutil.copy2(src_path, dst_path)
        return True
    
    return False


def _sync_folder(src_dir, dst_dir, items_to_sync):
    """
    Syncs specified files/folders from src to dst.
    Returns number of files actually copied.
    """
    if not os.path.exists(src_dir):
        log.warning(tr("Source directory not found: {}").format(src_dir))
        return 0
    
    os.makedirs(dst_dir, exist_ok=True)
    
    copied_count = 0
    
    for item in items_to_sync:
        src_path = os.path.join(src_dir, item)
        dst_path = os.path.join(dst_dir, item)
        
        if not os.path.exists(src_path):
            continue
        
        if os.path.isdir(src_path):
            # For folders: copy entire directory structure with file-level sync
            for root, dirs, files in os.walk(src_path):
                rel_path = os.path.relpath(root, src_dir)
                dst_subdir = os.path.join(dst_dir, rel_path)
                os.makedirs(dst_subdir, exist_ok=True)
                
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dst_subdir, file)
                    if _copy_file_if_changed(src_file, dst_file):
                        copied_count += 1
        else:
            # For files: copy if changed
            if _copy_file_if_changed(src_path, dst_path):
                copied_count += 1
    
    # Clean up old files in destination that no longer exist in source
    _cleanup_stale_files(dst_dir, items_to_sync)
    
    return copied_count


def _sync_full_folder(src_dir, dst_dir):
    """
    Sync entire folder content (for resource folders).
    Returns number of files actually copied.
    """
    if not os.path.exists(src_dir):
        return 0
    
    os.makedirs(dst_dir, exist_ok=True)
    
    copied_count = 0
    
    # Get all files in source
    src_files = set()
    for root, dirs, files in os.walk(src_dir):
        rel_path = os.path.relpath(root, src_dir)
        for file in files:
            src_files.add(os.path.join(rel_path, file) if rel_path != '.' else file)
    
    # Copy missing or changed files
    for root, dirs, files in os.walk(src_dir):
        rel_path = os.path.relpath(root, src_dir)
        dst_subdir = os.path.join(dst_dir, rel_path) if rel_path != '.' else dst_dir
        os.makedirs(dst_subdir, exist_ok=True)
        
        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(dst_subdir, file)
            if _copy_file_if_changed(src_file, dst_file):
                copied_count += 1
    
    # Remove files in destination that are no longer in source
    for root, dirs, files in os.walk(dst_dir, topdown=False):
        rel_path = os.path.relpath(root, dst_dir)
        for file in files:
            file_rel = os.path.join(rel_path, file) if rel_path != '.' else file
            if file_rel not in src_files:
                try:
                    os.remove(os.path.join(root, file))
                    log.info(tr("Removed stale file: {}").format(os.path.join(root, file)))
                except Exception as e:
                    log.warning(tr("Failed to remove stale file: {}").format(e))
        
        # Remove empty directories
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except Exception:
                pass
    
    return copied_count


def _cleanup_stale_files(dst_dir, items_to_sync):
    """Removes files/folders from dst_dir that are not in items_to_sync"""
    if not os.path.exists(dst_dir):
        return
    
    # Build set of all paths that should exist in the destination
    valid_paths = set()
    for item in items_to_sync:
        dst_path = os.path.join(dst_dir, item)
        if os.path.exists(dst_path):
            valid_paths.add(os.path.normpath(dst_path))
            if os.path.isdir(dst_path):
                for root, dirs, files in os.walk(dst_path):
                    for file in files:
                        valid_paths.add(os.path.normpath(os.path.join(root, file)))
    
    # Remove files not in the valid set
    for root, dirs, files in os.walk(dst_dir, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.normpath(file_path) not in valid_paths:
                try:
                    os.remove(file_path)
                    log.info(tr("Removed stale file: {}").format(file_path))
                except Exception as e:
                    log.warning(tr("Failed to remove stale file {}: {}").format(file_path, e))
        
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if os.path.normpath(dir_path) not in valid_paths:
                try:
                    if not os.listdir(dir_path):  # Check if empty
                        os.rmdir(dir_path)
                        log.info(tr("Removed stale directory: {}").format(dir_path))
                except Exception as e:
                    log.warning(tr("Failed to remove stale directory {}: {}").format(dir_path, e))


def create_vr_essential_backup(hl2vr_path):
    """
    Creates or updates copies of important VR mod files in the custom/vr_essential_resources folder.
    Only copies files that are missing or have changed (by size + mtime).
    Logs only when actual changes occur.
    """
    copied_count = 0
    
    try:
        # ----- HLVR -----
        hlvr_backup_path = os.path.join(hl2vr_path, "hlvr", "custom", "vr_essential_resources")
        hlvr_scripts_src = os.path.join(hl2vr_path, "hlvr", "scripts")
        
        scripts_to_copy = [
            "colorcorrection",
            "screens",
            "bhaptics_effects.txt",
            "game_sounds_weapons.txt",
            "HudAnimations.txt",
            "HudLayout.res",
            "rumble_effects.txt",
            "vgui_screens.txt",
            "weapon_357.txt",
            "weapon_ar2.txt",
            "weapon_bugbait.txt",
            "weapon_crossbow.txt",
            "weapon_crowbar.txt",
            "weapon_cubemap.txt",
            "weapon_frag.txt",
            "weapon_physcannon.txt",
            "weapon_physgun.txt",
            "weapon_pistol.txt",
            "weapon_rpg.txt",
            "weapon_shotgun.txt",
            "weapon_smg1.txt"
        ]
        
        # Sync scripts
        copied_count += _sync_folder(hlvr_scripts_src, os.path.join(hlvr_backup_path, "scripts"), scripts_to_copy)
        
        # Sync entire resource folder
        hlvr_resource_src = os.path.join(hl2vr_path, "hlvr", "resource")
        if os.path.exists(hlvr_resource_src):
            copied_count += _sync_full_folder(hlvr_resource_src, os.path.join(hlvr_backup_path, "resource"))
        
        # ----- EPISODICVR -----
        episodicvr_path = os.path.join(hl2vr_path, "episodicvr")
        if os.path.exists(episodicvr_path):
            episodicvr_backup_path = os.path.join(hl2vr_path, "episodicvr", "custom", "vr_essential_resources")
            episodic_resource_src = os.path.join(episodicvr_path, "resource")
            if os.path.exists(episodic_resource_src):
                copied_count += _sync_full_folder(episodic_resource_src, os.path.join(episodicvr_backup_path, "resource"))
        
        # ----- EP2VR -----
        ep2vr_path = os.path.join(hl2vr_path, "ep2vr")
        if os.path.exists(ep2vr_path):
            ep2vr_backup_path = os.path.join(hl2vr_path, "ep2vr", "custom", "vr_essential_resources")
            
            ep2_resource_src = os.path.join(ep2vr_path, "resource")
            if os.path.exists(ep2_resource_src):
                copied_count += _sync_full_folder(ep2_resource_src, os.path.join(ep2vr_backup_path, "resource"))
            
            ep2_scripts_src = os.path.join(ep2vr_path, "scripts")
            ep2_scripts_to_copy = ["hudlayout.res", "vgui_screens.txt"]
            copied_count += _sync_folder(ep2_scripts_src, os.path.join(ep2vr_backup_path, "scripts"), ep2_scripts_to_copy)
        
        # Only log if actual files were copied
        if copied_count > 0:
            log.info(tr("Essential VR files prioritized via custom folder ({} file(s) updated)").format(copied_count))
        
        return True, tr("VR essential files synchronized")
        
    except Exception as e:
        log.error(f"Error syncing VR resources: {str(e)}")
        return False, f"Error syncing VR resources: {str(e)}"

def add_addon_markers(gameinfo_path, hl2vr_path=None, hl2_path=None):
    """Adds start and end markers for addons block after custom folders"""
    try:
        with open(gameinfo_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Find insertion position - after custom folders and before "// mount VR files first"
        insert_index = -1
        found_custom = False
        
        for i, line in enumerate(lines):
            # Look for lines with custom folders
            if 'custom/*' in line and 'game+mod' in line:
                found_custom = True
                continue
            
            # If we found custom folders and now found "mount VR files", insert before it
            if found_custom and ('// mount VR files first' in line or '// mount VR files' in line):
                insert_index = i
                break
        
        # If exact match not found, look after the last custom folder
        if insert_index == -1 and found_custom:
            for i, line in enumerate(lines):
                if 'custom/*' in line and 'game+mod' in line:
                    insert_index = i + 1  # After the last custom folder
        
        # If still not found, use old logic (after SearchPaths {)
        if insert_index == -1:
            for i, line in enumerate(lines):
                if "SearchPaths" in line and i + 1 < len(lines) and "{" in lines[i + 1]:
                    insert_index = i + 2
                    break
        
        if insert_index == -1:
            return False, tr("gameinfo.txt is corrupted, addons cannot be mounted.")
        
        # Add markers
        marker_lines = ['\t\t//mounted_addons_start\n', '\t\t//mounted_addons_end\n']
        lines[insert_index:insert_index] = marker_lines
        
        # Write file
        with open(gameinfo_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)
        
        log.info(tr("Addon markers added to gameinfo.txt"))
        
        # Create VR files backup when adding markers for the first time
        if hl2vr_path:
            create_vr_essential_backup(hl2vr_path)
        
        return True, ""
    
    except Exception as e:
        log.error(f"Error adding markers: {str(e)}")
        return False, f"Error adding markers: {str(e)}"
    
def read_workshop_txt(hl2_path):
    """
    Reads addons list from workshop.txt
    Returns list of tuples (id, title) in file order
    """
    try:
        workshop_txt_path = os.path.join(hl2_path, "hl2_complete", "cfg", "workshop.txt")
        
        if not os.path.exists(workshop_txt_path):
            return None, tr("workshop.txt not found.")
        
        with open(workshop_txt_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Find addon IDs in format "ID" "1"
        pattern = r'"(\d+)"\s+"1"'
        matches = re.findall(pattern, content)
        
        if not matches:
            return None, tr("Installed addons not found.")
        
        log.info(tr("Read {} addons from workshop.txt").format(len(matches)))
        return matches, None
        
    except Exception as e:
        log.error(f"Error reading workshop.txt: {str(e)}")
        return None, f"Error reading workshop.txt: {str(e)}"
    
def check_addon_files_exists(addons_with_paths):
    """
    Checks addon files existence
    Returns tuple (existing_addons, missing_addons)
    """
    existing_addons = []
    missing_addons = []
    
    for vpk_path, title in addons_with_paths:
        if os.path.exists(vpk_path):
            existing_addons.append((vpk_path, title))
        else:
            # Extract ID from path for error message
            addon_id = extract_addon_id(vpk_path)
            missing_addons.append((addon_id, title, vpk_path))
    
    if missing_addons:
        log.warning(tr("Found {} missing addon files").format(len(missing_addons)))
    
    return existing_addons, missing_addons

def prepare_addons_for_embedding(collection_url, hl2vr_path, hl2_path, check_files=True):
    """
    Prepares addons for mounting
    check_files: whether to check addon files existence
    Returns tuple (success, data, error_message)
    """
    try:
        log.info(tr("Preparing addons from collection"))
        
        # Get addons from collection
        addons = workshop.get_collection_addons(collection_url)
        if not addons:
            return False, None, tr("Failed to find addons in collection.")
        
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        
        # Filter duplicates
        unique_addons, duplicates = filter_duplicate_addons(gameinfo_path, addons)
        
        if not unique_addons:
            if duplicates:
                return False, None, tr("All addons from collection already added.")
            else:
                return False, None, tr("Failed to find addons.")
        
        # Get workshop path
        from path_utils import get_workshop_path
        workshop_path = get_workshop_path(hl2_path)
        
        # Form paths to VPK files
        addons_with_paths = []
        for addon_id, title in unique_addons:
            vpk_path = os.path.join(workshop_path, addon_id, "workshop_dir.vpk")
            addons_with_paths.append((vpk_path, title))
        
        # Check files existence if option enabled
        missing_addons = []
        final_addons_with_paths = []
        final_unique_addons = []
        
        if check_files:
            # Separate addons into VPK and folders
            vpk_addons = [(path, title, addon_id) for (path, title), (addon_id, _) in 
                         zip(addons_with_paths, unique_addons) if path.endswith('.vpk')]
            folder_addons = [(path, title, addon_id) for (path, title), (addon_id, _) in 
                           zip(addons_with_paths, unique_addons) if not path.endswith('.vpk')]
            
            # Check VPK files
            existing_vpk_addons = []
            missing_vpk_addons = []
            
            for vpk_path, title, addon_id in vpk_addons:
                if os.path.exists(vpk_path):
                    existing_vpk_addons.append((vpk_path, title))
                    final_unique_addons.append((addon_id, title))
                else:
                    missing_vpk_addons.append((addon_id, title, vpk_path))
            
            # Folders always considered existing (they are created during extraction)
            existing_folder_addons = [(path, title) for path, title, addon_id in folder_addons]
            final_unique_addons.extend([(addon_id, title) for path, title, addon_id in folder_addons])
            
            # Combine existing addons
            final_addons_with_paths = existing_vpk_addons + existing_folder_addons
            missing_addons = missing_vpk_addons
            
            if not final_addons_with_paths and missing_addons:
                return False, None, tr("Addon files missing.")
        else:
            # If file check disabled, add all addons
            final_addons_with_paths = addons_with_paths
            final_unique_addons = unique_addons
        
        # Prepare data for return
        result_data = {
            'unique_addons': final_unique_addons,  # Only those that will be added
            'duplicates': duplicates,
            'missing_addons': missing_addons,
            'addons_with_paths': final_addons_with_paths,  # Only existing paths
            'gameinfo_path': gameinfo_path
        }
        
        log.info(tr("Prepared {} addons for mounting").format(len(final_unique_addons)))
        return True, result_data, ""
        
    except Exception as e:
        log.error(f"Error preparing addons: {str(e)}")
        return False, None, f"An unexpected error occurred:\n{str(e)}"

def prepare_single_addon_for_embedding(addon_url, hl2vr_path, hl2_path, check_files=True):
    """
    Prepares single addon for mounting
    check_files: whether to check addon files existence
    Returns tuple (success, data, error_message)
    """
    try:
        log.info(tr("Preparing single addon"))
        
        # Get addon information
        addon_id, title = workshop.get_single_addon(addon_url)
        if not addon_id:
            return False, None, tr("Failed to get addon information.")
        
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        
        # Check duplicates
        existing_ids = {addon['id'] for addon in read_addons_from_gameinfo(gameinfo_path)}
        if addon_id in existing_ids:
            return False, None, tr("Addon '{}' already added.").format(title)
        
        # Get workshop path
        from path_utils import get_workshop_path
        workshop_path = get_workshop_path(hl2_path)
        
        # Form path to VPK file
        vpk_path = os.path.join(workshop_path, addon_id, "workshop_dir.vpk")
        
        # Instead use VPK path directly
        final_path = vpk_path
        final_title = title
        # Check file existence if option enabled
        missing_addons = []
        final_unique_addons = []
        final_addons_with_paths = []
        
        if check_files and final_path.endswith('.vpk') and not os.path.exists(final_path):
            missing_addons = [(addon_id, title, final_path)]
            return False, None, tr("Addon file '{}' not found.").format(title)
        else:
            # File exists or check disabled
            final_unique_addons = [(addon_id, final_title)]
            final_addons_with_paths = [(final_path, final_title)]
        
        # Prepare data for return
        result_data = {
            'unique_addons': final_unique_addons,  # Only if will be added
            'duplicates': [],
            'missing_addons': missing_addons,
            'addons_with_paths': final_addons_with_paths,  # Only if exists
            'gameinfo_path': gameinfo_path
        }
        
        log.info(tr("Addon '{}' prepared for mounting").format(title))
        return True, result_data, ""
        
    except Exception as e:
        log.error(f"Error preparing single addon: {str(e)}")
        return False, None, f"An unexpected error occurred:\n{str(e)}"

def prepare_addons_from_workshop_txt(hl2vr_path, hl2_path, check_files=True, check_cancel=None, progress_callback=None):
    """
    Prepares addons from workshop.txt for mounting
    check_cancel: function that returns True if operation should be cancelled
    progress_callback: function(current, total) to report progress
    """
    try:
        log.info(tr("Starting preparation of addons from workshop.txt"))
        
        # Read addon IDs from workshop.txt
        addon_ids, error_message = read_workshop_txt(hl2_path)
        if error_message:
            return False, None, error_message
        
        if not addon_ids:
            return False, None, tr("Installed addons not found.")
        
        # Check cancellation before starting
        if check_cancel and check_cancel():
            return False, None, tr("Operation cancelled by user")
        
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        
        # Multithreaded processing with immediate stop capability
        unique_addons = []
        failed_addons = []
        
        # Flag to stop all threads
        rate_limit_hit = False
        
        def fetch_addon_info(addon_id):
            """Function to get information about one addon"""
            # Declare nonlocal BEFORE first use of the variable
            nonlocal rate_limit_hit
            
            if rate_limit_hit:
                return ('cancelled', addon_id, None)
                
            try:
                addon_id_str, title = workshop.get_addon_by_id(addon_id)
                if addon_id_str and title:
                    return ('success', addon_id_str, title)
                else:
                    return ('failed', addon_id, None)
            except workshop.SteamRateLimitException as e:
                # Mark that rate limit reached
                rate_limit_hit = True
                return ('rate_limit', addon_id, None)
            except Exception as e:
                return ('error', addon_id, str(e))
        
        # Use fewer threads to reduce load
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit tasks
            future_to_index = {}
            for index, addon_id in enumerate(addon_ids):
                # Check cancellation and limit before submitting each task
                if check_cancel and check_cancel():
                    return False, None, tr("Operation cancelled by user")
                
                if rate_limit_hit:
                    break
                    
                future = executor.submit(fetch_addon_info, addon_id)
                future_to_index[future] = index
            
            # Process results
            processed_count = 0
            for future in concurrent.futures.as_completed(future_to_index):
                # Check cancellation
                if check_cancel and check_cancel():
                    return False, None, tr("Operation cancelled by user")
                
                index = future_to_index[future]
                addon_id = addon_ids[index]
                
                try:
                    result_type, result_id, result_data = future.result()
                    
                    if result_type == 'rate_limit':
                        # Immediately stop when rate limit reached
                        error_msg = tr("Steam request limit exceeded! " \
                            "Open Help > Recommendations and issues, scroll down to \"Steam request limit exceeded\" paragraph for more details and solutions.")
                        log.error(f"Steam rate limit (429) detected while loading addon {addon_id}")
                        
                        # Cancel all remaining tasks
                        for f in future_to_index:
                            if not f.done():
                                f.cancel()
                        
                        return False, None, error_msg
                    
                    elif result_type == 'success':
                        log.info(tr("Loaded ({}/{}): {}").format(processed_count + 1, len(addon_ids), result_data))
                        unique_addons.append((result_id, result_data))
                    elif result_type == 'failed':
                        log.warning(tr("✗ Failed to load ({}/{}): ID {}").format(processed_count + 1, len(addon_ids), result_id))
                        failed_addons.append(result_id)
                    elif result_type == 'cancelled':
                        log.debug(tr("Cancelled loading ID {} due to rate limit").format(result_id))
                    else:
                        log.error(tr("✗ Error loading ({}/{}): ID {} - {}").format(processed_count + 1, len(addon_ids), result_id, result_data))
                        failed_addons.append(result_id)
                        
                except Exception as e:
                    log.error(tr("✗ Unexpected error ({}/{}): ID {} - {}").format(processed_count + 1, len(addon_ids), addon_id, str(e)))
                    failed_addons.append(addon_id)
                
                processed_count += 1
                # Update progress
                if progress_callback:
                    progress_callback(processed_count, len(addon_ids))
        
        # Check cancellation after loading
        if check_cancel and check_cancel():
            return False, None, tr("Operation cancelled by user")
        
        if not unique_addons:
            return False, None, tr("Failed to get information about installed addons.")
        
        log.info(tr("Successfully processed {} out of {} addons").format(len(unique_addons), len(addon_ids)))

        # Check cancellation before processing duplicates
        if check_cancel and check_cancel():
            return False, None, tr("Operation cancelled by user")
        
        # Check duplicates
        existing_ids = {addon['id'] for addon in read_addons_from_gameinfo(gameinfo_path)}
        filtered_addons = []
        duplicates = []
        
        for addon_id, title in unique_addons:
            if addon_id in existing_ids:
                duplicates.append((addon_id, title))
            else:
                filtered_addons.append((addon_id, title))
        
        # Check cancellation before preparing paths
        if check_cancel and check_cancel():
            return False, None, tr("Operation cancelled by user")
        
        if not filtered_addons:
            if duplicates:
                return False, None, tr("All addons already added.")
            else:
                return False, None, tr("Failed to find addons to add.")
        
        # Get workshop path
        from path_utils import get_workshop_path
        workshop_path = get_workshop_path(hl2_path)
        
        # Check cancellation before forming paths
        if check_cancel and check_cancel():
            return False, None, tr("Operation cancelled by user")
        
        # Form paths to VPK files
        addons_with_paths = []
        for addon_id, title in filtered_addons:
            vpk_path = os.path.join(workshop_path, addon_id, "workshop_dir.vpk")
            addons_with_paths.append((vpk_path, title))
        
        # Check cancellation before file existence check
        if check_cancel and check_cancel():
            return False, None, tr("Operation cancelled by user")
        
        # Check files existence if option enabled
        missing_addons = []
        final_addons_with_paths = []
        final_unique_addons = []
        
        if check_files:
            log.info(tr("Checking addon files existence"))
            # Separate addons into VPK and folders
            vpk_addons = [(path, title, addon_id) for (path, title), (addon_id, _) in 
                         zip(addons_with_paths, filtered_addons) if path.endswith('.vpk')]
            folder_addons = [(path, title, addon_id) for (path, title), (addon_id, _) in 
                           zip(addons_with_paths, filtered_addons) if not path.endswith('.vpk')]
            
            # Check VPK files
            existing_vpk_addons = []
            missing_vpk_addons = []
            
            for i, (vpk_path, title, addon_id) in enumerate(vpk_addons):
                # Check cancellation during file check
                if check_cancel and check_cancel():
                    return False, None, tr("Operation cancelled by user")
                    
                if os.path.exists(vpk_path):
                    existing_vpk_addons.append((vpk_path, title))
                    final_unique_addons.append((addon_id, title))
                else:
                    missing_vpk_addons.append((addon_id, title, vpk_path))
                
                # Update progress for file checking
                if progress_callback:
                    base_progress = len(addon_ids)
                    current_file_check = i + 1
                    total_files_check = len(vpk_addons) + len(folder_addons)
                    progress_callback(base_progress + current_file_check, base_progress + total_files_check)
            
            # Check cancellation after VPK check
            if check_cancel and check_cancel():
                return False, None, tr("Operation cancelled by user")
            
            # Folders always considered existing
            existing_folder_addons = [(path, title) for path, title, addon_id in folder_addons]
            final_unique_addons.extend([(addon_id, title) for path, title, addon_id in folder_addons])
            
            # Combine existing addons
            final_addons_with_paths = existing_vpk_addons + existing_folder_addons
            missing_addons = missing_vpk_addons
            
            # FIX: Check if there are any addons to add at all
            if not final_addons_with_paths:
                if missing_addons:
                    return False, None, tr("Addon files missing.")
                else:
                    return False, None, tr("Failed to find addons to add.")
                    
        else:
            # FIX: With file check disabled, use ALL addons from filtered_addons
            # regardless of whether their files exist or not
            final_addons_with_paths = addons_with_paths
            final_unique_addons = filtered_addons
            
            # FIX: Check that list is not empty
            if not final_addons_with_paths:
                return False, None, tr("Failed to find addons to add.")
        
        # Prepare data for return
        result_data = {
            'unique_addons': final_unique_addons,  # Only those that will be added
            'duplicates': duplicates,
            'failed_addons': failed_addons,
            'missing_addons': missing_addons,
            'addons_with_paths': final_addons_with_paths,  # Only existing paths
            'gameinfo_path': gameinfo_path
        }
        
        log.info(tr("Prepared {} addons from workshop.txt").format(len(final_unique_addons)))
        return True, result_data, ""
        
    except Exception as e:
        log.error(f"Error preparing addons from workshop.txt: {str(e)}")
        return False, None, f"An unexpected error occurred:\n{str(e)}"
    
def extract_map_vpk(vpk_path, output_dir, progress_callback=None, check_cancel=None):
    """
    Extracts map VPK file to specified directory
    progress_callback: function to update progress (current, total, filename) returns False if need to cancel
    Returns tuple (success, message)
    """
    try:
        # Check VPK file existence
        if not os.path.exists(vpk_path):
            return False, tr("VPK file not found: {}").format(vpk_path)
        
        # Check if addon already extracted
        if os.path.exists(output_dir):
            # Check if folder is not empty
            try:
                folder_contents = os.listdir(output_dir)
                if len(folder_contents) > 0:
                    return True, tr("Folder already exists and not empty")
                else:
                    # If folder is empty, delete it and extract again
                    shutil.rmtree(output_dir)
            except:
                pass
        
        # Create directory for extraction
        os.makedirs(output_dir, exist_ok=True)
        
        # Open VPK
        pak = vpk.open(vpk_path)
        
        # Get list of all files to count total
        all_files = list(pak)
        total_files = len(all_files)
        
        if total_files == 0:
            # If VPK is empty, delete created folder and return error
            os.rmdir(output_dir)
            return False, tr("VPK file is empty")
        
        log.info(tr("Starting map extraction: ({} files)").format(total_files))
        
        # Extract all files
        extracted_count = 0
        for i, filepath in enumerate(all_files):
            # Check cancellation via callback
            if check_cancel and check_cancel():
                # Delete partially extracted folder
                if os.path.exists(output_dir):
                    shutil.rmtree(output_dir)
                return False, tr("Extraction cancelled")
                
            try:
                pak_file = pak.get_file(filepath)
                save_path = os.path.join(output_dir, filepath)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                pak_file.save(save_path)
                extracted_count += 1
                
                # Call callback to update progress
                if progress_callback:
                    # If callback returns False - interrupt extraction
                    should_continue = progress_callback(i + 1, total_files, filepath)
                    if not should_continue:
                        # Delete partially extracted folder
                        if os.path.exists(output_dir):
                            shutil.rmtree(output_dir)
                        return False, tr("Extraction cancelled")
                    
            except Exception as e:
                # In case of error, try to delete empty folder
                try:
                    if os.path.exists(output_dir) and not os.listdir(output_dir):
                        shutil.rmtree(output_dir)
                except:
                    pass
                return False, tr("Error extracting {}: {}").format(filepath, e)
        
        log.info(tr("Map extracted: {}/{} files").format(extracted_count, total_files))
        
        # After successful extraction, remove specified folders and files
        cleanup_extracted_map(output_dir)
        
        return True, tr("Successfully extracted {} files").format(extracted_count)
        
    except Exception as e:
        # In case of error, try to delete empty folder
        try:
            if os.path.exists(output_dir) and not os.listdir(output_dir):
                shutil.rmtree(output_dir)
        except:
            pass
        log.error(tr("Error extracting map: {}").format(e))
        return False, tr("Error extracting map: {}. For possible solution see Help (Maps tab).").format(e)

def check_and_extract_maps(gameinfo_path, current_addons, progress_callback=None, specific_addons=None):
    """
    Checks addons for unpacked maps and extracts them
    ASSUMES all addons passed are already confirmed as maps
    progress_callback: function to update progress (current_map, total_maps, current_file, total_files, status) returns False if need to cancel
    """
    try:
        extracted_addons = []
        failed_addons = []
        updated_addons = []
        for addon in current_addons:
            updated_addons.append(addon.copy())

        # Determine which addons to process
        addons_to_process = specific_addons if specific_addons is not None else []
        
        # If specific_addons is None, this function shouldn't be called
        # But for safety, if it happens, just return
        if not addons_to_process:
            log.warning(tr("No specific addons provided for map extraction"))
            return True, [], {
                'extracted': [],
                'failed': [],
                'total_maps': 0,
                'updated_addons': updated_addons,
                'cancelled': False
            }

        total_maps = len(addons_to_process)
        current_map = 0

        log.info(tr("Extracting maps: {} maps to process").format(total_maps))

        for i, addon in enumerate(addons_to_process):
            # Check cancellation before processing each addon
            if progress_callback:
                should_continue = progress_callback(current_map, total_maps, 0, 0, tr("Processing addon: {}").format(addon['title']))
                if not should_continue:
                    return True, addons_to_process, {
                        'extracted': extracted_addons,
                        'failed': failed_addons,
                        'total_maps': total_maps,
                        'updated_addons': updated_addons,
                        'cancelled': True
                    }
            
            current_map += 1
            
            # Find the addon in updated_addons
            updated_addon = None
            for ua in updated_addons:
                if ua['id'] == addon['id']:
                    updated_addon = ua
                    break
            
            if not updated_addon:
                continue

            current_path = addon['path']
            current_title = addon['title']
            
            vpk_path = None
            output_dir = None
            
            if current_path.endswith('.vpk'):
                vpk_path = current_path
                output_dir = current_path.replace('workshop_dir.vpk', 'workshop_dir')
            elif current_path.endswith('workshop_dir'):
                vpk_path = current_path + '.vpk'
                output_dir = current_path

            # Check not only folder existence but also its contents
            folder_exists = False
            if output_dir and os.path.exists(output_dir):
                try:
                    folder_contents = os.listdir(output_dir)
                    folder_exists = len(folder_contents) > 0
                    if not folder_exists:
                        # Folder exists but empty - delete it
                        shutil.rmtree(output_dir)
                except Exception as e:
                    folder_exists = False

            # Check VPK file existence
            vpk_exists = vpk_path and os.path.exists(vpk_path)
            
            # If VPK file exists and no NON-EMPTY folder, extract
            if vpk_exists and not folder_exists:
                def file_progress(current_file, total_files, filename):
                    if progress_callback:
                        return progress_callback(current_map, total_maps, current_file, total_files, tr("{}: {}").format(addon['title'], filename))
                    return True

                success, message = extract_map_vpk(vpk_path, output_dir, file_progress)
                if success:
                    updated_addon['path'] = output_dir
                    if not current_title.startswith("MAP   |   "):
                        updated_addon['title'] = "MAP   |   " + current_title
                    extracted_addons.append(updated_addon)
                else:
                    if tr("cancelled") in message:
                        # Extraction was cancelled
                        return True, addons_to_process, {
                            'extracted': extracted_addons,
                            'failed': failed_addons,
                            'total_maps': total_maps,
                            'updated_addons': updated_addons,
                            'cancelled': True
                        }
                    failed_addons.append((updated_addon, message))
                    continue
            # If folder already exists AND NOT EMPTY, check prefix
            elif folder_exists:
                updated_addon['path'] = output_dir
                if not current_title.startswith("MAP   |   "):
                    updated_addon['title'] = "MAP   |   " + current_title
            # If VPK doesn't exist, but non-empty folder exists - all good
            elif not vpk_exists and folder_exists:
                updated_addon['path'] = output_dir
                if not current_title.startswith("MAP   |   "):
                    updated_addon['title'] = "MAP   |   " + current_title
            else:
                # Neither VPK nor non-empty folder exist
                error_msg = tr("VPK file and non-empty extraction folder not found")
                if vpk_path:
                    error_msg += tr(" (VPK: {})").format(vpk_path)
                failed_addons.append((updated_addon, error_msg))
                continue

        log.info(tr("Map check completed: {} extracted, {} errors").format(len(extracted_addons), len(failed_addons)))
        return True, addons_to_process, {
            'extracted': extracted_addons,
            'failed': failed_addons,
            'total_maps': total_maps,
            'updated_addons': updated_addons,
            'cancelled': False
        }
        
    except Exception as e:
        log.error(f"Error checking maps: {str(e)}")
        return False, [], f"Error checking maps: {str(e)}"

def check_and_update_map_paths(hl2_path, addons_with_paths):
    """
    Checks addons for unpacked maps and updates paths
    Returns updated list of addons_with_paths
    """
    try:
        updated_addons = []
        
        for vpk_path, title in addons_with_paths:
            updated_path = vpk_path
            
            # If path points to VPK file, check for unpacked folder
            if vpk_path.endswith('.vpk'):
                output_dir = vpk_path.replace('workshop_dir.vpk', 'workshop_dir')
                if os.path.exists(output_dir):
                    # Use folder path instead of VPK
                    updated_path = output_dir
                    # Do NOT add prefix here - this will only be done after is_addon_map check
            
            updated_addons.append((updated_path, title))
        
        return updated_addons
        
    except Exception as e:
        print(f"Error checking unpacked maps: {e}")
        return addons_with_paths
    
def clear_extracted_maps(workshop_path, gameinfo_path):
    """
    Deletes all extracted workshop_dir folders and returns paths to .vpk in gameinfo.txt
    Returns tuple (success, message)
    """
    try:
        log.info(tr("Clearing extracted maps..."))
        
        deleted_folders = 0
        updated_paths = 0
        
        # 1. Delete all workshop_dir folders in workshop folder
        if os.path.exists(workshop_path):
            for item in os.listdir(workshop_path):
                addon_path = os.path.join(workshop_path, item)
                if os.path.isdir(addon_path):
                    workshop_dir_path = os.path.join(addon_path, "workshop_dir")
                    if os.path.exists(workshop_dir_path):
                        try:
                            shutil.rmtree(workshop_dir_path)
                            deleted_folders += 1
                        except Exception as e:
                            print(f"Error deleting {workshop_dir_path}: {e}")
        
        # 2. Update paths in gameinfo.txt - FIXED LOGIC
        if os.path.exists(gameinfo_path):
            with open(gameinfo_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Find lines with paths to workshop_dir (without .vpk)
            new_lines = []
            for line in lines:
                original_line = line
                # Find lines with game+mod and path ending with workshop_dir (without .vpk)
                if 'game+mod' in line and 'workshop_dir' in line and '.vpk' not in line:
                    # Replace folder path with .vpk path
                    line = line.replace('workshop_dir"', 'workshop_dir.vpk"')
                    if line != original_line:
                        updated_paths += 1
                
                new_lines.append(line)
            
            # Write changes only if there are any
            if updated_paths > 0:
                with open(gameinfo_path, 'w', encoding='utf-8') as file:
                    file.writelines(new_lines)
        
        log.info(tr("Clearing completed: {} folders deleted, {} paths updated").format(deleted_folders, updated_paths))
        return True, tr("Deleted folders: {}").format(deleted_folders)
        
    except Exception as e:
        log.error(f"Error clearing maps: {str(e)}")
        return False, f"Error clearing maps: {str(e)}"
    
def reverse_addons_order(gameinfo_path):
    """
    Reverses the order of addons in gameinfo.txt
    Returns tuple (success, message)
    """
    try:
        # Read current addons
        current_addons = read_addons_from_gameinfo(gameinfo_path)
        if not current_addons:
            return False, tr("No addons to reverse")
        
        # Reverse the list
        reversed_addons = list(reversed(current_addons))
        
        # Update gameinfo.txt with reversed order
        addons_with_paths = [(addon['path'], addon['title']) for addon in reversed_addons]
        success, message = gameinfo.update_gameinfo_order(gameinfo_path, addons_with_paths)
        
        if success:
            log.info(tr("Addons order reversed"))
            return True, tr("Addons order reversed")
        else:
            return False, message
            
    except Exception as e:
        log.error(f"Error reversing addons order: {str(e)}")
        return False, f"Error reversing addons order: {str(e)}"


def cleanup_extracted_map(extracted_dir):
    """
    Removes specified folders and files from the extracted map addon folder.
    Also removes shader files that conflict with HL2:VR's own shaders.
    """
    log.info(tr("Cleaning problematic files..."))
    
    # ----- 1. Standard cleanup items -----
    items_to_remove = [
        'bin',
        os.path.join('cfg', 'config.cfg'),
        'gameinfo.txt',
        'gamestate.txt',
        os.path.join('cfg', 'videoconfig.cfg'),
        'survival_scenes.txt',
        'steam.inf',
        'glbaseshaders.cfg',
        'albedo.tga',
        'demoheader.tmp',
        'stats.txt',
        'textwindow_temp.html',
        os.path.join('cfg', 'banned_user.cfg'),
        os.path.join('cfg', 'banned_ip.cfg'),
        os.path.join('cfg', 'pet.txt'),
        os.path.join('scripts', 'kb_def.lst'),
        os.path.join('scripts', 'settings.scr'),
        os.path.join('maps', 'graphs')
    ]
    
    for item in items_to_remove:
        item_path = os.path.join(extracted_dir, item)
        
        if os.path.isdir(item_path):
            try:
                shutil.rmtree(item_path)
                log.info(tr("Removed directory: {}").format(item_path))
            except Exception as e:
                log.warning(tr("Failed to remove directory {}: {}").format(item_path, e))
        elif os.path.isfile(item_path):
            try:
                os.remove(item_path)
                log.info(tr("Removed file: {}").format(item_path))
            except Exception as e:
                log.warning(tr("Failed to remove file {}: {}").format(item_path, e))
    
    # ----- 2. Remove conflicting shader files -----
    # Check if the mod has a shaders folder
    mod_shaders_path = os.path.join(extracted_dir, 'shaders')
    if os.path.exists(mod_shaders_path) and os.path.isdir(mod_shaders_path):
        log.info(tr("Checking for conflicting shader files..."))
        
        # Load config to get hl2vr_path
        try:
            import config
            app_config = config.load_config()
            hl2vr_path = app_config.get("hl2vr_path", "")
        except Exception as e:
            log.warning(tr("Failed to load config for shader cleanup: {}").format(e))
            hl2vr_path = ""
        
        if hl2vr_path and os.path.exists(hl2vr_path):
            # VR shader directories to compare against
            vr_shader_dirs = [
                os.path.join(hl2vr_path, "hlvr", "shaders", "fxc"),
                os.path.join(hl2vr_path, "hlvr", "shaders", "psh"),
                os.path.join(hl2vr_path, "hlvr", "shaders", "vsh")
            ]
            
            # Collect all VR shader filenames
            vr_shader_filenames = set()
            for vr_dir in vr_shader_dirs:
                if os.path.exists(vr_dir) and os.path.isdir(vr_dir):
                    for root, dirs, files in os.walk(vr_dir):
                        for file in files:
                            vr_shader_filenames.add(file)
            
            if vr_shader_filenames:
                # Scan mod's shaders folder recursively and remove conflicting files
                removed_shader_count = 0
                for root, dirs, files in os.walk(mod_shaders_path):
                    for file in files:
                        if file in vr_shader_filenames:
                            file_path = os.path.join(root, file)
                            try:
                                os.remove(file_path)
                                removed_shader_count += 1
                            except Exception as e:
                                log.warning(tr("Failed to remove conflicting shader {}: {}").format(file_path, e))
                
                if removed_shader_count > 0:
                    log.info(tr("Removed {} conflicting shader files").format(removed_shader_count))
                
                # Remove empty subdirectories in shaders folder
                for root, dirs, files in os.walk(mod_shaders_path, topdown=False):
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        try:
                            if not os.listdir(dir_path):  # Check if empty
                                os.rmdir(dir_path)
                        except Exception as e:
                            log.warning(tr("Failed to remove empty directory {}: {}").format(dir_path, e))
                
                # If shaders folder is empty after cleanup, remove it entirely
                if os.path.exists(mod_shaders_path):
                    try:
                        if not os.listdir(mod_shaders_path):
                            os.rmdir(mod_shaders_path)
                            log.info(tr("Removed empty shaders folder: {}").format(mod_shaders_path))
                    except Exception as e:
                        log.warning(tr("Failed to remove empty shaders folder {}: {}").format(mod_shaders_path, e))
            else:
                log.info(tr("No VR shader files found to compare against"))
        else:
            log.warning(tr("HL2:VR path not configured or invalid, skipping shader cleanup"))


def scan_mods_folder(mods_path, hl2vr_path):
    """
    Scans the mods folder and returns a list of found mods
    Args:
        mods_path: path to the mods folder
        hl2vr_path: path to Half-Life 2 VR
    Returns:
        tuple (valid_mods, invalid_mods, error_message)
        valid_mods: list of tuples (path, title) for valid mods
        invalid_mods: list of tuples (path, title, reason) for invalid mods
    """
    try:
        # Check that the mods folder path does not match the custom folder
        custom_paths = [
            os.path.join(hl2vr_path, "hlvr", "custom"),
            os.path.join(hl2vr_path, "episodicvr", "custom"),
            os.path.join(hl2vr_path, "ep2vr", "custom")
        ]
        
        for custom_path in custom_paths:
            if os.path.normpath(mods_path) == os.path.normpath(custom_path):
                return [], [], tr("Mods folder path cannot be the same as custom folder") + ". " + tr("Create a separate folder for third-party mods")
        
        if not os.path.exists(mods_path):
            return [], [], tr("Mods folder not found")
        
        valid_mods = []
        invalid_mods = []
        
        # Get list of items in mods folder
        for item in os.listdir(mods_path):
            item_path = os.path.join(mods_path, item)
            
            # Check if element is a folder or VPK file
            if os.path.isdir(item_path):
                # This is a mod folder
                # Check if folder is named "materials" - such addons are considered invalid
                if item.lower() == "materials":
                    invalid_mods.append((item_path, item, tr("Mod folder structure is invalid")))
                else:
                    mod_valid = is_valid_mod_folder(item_path)
                    if mod_valid:
                        # Use folder name as mod title
                        mod_title = item
                        valid_mods.append((item_path, mod_title))
                    else:
                        invalid_mods.append((item_path, item, tr("Mod folder structure is invalid")))
            
            elif item.lower().endswith('.vpk'):
                # This is a VPK file
                # Check if this is a multipart archive
                base_name = item[:-4]  # Remove .vpk
                if base_name.endswith('_dir'):
                    # This is the main file of a multipart archive
                    mod_title = base_name
                    valid_mods.append((item_path, mod_title))
                elif re.match(r'.+_\d+$', base_name):
                    # This is a part of a multipart archive, skip
                    continue
                else:
                    # This is a single VPK file
                    mod_title = base_name
                    valid_mods.append((item_path, mod_title))
        
        log.info(tr("Found {} mods in folder").format(len(valid_mods)))
        return valid_mods, invalid_mods, ""
    
    except Exception as e:
        log.error(f"Error scanning mods folder: {str(e)}")
        return [], [], f"Error scanning mods folder: {str(e)}"


def is_valid_mod_folder(folder_path):
    """
    Checks if the folder is a valid mod folder
    Args:
        folder_path: path to the mod folder
    Returns:
        bool: True if the folder contains at least one of the required elements
    """
    required_elements = [
        'gameinfo.txt',
        'bin',
        'cfg',
        'materials',
        'models',
        'sound',
        'maps',
        'scripts',
        'particles',
        'resource',
        'scenes',
        'downloadlists',
        'media',
        'shaders'
    ]
    
    for element in required_elements:
        element_path = os.path.join(folder_path, element)
        if os.path.exists(element_path):
            return True
    
    return False


def prepare_mods_from_folder(mods_path, hl2vr_path, check_files=True):
    """
    Prepares mods from folder for mounting
    Args:
        mods_path: path to the mods folder
        hl2vr_path: path to Half-Life 2 VR
        check_files: whether to check file existence
    Returns:
        tuple (success, data, error_message)
    """
    try:
        log.info(tr("Scanning folder for mods..."))
        
        # Scan mods folder
        valid_mods, invalid_mods, error_message = scan_mods_folder(mods_path, hl2vr_path)
        
        if error_message:
            return False, None, error_message
        
        if not valid_mods and not invalid_mods:
            return False, None, tr("No mods found in folder")
        
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        
        # Filter duplicates only among valid mods
        valid_addons = [(get_mod_id(path), title) for path, title in valid_mods]
        unique_addons, duplicates = filter_duplicate_addons(gameinfo_path, valid_addons)
        
        # Separate valid mods into unique and duplicates
        unique_valid_mods = []
        duplicate_valid_mods = []
        
        for mod_path, mod_title in valid_mods:
            mod_id = get_mod_id(mod_path)
            if any(uid == mod_id for uid, _ in unique_addons):
                unique_valid_mods.append((mod_path, mod_title))
            elif any(uid == mod_id for uid, _ in duplicates):
                duplicate_valid_mods.append((mod_path, mod_title))
        
        # Check file existence if check is enabled
        missing_addons = []
        final_addons_with_paths = []
        
        if check_files:
            for mod_path, mod_title in unique_valid_mods:
                if os.path.exists(mod_path):
                    final_addons_with_paths.append((mod_path, mod_title))
                    
                    # For mod folders apply cleanup, as for maps
                    if os.path.isdir(mod_path):
                        cleanup_extracted_map(mod_path)
                else:
                    mod_id = get_mod_id(mod_path)
                    missing_addons.append((mod_id, mod_title, mod_path))
        else:
            # If file check is disabled, add all unique mods
            final_addons_with_paths = unique_valid_mods
            for mod_path, mod_title in unique_valid_mods:
                if os.path.isdir(mod_path):
                    cleanup_extracted_map(mod_path)
        
        # Prepare data for return
        result_data = {
            'unique_addons': [(get_mod_id(path), title) for path, title in final_addons_with_paths],
            'duplicates': duplicates,
            'missing_addons': missing_addons,
            'invalid_addons': invalid_mods,
            'addons_with_paths': final_addons_with_paths,
            'gameinfo_path': gameinfo_path
        }
        
        log.info(tr("Prepared {} external mods").format(len(final_addons_with_paths)))
        return True, result_data, ""
    
    except Exception as e:
        log.error(f"Error preparing external mods: {str(e)}")
        return False, None, f"An unexpected error occurred:\n{str(e)}"




def get_mod_id(mod_path):
    """
    Gets the mod identifier from the path
    Args:
        mod_path: path to the mod (folder or VPK file)
    Returns:
        str: mod identifier
    """
    if os.path.isdir(mod_path):
        # For folders use folder name as identifier
        return os.path.basename(mod_path)
    elif mod_path.lower().endswith('.vpk'):
        # For VPK files use filename without extension
        return os.path.splitext(os.path.basename(mod_path))[0]
    else:
        # For other cases return basename
        return os.path.basename(mod_path)