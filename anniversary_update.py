import os
import shutil
from path_utils import validate_paths
from logger import log
from i18n import tr, translator

class AnniversaryUpdateManager:
    def __init__(self, hl2vr_path, hl2_path):
        self.hl2vr_path = hl2vr_path
        self.hl2_path = hl2_path
        self.anniversary_content_path = os.path.join(os.path.dirname(__file__), "AnniversaryContent")
    
    def validate_paths(self):
        return validate_paths(self.hl2vr_path, self.hl2_path)
    
    def check_game_directories(self):
        directories = {
            'hlvr': os.path.join(self.hl2vr_path, 'hlvr'),
            'episodicvr': os.path.join(self.hl2vr_path, 'episodicvr'),
            'ep2vr': os.path.join(self.hl2vr_path, 'ep2vr')
        }
        
        exists = {game: os.path.exists(path) for game, path in directories.items()}
        return exists
    
    def get_gameinfo_content(self, game_type):
        templates = {
            'hlvr': '''"GameInfo"
{{
    GameLogo        1
    Game            "Half-Life 2: VR Mod"
    Title           ""
    Title2          ""
    Developer       "Source VR Team"    
    Developer_URL   "https://halflife2vr.com/"
    Type            singleplayer_only
    Icon            "resource/game"
    NoModels        0
    SupportsVR      0
    SupportsDX8     0
    GameData        "halflife2vr.fgd"
    InstancePath    "instances"

    FileSystem
    {{
        SteamAppId              658920
                
        SearchPaths
        {{  
            // First, mount all user customizations.  This will search for VPKs and subfolders
            // and mount them in alphabetical order.  The easiest way to distribute a mod is to
            // pack up the custom content into a VPK.  To "install" a mod, just drop it in this
            // folder.
            //
            // Note that this folder is scanned only when the game is booted.
            game+mod            hlvr/custom/*
            
            // mount VR files first
            game+mod    |gameinfo_path|.
            game_write+mod_write+default_write_path     |gameinfo_path|.
            gamebin     |gameinfo_path|bin

            // HL2 Content
            game_lv             "{hl2_path}\\hl2\\hl2_lv.vpk"
            game+mod            "{hl2_path}\\hl2\\hl2_sound_vo_english.vpk"
            game+mod            "{hl2_path}\\hl2\\hl2_pak.vpk"
            game                "{hl2_path}\\hl2\\hl2_textures.vpk"
            game                "{hl2_path}\\hl2\\hl2_sound_misc.vpk"
            game                "{hl2_path}\\hl2\\hl2_misc.vpk"
            
            platform            |all_source_engine_paths|platform/platform_misc.vpk

            // Last, mount in shared HL2 loose files
            game                "{hl2_path}\\hl2"
            platform            |all_source_engine_paths|platform

        }}
    }}
}}''',

            'episodicvr': '''"GameInfo"
{{
    GameLogo        1
    Game            "Half-Life 2: VR Mod - Episode 1"
    Title           ""
    Title2          ""
    Developer       "Source VR Team"    
    Developer_URL   "https://halflife2vr.com/"
    Type            singleplayer_only
    Icon            "resource/game"
    NoModels        0
    SupportsVR      0
    SupportsDX8     0
    GameData        "halflife2vr.fgd"
    InstancePath    "instances"

    FileSystem
    {{
        SteamAppId              2177750
                
        SearchPaths
        {{  
            // First, mount all user customizations.  This will search for VPKs and subfolders
            // and mount them in alphabetical order.  The easiest way to distribute a mod is to
            // pack up the custom content into a VPK.  To "install" a mod, just drop it in this
            // folder.
            //
            // Note that this folder is scanned only when the game is booted.
            game+mod            episodicvr/custom/*
            game+mod            hlvr/custom/*

            // mount VR files first
            game+mod    |gameinfo_path|.
            game+mod+game_write+mod_write+default_write_path    |gameinfo_path|.
            gamebin     |gameinfo_path|bin
            game        hlvr

            //HL2 + Ep1 Content
            game_lv             "{hl2_path}\\hl2\\hl2_lv.vpk"
            game+mod            "{hl2_path}\\episodic\\ep1_sound_vo_english.vpk"
            game+mod            "{hl2_path}\\episodic\\ep1_pak.vpk"
            game+mod            "{hl2_path}\\hl2\\hl2_sound_vo_english.vpk"
            game+mod            "{hl2_path}\\hl2\\hl2_pak.vpk"
            game                "{hl2_path}\\hl2\\hl2_textures.vpk"
            game                "{hl2_path}\\hl2\\hl2_sound_misc.vpk"
            game                "{hl2_path}\\hl2\\hl2_misc.vpk"
            
            platform            |all_source_engine_paths|platform/platform_misc.vpk

            // Last, mount in shared HL2 loose files
            game                "{hl2_path}\\episodic"
            game                "{hl2_path}\\hl2"
            platform            |all_source_engine_paths|platform

        }}
    }}
}}''',

            'ep2vr': '''"GameInfo"
{{
    GameLogo        1
    Game            "Half-Life 2: VR Mod - Episode 2"
    Title           ""
    Title2          ""
    Developer       "Source VR Team"    
    Developer_URL   "https://halflife2vr.com/"
    Type            singleplayer_only
    Icon            "resource/game"
    NoModels        0
    SupportsVR      0
    SupportsDX8     0
    GameData        "halflife2vr.fgd"
    InstancePath    "instances"

    FileSystem
    {{
        SteamAppId              2177760
                
        SearchPaths
        {{
            // First, mount all user customizations.  This will search for VPKs and subfolders
            // and mount them in alphabetical order.  The easiest way to distribute a mod is to
            // pack up the custom content into a VPK.  To "install" a mod, just drop it in this
            // folder.
            //
            // Note that this folder is scanned only when the game is booted.
            game+mod            ep2vr/custom/*
            game+mod            episodicvr/custom/*
            game+mod            hlvr/custom/*

            // mount VR files first
            game+mod    |gameinfo_path|.
            game+mod+game_write+mod_write+default_write_path    |gameinfo_path|.
            gamebin     episodicvr/bin
            game        episodicvr
            game        hlvr

            //HL2 + Ep1 Content
            game_lv             "{hl2_path}/hl2/hl2_lv.vpk"
            game+mod            "{hl2_path}/ep2/ep2_sound_vo_english.vpk"
            game+mod            "{hl2_path}/ep2/ep2_pak.vpk"
            game+mod            "{hl2_path}/episodic/ep1_sound_vo_english.vpk"
            game+mod            "{hl2_path}/episodic/ep1_pak.vpk"
            game+mod            "{hl2_path}/hl2/hl2_sound_vo_english.vpk"
            game+mod            "{hl2_path}/hl2/hl2_pak.vpk"
            game                "{hl2_path}/hl2/hl2_textures.vpk"
            game                "{hl2_path}/hl2/hl2_sound_misc.vpk"
            game                "{hl2_path}/hl2/hl2_misc.vpk"
            platform            |all_source_engine_paths|platform/platform_misc.vpk

            // Last, mount in shared HL2 loose files
            game                "{hl2_path}/ep2"
            game                "{hl2_path}/episodic"
            game                "{hl2_path}/hl2"
            platform            |all_source_engine_paths|platform

        }}
    }}
}}'''
        }
        
        return templates[game_type].format(hl2_path=self.hl2_path.replace('\\', '/'))
    
    def copy_vpk_files(self, existing_dirs):
        """Копирует VPK файлы из AnniversaryContent для существующих папок"""
        try:
            if not os.path.exists(self.anniversary_content_path):
                return False, f"Папка AnniversaryContent не найдена"
            
            # Список VPK файлов для копирования с проверкой существования папки
            vpk_files_to_copy = []
            if existing_dirs['hlvr']:
                vpk_files_to_copy.append(('hlvr/hl2vr.vpk', 'hlvr/hl2vr.vpk'))
            if existing_dirs['episodicvr']:
                vpk_files_to_copy.append(('episodicvr/ep1vr.vpk', 'episodicvr/ep1vr.vpk'))
            if existing_dirs['ep2vr']:
                vpk_files_to_copy.append(('ep2vr/ep2vr.vpk', 'ep2vr/ep2vr.vpk'))
            
            if not vpk_files_to_copy:
                return True, tr("Game folders not found")
            
            copied_files = []
            
            for src_relative, dst_relative in vpk_files_to_copy:
                src_path = os.path.join(self.anniversary_content_path, src_relative)
                dst_path = os.path.join(self.hl2vr_path, dst_relative)
                
                if os.path.exists(src_path):
                    # Copy VPK file
                    shutil.copy2(src_path, dst_path)
                    copied_files.append(dst_relative)
                else:
                    return False, f"File not found: {src_path}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Error copying VPK files: {str(e)}"
    
    def copy_hlvr_folders(self, existing_dirs):
        """Copies maps and shaders folders from AnniversaryContent to hlvr, replacing existing ones"""
        try:
            if not existing_dirs['hlvr']:
                return True, tr("hlvr folder not found, skipping folder copy")
                
            # Folders to copy from AnniversaryContent to hlvr
            folders_to_copy = ['maps', 'shaders']
            
            for folder_name in folders_to_copy:
                src_folder = os.path.join(self.anniversary_content_path, "hlvr", folder_name)
                dst_folder = os.path.join(self.hl2vr_path, "hlvr", folder_name)
                
                if not os.path.exists(src_folder):
                    return False, f"Folder {folder_name} not found in AnniversaryContent: {src_folder}"
                
                # Delete target folder if it exists
                if os.path.exists(dst_folder):
                    shutil.rmtree(dst_folder)
                
                # Copy folder from AnniversaryContent
                shutil.copytree(src_folder, dst_folder)
            
            return True, ""
            
        except Exception as e:
            return False, f"Error copying hlvr folders: {str(e)}"
    
    def remove_episodes_maps_folders(self, existing_dirs):
        """Deletes maps folders from episodicvr and ep2vr"""
        try:
            folders_to_clean = []
            if existing_dirs['episodicvr']:
                folders_to_clean.append('episodicvr')
            if existing_dirs['ep2vr']:
                folders_to_clean.append('ep2vr')
            
            if not folders_to_clean:
                return True, tr("Episode folders not found")
            
            removed_count = 0
            
            for folder in folders_to_clean:
                maps_path = os.path.join(self.hl2vr_path, folder, 'maps')
                if os.path.exists(maps_path) and os.path.isdir(maps_path):
                    shutil.rmtree(maps_path)
                    removed_count += 1
            
            return True, ""
            
        except Exception as e:
            return False, f"Error deleting maps folders from episodes: {str(e)}"
    
    def update_gameinfo_files(self, existing_dirs):
        """Updates gameinfo.txt files for existing game folders"""
        try:
            gameinfo_paths = {}
            if existing_dirs['hlvr']:
                gameinfo_paths['hlvr'] = os.path.join(self.hl2vr_path, 'hlvr', 'gameinfo.txt')
            if existing_dirs['episodicvr']:
                gameinfo_paths['episodicvr'] = os.path.join(self.hl2vr_path, 'episodicvr', 'gameinfo.txt')
            if existing_dirs['ep2vr']:
                gameinfo_paths['ep2vr'] = os.path.join(self.hl2vr_path, 'ep2vr', 'gameinfo.txt')
            
            if not gameinfo_paths:
                return True, tr("Game folders not found")
            
            updated_count = 0
            for game_type, gameinfo_path in gameinfo_paths.items():
                content = self.get_gameinfo_content(game_type)
                with open(gameinfo_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                updated_count += 1
            
            return True, ""
            
        except Exception as e:
            return False, f"Error updating gameinfo.txt: {str(e)}"
    
    def install_anniversary_content(self):
        """Main function for installing anniversary content"""
        try:
            log.info(tr("Starting Anniversary Update installation"))
            
            # Check paths
            success, error_message = self.validate_paths()
            if not success:
                return False, error_message
            
            # Check game folders existence
            existing_dirs = self.check_game_directories()
            
            # Copy VPK files only for existing folders
            success, message = self.copy_vpk_files(existing_dirs)
            if not success:
                return False, message
            
            # Copy maps and shaders folders to hlvr (replacing existing ones)
            success, message = self.copy_hlvr_folders(existing_dirs)
            if not success:
                return False, message
            
            # Delete maps folders from episodicvr and ep2vr
            success, message = self.remove_episodes_maps_folders(existing_dirs)
            log.info(tr("Changes made to files and folders"))
            if not success:
                return False, message
            
            # Update gameinfo.txt only for existing folders
            success, message = self.update_gameinfo_files(existing_dirs)
            log.info(tr("gameinfo.txt updated"))
            if not success:
                return False, message

            log.info(tr("Anniversary Update successfully installed"))
            return True, tr("Anniversary update content installed!")
            
        except Exception as e:
            log.error(f"Error installing Anniversary Update: {str(e)}")
            return False, f"An unexpected error occurred: {str(e)}"

def install_anniversary_update(hl2vr_path, hl2_path):
    manager = AnniversaryUpdateManager(hl2vr_path, hl2_path)
    return manager.install_anniversary_content()