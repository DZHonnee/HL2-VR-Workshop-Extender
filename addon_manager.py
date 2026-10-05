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

MAP_MARKER = "//@map"
LEGACY_MAP_PREFIX = "MAP   |   "


def unpacked_folder_for(addon_path):
    """
    Returns the unpacked folder path for a workshop addon path.
    '.../workshop_dir.vpk' -> '.../workshop_dir'
    Returns None when the path is not a workshop_dir path.
    """
    if not addon_path:
        return None
    if addon_path.endswith('workshop_dir.vpk'):
        return addon_path[:-len('.vpk')]
    if addon_path.endswith('workshop_dir'):
        return addon_path
    return None


def vpk_path_for(addon_path):
    """
    Returns the .vpk path for a workshop addon path.
    '.../workshop_dir' -> '.../workshop_dir.vpk'
    Returns the path unchanged when it is not a workshop_dir path.
    """
    folder = unpacked_folder_for(addon_path)
    if folder:
        return folder + '.vpk'
    return addon_path


def compute_is_unpacked(addon_path):
    """
    True when the addon is unpacked on disk.
    A .vpk path with a non-empty workshop_dir folder next to it counts as
    unpacked, because the user may have unpacked the map with an external
    tool while gameinfo.txt still points at the .vpk.
    """
    folder = unpacked_folder_for(addon_path)
    if not folder:
        return False
    if not os.path.isdir(folder):
        return False
    try:
        with os.scandir(folder) as entries:
            return any(True for _ in entries)
    except OSError:
        return False


def resolve_embed_path(workshop_path, addon_id, is_map=False):
    """
    Builds the path that goes into gameinfo.txt for a workshop addon.
    A map is always mounted as a folder: a packed map does not work in the
    game, so a .vpk path would only be a broken entry. Being unpacked is a
    fact about disk, reported by compute_is_unpacked, and not a reason to
    store a different path.
    """
    vpk_path = os.path.join(workshop_path, addon_id, 'workshop_dir.vpk')
    if is_map or compute_is_unpacked(vpk_path):
        return unpacked_folder_for(vpk_path)
    return vpk_path


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

        # Parse the block line by line: a title comment, an optional
        # //@map marker, then the game+mod line carrying the path.
        # Line-based parsing keeps a map addon from silently disappearing
        # when the optional marker line is present.
        block_lines = addon_content.split('\n')
        idx = 0
        while idx < len(block_lines):
            stripped = block_lines[idx].strip()

            if not stripped.startswith('//'):
                idx += 1
                continue

            title = stripped[2:].strip()
            is_map = False

            # Optional //@map marker line
            if idx + 1 < len(block_lines) and block_lines[idx + 1].strip() == MAP_MARKER:
                is_map = True
                idx += 1

            if idx + 1 >= len(block_lines):
                break

            path_match = re.match(r'game\+mod\s+"(.*)"\s*$', block_lines[idx + 1].strip())
            if not path_match:
                idx += 1
                continue

            path = path_match.group(1)

            # Backward compatibility: legacy files carry the MAP prefix
            # inside the title instead of the //@map marker line.
            if title.startswith(LEGACY_MAP_PREFIX):
                title = title[len(LEGACY_MAP_PREFIX):].lstrip()
                is_map = True

            # A map is mounted as a folder, so the stored path is normalized
            # on read. Legacy entries carry either the //@map marker or the
            # MAP prefix and are covered as well; the next write of the block
            # stores the folder path.
            if is_map:
                path = unpacked_folder_for(path) or path

            if title:
                addons.append({
                    'number': len(addons) + 1,
                    'title': title,
                    'id': extract_addon_id(path),
                    'path': path,
                    'is_map': is_map,
                    'is_unpacked': compute_is_unpacked(path),
                })

            idx += 2

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
                    if clean_line.startswith('//') and (addon['title'] in clean_line or addon['title'].replace(LEGACY_MAP_PREFIX, "") in clean_line):
                        # Skip the optional //@map marker line to find the path line
                        path_line_index = i + 1
                        while path_line_index < len(lines) and lines[path_line_index].strip() == MAP_MARKER:
                            path_line_index += 1

                        # Check next line for path - enhanced to handle all types of paths properly
                        if path_line_index < len(lines):
                            next_line = lines[path_line_index]

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
                                # Remove the optional //@map marker along with it
                                for marker_index in range(i + 1, path_line_index):
                                    lines_to_remove.add(marker_index)
                                lines_to_remove.add(path_line_index)  # Path
                                # Check if there's empty line after
                                if path_line_index + 1 < len(lines) and lines[path_line_index + 1].strip() == '':
                                    lines_to_remove.add(path_line_index + 1)

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

    # Tuples may carry extra trailing fields (e.g. is_map), so index by
    # position and keep the original tuple intact.
    for addon in addons:
        addon_id = addon[0]
        if addon_id in existing_ids:
            duplicates.append(addon)
        else:
            unique_addons.append(addon)
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
    Returns list of tuples (id, flag) in file order, enabled and disabled
    alike. Disabled entries ("0") are kept so that scanning the workshop
    folder later cannot bring an addon the user switched off back in.
    """
    try:
        workshop_txt_path = os.path.join(hl2_path, "hl2_complete", "cfg", "workshop.txt")

        if not os.path.exists(workshop_txt_path):
            return None, tr("workshop.txt not found.")

        with open(workshop_txt_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Find addon IDs in format "ID" "1"; "0" means switched off
        pattern = r'"(\d+)"\s+"(\d)"'
        matches = re.findall(pattern, content)

        if not matches:
            return None, tr("Installed addons not found.")

        enabled_count = sum(1 for _id, flag in matches if flag == "1")
        log.info(tr("Read {} addons from workshop.txt").format(enabled_count))
        return matches, None

    except Exception as e:
        log.error(f"Error reading workshop.txt: {str(e)}")
        return None, f"Error reading workshop.txt: {str(e)}"


def scan_workshop_folder_ids(hl2_path):
    """
    Collects addon IDs from folder names in the Steam workshop folder.
    Campaign addons are not listed in workshop.txt at all, so their folders
    are the only place they show up. Only numeric folder names that actually
    carry addon content are returned, numerically sorted.
    Returns an empty list if the folder is missing or unreadable.
    """
    try:
        from path_utils import get_workshop_path
        workshop_path = get_workshop_path(hl2_path)

        if not workshop_path or not os.path.isdir(workshop_path):
            return []

        found = []
        for name in os.listdir(workshop_path):
            if not name.isdigit():
                continue

            folder = os.path.join(workshop_path, name)
            if not os.path.isdir(folder):
                continue

            # An addon carries content as a .vpk or as an unpacked folder
            has_vpk = os.path.exists(os.path.join(folder, 'workshop_dir.vpk'))
            has_unpacked = os.path.isdir(os.path.join(folder, 'workshop_dir'))
            if has_vpk or has_unpacked:
                found.append(name)

        found.sort(key=int)
        return found

    except Exception as e:
        log.warning(tr("Could not read workshop folder: {}").format(str(e)))
        return []


def collect_installed_addon_ids(hl2_path):
    """
    Builds the full ID list for the workshop.txt scenario.

    Reads every ID from workshop.txt - enabled and disabled alike - then adds
    the folders found on disk that the file never mentions. Those extra IDs
    are the campaign addons.

    Disabled addons are never returned: their ID is in `known`, so the folder
    scan cannot bring them back.

    Returns (extra, enabled, error_message).
    """
    entries, error_message = read_workshop_txt(hl2_path)
    if error_message:
        return None, None, error_message

    known = set(addon_id for addon_id, _flag in entries)
    enabled = [addon_id for addon_id, flag in entries if flag == "1"]

    extra = [addon_id for addon_id in scan_workshop_folder_ids(hl2_path)
             if addon_id not in known]

    if extra:
        log.info(tr("Found {} addons on disk that are not in workshop.txt").format(len(extra)))

    return extra, enabled, None


def prepare_addons_for_embedding(collection_url, hl2vr_path, hl2_path, check_files=True,
                                 check_cancel=None, progress_callback=None, status_callback=None):
    """
    Prepares addons for mounting.
    check_files: whether to check addon files existence
    Returns tuple (success, data, error_message)
    """
    try:
        log.info(tr("Preparing addons from collection"))

        if progress_callback:
            progress_callback(0, 0)

        if status_callback:
            status_callback(tr("Requesting addon info from Steam..."))

        scale = {'total': 0}

        def network_progress(done, total):
            if progress_callback:
                progress_callback(done, scale['total'])

        failures = {}

        # Get addons from collection: [(id, title, is_map), ...]
        addons = workshop.get_collection_addons(
            collection_url,
            check_cancel=check_cancel,
            progress_callback=network_progress,
            status_callback=status_callback,
            failures=failures
        )

        if addons is None:
            return False, {'cancelled': True}, tr("Operation cancelled by user")

        failed_addons = [
            (fid, workshop.html_failure_reason(code))
            for fid, code in sorted(failures.items())
        ]

        if not addons:
            if failed_addons:
                return False, {
                    'failed_addons': failed_addons,
                    'unique_addons': []
                }, tr("Failed to load any addon from the collection.")
            return False, None, tr("Failed to find addons in collection.")

        network_total = len(addons)
        total_steps = network_total * 2
        scale['total'] = total_steps

        if progress_callback:
            progress_callback(network_total, total_steps)

        if status_callback:
            status_callback(tr("Processing addon information..."))

        if check_cancel and check_cancel():
            return False, {'cancelled': True}, tr("Operation cancelled by user")

        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")

        # Keep the is_map flag alongside the id and title; it is stored in
        # gameinfo.txt as a //@map marker rather than in the title.
        unique_3t, duplicates = filter_duplicate_addons(gameinfo_path, addons)

        if not unique_3t:
            if duplicates:
                return False, None, tr("All addons from collection already added.")
            else:
                return False, None, tr("Failed to find addons.")

        # Get workshop path
        from path_utils import get_workshop_path
        workshop_path = get_workshop_path(hl2_path)

        # Form paths to VPK files
        addons_with_paths = []
        for addon_id, title, is_map in unique_3t:
            addon_path = resolve_embed_path(workshop_path, addon_id, is_map)
            addons_with_paths.append({'path': addon_path, 'title': title, 'is_map': is_map})

        # Check files existence if option enabled
        missing_addons = []
        final_addons_with_paths = []
        final_unique_addons = []

        if check_files:
            # One pass in the original order. Splitting the list into .vpk and
            # folder groups used to push every unpacked addon to the bottom,
            # so an unpacked campaign lost its place from workshop.txt.
            existing_addons = []
            missing_vpk_addons = []
            total_files_check = len(addons_with_paths)

            for i, entry in enumerate(addons_with_paths):
                if check_cancel and check_cancel():
                    return False, {'cancelled': True}, tr("Operation cancelled by user")

                addon_path = entry['path']
                title = entry['title']
                is_map = entry['is_map']
                addon_id = extract_addon_id(addon_path)

                # Existence is judged by the .vpk the addon was downloaded
                # as, not by the path written to gameinfo.txt: a map is
                # referenced as a folder before it gets unpacked, while a
                # deleted .vpk means the addon is no longer installed.
                source_vpk = vpk_path_for(addon_path)
                if not os.path.exists(source_vpk):
                    missing_vpk_addons.append((addon_id, title, source_vpk, is_map))
                else:
                    existing_addons.append(dict(entry))
                    final_unique_addons.append((addon_id, title, is_map))

                if progress_callback and total_files_check > 0:
                    done = (i + 1) * network_total // total_files_check
                    progress_callback(network_total + done, total_steps)

                if status_callback:
                    status_callback(tr("Checking files: {}/{}").format(i + 1, total_files_check))

            if check_cancel and check_cancel():
                return False, {'cancelled': True}, tr("Operation cancelled by user")

            final_addons_with_paths = existing_addons
            missing_addons = missing_vpk_addons

            if not final_addons_with_paths and missing_addons:
                return False, {'all_missing': True}, tr("Addon files missing.")
        else:
            final_addons_with_paths = addons_with_paths
            final_unique_addons = unique_3t

        if progress_callback:
            progress_callback(total_steps, total_steps)

        result_data = {
            'cancelled': False,
            'unique_addons': final_unique_addons,
            'duplicates': duplicates,
            'missing_addons': missing_addons,
            'failed_addons': failed_addons,
            'addons_with_paths': final_addons_with_paths,
            'gameinfo_path': gameinfo_path
        }

        log.info(tr("Prepared {} addons for mounting").format(len(final_unique_addons)))
        return True, result_data, ""

    except workshop.SteamRateLimitException:
        log.error(tr("Error preparing addons: Steam rate limit exceeded"))
        return False, None, workshop.rate_limit_message()

    except Exception as e:
        log.error(f"Error preparing addons: {str(e)}")
        return False, None, f"An unexpected error occurred:\n{str(e)}"


def prepare_single_addon_for_embedding(addon_url, hl2vr_path, hl2_path, check_files=True):
    """
    Prepares single addon for mounting.
    Returns tuple (success, data, error_message)
    """
    try:
        log.info(tr("Preparing single addon"))

        # Get addon information: (id, title, is_map)
        addon_id, title, is_map = workshop.get_single_addon(addon_url)
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

        final_path = resolve_embed_path(workshop_path, addon_id, is_map)
        final_title = title

        missing_addons = []
        final_unique_addons = []
        final_addons_with_paths = []

        if check_files and not os.path.exists(vpk_path_for(final_path)):
            missing_addons = [(addon_id, title, final_path, is_map)]
            return False, None, tr("Addon file '{}' not found.").format(title)
        else:
            final_unique_addons = [(addon_id, final_title, is_map)]
            final_addons_with_paths = [{'path': final_path, 'title': final_title, 'is_map': is_map}]

        result_data = {
            'unique_addons': final_unique_addons,
            'duplicates': [],
            'missing_addons': missing_addons,
            'addons_with_paths': final_addons_with_paths,
            'gameinfo_path': gameinfo_path
        }

        log.info(tr("Addon '{}' prepared for mounting").format(title))
        return True, result_data, ""

    except workshop.SteamRateLimitException:
        log.error(tr("Error preparing single addon: Steam rate limit exceeded"))
        return False, None, workshop.rate_limit_message()

    except Exception as e:
        log.error(f"Error preparing single addon: {str(e)}")
        return False, None, f"An unexpected error occurred:\n{str(e)}"


def prepare_addons_from_workshop_txt(hl2vr_path, hl2_path, check_files=True, check_cancel=None,
                                     progress_callback=None, status_callback=None):
    """
    Prepares addons from workshop.txt for mounting.
    Uses batch Steam Web API - one request per 50 addons.
    check_cancel: function that returns True if operation should be cancelled
    progress_callback: function(current, total) to report progress.
                     Called with total <= 0 to mark an indeterminate (network) phase.
    status_callback: optional function(message) to report a status text
    """
    try:
        log.info(tr("Starting preparation of addons from workshop.txt"))

        # Read addon IDs from workshop.txt and merge in the folders on disk,
        # which is where campaign addons live.
        extra_ids, enabled_ids, error_message = collect_installed_addon_ids(hl2_path)
        if error_message:
            return False, None, error_message

        addon_ids = extra_ids + enabled_ids

        if not addon_ids:
            return False, None, tr("Installed addons not found.")

        # Check cancellation before starting
        if check_cancel and check_cancel():
            return False, {'cancelled': True}, tr("Operation cancelled by user")

        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")

        # ----- Batch fetch addon info via Steam Web API -----
        log.info(tr("Fetching info for {} addons via Steam Web API...").format(len(addon_ids)))

        # Unified progress scale: the first half is the network phase,
        # the second half is local file processing.
        network_total = len(addon_ids)
        total_steps = network_total * 2

        def network_progress(done, batch_total):
            if progress_callback:
                progress_callback(min(done, network_total), total_steps)

        if progress_callback:
            # total <= 0 marks the indeterminate network phase
            progress_callback(0, 0)

        # One (or a few) HTTP request(s) for the entire list
        failures = {}
        batch_result = workshop.get_multiple_addons_info(
            addon_ids,
            progress_callback=network_progress,
            status_callback=status_callback,
            failures=failures,
            check_cancel=check_cancel
        )

        if progress_callback:
            progress_callback(network_total, total_steps)

        if status_callback:
            status_callback(tr("Processing addon information..."))

        # Check cancellation after network request
        if check_cancel and check_cancel():
            return False, {'cancelled': True}, tr("Operation cancelled by user")

        unique_addons = []
        failed_addons = []

        for addon_id in addon_ids:
            info = batch_result.get(str(addon_id))
            if info is None:
                log.warning(tr("✗ Failed to load addon ID {}").format(addon_id))
                code = failures.get(str(addon_id))
                reason = workshop.html_failure_reason(code) if code else tr("Not available in Steam")
                failed_addons.append((str(addon_id), reason))
                continue

            title = info.get('title', tr("Unknown title"))
            is_map = bool(info.get('is_map'))
            unique_addons.append((str(addon_id), title, is_map))

        if not unique_addons:
            return False, None, tr("Failed to get information about installed addons.")

        log.info(tr("Successfully processed {} out of {} addons").format(
            len(unique_addons), len(addon_ids)))

        # Check cancellation before processing duplicates
        if check_cancel and check_cancel():
            return False, {'cancelled': True}, tr("Operation cancelled by user")

        # ----- Filter duplicates -----
        existing_ids = {addon['id'] for addon in read_addons_from_gameinfo(gameinfo_path)}
        filtered_addons = []
        duplicates = []

        for addon_id, title, is_map in unique_addons:
            if addon_id in existing_ids:
                duplicates.append((addon_id, title, is_map))
            else:
                filtered_addons.append((addon_id, title, is_map))

        if check_cancel and check_cancel():
            return False, {'cancelled': True}, tr("Operation cancelled by user")

        if not filtered_addons:
            if duplicates:
                return False, None, tr("All addons already added.")
            else:
                return False, None, tr("Failed to find addons to add.")

        # ----- Form VPK paths -----
        from path_utils import get_workshop_path
        workshop_path = get_workshop_path(hl2_path)

        addons_with_paths = []
        for addon_id, title, is_map in filtered_addons:
            addon_path = resolve_embed_path(workshop_path, addon_id, is_map)
            addons_with_paths.append({'path': addon_path, 'title': title, 'is_map': is_map})

        # ----- Check files existence if option enabled -----
        missing_addons = []
        final_addons_with_paths = []
        final_unique_addons = []

        if check_files:
            log.info(tr("Checking addon files existence"))

            # One pass in the original order - see the collection scenario.
            existing_addons = []
            missing_vpk_addons = []
            total_files_check = len(addons_with_paths)

            if progress_callback:
                progress_callback(network_total, total_steps)
                if status_callback:
                    status_callback(tr("Checking files: {}/{}").format(0, total_files_check))

            for i, entry in enumerate(addons_with_paths):
                if check_cancel and check_cancel():
                    return False, {'cancelled': True}, tr("Operation cancelled by user")

                addon_path = entry['path']
                title = entry['title']
                is_map = entry['is_map']
                addon_id = extract_addon_id(addon_path)

                # Existence is judged by the .vpk the addon was downloaded
                # as, not by the path written to gameinfo.txt: a map is
                # referenced as a folder before it gets unpacked, while a
                # deleted .vpk means the addon is no longer installed.
                source_vpk = vpk_path_for(addon_path)
                if not os.path.exists(source_vpk):
                    missing_vpk_addons.append((addon_id, title, source_vpk, is_map))
                else:
                    existing_addons.append(dict(entry))
                    final_unique_addons.append((addon_id, title, is_map))

                if progress_callback and total_files_check > 0:
                    done = (i + 1) * network_total // total_files_check
                    progress_callback(network_total + done, total_steps)
                if status_callback:
                    status_callback(tr("Checking files: {}/{}").format(i + 1, total_files_check))

            if check_cancel and check_cancel():
                return False, {'cancelled': True}, tr("Operation cancelled by user")

            final_addons_with_paths = existing_addons
            missing_addons = missing_vpk_addons

            if not final_addons_with_paths:
                if missing_addons:
                    return False, None, tr("Addon files missing.")
                else:
                    return False, None, tr("Failed to find addons to add.")
        else:
            final_addons_with_paths = addons_with_paths
            final_unique_addons = filtered_addons
            if not final_addons_with_paths:
                return False, None, tr("Failed to find addons to add.")

        # Make sure the bar always ends at 100%
        if progress_callback:
            progress_callback(total_steps, total_steps)

        result_data = {
            'cancelled': False,
            'unique_addons': final_unique_addons,
            'duplicates': duplicates,
            'failed_addons': failed_addons,
            'missing_addons': missing_addons,
            'addons_with_paths': final_addons_with_paths,
            'gameinfo_path': gameinfo_path
        }

        log.info(tr("Prepared {} addons from workshop.txt").format(len(final_unique_addons)))
        return True, result_data, ""

    except workshop.SteamRateLimitException:
        log.error(tr("Error preparing addons from workshop.txt: Steam rate limit exceeded"))
        return False, None, workshop.rate_limit_message()

    except Exception as e:
        log.error(f"Error preparing addons from workshop.txt: {str(e)}")
        return False, None, f"An unexpected error occurred:\n{str(e)}"


def extract_map_vpk(vpk_path, output_dir, progress_callback=None, check_cancel=None):
    """
    Extracts map VPK file to specified directory
    progress_callback: function to update progress (current, total, filename) returns False if need to cancel
    Returns tuple (success, message, cancelled)
    """
    try:
        # Check VPK file existence
        if not os.path.exists(vpk_path):
            return False, tr("VPK file not found: {}").format(vpk_path), False

        # Check if addon already extracted
        if os.path.exists(output_dir):
            # Check if folder is not empty
            try:
                folder_contents = os.listdir(output_dir)
                if len(folder_contents) > 0:
                    return True, tr("Folder already exists and not empty"), False
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
            return False, tr("VPK file is empty"), False

        log.info(tr("Starting map unpacking: ({} files)").format(total_files))

        # Extract all files
        extracted_count = 0
        for i, filepath in enumerate(all_files):
            # Check cancellation via callback
            if check_cancel and check_cancel():
                # Delete partially extracted folder
                if os.path.exists(output_dir):
                    shutil.rmtree(output_dir)
                return False, tr("Unpacking cancelled"), True

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
                        return False, tr("Unpacking cancelled"), True

            except Exception as e:
                # In case of error, try to delete empty folder
                try:
                    if os.path.exists(output_dir) and not os.listdir(output_dir):
                        shutil.rmtree(output_dir)
                except:
                    pass
                return False, tr("Error unpacking {}: {}").format(filepath, e), False

        log.info(tr("Map unpacked: {}/{} files").format(extracted_count, total_files))

        # After successful extraction, remove specified folders and files
        cleanup_extracted_map(output_dir)

        return True, tr("Successfully unpacked {} files").format(extracted_count), False

    except Exception as e:
        # In case of error, try to delete empty folder
        try:
            if os.path.exists(output_dir) and not os.listdir(output_dir):
                shutil.rmtree(output_dir)
        except:
            pass
        log.error(tr("Error unpacking map: {}").format(e))
        return False, tr("Error unpacking map: {}. For possible solution see Help (Maps tab).").format(e), False


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
            log.warning(tr("No specific addons provided for map unpacking"))
            return True, [], {
                'extracted': [],
                'failed': [],
                'total_maps': 0,
                'updated_addons': updated_addons,
                'cancelled': False,
                'interrupted_folder_removed': False
            }

        total_maps = len(addons_to_process)
        current_map = 0

        log.info(tr("Unpacking maps: {} maps to process").format(total_maps))

        for i, addon in enumerate(addons_to_process):
            # Check cancellation before processing each addon
            if progress_callback:
                should_continue = progress_callback(current_map, total_maps, 0, 0, tr("Processing addon: {}").format(addon['title']))
                if not should_continue:
                    # Cancelled between maps: nothing was written, so there
                    # is no partial folder to clean up.
                    return True, addons_to_process, {
                        'extracted': extracted_addons,
                        'failed': failed_addons,
                        'total_maps': total_maps,
                        'updated_addons': updated_addons,
                        'cancelled': True,
                        'interrupted_folder_removed': False
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

            vpk_path = vpk_path_for(current_path)
            output_dir = unpacked_folder_for(current_path)
            if output_dir is None:
                # Not a workshop addon path: there is neither a .vpk nor a
                # folder to look for, exactly as before.
                vpk_path = None

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

                success, message, cancelled = extract_map_vpk(vpk_path, output_dir, file_progress)
                if success:
                    updated_addon['is_map'] = True
                    updated_addon['is_unpacked'] = True
                    extracted_addons.append(updated_addon)
                    continue

                if cancelled:
                    # Extraction was cancelled. extract_map_vpk has
                    # already deleted the partially written folder.
                    return True, addons_to_process, {
                        'extracted': extracted_addons,
                        'failed': failed_addons,
                        'total_maps': total_maps,
                        'updated_addons': updated_addons,
                        'cancelled': True,
                        'interrupted_folder_removed': True
                    }

                failed_addons.append((updated_addon, message))
                continue

            # If folder already exists AND NOT EMPTY
            if folder_exists:
                updated_addon['is_map'] = True
                updated_addon['is_unpacked'] = True
                continue

            # If VPK doesn't exist, but non-empty folder exists - all good
            if not vpk_exists and folder_exists:
                updated_addon['is_map'] = True
                updated_addon['is_unpacked'] = True
                continue

            # Neither VPK nor non-empty folder exist
            error_msg = tr("VPK file and non-empty unpacking folder not found")
            if vpk_path:
                error_msg += tr(" (VPK: {})").format(vpk_path)
            failed_addons.append((updated_addon, error_msg))

        log.info(tr("Map check completed: {} unpacked, {} errors").format(len(extracted_addons), len(failed_addons)))
        return True, addons_to_process, {
            'extracted': extracted_addons,
            'failed': failed_addons,
            'total_maps': total_maps,
            'updated_addons': updated_addons,
            'cancelled': False,
            'interrupted_folder_removed': False
        }

    except Exception as e:
        log.error(f"Error checking maps: {str(e)}")
        return False, [], f"Error checking maps: {str(e)}"


def clear_extracted_maps(workshop_path, gameinfo_path):
    """
    Deletes all extracted workshop_dir folders in the workshop folder.
    gameinfo.txt is left untouched: a map is mounted as a folder whether it
    is unpacked or not, so the stored paths stay valid. gameinfo_path is kept
    in the signature for the caller but is not used.
    Returns tuple (success, message)
    """
    try:
        log.info(tr("Clearing unpacked maps..."))

        deleted_folders = 0

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

        # 2. gameinfo.txt is not rewritten: a map entry already points at
        # the unpacked folder, and that path stays correct either way.

        log.info(tr("Clearing completed: {} folders deleted").format(deleted_folders))
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
        # Pass the addon dicts straight through: they already carry
        # path, title and is_map.
        success, message = gameinfo.update_gameinfo_order(gameinfo_path, reversed_addons)

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
                    # External mods are never maps
                    final_addons_with_paths.append({'path': mod_path, 'title': mod_title, 'is_map': False})

                    # For mod folders apply cleanup, as for maps
                    if os.path.isdir(mod_path):
                        cleanup_extracted_map(mod_path)
                else:
                    mod_id = get_mod_id(mod_path)
                    missing_addons.append((mod_id, mod_title, mod_path, False))
        else:
            # If file check is disabled, add all unique mods
            final_addons_with_paths = [{'path': path, 'title': title, 'is_map': False}
                                       for path, title in unique_valid_mods]
            for mod_path, mod_title in unique_valid_mods:
                if os.path.isdir(mod_path):
                    cleanup_extracted_map(mod_path)

        # Prepare data for return
        result_data = {
            'unique_addons': [(get_mod_id(entry['path']), entry['title'], entry['is_map'])
                              for entry in final_addons_with_paths],
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