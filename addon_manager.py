import os
import re
import workshop
import vpk
import shutil
from logger import log
import concurrent.futures
from i18n import tr, translator

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
    
    return tr("Unknown")

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
                        # Check next line for path
                        if i + 1 < len(lines) and (addon['path'] in lines[i + 1] or addon['path'].replace('workshop_dir', 'workshop_dir.vpk') in lines[i + 1] or addon['path'].replace('workshop_dir.vpk', 'workshop_dir') in lines[i + 1]):
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


def create_vr_essential_backup(hl2vr_path):
    """
    Creates copies of important VR mod files in the custom/vr_essential_resources folder
    Returns a tuple (success, message)
    """
    try:
        # Path to AnniversaryContent (assumed to be in the same folder as the program)
        anniversary_content_path = os.path.join(os.path.dirname(__file__), "AnniversaryContent")
        
        # ===== FOR HLVR =====
        hlvr_backup_path = os.path.join(hl2vr_path, "hlvr", "custom", "vr_essential_resources")
        
        if not os.path.exists(hlvr_backup_path):
            log.info(tr("Copying essential VR files to custom (hlvr)"))
            os.makedirs(hlvr_backup_path, exist_ok=True)
            
            # Copy scripts (only specified files)
            hlvr_scripts_src = os.path.join(hl2vr_path, "hlvr", "scripts")
            hlvr_scripts_dst = os.path.join(hlvr_backup_path, "scripts")
            
            if os.path.exists(hlvr_scripts_src):
                os.makedirs(hlvr_scripts_dst, exist_ok=True)
                
                # List of files and folders to copy from scripts
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
                
                for item in scripts_to_copy:
                    src_path = os.path.join(hlvr_scripts_src, item)
                    dst_path = os.path.join(hlvr_scripts_dst, item)
                    
                    if os.path.exists(src_path):
                        if os.path.isdir(src_path):
                            shutil.copytree(src_path, dst_path)
                        else:
                            shutil.copy2(src_path, dst_path)
            
            # Copy resource (entire folder)
            hlvr_resource_src = os.path.join(hl2vr_path, "hlvr", "resource")
            hlvr_resource_dst = os.path.join(hlvr_backup_path, "resource")
            
            if os.path.exists(hlvr_resource_src):
                shutil.copytree(hlvr_resource_src, hlvr_resource_dst)
            
            # Copy shaders from AnniversaryContent
            anniversary_shaders_src = os.path.join(anniversary_content_path, "hlvr", "shaders")
            hlvr_shaders_dst = os.path.join(hlvr_backup_path, "shaders")
            
            if os.path.exists(anniversary_shaders_src):
                shutil.copytree(anniversary_shaders_src, hlvr_shaders_dst)
        
        # ===== FOR EPISODICVR =====
        episodicvr_backup_path = os.path.join(hl2vr_path, "episodicvr", "custom", "vr_essential_resources")
        
        if not os.path.exists(episodicvr_backup_path):
            episodicvr_path = os.path.join(hl2vr_path, "episodicvr")
            if os.path.exists(episodicvr_path):
                log.info(tr("Copying essential VR files to custom (episodicvr)"))
                os.makedirs(episodicvr_backup_path, exist_ok=True)
                
                # Copy resource (entire folder)
                episodic_resource_src = os.path.join(episodicvr_path, "resource")
                episodic_resource_dst = os.path.join(episodicvr_backup_path, "resource")
                
                if os.path.exists(episodic_resource_src):
                    shutil.copytree(episodic_resource_src, episodic_resource_dst)
        
        # ===== FOR EP2VR =====
        ep2vr_backup_path = os.path.join(hl2vr_path, "ep2vr", "custom", "vr_essential_resources")
        
        if not os.path.exists(ep2vr_backup_path):
            ep2vr_path = os.path.join(hl2vr_path, "ep2vr")
            if os.path.exists(ep2vr_path):
                log.info(tr("Copying essential VR files to custom (ep2vr)"))
                os.makedirs(ep2vr_backup_path, exist_ok=True)
                
                # Copy resource (entire folder)
                ep2_resource_src = os.path.join(ep2vr_path, "resource")
                ep2_resource_dst = os.path.join(ep2vr_backup_path, "resource")
                
                if os.path.exists(ep2_resource_src):
                    shutil.copytree(ep2_resource_src, ep2_resource_dst)
                
                # Copy only specified files from scripts
                ep2_scripts_src = os.path.join(ep2vr_path, "scripts")
                ep2_scripts_dst = os.path.join(ep2vr_backup_path, "scripts")
                
                if os.path.exists(ep2_scripts_src):
                    os.makedirs(ep2_scripts_dst, exist_ok=True)
                    
                    # Only two files
                    ep2_scripts_to_copy = [
                        "hudlayout.res",
                        "vgui_screens.txt"
                    ]
                    
                    for file in ep2_scripts_to_copy:
                        src_path = os.path.join(ep2_scripts_src, file)
                        dst_path = os.path.join(ep2_scripts_dst, file)
                        
                        if os.path.exists(src_path):
                            shutil.copy2(src_path, dst_path)
        
        log.info(tr("Essential VR files prioritized via custom folder"))
        return True, tr("Essential VR files prioritized via custom folder")
        
    except Exception as e:
        log.error(f"Error copying VR resources: {str(e)}")
        return False, f"Error copying VR resources: {str(e)}"

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

def prepare_addons_from_workshop_txt(hl2vr_path, hl2_path, check_files=True):
    """
    Prepares addons from workshop.txt for mounting
    """
    try:
        log.info(tr("Starting preparation of addons from workshop.txt"))
        
        # Read addon IDs from workshop.txt
        addon_ids, error_message = read_workshop_txt(hl2_path)
        if error_message:
            return False, None, error_message
        
        if not addon_ids:
            return False, None, tr("Installed addons not found.")
        
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        
        # MULTITHREADED PROCESSING - get addon titles in parallel
        unique_addons = []
        failed_addons = []
        
        def fetch_addon_info(addon_id):
            """Function to get information about one addon"""
            try:
                addon_id_str, title = workshop.get_addon_by_id(addon_id)
                if addon_id_str and title:
                    return ('success', addon_id_str, title)
                else:
                    return ('failed', addon_id, None)
            except Exception as e:
                return ('error', addon_id, str(e))
        
        # Use ThreadPoolExecutor for parallel requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Start all tasks
            future_to_id = {executor.submit(fetch_addon_info, addon_id): addon_id for addon_id in addon_ids}
            
            # Process results as they complete
            for i, future in enumerate(concurrent.futures.as_completed(future_to_id), 1):
                addon_id = future_to_id[future]
                try:
                    result_type, result_id, result_data = future.result()
                    if result_type == 'success':
                        log.info(tr("Loaded ({}/{}): {}").format(i, len(addon_ids), result_data))
                        unique_addons.append((result_id, result_data))
                    elif result_type == 'failed':
                        log.warning(tr("✗ Failed to load ({}/{}): ID {}").format(i, len(addon_ids), result_id))
                        failed_addons.append(result_id)
                    else:
                        log.error(tr("✗ Error loading ({}/{}): ID {} - {}").format(i, len(addon_ids), result_id, result_data))
                        failed_addons.append(result_id)
                except Exception as e:
                    log.error(tr("✗ Unexpected error ({}/{}): ID {} - {}").format(i, len(addon_ids), addon_id, str(e)))
                    failed_addons.append(addon_id)
        
        if not unique_addons:
            return False, None, tr("Failed to get information about installed addons.")
        
        log.info(tr("Successfully processed {} out of {} addons").format(len(unique_addons), len(addon_ids)))

        # Check duplicates
        existing_ids = {addon['id'] for addon in read_addons_from_gameinfo(gameinfo_path)}
        filtered_addons = []
        duplicates = []
        
        for addon_id, title in unique_addons:
            if addon_id in existing_ids:
                duplicates.append((addon_id, title))
            else:
                filtered_addons.append((addon_id, title))
        
        if not filtered_addons:
            if duplicates:
                return False, None, tr("All addons already added.")
            else:
                return False, None, tr("Failed to find addons to add.")
        
        # Get workshop path
        from path_utils import get_workshop_path
        workshop_path = get_workshop_path(hl2_path)
        
        # Form paths to VPK files
        addons_with_paths = []
        for addon_id, title in filtered_addons:
            vpk_path = os.path.join(workshop_path, addon_id, "workshop_dir.vpk")
            addons_with_paths.append((vpk_path, title))
        
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
            
            for vpk_path, title, addon_id in vpk_addons:
                if os.path.exists(vpk_path):
                    existing_vpk_addons.append((vpk_path, title))
                    final_unique_addons.append((addon_id, title))
                else:
                    missing_vpk_addons.append((addon_id, title, vpk_path))
            
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
    Checks addons for maps and extracts them
    progress_callback: function to update progress (current_map, total_maps, current_file, total_files, status) returns False if need to cancel
    """
    try:
        map_addons = []
        extracted_addons = []
        failed_addons = []
        updated_addons = []
        for addon in current_addons:
            updated_addons.append(addon.copy())

        addons_to_process = current_addons
        if specific_addons is not None:
            addons_to_process = specific_addons

        log.info(tr("Checking maps: {} addons to process").format(len(addons_to_process)))

        # Find all maps among addons to process
        for addon in addons_to_process:
            addon_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={addon['id']}"
            if workshop.is_addon_map(addon_url):
                map_addons.append(addon)

        total_maps = len(map_addons)
        current_map = 0

        log.info(tr("Maps found: {}").format(total_maps))

        for i, addon in enumerate(addons_to_process):
            # Check cancellation before processing each addon
            if progress_callback:
                should_continue = progress_callback(current_map, total_maps, 0, 0, tr("Checking addon: {}").format(addon['title']))
                if not should_continue:
                    return True, map_addons, {
                        'extracted': extracted_addons,
                        'failed': failed_addons,
                        'total_maps': len(map_addons),
                        'updated_addons': updated_addons,
                        'cancelled': True
                    }
            
            addon_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={addon['id']}"
            is_map = workshop.is_addon_map(addon_url)
            
            if is_map:
                current_map += 1
                
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
                            return True, map_addons, {
                                'extracted': extracted_addons,
                                'failed': failed_addons,
                                'total_maps': len(map_addons),
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
        return True, map_addons, {
            'extracted': extracted_addons,
            'failed': failed_addons,
            'total_maps': len(map_addons),
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