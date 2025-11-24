import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QFileDialog, QProgressDialog,
                             QSplitter, QFrame, QAbstractItemView, QCheckBox, QDialog, QScrollArea, QTextEdit, QSizePolicy, QMenu, QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QFontMetrics, QPen, QIcon
import workshop
import gameinfo
import addon_manager
import config
import path_utils
from logger import log
import concurrent.futures
from i18n import tr, translator
import re
import webbrowser
import subprocess
from help_dialog import HelpDialog



class AddonWorker(QThread):
    """Addons processing thread"""
    prepared = pyqtSignal(bool, object, str)
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, url, hl2vr_path, hl2_path, is_collection=True, check_files=True, execute=False, prepared_data=None):
        super().__init__()
        self.url = url
        self.hl2vr_path = hl2vr_path
        self.hl2_path = hl2_path
        self.is_collection = is_collection
        self.check_files = check_files
        self.execute = execute 
        self.prepared_data = prepared_data
    
    def run(self):
            try:
                if not self.execute:
                    # PREPARATION MODE
                    self.progress.emit(tr("Preparing data..."))
                    
                    if self.is_collection:
                        success, data, error_message = addon_manager.prepare_addons_for_embedding(
                            self.url, self.hl2vr_path, self.hl2_path, self.check_files
                        )
                    else:
                        success, data, error_message = addon_manager.prepare_single_addon_for_embedding(
                            self.url, self.hl2vr_path, self.hl2_path, self.check_files
                        )
                    
                    self.prepared.emit(success, data, error_message)
                    
                else:
                    # EXECUTION MODE
                    self.progress.emit(tr("Mounting addons..."))
                    
                    success, message = gameinfo.update_gameinfo(
                        self.prepared_data['gameinfo_path'], 
                        self.prepared_data['addons_with_paths']
                    )
                    
                    if success:
                        if self.is_collection:
                            final_message = tr("Collection successfully processed!") + f"\n{message}"
                        else:
                            final_message = tr("Addon successfully mounted!")
                        
                        self.finished.emit(True, final_message)
                    else:
                        self.finished.emit(False, message)
                        
            except Exception as e:
                if not self.execute:
                    self.prepared.emit(False, None, f"An unexpected error occurred during preparation:\n{str(e)}")
                else:
                    self.finished.emit(False, f"An unexpected error occurred:\n{str(e)}")

class WorkshopTxtWorker(QThread):
    """workshop.txt processing thread"""
    prepared = pyqtSignal(bool, object, str)
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, hl2vr_path, hl2_path, check_files=True, execute=False, prepared_data=None):
        super().__init__()
        self.hl2vr_path = hl2vr_path
        self.hl2_path = hl2_path
        self.check_files = check_files
        self.execute = execute
        self.prepared_data = prepared_data
    
    def run(self):
            try:
                if not self.execute:
                    # PREPARATION MODE - only get data for dialog
                    self.progress.emit(tr("Preparing data..."))
                    
                    success, data, error_message = addon_manager.prepare_addons_from_workshop_txt(
                        self.hl2vr_path, self.hl2_path, self.check_files
                    )
                    
                    self.prepared.emit(success, data, error_message)
                    
                else:
                    # EXECUTION MODE - actual addon mounting
                    self.progress.emit(tr("Mounting addons..."))
                    
                    # Use prepared data
                    success, message = gameinfo.update_gameinfo(
                        self.prepared_data['gameinfo_path'], 
                        self.prepared_data['addons_with_paths']
                    )
                    
                    if success:
                        final_message = tr("Installed addons successfully processed!") + f"\n{message}"
                        self.finished.emit(True, final_message)
                    else:
                        self.finished.emit(False, message)
                        
            except Exception as e:
                if not self.execute:
                    self.prepared.emit(False, None, f"An unexpected error occurred during preparation:\n{str(e)}")
                else:
                    self.finished.emit(False, f"An unexpected error occurred:\n{str(e)}")

class MapExtractionWorker(QThread):
    """Map extraction thread"""
    progress = pyqtSignal(int, int, int, int, str)  # current_map, total_maps, current_file, total_files, status
    finished = pyqtSignal(bool, object)  # success, result
    
    def __init__(self, gameinfo_path, current_addons, specific_addons=None):
        super().__init__()
        self.gameinfo_path = gameinfo_path
        self.current_addons = current_addons
        self.specific_addons = specific_addons
        self._is_cancelled = False
    
    def cancel(self):
        self._is_cancelled = True
    
    def is_cancelled(self):
        return self._is_cancelled
    
    def run(self):
        try:
            # Callback function for progress updates
            def progress_callback(current_map, total_maps, current_file, total_files, status):
                # Check for cancellation before each progress update
                if self.is_cancelled():
                    return False  # Signal to abort
                self.progress.emit(current_map, total_maps, current_file, total_files, status)
                return True
            
            success, map_addons, result = addon_manager.check_and_extract_maps(
                self.gameinfo_path, 
                self.current_addons,
                progress_callback,
                self.specific_addons
            )
            
            # If cancellation occurred, return special result
            if self.is_cancelled():
                self.finished.emit(False, {"cancelled": True, "message": tr("Extraction cancelled")})
            else:
                self.finished.emit(success, result)
                
        except Exception as e:
            self.finished.emit(False, f"An unexpected error occurred during map extraction:\n{str(e)}")

class CheckBoxTableWidgetItem(QTableWidgetItem):
    def __init__(self, checked=False):
        super().__init__()
        self.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        self.setCheckState(Qt.Checked if checked else Qt.Unchecked)

class ConfirmAddonsDialog(QDialog):
    def __init__(self, parent=None, title=tr("Mounting confirmation"), 
                 summary="", addons_list="", duplicates_list="", 
                 missing_list="", failed_list="", dialog_type="add",
                 maps_list="", extracted_list="", extraction_results=None,
                 enable_extract_button=True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        screen_geometry = QApplication.desktop().screenGeometry()
        max_height = int(screen_geometry.height() * 0.7)
        self.setMaximumHeight(max_height)
        
        self.setup_ui(summary, addons_list, duplicates_list, missing_list, failed_list, 
                     dialog_type, maps_list, extracted_list, extraction_results, enable_extract_button)
        
    def setup_ui(self, summary, addons_list, duplicates_list, missing_list, failed_list, 
                dialog_type, maps_list, extracted_list, extraction_results, enable_extract_button):
        layout = QVBoxLayout(self)

        info_label = QLabel(summary)
        if dialog_type == "add":
            info_style = """
                QLabel {
                    background-color: #e3f2fd;
                    border: 1px solid #90caf9;
                    border-radius: 5px;
                    padding: 10px;
                    margin: 5px;
                }
            """
        elif dialog_type == "remove":
            info_style = """
                QLabel {
                    background-color: #ffebee;
                    border: 1px solid #ffcdd2;
                    border-radius: 5px;
                    padding: 10px;
                    margin: 5px;
                }
            """
        elif dialog_type == "check":
            info_style = """
                QLabel {
                    background-color: #fff3e0;
                    border: 1px solid #ffcc80;
                    border-radius: 5px;
                    padding: 10px;
                    margin: 5px;
                }
            """
        elif dialog_type == "maps":
            info_style = """
                QLabel {
                    background-color: #e8f5e9;
                    border: 1px solid #a5d6a7;
                    border-radius: 5px;
                    padding: 10px;
                    margin: 5px;
                }
            """
        else:  # extraction_results
            info_style = """
                QLabel {
                    background-color: #fff3e0;
                    border: 1px solid #ffcc80;
                    border-radius: 5px;
                    padding: 10px;
                    margin: 5px;
                }
            """
        
        info_label.setStyleSheet(info_style)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        if dialog_type == "extraction_results":
            if extraction_results and 'extracted' in extraction_results and extraction_results['extracted']:
                extracted_label = QLabel(tr("Successfully extracted maps:"))
                extracted_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #4caf50;")
                content_layout.addWidget(extracted_label)
                
                extracted_list = "\n".join([f"{i+1}. {addon['title']}" for i, addon in enumerate(extraction_results['extracted'])])
                extracted_text = QTextEdit()
                extracted_text.setPlainText(extracted_list)
                extracted_text.setReadOnly(True)
                extracted_text.setMaximumHeight(150)

                content_layout.addWidget(extracted_text)
            
            if extraction_results and 'failed' in extraction_results and extraction_results['failed']:
                failed_label = QLabel(tr("Extraction errors:"))
                failed_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #f44336;")
                content_layout.addWidget(failed_label)
                
                failed_list = "\n".join([f"{i+1}. {addon['title']}: {error}" for i, (addon, error) in enumerate(extraction_results['failed'])])
                failed_text = QTextEdit()
                failed_text.setPlainText(failed_list)
                failed_text.setReadOnly(True)
                failed_text.setMaximumHeight(150)

                content_layout.addWidget(failed_text)
        
        elif dialog_type == "maps":
            if maps_list:
                maps_label = QLabel(tr("Maps to extract:"))
                maps_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #ff9800;")
                content_layout.addWidget(maps_label)
                
                maps_text = QTextEdit()
                maps_text.setPlainText(maps_list)
                maps_text.setReadOnly(True)
                maps_text.setMaximumHeight(150)

                content_layout.addWidget(maps_text)
            
            if extracted_list:
                extracted_label = QLabel(tr("Already extracted maps:"))
                extracted_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #4caf50;")
                content_layout.addWidget(extracted_label)
                
                extracted_text = QTextEdit()
                extracted_text.setPlainText(extracted_list)
                extracted_text.setReadOnly(True)
                extracted_text.setMaximumHeight(150)

                content_layout.addWidget(extracted_text)
        
        else:
            if addons_list:
                if dialog_type == "add":
                    addons_label = QLabel(tr("Addons to add:"))
                elif dialog_type == "remove":
                    addons_label = QLabel(tr("Addons to remove:"))
                else:
                    addons_label = QLabel(tr("Missing addons:"))
                
                addons_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
                content_layout.addWidget(addons_label)
                
                addons_text = QTextEdit()
                addons_text.setPlainText(addons_list)
                addons_text.setReadOnly(True)
                addons_text.setMaximumHeight(150)
                content_layout.addWidget(addons_text)
            
            if duplicates_list and dialog_type == "add":
                duplicates_label = QLabel(tr("Duplicates (skipped):"))
                duplicates_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #ff9800;")
                content_layout.addWidget(duplicates_label)
                
                duplicates_text = QTextEdit()
                duplicates_text.setPlainText(duplicates_list)
                duplicates_text.setReadOnly(True)
                duplicates_text.setMaximumHeight(100)

                content_layout.addWidget(duplicates_text)
            
            if missing_list and dialog_type == "add":
                missing_label = QLabel(tr("Missing addons (skipped):"))
                missing_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #f44336;")
                content_layout.addWidget(missing_label)
                
                missing_text = QTextEdit()
                missing_text.setPlainText(missing_list)
                missing_text.setReadOnly(True)
                missing_text.setMaximumHeight(100)

                content_layout.addWidget(missing_text)
            
            if failed_list and dialog_type == "add":
                failed_label = QLabel(tr("Failed to get information:"))
                failed_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #f44336;")
                content_layout.addWidget(failed_label)
                
                failed_text = QTextEdit()
                failed_text.setPlainText(failed_list)
                failed_text.setReadOnly(True)
                failed_text.setMaximumHeight(100)

                content_layout.addWidget(failed_text)
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        buttons_layout = QHBoxLayout()
        
        if dialog_type == "add":
            self.yes_button = QPushButton(tr("Yes"))
            self.no_button = QPushButton(tr("No"))
        elif dialog_type == "remove":
            self.yes_button = QPushButton(tr("Remove"))
            self.no_button = QPushButton(tr("Cancel"))
        elif dialog_type == "check":
            self.yes_button = QPushButton(tr("Remove missing"))
            self.no_button = QPushButton(tr("Cancel"))
        elif dialog_type == "maps":
            self.yes_button = QPushButton(tr("Extract maps"))
            self.no_button = QPushButton(tr("Skip"))

            # Manage extract button activity
            self.yes_button.setEnabled(enable_extract_button)
            if not enable_extract_button:
                self.yes_button.setToolTip(tr("No maps to extract"))

        else:
            self.yes_button = QPushButton(tr("OK"))
            self.no_button = QPushButton("")
        
        self.yes_button.setDefault(True)
        
        if dialog_type == "extraction_results":
            self.no_button.setVisible(False)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.yes_button)
        buttons_layout.addWidget(self.no_button)
        
        layout.addLayout(buttons_layout)
        
        self.yes_button.clicked.connect(self.accept)
        self.no_button.clicked.connect(self.reject)

class RotatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(30, 40)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.isDown():
            bg_color = QColor(200, 200, 200)
            border_color = QColor(100, 100, 100)
            text_offset = 1
        elif self.underMouse():
            bg_color = QColor(230, 230, 230)
            border_color = QColor(150, 150, 150)
            text_offset = 0
        else:
            bg_color = QColor(240, 240, 240)
            border_color = QColor(180, 180, 180)
            text_offset = 0
        
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1))
        painter.drawRect(0, 0, self.width()-1, self.height()-1)
        
        painter.save()
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(-90)
        
        font = self.font()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(Qt.black)
        
        metrics = QFontMetrics(font)
        text_width = metrics.width(self.text())
        text_height = metrics.height()

        painter.drawText(-text_width // 2 + text_offset, text_height // 4 + text_offset, self.text())
        painter.restore()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.current_addons = []

        self.setWindowIcon(self.load_icon())

        self.app_config = config.load_config()
        language = self.app_config.get("language", "en")
        translator.set_language(language)

        self.init_ui()

        self.load_config()
        
        # Adding a timer for delayed saving
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_addons_order)
        
    def load_icon(self):
        possible_paths = [
            "icon.ico",
            os.path.join(os.path.dirname(sys.executable), "icon.ico"),
            os.path.join(os.path.dirname(sys.executable), "_internal", "icon.ico"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return QIcon(path)

        print("Warning: Icon not found at any path")
        return QIcon()

    def init_ui(self):
        self.setWindowTitle("HL2:VR Workshop Extender")
        self.setGeometry(100, 100, 1200, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)



        # === LEFT PANEL ===



        # Title
        title_label = QLabel("HL2:VR Workshop Extender")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_label)

        # Separator
        separator0 = QFrame()
        separator0.setFrameShape(QFrame.HLine)
        separator0.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(separator0)

        # Path to HL2 VR
        hl2vr_label = QLabel(tr("Half-Life 2 VR Mod folder:"))
        left_layout.addWidget(hl2vr_label)

        hl2vr_layout = QHBoxLayout()
        self.hl2vr_entry = QLineEdit()
        self.hl2vr_entry.setFocusPolicy(Qt.ClickFocus)
        hl2vr_layout.addWidget(self.hl2vr_entry)

        hl2vr_browse_btn = QPushButton(tr("Browse"))
        hl2vr_browse_btn.clicked.connect(lambda: self.select_folder(self.hl2vr_entry, tr("Select Half-Life 2 VR folder")))
        hl2vr_layout.addWidget(hl2vr_browse_btn)

        left_layout.addLayout(hl2vr_layout)

        # HL2 path
        hl2_label = QLabel(tr("Half-Life 2 folder:"))
        left_layout.addWidget(hl2_label)

        hl2_layout = QHBoxLayout()
        self.hl2_entry = QLineEdit()
        self.hl2_entry.setFocusPolicy(Qt.ClickFocus)

        # Text change handler
        self.hl2vr_entry.textChanged.connect(self.on_hl2vr_path_changed)
        hl2_layout.addWidget(self.hl2_entry)

        hl2_browse_btn = QPushButton(tr("Browse"))
        hl2_browse_btn.clicked.connect(lambda: self.select_folder(self.hl2_entry, tr("Select Half-Life 2 folder")))
        hl2_layout.addWidget(hl2_browse_btn)

        left_layout.addLayout(hl2_layout)

        # Button for mounting installed addons
        self.embed_installed_btn = QPushButton(tr("Mount installed addons"))
        self.embed_installed_btn.setFont(QFont("", 10, QFont.Bold))
        self.embed_installed_btn.clicked.connect(self.embed_installed_addons)
        left_layout.addWidget(self.embed_installed_btn)


        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(separator1)

        # Collection URL
        url_label = QLabel(tr("Steam Workshop collection URL:"))
        left_layout.addWidget(url_label)

        self.url_entry = QLineEdit()
        self.url_entry.setFocusPolicy(Qt.ClickFocus)  # Focus only on click
        self.url_entry.textChanged.connect(self.on_url_change)
        left_layout.addWidget(self.url_entry)

        # Mount collection button
        self.embed_collection_btn = QPushButton(tr("Mount collection"))
        self.embed_collection_btn.setFont(QFont("", 10, QFont.Bold))
        self.embed_collection_btn.clicked.connect(self.embed_collection)
        left_layout.addWidget(self.embed_collection_btn)


        # Single addon URL
        single_addon_label = QLabel(tr("Addon URL:"))
        left_layout.addWidget(single_addon_label)

        self.single_addon_entry = QLineEdit()
        self.single_addon_entry.setFocusPolicy(Qt.ClickFocus)  # Focus only on click
        self.single_addon_entry.textChanged.connect(self.on_url_change)
        left_layout.addWidget(self.single_addon_entry)

        # Mount addon button
        self.embed_single_btn = QPushButton(tr("Mount addon"))
        self.embed_single_btn.setFont(QFont("", 10, QFont.Bold))
        self.embed_single_btn.clicked.connect(self.embed_single_addon)
        left_layout.addWidget(self.embed_single_btn)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray;")
        self.status_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.status_label)

        # Checkbox for addon file verification
        self.check_files_checkbox = QCheckBox(tr("Validate files"))
        self.check_files_checkbox.setChecked(True)
        self.check_files_checkbox.stateChanged.connect(self.on_check_files_changed)
        left_layout.addWidget(self.check_files_checkbox)

        # ADD: Checkbox for automatic map checking
        self.auto_check_maps_checkbox = QCheckBox(tr("Check maps automatically"))
        self.auto_check_maps_checkbox.setChecked(True)
        self.auto_check_maps_checkbox.stateChanged.connect(self.on_auto_check_maps_changed)
        left_layout.addWidget(self.auto_check_maps_checkbox)

        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(separator2)

        # ADD: Horizontal layout for checkbox and button
        episodes_layout = QHBoxLayout()

        # Checkbox for episode synchronization
        self.embed_episodes_checkbox = QCheckBox(tr("Sync with Episodes"))
        self.embed_episodes_checkbox.stateChanged.connect(self.on_embed_episodes_changed)
        episodes_layout.addWidget(self.embed_episodes_checkbox)

        self.sync_list_btn = QPushButton("⟳")
        self.sync_list_btn.setToolTip(tr("Resync"))
        self.sync_list_btn.setFixedSize(20, 20)
        self.sync_list_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
               
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        self.sync_list_btn.clicked.connect(self.sync_with_episodes)

        episodes_layout.addWidget(self.sync_list_btn)

        episodes_layout.addStretch()

        left_layout.addLayout(episodes_layout)

        # Episode status label
        self.episodes_status_label = QLabel(tr("Checking Episodes..."))
        self.episodes_status_label.setStyleSheet("color: gray; font-size: 10px;")

        left_layout.addWidget(self.episodes_status_label)

        # Separator before anniversary update
        separator_anniversary = QFrame()
        separator_anniversary.setFrameShape(QFrame.HLine)
        separator_anniversary.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(separator_anniversary)
        left_layout.addStretch()

        # Anniversary update mounting button
        self.anniversary_btn = QPushButton(tr("Mount Anniversary Update content"))
        self.anniversary_btn.setFont(QFont("", 10, QFont.Bold))
        self.anniversary_btn.clicked.connect(self.install_anniversary_update)
        left_layout.addWidget(self.anniversary_btn)

        separator_anniversary2 = QFrame()
        separator_anniversary2.setFrameShape(QFrame.HLine)
        separator_anniversary2.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(separator_anniversary2)
        left_layout.addStretch()

        # Widget for displaying logs
        self.log_widget = QTextEdit()
        self.log_widget.setMaximumHeight(200)
        self.log_widget.setReadOnly(True)
        self.log_widget.setFont(QFont("Consolas", 9))
        left_layout.addWidget(self.log_widget)

        log.set_widget(self.log_widget)
        
        # Help button
        help_btn = QPushButton(tr("Help"))
        help_btn.setFixedWidth(100)
        help_btn.clicked.connect(self.show_help)
        left_layout.addWidget(help_btn)



        # === RIGHT PANEL ===
        


        # Search panel
        search_layout = QHBoxLayout()
        search_label = QLabel(tr("Search:"))
        self.search_entry = QLineEdit()
        self.search_entry.textChanged.connect(self.on_search_text_changed)

        self.search_entry.setMaximumWidth(250)

        left_spacer = QWidget()
        left_spacer.setFixedWidth(56)
        search_layout.addWidget(left_spacer)

        # Checkbox toggle button
        self.toggle_check_btn = QPushButton()
        self.toggle_check_btn.setCheckable(True)
        self.toggle_check_btn.setChecked(False)
        self.toggle_check_btn.setFixedSize(20, 20) 
        self.toggle_check_btn.clicked.connect(self.toggle_all_checks)

        self.toggle_check_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #cccccc;
                border-radius: 3px;
            }
            QPushButton:checked {
                background-color: #2a82da;
                border: 2px solid #1e65b3;
            }
            QPushButton:checked:hover {
                background-color: #1e65b3;
                border: 2px solid #165099;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border: 2px solid #aaaaaa;
            }
        """)

        search_layout.addWidget(self.toggle_check_btn)
        search_layout.addSpacing(5)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_entry)

        # Search results navigation buttons
        self.prev_search_btn = QPushButton("←")
        self.prev_search_btn.setFixedWidth(30)
        self.prev_search_btn.clicked.connect(self.previous_search_result)
        self.prev_search_btn.setEnabled(False)
        search_layout.addWidget(self.prev_search_btn)

        self.next_search_btn = QPushButton("→")
        self.next_search_btn.setFixedWidth(30)
        self.next_search_btn.clicked.connect(self.next_search_result)
        self.next_search_btn.setEnabled(False)
        search_layout.addWidget(self.next_search_btn)

        search_layout.addStretch(1)

        # Language combobox
        self.language_combo = QComboBox()
        for lang_code, lang_name in translator.get_available_languages():
            self.language_combo.addItem(lang_name, lang_code)

        # Set the current language
        current_index = self.language_combo.findData(translator.current_language)
        if current_index >= 0:
            self.language_combo.setCurrentIndex(current_index)

        self.language_combo.currentIndexChanged.connect(self.on_language_changed)

        search_layout.addStretch()
        search_layout.addWidget(QLabel(tr("Language") + ":"))
        search_layout.addWidget(self.language_combo)
        right_layout.addLayout(search_layout)

        # Addons tab
        self.addons_table = QTableWidget()
        self.addons_table.setColumnCount(4)
        self.addons_table.setHorizontalHeaderLabels(["", tr("Name"), tr("Link"), tr("Folder")])
        
        # Стиль для таблицы
        self.addons_table.setStyleSheet("""
            QTableWidget {
                outline: none;
            }
            QTableWidget::item:focus {
                outline: none;
                border: none;
                background: none;
            }
            QTableWidget::item:selected {
                background-color: #2a82da;
                color: white;
            }
            QTableWidget::item:hover:!selected {
                background-color: #e6f3ff;
            }
            QTableWidget::indicator {
                width: 20px;
                height: 20px;
            }
            QTableWidget::indicator:checked {
                background-color: #2a82da;
                border: 1px solid #1e65b3;
            }
            QTableWidget::indicator:unchecked {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
            }
        """)

        # Customizing the display of rows and columns
        self.addons_table.verticalHeader().setVisible(True)
        self.addons_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.addons_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.addons_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.addons_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.addons_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.addons_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.addons_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.addons_table.setFocusPolicy(Qt.NoFocus)
        
        right_layout.addWidget(self.addons_table)
        
        self.addons_table.cellClicked.connect(self.on_table_cell_clicked)
        self.addons_table.itemChanged.connect(self.on_checkbox_changed)
        left_buttons_main_layout = QVBoxLayout()

        self.addons_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.addons_table.customContextMenuRequested.connect(self.show_context_menu)

        refresh_container = QVBoxLayout()
        refresh_container.setAlignment(Qt.AlignTop)

        # List refresh button
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setToolTip(tr("Refresh addons list"))
        self.refresh_btn.setFixedSize(30, 30)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        self.refresh_btn.clicked.connect(self.load_addons_list)
        refresh_container.addWidget(self.refresh_btn)

        # Adjustable padding for the refresh button
        #refresh_container.addSpacing(0)

        # The center part is a container for order buttons with center alignment.
        center_container = QVBoxLayout()
        center_container.setAlignment(Qt.AlignCenter)

        self.order_buttons_layout = QVBoxLayout()
        self.order_buttons_layout.setAlignment(Qt.AlignCenter)
        self.order_buttons_layout.setSpacing(5)

        self.setup_order_buttons()

        # Adding timers for auto-repeat when holding buttons
        self.move_up_timer = QTimer()
        self.move_up_timer.setSingleShot(False)
        self.move_up_timer.timeout.connect(self.move_addon_up)
        
        self.move_down_timer = QTimer()
        self.move_down_timer.setSingleShot(False)
        self.move_down_timer.timeout.connect(self.move_addon_down)
        
        self.move_top_timer = QTimer()
        self.move_top_timer.setSingleShot(False)
        self.move_top_timer.timeout.connect(self.move_addon_to_top)
        
        self.move_bottom_timer = QTimer()
        self.move_bottom_timer.setSingleShot(False)
        self.move_bottom_timer.timeout.connect(self.move_addon_to_bottom)
        
        # Delay timers before auto-repeat starts
        self.move_up_delay_timer = QTimer()
        self.move_up_delay_timer.setSingleShot(True)
        self.move_up_delay_timer.timeout.connect(lambda: self.start_timer(self.move_up_timer, 100))
        
        self.move_down_delay_timer = QTimer()
        self.move_down_delay_timer.setSingleShot(True)
        self.move_down_delay_timer.timeout.connect(lambda: self.start_timer(self.move_down_timer, 100))
        
        self.move_top_delay_timer = QTimer()
        self.move_top_delay_timer.setSingleShot(True)
        self.move_top_delay_timer.timeout.connect(lambda: self.start_timer(self.move_top_timer, 100))
        
        self.move_bottom_delay_timer = QTimer()
        self.move_bottom_delay_timer.setSingleShot(True)
        self.move_bottom_delay_timer.timeout.connect(lambda: self.start_timer(self.move_bottom_timer, 100))

        #order_buttons_layout.addSpacing(90)

        center_container.addLayout(self.order_buttons_layout)

        bottom_spacer = QVBoxLayout()
        bottom_spacer.addStretch(1)

        left_buttons_main_layout.addLayout(refresh_container)
        left_buttons_main_layout.addStretch(1)  # Stretching element in front of the center
        left_buttons_main_layout.addLayout(center_container)
        left_buttons_main_layout.addStretch(1)  # Stretching element after center

        # Add buttons on the left and a table on the right
        table_with_buttons_layout = QHBoxLayout()
        table_with_buttons_layout.addLayout(left_buttons_main_layout)
        table_with_buttons_layout.addWidget(self.addons_table)

        right_layout.addLayout(table_with_buttons_layout)

        buttons_layout = QHBoxLayout()

        # Add some space to the left of the add-on check button
        buttons_layout.addSpacing(35)

        # List save and load buttons
        self.save_list_btn = QPushButton(tr("Save list"))
        self.save_list_btn.clicked.connect(self.save_addons_list)
        buttons_layout.addWidget(self.save_list_btn)

        self.load_list_btn = QPushButton(tr("Load list")) 
        self.load_list_btn.clicked.connect(self.load_addons_list_from_file)
        buttons_layout.addWidget(self.load_list_btn)

        # Separator between save/load and check
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setFrameShadow(QFrame.Sunken)
        buttons_layout.addWidget(separator1)

        # Addon check button
        check_addons_btn = QPushButton(tr("Check files"))
        check_addons_btn.clicked.connect(self.check_addons_files)
        buttons_layout.addWidget(check_addons_btn)
        
        # Map check button
        check_maps_btn = QPushButton(tr("Check maps"))
        check_maps_btn.clicked.connect(lambda: self.check_maps())  # Explicitly call without parameters
        buttons_layout.addWidget(check_maps_btn)

        # Map clear button
        clear_maps_btn = QPushButton(tr("Clear maps"))
        clear_maps_btn.clicked.connect(self.clear_extracted_maps)
        buttons_layout.addWidget(clear_maps_btn)

        # Separator between save/load and check
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setFrameShadow(QFrame.Sunken)
        buttons_layout.addWidget(separator1)
        
        remove_btn = QPushButton(tr("Remove selected"))
        remove_btn.clicked.connect(self.remove_selected_addons)
        buttons_layout.addWidget(remove_btn)
        
        remove_all_btn = QPushButton(tr("Remove all"))
        remove_all_btn.clicked.connect(self.remove_all_addons)
        buttons_layout.addWidget(remove_all_btn)
        
        right_layout.addLayout(buttons_layout)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])  # Initial sizes
        
        main_layout.addWidget(splitter)

    def load_config(self):
        app_config = config.load_config()

        # Set language from config
        language = app_config.get("language", "en")
        translator.set_language(language)

        # Update language combobox
        current_index = self.language_combo.findData(language)
        if current_index >= 0:
            self.language_combo.setCurrentIndex(current_index)

        self.url_entry.setText(app_config.get("collection_url", ""))
        self.single_addon_entry.setText(app_config.get("single_addon_url", ""))
        self.hl2vr_entry.setText(app_config.get("hl2vr_path", ""))
        self.hl2_entry.setText(app_config.get("hl2_path", ""))
        
        # Load checkbox states
        check_files = app_config.get("check_addon_files", True)
        self.check_files_checkbox.setChecked(check_files)
        
        auto_check_maps = app_config.get("auto_check_maps", True)
        self.auto_check_maps_checkbox.setChecked(auto_check_maps)
        
        embed_episodes = app_config.get("embed_into_episodes", True)
        self.embed_episodes_checkbox.setChecked(embed_episodes)

        self.update_episodes_checkbox_availability(force_enable=False)
        
        # Automatically load addons list on startup
        if self.hl2vr_entry.text():
            self.load_addons_list()

    def save_config(self):
        config.save_config(
            self.url_entry.text().strip(),
            self.single_addon_entry.text().strip(), 
            self.hl2vr_entry.text().strip(),
            self.hl2_entry.text().strip(),
            self.check_files_checkbox.isChecked(),
            self.auto_check_maps_checkbox.isChecked(),
            self.embed_episodes_checkbox.isChecked(),
            translator.current_language
        )

    def on_language_changed(self):
        language = self.language_combo.currentData()

        if language == translator.current_language:
            return
        
        # DISCONNECT the signal to avoid recursion when changing index
        self.language_combo.currentIndexChanged.disconnect(self.on_language_changed)
        
        try:
            # Set new language
            translator.set_language(language)
            self.save_config()
            
            reply = QMessageBox.information(
                self, 
                tr("Language changed"), 
                tr("Restart the application to change the language"),
                QMessageBox.Ok
            )
            
            # AFTER closing the dialog RESTORE the connection
            self.language_combo.currentIndexChanged.connect(self.on_language_changed)
            
        except Exception as e:
            # In case of error also restore the connection
            self.language_combo.currentIndexChanged.connect(self.on_language_changed)
            log.error(f"Error changing language: {e}")

    def setup_order_buttons(self):
        """Setup order buttons with hold support"""
        move_top_btn = RotatedButton(">>|")
        move_top_btn.setToolTip(tr("To top"))
        move_top_btn.pressed.connect(lambda: self.start_delay_timer(self.move_top_delay_timer))
        move_top_btn.released.connect(lambda: self.stop_timers(self.move_top_delay_timer, self.move_top_timer))
        move_top_btn.clicked.connect(self.move_addon_to_top)
        self.order_buttons_layout.addWidget(move_top_btn)

        move_up_btn = RotatedButton(">")
        move_up_btn.setToolTip(tr("Up (hold for continuous movement)"))
        move_up_btn.pressed.connect(lambda: self.start_delay_timer(self.move_up_delay_timer))
        move_up_btn.released.connect(lambda: self.stop_timers(self.move_up_delay_timer, self.move_up_timer))
        move_up_btn.clicked.connect(self.move_addon_up)
        self.order_buttons_layout.addWidget(move_up_btn)

        self.order_buttons_layout.addSpacing(10)

        move_down_btn = RotatedButton("<")
        move_down_btn.setToolTip(tr("Down (hold for continuous movement)"))
        move_down_btn.pressed.connect(lambda: self.start_delay_timer(self.move_down_delay_timer))
        move_down_btn.released.connect(lambda: self.stop_timers(self.move_down_delay_timer, self.move_down_timer))
        move_down_btn.clicked.connect(self.move_addon_down)
        self.order_buttons_layout.addWidget(move_down_btn)

        move_bottom_btn = RotatedButton("|<<")
        move_bottom_btn.setToolTip(tr("To bottom"))
        move_bottom_btn.pressed.connect(lambda: self.start_delay_timer(self.move_bottom_delay_timer))
        move_bottom_btn.released.connect(lambda: self.stop_timers(self.move_bottom_delay_timer, self.move_bottom_timer))
        move_bottom_btn.clicked.connect(self.move_addon_to_bottom)
        self.order_buttons_layout.addWidget(move_bottom_btn)

    def load_addons_list(self):
        """Loads addons list from gameinfo.txt and updates table"""

        hl2vr_path = self.hl2vr_entry.text().strip()
        
        if not hl2vr_path:
            return
        
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        
        if not os.path.exists(gameinfo_path):
            return
        
        try:
            # Check markers
            marker_status = addon_manager.validate_addon_markers(gameinfo_path)
            
            if marker_status == "missing_start":
                QMessageBox.warning(self, tr("Warning"), 
                    tr("End marker of addons block (//mounted_addons_end) found, but start marker is missing!\n\n"
                    "Remove the addons list with marker from gameinfo.txt, or add //mounted_addons_start to the beginning of the list."))
                return
            elif marker_status == "missing_end":
                QMessageBox.warning(self, tr("Warning"), 
                    tr("Start marker of addons block (//mounted_addons_start) found, but end marker is missing!\n\n"
                    "Remove the addons list with marker from gameinfo.txt, or add //mounted_addons_end to the end of addons list in gameinfo.txt."))
                return
            
            elif marker_status == "no_markers":
                # Add markers if missing
                success, message = addon_manager.add_addon_markers(
                    gameinfo_path,
                    hl2vr_path,  # or self.hl2vr_entry.text().strip()
                    self.hl2_entry.text().strip()
                )

            self.current_addons = addon_manager.read_addons_from_gameinfo(gameinfo_path)
            self.update_addons_table()
                
            self.update_toggle_button_state()
        
        except Exception as e:
            QMessageBox.critical(self, tr("Error"), f"Error loading addons list:\n{str(e)}")

    def save_addons_list(self):
        """Saves current addons list to file"""
        if not self.current_addons:
            QMessageBox.information(self, tr("Information"), tr("No addons to save."))
            return
        
        # Prompt user to select save file
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            tr("Save addons list"), 
            "", 
            "Text files (*.txt)"
        )
        
        if not file_path:
            return
        
        try:
            log.info(tr("Saving addons list to file: ") + file_path)
            
            # Form file content
            content = "HL2VR_addons_list_save\n"
            
            # Add each addon in gameinfo.txt format
            for addon in self.current_addons:
                content += f"\t\t// {addon['title']}\n"
                content += f'\t\tgame+mod\t\t"{addon["path"]}"\n'
                content += "\n"
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            
            log.info(tr("List of {} addons successfully saved").format(len(self.current_addons)))
            QMessageBox.information(self, tr("Success"), tr("Addons list successfully saved!"))
            
        except Exception as e:
            log.error(f"Error saving addons list: {str(e)}")
            QMessageBox.critical(self, tr("Error"), f"Failed to save file:\n{str(e)}")

    def load_addons_list_from_file(self):
        """Loads addons list from file and replaces current one"""
        hl2vr_path = self.hl2vr_entry.text().strip()
        
        if not hl2vr_path:
            QMessageBox.critical(self, tr("Error"), tr("Specify Half-Life 2 VR path"))
            return
        
        # Prompt user to select file
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            tr("Load addons list"), 
            "", 
            "Text files (*.txt)"
        )
        
        if not file_path:
            return
        
        try:
            log.info(tr("Loading addons list from file: ") + file_path)
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Check file validity
            if not content.startswith("HL2VR_addons_list_save"):
                QMessageBox.critical(self, tr("Error"), 
                                tr("File is not a valid addons list save."))
                return
            
            # Confirm replacement
            reply = QMessageBox.question(
                self, 
                tr("Confirmation"), 
                tr("Current addons list will be completely replaced. Continue?"),
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Remove first line with marker
            lines = content.split('\n')[1:]
            addons_content = '\n'.join(lines)
            
            # Get path to gameinfo.txt
            gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
            
            if not os.path.exists(gameinfo_path):
                QMessageBox.critical(self, tr("Error"), tr("gameinfo.txt not found"))
                return
            
            # Check markers in gameinfo.txt
            marker_status = addon_manager.validate_addon_markers(gameinfo_path)
            
            if marker_status == "missing_start":
                QMessageBox.critical(self, tr("Error"), 
                    tr("End marker of addons block (//mounted_addons_end) found, but start marker is missing!\n\n"
                    "Remove the addons list with marker from gameinfo.txt, or add //mounted_addons_start to the beginning of the list."))
                return
            elif marker_status == "missing_end":
                QMessageBox.critical(self, tr("Error"), 
                    tr("Start marker of addons block (//mounted_addons_start) found, but end marker is missing!\n\n"
                    "Remove the addons list with marker from gameinfo.txt, or add //mounted_addons_end to the end of addons list in gameinfo.txt."))
                return
            elif marker_status == "no_markers":
                # Add markers if missing
                success, message = addon_manager.add_addon_markers(
                    gameinfo_path,
                    hl2vr_path,
                    self.hl2_entry.text().strip()
                )
                if not success:
                    QMessageBox.critical(self, tr("Error"), 
                                    tr("Failed to add markers to gameinfo.txt: ") + message)
                    return
            
            # Read current gameinfo.txt
            with open(gameinfo_path, 'r', encoding='utf-8') as file:
                gameinfo_content = file.read()
            
            # Find marker positions
            start_index = gameinfo_content.find("//mounted_addons_start")
            end_index = gameinfo_content.find("//mounted_addons_end")
            
            if start_index == -1 or end_index == -1:
                QMessageBox.critical(self, tr("Error"), tr("Failed to find addons block markers in gameinfo.txt"))
                return
            
            # Replace block between markers
            end_index += len("//mounted_addons_end")
            
            new_content = (
                gameinfo_content[:start_index] + 
                "//mounted_addons_start\n" + 
                addons_content + 
                "\t\t//mounted_addons_end" + 
                gameinfo_content[end_index:]
            )
            
            # Save updated gameinfo.txt
            with open(gameinfo_path, 'w', encoding='utf-8') as file:
                file.write(new_content)
            
            # Update addons list in interface
            self.load_addons_list()
            
            # Sync with episodes
            if self.embed_episodes_checkbox.isChecked():
                sync_success, sync_message = self.sync_episodes_with_main()
                if not sync_success:
                    QMessageBox.warning(self, tr("Warning"), 
                                    tr("List loaded, but failed to sync with episodes: ") + sync_message)
            
            log.info(tr("Addons list successfully loaded from file"))
            QMessageBox.information(self, tr("Success"), tr("Addons list successfully loaded!"))
            
        except Exception as e:
            log.error(f"Error loading addons list: {str(e)}")
            QMessageBox.critical(self, tr("Error"), tr("Failed to load addons list:\n") + str(e))

    def update_episodes_checkbox_availability(self, force_enable=False):
        """Updates episode mounting checkbox availability and status text"""
        hl2vr_path = self.hl2vr_entry.text().strip()
        episodes_status = self.check_episodes_availability(hl2vr_path)
        
        if not episodes_status['any_available']:
            # Episodes not found - disable and uncheck
            self.embed_episodes_checkbox.setChecked(False)
            self.embed_episodes_checkbox.setEnabled(False)
            self.sync_list_btn.setEnabled(False)  # ADD: disable sync button
            self.episodes_status_label.setText(tr("Episodes not installed"))
        else:
            # At least one episode found - enable
            self.embed_episodes_checkbox.setEnabled(True)
            self.sync_list_btn.setEnabled(True)
            
            # If force enable (when changing path via dialog) and episodes are available
            if force_enable:
                self.embed_episodes_checkbox.setChecked(True)
            
            # Update status text
            if episodes_status['ep1_available'] and episodes_status['ep2_available']:
                self.episodes_status_label.setText(tr("Both Episodes installed"))
            elif episodes_status['ep1_available']:
                self.episodes_status_label.setText(tr("Only Episode 1 installed"))
            else:
                self.episodes_status_label.setText(tr("Only Episode 2 installed"))

    def check_episodes_availability(self, hl2vr_path):
        if not hl2vr_path or not os.path.exists(hl2vr_path):
            return {
                'ep1_available': False,
                'ep2_available': False,
                'any_available': False
            }
        
        ep1_path = os.path.join(hl2vr_path, "episodicvr", "gameinfo.txt")
        ep2_path = os.path.join(hl2vr_path, "ep2vr", "gameinfo.txt")
        
        ep1_available = os.path.exists(ep1_path)
        ep2_available = os.path.exists(ep2_path)
        
        return {
            'ep1_available': ep1_available,
            'ep2_available': ep2_available,
            'any_available': ep1_available or ep2_available
        }
    


    # === ADDON MOUNTING ===



    def embed_collection(self):
        collection_url = self.url_entry.text().strip()
        self.embed_addons(collection_url, is_collection=True)

    def embed_single_addon(self):
        addon_url = self.single_addon_entry.text().strip()
        self.embed_addons(addon_url, is_collection=False)

    def embed_installed_addons(self):
        hl2vr_path = self.hl2vr_entry.text().strip()
        hl2_path = self.hl2_entry.text().strip()
        
        # Check paths
        success, error_message = path_utils.validate_paths(hl2vr_path, hl2_path)
        if not success:
            QMessageBox.critical(self, tr("Error"), error_message)
            return
        
        # Immediately disable button
        self.embed_installed_btn.setEnabled(False)
        self.status_label.setText(tr("Preparing data..."))
        
        # Get file check checkbox state
        check_files = self.check_files_checkbox.isChecked()
        
        # Start worker in PREPARATION mode (only data collection)
        self.preparation_worker = WorkshopTxtWorker(
            hl2vr_path, 
            hl2_path, 
            check_files, 
            execute=False  # Only preparation, not execution
        )
        self.preparation_worker.prepared.connect(self.on_workshop_txt_prepared)
        self.preparation_worker.progress.connect(self.status_label.setText)
        self.preparation_worker.start()

    def embed_addons(self, url, is_collection=True):
        """Main function for mounting addons (collections or single) - NEW VERSION"""
        hl2vr_path = self.hl2vr_entry.text().strip()
        hl2_path = self.hl2_entry.text().strip()
        
        # Check paths
        success, error_message = path_utils.validate_paths(hl2vr_path, hl2_path)
        if not success:
            QMessageBox.critical(self, tr("Error"), error_message)
            return
        
        if not url:
            url_type = tr("collection") if is_collection else tr("addon")
            QMessageBox.critical(self, tr("Error"), tr("Enter Steam Workshop URL for {}").format(url_type))
            return
        
        # Check URL validity
        expected_type = 'collection' if is_collection else 'addon'
        is_valid, error_message = workshop.validate_workshop_url(url, expected_type)
        if not is_valid:
            QMessageBox.critical(self, tr("Error"), error_message)
            return
        
        # Disable corresponding button
        if is_collection:
            self.embed_collection_btn.setEnabled(False)
        else:
            self.embed_single_btn.setEnabled(False)
            
        self.status_label.setText(tr("Preparing data..."))
        
        # Get file check checkbox state
        check_files = self.check_files_checkbox.isChecked()
        
        # Start worker in PREPARATION mode
        self.preparation_worker = AddonWorker(
            url, hl2vr_path, hl2_path, is_collection, check_files, execute=False
        )
        self.preparation_worker.prepared.connect(lambda success, data, error: 
            self.on_addon_prepared(success, data, error, is_collection))
        self.preparation_worker.progress.connect(self.status_label.setText)
        self.preparation_worker.start()


    # === PREPARATION AND EXECUTION ===



    def on_addon_prepared(self, success, data, error_message, is_collection):
        """Handler for completion of data preparation for collections/single addons"""
        # Enable buttons temporarily for dialog display
        self.embed_collection_btn.setEnabled(True)
        self.embed_single_btn.setEnabled(True)
        self.embed_installed_btn.setEnabled(True)
        
        if not success:
            self.status_label.setText(tr("❌ Error preparing data"))
            log.error(tr("Error preparing data: ") + error_message)
            
            # If file check is enabled and all addons are missing, show simple message
            if self.check_files_checkbox.isChecked() and tr("missing in workshop folder") in error_message:
                return
            QMessageBox.critical(self, tr("Error"), error_message)
            return
        
        # Check if there are any addons to mount
        if not data['unique_addons']:
            # If all addons are missing
            if data.get('missing_addons'):
                log.warning(tr("All addons missing in workshop folder"))
                return
            # If all addons are already in the list
            elif data['duplicates']:
                log.info(tr("All addons already mounted (duplicates)"))
                return
            else:
                return
        
        # For single addons use simple dialog (only one addon)
        if not is_collection and len(data['unique_addons']) == 1:
            addon_title = data['unique_addons'][0][1]
            reply = QMessageBox.question(self, tr("Addon Mount Confirmation"), 
                                        tr("Addon to mount:\n\n{}").format(addon_title), 
                                        QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                self.status_label.setText(tr("Operation cancelled"))
                log.info(tr("Addon mounting cancelled by user"))
                return
            
            # Immediately start execution for single addon
            self.start_addon_execution(data, is_collection)
            
        else:
            # For collections use custom dialog
            summary = tr("{} addons will be mounted").format(len(data['unique_addons']))
            
            addons_list = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(data['unique_addons'])])
            
            duplicates_list = ""
            if data['duplicates']:
                duplicates_list = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(data['duplicates'])])
            
            missing_list = ""
            if data.get('missing_addons'):
                missing_list = "\n".join([f"{i+1}. {title}" for i, (_, title, _) in enumerate(data['missing_addons'])])
            
            dialog = ConfirmAddonsDialog(
                parent=self,
                title=tr("Addon Mount Confirmation"),
                summary=summary,
                addons_list=addons_list,
                duplicates_list=duplicates_list,
                missing_list=missing_list
            )
            
            result = dialog.exec_()
            
            if result != QDialog.Accepted:
                self.status_label.setText(tr("Operation cancelled"))
                log.info(tr("Collection mounting cancelled by user"))
                return
            
            # Start execution
            self.start_addon_execution(data, is_collection)

    def start_addon_execution(self, data, is_collection):
        """Starts mounting execution after confirmation"""
        # Disable corresponding button
        if is_collection:
            self.embed_collection_btn.setEnabled(False)
        else:
            self.embed_single_btn.setEnabled(False)
            
        self.status_label.setText(tr("Mounting addons..."))
        
        # Get hl2vr_path from gameinfo_path
        hl2vr_path = data['gameinfo_path'].replace("/hlvr/gameinfo.txt", "").replace("\\hlvr\\gameinfo.txt", "")
        
        # Define source_type explicitly
        source_type = 'collection' if is_collection else 'single'
        
        url_type = tr("collection") if is_collection else tr("addon")
        log.info(tr("Starting {} mounting execution: {} addons").format(url_type, len(data['unique_addons'])))
        
        # Start worker in EXECUTION mode
        self.execution_worker = AddonWorker(
            "",  # URL not needed for execution
            hl2vr_path,
            self.hl2_entry.text().strip(),
            is_collection,
            self.check_files_checkbox.isChecked(),
            execute=True,
            prepared_data=data
        )

        self.execution_worker.progress.connect(self.status_label.setText)
        self.execution_worker.finished.connect(
            lambda success, message: 
            self.on_execution_finished(success, message, source_type, is_collection)
        )
        self.execution_worker.start()

    def on_workshop_txt_prepared(self, success, data, error_message):
        """Handler for completion of data preparation"""
        # Enable button temporarily for dialog display
        self.embed_installed_btn.setEnabled(True)
        
        if not success:
            # Handle preparation error
            self.status_label.setText(tr("❌ Error preparing data"))
            log.error(tr("Error preparing data from workshop.txt: ") + error_message)
            QMessageBox.critical(self, tr("Error"), error_message)
            return
        
        # Check if there are any addons to mount
        if not data['unique_addons']:
            log.info(tr("No addons to mount from workshop.txt"))
            return
        
        
        # Show confirmation with custom dialog
        summary = tr("{} addons will be mounted").format(len(data['unique_addons']))

        addons_list = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(data['unique_addons'])])

        duplicates_list = ""
        if data['duplicates']:
            duplicates_list = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(data['duplicates'])])

        missing_list = ""
        if data.get('missing_addons'):
            missing_list = "\n".join([f"{i+1}. {title}" for i, (_, title, _) in enumerate(data['missing_addons'])])

        failed_list = ""
        if data.get('failed_addons'):
            failed_list = "\n".join([f"{i+1}. ID: {addon_id}" for i, addon_id in enumerate(data['failed_addons'])])
        
        # Create custom dialog
        dialog = ConfirmAddonsDialog(
            parent=self,
            title=tr("Addon mount confirmation"),
            summary=summary,
            addons_list=addons_list,
            duplicates_list=duplicates_list,
            missing_list=missing_list,
            failed_list=failed_list
        )
        
        result = dialog.exec_()
        
        if result != QDialog.Accepted:
            self.status_label.setText(tr("Operation cancelled"))
            log.info(tr("Addons mounting from workshop.txt cancelled by user"))
            return
        
        log.info(tr("Starting addons mounting execution from workshop.txt"))
        
        # Disable button again and start EXECUTION
        self.embed_installed_btn.setEnabled(False)
        self.status_label.setText(tr("Mounting addons..."))
        
        # Start worker in EXECUTION mode with prepared data
        self.execution_worker = WorkshopTxtWorker(
            data['gameinfo_path'].replace("/hlvr/gameinfo.txt", ""),  # Get hl2vr_path from gameinfo_path
            self.hl2_entry.text().strip(),
            self.check_files_checkbox.isChecked(),
            execute=True,  # Execution mode
            prepared_data=data  # Pass prepared data
        )
        self.execution_worker.progress.connect(self.status_label.setText)
        self.execution_worker.finished.connect(
            lambda success, message: 
            self.on_execution_finished(success, message, 'workshop_txt', True)
        )
        self.execution_worker.start()

    def on_execution_finished(self, success, message, source_type=None, is_collection=None):
        """
        Universal handler for completion of addons mounting execution
        """
        # Enable all buttons
        self.embed_collection_btn.setEnabled(True)
        self.embed_single_btn.setEnabled(True)
        self.embed_installed_btn.setEnabled(True)

        if success:
            # Determine operation type for logs
            operation_type = ""
            if source_type == 'single':
                operation_type = tr("single addon")
            elif source_type == 'collection':
                operation_type = tr("collection")
            elif source_type == 'workshop_txt':
                operation_type = tr("addons from workshop.txt")
            else:
                operation_type = tr("addons")
            
            log.info(tr("Mounting of {} completed").format(operation_type))
            
            # Show success message for all operation types
            QMessageBox.information(self, tr("Success"), message)
            
            self.load_addons_list()

            # Sync with episodes
            self.sync_episodes_with_main()

            # Automatic map check if enabled
            if self.auto_check_maps_checkbox.isChecked():
                # Determine number of new addons to check
                new_addons_count = None
                
                # For single addons - always check 1 addon
                if source_type == 'single':
                    new_addons_count = 1
                # For collections and workshop.txt - extract count from message
                elif source_type in ['collection', 'workshop_txt']:
                    # Try different message formats
                    match = re.search(tr('Added {} addons').format(r'(\d+)'), message)
                    if not match:
                        match = re.search(tr('{} addons').format(r'(\d+)'), message)
                    if not match:
                        match = re.search(tr('addons: {}').format(r'(\d+)'), message)
                    
                    if match:
                        new_addons_count = int(match.group(1))
                
                # For backward compatibility with old calls
                elif is_collection is not None:
                    if is_collection:
                        match = re.search(tr('Added {} addons').format(r'(\d+)'), message)
                        if match:
                            new_addons_count = int(match.group(1))
                    else:
                        new_addons_count = 1
                
                # Start map check if count determined
                if new_addons_count is not None:
                    self.check_maps(new_addons_count)
                else:
                    log.info(tr("Failed to determine number of new addons for check"))
            else:
                log.info(tr("Auto map check disabled in settings"))         
        else:
            self.status_label.setText(tr("❌ Error adding addons"))
            log.error(tr("Error during mounting execution: ") + message)
            QMessageBox.critical(self, tr("Error"), message)



    # === REMOVING ADDONS ===



    def remove_selected_addons(self):
        """Removes selected addons (checked with checkboxes)"""
        hl2vr_path = self.hl2vr_entry.text().strip()
        
        if not hl2vr_path:
            QMessageBox.critical(self, tr("Error"), tr("First select Half-Life 2 VR folder"))
            return
        
        # Get checked addons
        checked_addons = self.get_checked_addons()
        if not checked_addons:
            QMessageBox.information(self, tr("Information"), 
                tr("Check addons to remove."))
            return
        
        # Collect IDs of selected addons
        addon_ids = [addon_id for addon_id, _ in checked_addons]
        addon_names = [addon_name for _, addon_name in checked_addons]
        
        log.info(tr("Preparing removal of {} selected addons").format(len(addon_ids)))
        
        addon_names_text = "\n".join([f"{i+1}. {name}" for i, name in enumerate(addon_names)])
        
        # Use custom dialog for removal confirmation
        dialog = ConfirmAddonsDialog(
            parent=self,
            title=tr("Remove addons confirmation"),
            summary=tr("Do you really want to remove the following {} addons?").format(len(addon_ids)),
            addons_list=addon_names_text,
            dialog_type="remove"
        )
        
        result = dialog.exec_()
        
        if result != QDialog.Accepted:
            log.info(tr("Addons removal cancelled by user"))
            return
        
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        
        success, message = addon_manager.remove_addons_from_gameinfo(gameinfo_path, addon_ids)
        
        if success:
            # SYNC REMOVAL WITH EPISODES
            sync_success, sync_message = self.sync_episodes_with_main()
            
            main_message = tr("Addons successfully removed!")
            if not sync_success:
                main_message += tr("\nWarning: ") + sync_message
            
            log.info(tr("Successfully removed {} addons").format(len(addon_ids)))
            QMessageBox.information(self, tr("Success"), main_message)
            self.load_addons_list()
        else:
            log.error(tr("Error removing addons: ") + message)
            QMessageBox.critical(self, tr("Error"), message)
    
    def remove_all_addons(self):
        """Removes all addons"""
        hl2vr_path = self.hl2vr_entry.text().strip()
        
        if not hl2vr_path:
            QMessageBox.critical(self, tr("Error"), tr("First select Half-Life 2 VR folder"))
            return
        
        if not self.current_addons:
            QMessageBox.information(self, tr("Information"), tr("No addons to remove."))
            return
        
        log.info(tr("Preparing removal of all {} addons").format(len(self.current_addons)))
        
        reply = QMessageBox.question(self, tr("Remove all confirmation"),
            tr("Do you really want to remove ALL {} addons?").format(len(self.current_addons)),
            QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            self.status_label.setText(tr("Ready"))
            log.info(tr("Removal of all addons cancelled by user"))
            return
        
        # Get IDs of all addons
        all_addon_ids = [addon['id'] for addon in self.current_addons]
        
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        
        success, message = addon_manager.remove_addons_from_gameinfo(gameinfo_path, all_addon_ids)
        
        if success:
            # SYNC REMOVAL WITH EPISODES
            sync_success, sync_message = self.sync_episodes_with_main()
            
            main_message = tr("All addons successfully removed!")
            if not sync_success:
                main_message += tr("\nWarning: ") + sync_message
            
            log.info(tr("Successfully removed all {} addons").format(len(self.current_addons)))
            QMessageBox.information(self, tr("Success"), main_message)
            self.load_addons_list()
        else:
            log.error(tr("Error removing all addons: ") + message)
            QMessageBox.critical(self, tr("Error"), message)



    # === CHECKS ===



    def check_addons_files(self):
        """Checks addon files existence and offers to remove missing ones"""
        hl2vr_path = self.hl2vr_entry.text().strip()
        
        if not hl2vr_path:
            QMessageBox.critical(self, tr("Error"), tr("First select Half-Life 2 VR folder"))
            return
        
        if not self.current_addons:
            QMessageBox.information(self, tr("Information"), tr("No addons to check."))
            return
        
        log.info(tr("Checking files..."))
        
        # Check files existence
        missing_addons = []
        for addon in self.current_addons:
            if not os.path.exists(addon['path']):
                missing_addons.append(addon)
        
        if not missing_addons:
            log.info(tr("All addon files are present"))
            QMessageBox.information(self, tr("Files checked"), tr("All addons are installed."))
            return
        
        log.warning(tr("Found {} addons with missing files").format(len(missing_addons)))
        
        # Form list of missing addons
        missing_list = "\n".join([f"{i+1}. {addon['title']}" for i, addon in enumerate(missing_addons)])
        
        # Use custom dialog for file check
        dialog = ConfirmAddonsDialog(
            parent=self,
            title=tr("Missing Addons Found"),
            summary=tr("Found {} addons with missing files. Remove them from the list?").format(len(missing_addons)),
            addons_list=missing_list,
            dialog_type="check"
        )
        
        result = dialog.exec_()
        
        if result != QDialog.Accepted:
            self.status_label.setText(tr("Ready"))
            log.info(tr("Removal of missing addons cancelled by user"))
            return
        
        # Remove missing addons
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        addon_ids = [addon['id'] for addon in missing_addons]
        
        success, message = addon_manager.remove_addons_from_gameinfo(gameinfo_path, addon_ids)
        
        if success:
            # SYNC REMOVAL WITH EPISODES
            sync_success, sync_message = self.sync_episodes_with_main()
            
            main_message = tr("Addons with missing files removed!")
            if not sync_success:
                main_message += tr("\nWarning: ") + sync_message
            
            log.info(tr("Removed {} addons with missing files").format(len(missing_addons)))
            QMessageBox.information(self, tr("Success"), main_message)
            self.load_addons_list()  # Update list
        else:
            log.error(tr("Error removing missing addons: ") + message)
            QMessageBox.critical(self, tr("Error"), message)

    def check_maps(self, new_addons_count=None, specific_addon=None):
        """
        Universal map checking function
        """
        hl2vr_path = self.hl2vr_entry.text().strip()
        
        if not hl2vr_path:
            QMessageBox.critical(self, tr("Error"), tr("Select Half-Life 2 VR folder"))
            return
        
        if not self.current_addons:
            QMessageBox.information(self, tr("Information"), tr("No addons to check."))
            return
        
        # DETERMINE WHICH ADDONS TO CHECK
        if specific_addon:
            addons_to_check = [specific_addon]
            check_type = "single"
            log.info(tr("Checking map for addon: {}").format(specific_addon['title']))
        elif new_addons_count is not None:
            addons_to_check = self.current_addons[:new_addons_count]
            check_type = "auto"
            log.info(tr("Auto map check for {} new addons").format(new_addons_count))
        else:
            addons_to_check = self.current_addons
            check_type = "manual"
            log.info(tr("Manual map check for {} addons").format(len(addons_to_check)))
        
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        
        # ADD PROGRESS BAR FOR MAP CHECKING
        progress = None
        if check_type in ["manual", "auto"] and len(addons_to_check) > 1:
            progress = QProgressDialog(tr("Checking addons for maps..."), tr("Cancel"), 0, len(addons_to_check), self)
            progress.setWindowTitle(tr("Map check"))
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowFlags(progress.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            progress.show()

            progress.setFixedSize(600, 100)
            
            progress.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

            progress.setWindowFlags(progress.windowFlags() | Qt.MSWindowsFixedSizeDialogHint)

        # MULTITHREADED MAP CHECKING
        map_addons = []
        maps_to_extract = []
        maps_already_extracted = []
        needs_path_update = False
        
        # Function to check single addon
        def check_single_addon(addon):
            """Checks single addon for map presence"""
            try:
                addon_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={addon['id']}"
                is_map = workshop.is_addon_map(addon_url)
                
                if not is_map:
                    return None
                    
                # If it's a map, check local files
                current_path = addon['path']
                current_title = addon['title']
                
                # Determine corresponding VPK and folder paths
                vpk_path = None
                folder_path = None
                
                if current_path.endswith('.vpk'):
                    vpk_path = current_path
                    folder_path = current_path.replace('workshop_dir.vpk', 'workshop_dir')
                elif current_path.endswith('workshop_dir'):
                    vpk_path = current_path + '.vpk'
                    folder_path = current_path
                
                # Check files existence
                vpk_exists = vpk_path and os.path.exists(vpk_path)
                
                # Check not only folder existence but also its contents
                folder_exists = False
                if folder_path and os.path.exists(folder_path):
                    try:
                        folder_contents = os.listdir(folder_path)
                        folder_exists = len(folder_contents) > 0
                    except:
                        folder_exists = False
                
                # Determine if paths and titles need updating
                should_have_folder_path = folder_exists or not vpk_exists
                should_have_map_prefix = not current_title.startswith("MAP   |   ")
                
                needs_update_for_this_addon = False
                
                if should_have_folder_path and current_path != folder_path:
                    # Path should point to folder but points to VPK
                    addon['path'] = folder_path
                    needs_update_for_this_addon = True
                
                if should_have_map_prefix:
                    # Need to add MAP prefix
                    addon['title'] = "MAP   |   " + current_title
                    needs_update_for_this_addon = True
                
                return {
                    'addon': addon,
                    'vpk_exists': vpk_exists,
                    'folder_exists': folder_exists,
                    'vpk_path': vpk_path,
                    'folder_path': folder_path,
                    'needs_update': needs_update_for_this_addon
                }
                
            except Exception as e:
                log.error(tr("Error checking addon {}: {}").format(addon['title'], str(e)))
                return None
        
        # Use ThreadPoolExecutor for parallel checking
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Start all tasks
            future_to_addon = {executor.submit(check_single_addon, addon): addon for addon in addons_to_check}
            
            # Process results as they complete
            for i, future in enumerate(concurrent.futures.as_completed(future_to_addon), 1):
                addon = future_to_addon[future]
                
                # Update progress bar if exists
                if progress:
                    progress.setValue(i)
                    progress.setLabelText(tr("Checking addon {} of {}: {}").format(i, len(addons_to_check), addon['title']))
                    QApplication.processEvents()
                    
                    if progress.wasCanceled():
                        progress.close()
                        log.info(tr("Map check cancelled by user"))
                        return
                
                try:
                    result = future.result()
                    if result is None:
                        continue  # Not a map
                    
                    map_addons.append(result['addon'])
                    
                    # Determine if extraction needed
                    if result['vpk_exists'] and not result['folder_exists']:
                        maps_to_extract.append(result['addon'])
                    elif result['folder_exists'] or not result['vpk_exists']:
                        maps_already_extracted.append(result['addon'])
                    
                    if result['needs_update']:
                        needs_path_update = True
                        
                    log.info(tr("Map found: {}").format(result['addon']['title']))
                    
                except Exception as e:
                    log.error(tr("Error processing result for {}: {}").format(addon['title'], str(e)))
        
        # Close check progress bar
        if progress:
            progress.setValue(len(addons_to_check))
            progress.close()
        
        log.info(tr("Check completed: {} maps, {} require extraction").format(len(map_addons), len(maps_to_extract)))
        
        # PROCESS CHECK RESULTS
        
        # Case 1: Automatic check after adding addons
        if check_type == "auto":
            self.handle_auto_check_result(map_addons, maps_to_extract, maps_already_extracted, 
                                        needs_path_update, gameinfo_path)
        
        # Case 2: Single addon check via context menu
        elif check_type == "single" and specific_addon:
            self.handle_single_check_result(specific_addon, map_addons, maps_to_extract, 
                                        maps_already_extracted, needs_path_update, gameinfo_path)
        
        # Case 3: Manual check of all addons
        elif check_type == "manual":
            self.handle_manual_check_result(map_addons, maps_to_extract, maps_already_extracted, 
                                        needs_path_update, gameinfo_path)

    def handle_auto_check_result(self, map_addons, maps_to_extract, maps_already_extracted, 
                            needs_path_update, gameinfo_path):
        """Handles automatic check results"""
        if needs_path_update:
            self.update_gameinfo_paths(gameinfo_path)
        
        if not map_addons:
            return

        self.sync_episodes_after_map_check()

        if maps_to_extract:
            self.show_extraction_dialog(maps_to_extract, maps_already_extracted, 
                                    tr("New map addons found"), gameinfo_path)

        elif map_addons:
            self.show_extraction_dialog([], maps_already_extracted, 
                                    tr("Check completed"), gameinfo_path)

    def handle_single_check_result(self, specific_addon, map_addons, maps_to_extract, 
                                    maps_already_extracted, needs_path_update, gameinfo_path):
        """Handles single addon check results"""
        if not map_addons:
            log.info(tr("Addon '{}' is not a map").format(specific_addon['title']))
            QMessageBox.information(self, tr("Check result"), 
                                tr("Addon '{}' is not a map.").format(specific_addon['title']))
            return
        
        if needs_path_update:
            self.update_gameinfo_paths(gameinfo_path)

        self.sync_episodes_after_map_check()
        
        if maps_to_extract:
            self.show_extraction_dialog(maps_to_extract, maps_already_extracted,
                                    tr("Map found"), gameinfo_path, is_single=True)
        else:
            self.show_extraction_dialog([], maps_already_extracted,
                                    tr("Check result"), gameinfo_path, is_single=True)

    def handle_manual_check_result(self, map_addons, maps_to_extract, maps_already_extracted, 
                                    needs_path_update, gameinfo_path):
        """Handles manual check results"""
        if not map_addons:
            log.info(tr("Manual check: maps not found"))
            self.show_extraction_dialog([], [], tr("Map check result"), gameinfo_path)
            return

        if needs_path_update:
            self.update_gameinfo_paths(gameinfo_path)

        self.sync_episodes_after_map_check()

        self.show_extraction_dialog(maps_to_extract, maps_already_extracted,
                                tr("Map check result"), gameinfo_path)

    def show_extraction_dialog(self, maps_to_extract, maps_already_extracted, title, 
                                gameinfo_path, is_single=False):
        """Shows dialog with map extraction proposal"""
        maps_list = ""
        extracted_list = ""
        
        if maps_to_extract:
            maps_list = "\n".join([f"{i+1}. {addon['title']}" for i, addon in enumerate(maps_to_extract)])
        
        if maps_already_extracted:
            extracted_list = "\n".join([f"{i+1}. {addon['title']}" for i, addon in enumerate(maps_already_extracted)])
        
        # Determine summary based on results
        total_maps = len(maps_to_extract) + len(maps_already_extracted)
        
        # Determine if extract button should be activated
        enable_extract_button = bool(maps_to_extract)  # True if there are maps to extract
        
        if maps_to_extract and maps_already_extracted:
            summary = tr("Found {} map addons:\n• {} require extraction\n• {} already extracted").format(total_maps, len(maps_to_extract), len(maps_already_extracted))
        elif maps_to_extract:
            summary = tr("Found {} map addons that require extraction.").format(len(maps_to_extract))
        elif maps_already_extracted:
            summary = tr("All {} map addons are already extracted.").format(len(maps_already_extracted))
        else:
            summary = tr("Map addons not found.")
        
        # For single addon change text
        if is_single and maps_to_extract:
            addon = maps_to_extract[0]
            summary = tr("Addon '{}' is a map but not extracted.").format(addon['title'])
        
        # Show dialog with check results
        dialog = ConfirmAddonsDialog(
            parent=self,
            title=title,
            summary=summary,
            maps_list=maps_list,
            extracted_list=extracted_list,
            dialog_type="maps",
            enable_extract_button=enable_extract_button  # Pass button state
        )
        
        result = dialog.exec_()
        
        # If there are maps to extract and user agreed
        if result == QDialog.Accepted and maps_to_extract:
            log.info(tr("Starting extraction of {} maps").format(len(maps_to_extract)))
            
            # Create progress dialog for extraction
            self.extraction_progress = QProgressDialog(tr("Preparing for extraction..."), tr("Cancel"), 0, 100, self)
            self.extraction_progress.setWindowTitle(tr("Map extraction"))
            self.extraction_progress.setWindowModality(Qt.WindowModal)
            self.extraction_progress.setWindowFlags(self.extraction_progress.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            
            self.extraction_progress.setFixedSize(600, 100)
            self.extraction_progress.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.extraction_progress.setWindowFlags(self.extraction_progress.windowFlags() | Qt.MSWindowsFixedSizeDialogHint)

            # ADD DETAILED PROGRESS DESCRIPTION
            if len(maps_to_extract) == 1:
                self.extraction_progress.setLabelText(tr("Extracting map: {}").format(maps_to_extract[0]['title']))
            else:
                self.extraction_progress.setLabelText(tr("Extracting {} maps...").format(len(maps_to_extract)))
            
            self.extraction_progress.show()
            
            # Start extraction
            self.map_extraction_worker = MapExtractionWorker(gameinfo_path, self.current_addons, 
                                                        specific_addons=maps_to_extract)
            self.map_extraction_worker.progress.connect(self.update_extraction_progress)
            self.map_extraction_worker.finished.connect(self.on_map_extraction_finished)
            
            # Connect cancellation in progress dialog with cancellation in worker
            self.extraction_progress.canceled.connect(self.map_extraction_worker.cancel)
            
            self.map_extraction_worker.start()
        else:
            log.info(tr("Map extraction not required or cancelled by user"))

    def update_gameinfo_paths(self, gameinfo_path):
        """Updates map paths and titles in gameinfo.txt"""
        addons_with_paths = [(addon['path'], addon['title']) for addon in self.current_addons]
        success, message = gameinfo.update_gameinfo_order(gameinfo_path, addons_with_paths)
        
        if success:
            # Sync with episodes
            self.sync_episodes_with_main(addons_with_paths)
            self.load_addons_list()  # Update table
            
            log.info(tr("Map paths and titles updated in gameinfo.txt"))
            return True
        else:
            log.error(tr("Error updating map paths: ") + message)
            return False

    def sync_episodes_after_map_check(self):
        """Syncs with episodes after map check"""
        hl2vr_path = self.hl2vr_entry.text().strip()
        if not hl2vr_path:
            return
        
        #gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        addons_with_paths = [(addon['path'], addon['title']) for addon in self.current_addons]
        
        self.sync_episodes_with_main(addons_with_paths)
        #if not sync_success:
            #print(f"Sync warning: {sync_message}")
                    


    # === ORDER MANAGING === 



    def move_addon_up(self):
        current_row = self.addons_table.currentRow()
        if current_row <= 0:
            return
        self.current_addons[current_row], self.current_addons[current_row - 1] = \
            self.current_addons[current_row - 1], self.current_addons[current_row]
        
        self.fast_table_update()
        self.addons_table.setCurrentCell(current_row - 1, 0)
        self.save_timer.start(300)

    def move_addon_down(self):
        current_row = self.addons_table.currentRow()
        if current_row < 0 or current_row >= len(self.current_addons) - 1:
            return
        
        self.current_addons[current_row], self.current_addons[current_row + 1] = \
            self.current_addons[current_row + 1], self.current_addons[current_row]
        
        self.fast_table_update()
        self.addons_table.setCurrentCell(current_row + 1, 0)
        self.save_timer.start(300)

    def move_addon_to_top(self):
        current_row = self.addons_table.currentRow()
        if current_row <= 0:
            return
        selected_addon = self.current_addons[current_row]
        del self.current_addons[current_row]
        self.current_addons.insert(0, selected_addon)
        self.fast_table_update()
        self.addons_table.setCurrentCell(0, 0)
        self.save_timer.start(300)

    def move_addon_to_bottom(self):
        current_row = self.addons_table.currentRow()
        if current_row < 0 or current_row >= len(self.current_addons) - 1:
            return
        selected_addon = self.current_addons[current_row]
        del self.current_addons[current_row]
        self.current_addons.append(selected_addon)
        self.fast_table_update()
        self.addons_table.setCurrentCell(len(self.current_addons) - 1, 0)
        self.save_timer.start(300)

    def save_addons_order(self):
        """Saves current addons order to gameinfo.txt"""
        if not self.current_addons:
            return
        
        hl2vr_path = self.hl2vr_entry.text().strip()
        if not hl2vr_path:
            return
        
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        
        try:
            # Form addons list in current order
            addons_with_paths = []
            for addon in self.current_addons:
                addons_with_paths.append((addon['path'], addon['title']))
            
            
            # Save new order to main gameinfo
            success, message = gameinfo.update_gameinfo_order(gameinfo_path, addons_with_paths)
            
            if success:
                # SYNC ORDER WITH EPISODES
                sync_success, sync_message = self.sync_episodes_with_main(addons_with_paths)

                if not sync_success:
                    self.status_label.setText(tr("Order updated, but: {}").format(sync_message))
                    log.warning(tr("Order saved, but episode sync failed: {}").format(sync_message))
            else:
                log.error(tr("Error saving addons order: ") + message)
                QMessageBox.critical(self, tr("Error"), tr("Error saving order: {}").format(message))
                # In case of error, reload list from file
                self.load_addons_list()
                
        except Exception as e:
            log.error(tr("Error saving addons order: ") + str(e))
            QMessageBox.critical(self, tr("Error"), tr("Error saving order: {}").format(str(e)))
            # In case of error, reload list from file
            self.load_addons_list()

    def start_delay_timer(self, delay_timer):
        delay_timer.start(300)

    def stop_timers(self, delay_timer, repeat_timer):
        delay_timer.stop()
        repeat_timer.stop()

    def start_timer(self, timer, interval):
        timer.start(interval)



    # === ТАБЛИЦА И ИНТЕРФЕЙС === 



    def update_addons_table(self):
        """Updates table from current current_addons list"""
        # Clear table
        self.addons_table.setRowCount(0)
        
        # Fill table
        for addon in self.current_addons:
            row = self.addons_table.rowCount()
            self.addons_table.insertRow(row)
            
            # Checkbox
            checkbox_item = CheckBoxTableWidgetItem(False)
            self.addons_table.setItem(row, 0, checkbox_item)
            
            # Title
            title_item = QTableWidgetItem(addon['title'])
            self.addons_table.setItem(row, 1, title_item)
            
            # Link
            link_item = QTableWidgetItem(tr("Open in Steam"))
            link_item.setForeground(QColor(0, 100, 200))
            font = link_item.font()
            font.setUnderline(True)
            link_item.setFont(font)
            self.addons_table.setItem(row, 2, link_item)
            
            # Addon folder open button
            folder_btn = QPushButton(tr("Open folder"))
            addon_folder_path = self.get_addon_folder_path(addon['path'])
            folder_btn.clicked.connect(lambda checked, path=addon_folder_path: self.open_addon_folder(path))
            self.addons_table.setCellWidget(row, 3, folder_btn)
        
        # ALWAYS APPLY SEARCH HIGHLIGHTING WHEN UPDATING TABLE
        self.highlight_matching_addons(self.search_entry.text())
        
        # Update status
        if not self.search_entry.text():
            self.status_label.setText(tr("Loaded {} addons").format(len(self.current_addons)))
        
        log.info(tr("Addons table updated"))
    
    def fast_table_update(self):
        """Fast table update without recreating all elements"""
        # Save current state
        current_row = self.addons_table.currentRow()
        scroll_pos = self.addons_table.verticalScrollBar().value()
        
        # Temporarily disable updates
        self.addons_table.setUpdatesEnabled(False)
        
        # Update only text cells
        for row, addon in enumerate(self.current_addons):
            if row < self.addons_table.rowCount():
                # Update title (column 1)
                title_item = self.addons_table.item(row, 1)
                if title_item:
                    title_item.setText(addon['title'])
                
                # Update checkbox (column 0) - preserve state
                checkbox_item = self.addons_table.item(row, 0)
                if checkbox_item:
                    # Save current checkbox state
                    current_state = checkbox_item.checkState()
                    # Here we can update other properties if needed
                
                # Update "Open folder" button (column 3)
                folder_btn = self.addons_table.cellWidget(row, 3)
                if folder_btn:
                    # Update button action with new path
                    addon_folder_path = self.get_addon_folder_path(addon['path'])
                    # Remove old connections and create new one
                    try:
                        folder_btn.clicked.disconnect()
                    except:
                        pass
                    folder_btn.clicked.connect(lambda checked, path=addon_folder_path: self.open_addon_folder(path))
        
        # Enable updates
        self.addons_table.setUpdatesEnabled(True)
        
        # Restore state
        if current_row >= 0:
            self.addons_table.setCurrentCell(current_row, 0)
        self.addons_table.verticalScrollBar().setValue(scroll_pos)
        
        # Restore search highlighting
        if self.search_entry.text():
            self.highlight_matching_addons(self.search_entry.text())

    def update_toggle_button_state(self):
        checked_addons = self.get_checked_addons()
        
        if checked_addons:
            if not self.toggle_check_btn.isChecked():
                self.toggle_check_btn.setChecked(True)
        else:
            if self.toggle_check_btn.isChecked():
                self.toggle_check_btn.setChecked(False)

    def get_checked_addons(self):
        checked_addons = []
        for row in range(self.addons_table.rowCount()):
            checkbox_item = self.addons_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.Checked:

                addon_id = self.current_addons[row]['id']
                addon_name = self.current_addons[row]['title']
                checked_addons.append((addon_id, addon_name))
        return checked_addons



    # === MANAGING CHECKBOXES ===



    def toggle_all_checks(self):
        if self.toggle_check_btn.isChecked():
            self.check_all_addons()
        else:
            self.uncheck_all_addons()

    def check_all_addons(self):
        for row in range(self.addons_table.rowCount()):
            checkbox_item = self.addons_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.Checked)

        if not self.toggle_check_btn.isChecked():
            self.toggle_check_btn.setChecked(True)
        self.toggle_check_btn.setToolTip(tr("Uncheck all"))

    def uncheck_all_addons(self):
        for row in range(self.addons_table.rowCount()):
            checkbox_item = self.addons_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.Unchecked)
        
        if self.toggle_check_btn.isChecked():
            self.toggle_check_btn.setChecked(False)

    def on_checkbox_changed(self, item):
        if item.column() == 0:
            checked_addons = self.get_checked_addons()

            if checked_addons:
                if not self.toggle_check_btn.isChecked():
                    self.toggle_check_btn.setChecked(True)
            else:
                if self.toggle_check_btn.isChecked():
                    self.toggle_check_btn.setChecked(False)



    # === SEARCH ===



    def on_search_text_changed(self, text):
        self.highlight_matching_addons(text)
        
        if text.strip():
            self.next_search_result()

    def highlight_matching_addons(self, search_text):
        search_text = search_text.lower().strip()
        match_count = 0
        
        for row in range(self.addons_table.rowCount()):
            if row >= len(self.current_addons):
                continue
                
            addon = self.current_addons[row]
            addon_title = addon['title'].lower()
            addon_id = addon['id'].lower()
            
            # Check title or ID match
            matches = search_text in addon_title or search_text in addon_id
            if matches:
                match_count += 1
    
            color = QColor(255, 255, 200) if matches and search_text else QColor(255, 255, 255)
            
            for col in range(self.addons_table.columnCount()):
                item = self.addons_table.item(row, col)
                if item:
                    item.setBackground(color)
                    
            # Also highlight "Open folder" button
            folder_btn = self.addons_table.cellWidget(row, 3)
            if folder_btn:
                # RESET BUTTON STYLE WHEN SEARCH IS EMPTY
                if matches and search_text:
                    folder_btn.setStyleSheet(f"background-color: {color.name()};")
                else:
                    folder_btn.setStyleSheet("")  # Reset style
        
        # MANAGE NAVIGATION BUTTONS
        has_matches = match_count > 0 and len(search_text) > 0
        self.prev_search_btn.setEnabled(has_matches)
        self.next_search_btn.setEnabled(has_matches)
        
        # Update status with found addons count
        # LIMIT SEARCH TEXT LENGTH IN STATUS
        if search_text and has_matches:
            # Trim long search text
            display_text = search_text[:15] + "..." if len(search_text) > 15 else search_text
            self.status_label.setText(tr("{} addons for query '{}'").format(match_count, display_text))
        elif search_text and not has_matches:
            # Trim long search text
            display_text = search_text[:15] + "..." if len(search_text) > 15 else search_text
            self.status_label.setText(tr("No addons found for query '{}'").format(display_text))
        else:
            self.status_label.setText(tr("Loaded {} addons").format(len(self.current_addons)))

    def previous_search_result(self):
        current_row = self.addons_table.currentRow()
        search_text = self.search_entry.text().lower()
        
        if not search_text:
            return

        if current_row == -1:
            current_row = self.addons_table.rowCount()

        for row in range(current_row - 1, -1, -1):
            if self.is_row_matching_search(row, search_text):
                self.addons_table.setCurrentCell(row, 0)
                self.addons_table.scrollToItem(self.addons_table.item(row, 0))
                return

        for row in range(self.addons_table.rowCount() - 1, current_row, -1):
            if self.is_row_matching_search(row, search_text):
                self.addons_table.setCurrentCell(row, 0)
                self.addons_table.scrollToItem(self.addons_table.item(row, 0))
                return

    def next_search_result(self):
        current_row = self.addons_table.currentRow()
        search_text = self.search_entry.text().lower()
        
        if not search_text:
            return

        if current_row == -1:
            current_row = -1

        for row in range(current_row + 1, self.addons_table.rowCount()):
            if self.is_row_matching_search(row, search_text):
                self.addons_table.setCurrentCell(row, 0)
                self.addons_table.scrollToItem(self.addons_table.item(row, 0))
                return

        for row in range(0, current_row + 1):
            if self.is_row_matching_search(row, search_text):
                self.addons_table.setCurrentCell(row, 0)
                self.addons_table.scrollToItem(self.addons_table.item(row, 0))
                return

    def is_row_matching_search(self, row, search_text):
        if row >= len(self.current_addons) or row < 0:
            return False
            
        addon = self.current_addons[row]
        addon_title = addon['title'].lower()
        addon_id = addon['id'].lower()
        
        return search_text in addon_title or search_text in addon_id

    def clear_search(self):
        self.search_entry.clear()

    def add_search_navigation(self):
        """Adds search results navigation buttons"""
        # In search_layout after search clear
        search_layout = self.right_panel.findChild(QHBoxLayout)
        
        self.prev_search_btn = QPushButton("←")
        self.prev_search_btn.setToolTip(tr("Previous result"))
        self.prev_search_btn.clicked.connect(self.previous_search_result)
        self.prev_search_btn.setEnabled(False)
        search_layout.addWidget(self.prev_search_btn)
        
        self.next_search_btn = QPushButton("→")
        self.next_search_btn.setToolTip(tr("Next result"))
        self.next_search_btn.clicked.connect(self.next_search_result)
        self.next_search_btn.setEnabled(False)
        search_layout.addWidget(self.next_search_btn)



    # === SYNC WITH EPISODES ===



    def sync_with_episodes(self):
        """Manual synchronization of current addons list with episodes"""
        if not self.embed_episodes_checkbox.isChecked():
            QMessageBox.information(self, tr("Information"), 
                                tr("First enable sync with Episodes."))
            return
        
        hl2vr_path = self.hl2vr_entry.text().strip()
        if not hl2vr_path:
            QMessageBox.critical(self, tr("Error"), tr("First select Half-Life 2 VR folder"))
            return
        
        if not self.current_addons:
            QMessageBox.information(self, tr("Information"), tr("No addons to sync."))
            return
        
        log.info(tr("Manual sync with episodes: {} addons").format(len(self.current_addons)))
        
        # Form addons list in current order
        addons_with_paths = []
        for addon in self.current_addons:
            addons_with_paths.append((addon['path'], addon['title']))
        
        # Sync
        success, message = self.sync_episodes_with_main(addons_with_paths)
        
        if success:
            QMessageBox.information(self, tr("Success"), message)
        else:
            log.error(tr("Error syncing with episodes: ") + message)
            QMessageBox.critical(self, tr("Error"), message)

    def sync_episodes_with_main(self, main_addons_with_paths=None):
        """Syncs addons in episodes with main gameinfo"""
        if not self.embed_episodes_checkbox.isChecked():
            return True, tr("Sync with episodes disabled")
        
        try:
            hl2vr_path = self.hl2vr_entry.text().strip()
            if not hl2vr_path:
                return False, tr("Half-Life 2 VR path not specified")
            
            # If addons list not provided, read from main gameinfo
            if main_addons_with_paths is None:
                main_gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
                current_addons = addon_manager.read_addons_from_gameinfo(main_gameinfo_path)
                main_addons_with_paths = [(addon['path'], addon['title']) for addon in current_addons]
            
            episode_paths = self.get_episode_gameinfo_paths()
            
            if not episode_paths:
                return False, tr("Episodes not installed")
            
            log.info(tr("Syncing with Episodes..."))
            
            synced_count = 0
            
            for episode_path in episode_paths:
                episode_name = os.path.basename(os.path.dirname(episode_path))
                
                # Check markers
                marker_status = addon_manager.validate_addon_markers(episode_path)
                
                if marker_status == "missing_start":
                    return False, tr("{}: End marker of addons block (//mounted_addons_end) found, but start marker is missing!\n\nRemove the addons list with marker from gameinfo.txt, or add //mounted_addons_start to the beginning of the list.").format(episode_name)
            
                elif marker_status == "missing_end":
                    return False, tr("{}: Start marker of addons block (//mounted_addons_start) found, but end marker is missing!\n\nRemove the addons list with marker from gameinfo.txt, or add //mounted_addons_end to the end of addons list in gameinfo.txt.").format(episode_name)
                elif marker_status == "no_markers":
                    # Add markers on first use
                    success, message = addon_manager.add_addon_markers(episode_path, hl2vr_path)
                    if not success:
                        return False, tr("Failed to add markers to {}: {}").format(episode_name, message)
                
                # Update addons list in episode
                success, message = gameinfo.update_gameinfo_order(episode_path, main_addons_with_paths)
                if not success:
                    return False, tr("Error syncing with {}: {}").format(episode_name, message)
                
                synced_count += 1
            
            log.info(tr("Sync completed: {} episodes updated").format(synced_count))
            return True, tr("Synced with Episodes")
        
        except Exception as e:
            log.error(tr("Error syncing with episodes: ") + str(e))
            return False, tr("Error syncing with episodes: {}").format(str(e))

    def get_episode_gameinfo_paths(self):
        hl2vr_path = self.hl2vr_entry.text().strip()
        if not hl2vr_path:
            return []
        
        episodes_status = self.check_episodes_availability(hl2vr_path)
        episode_paths = []
        
        if episodes_status['ep1_available']:
            episode_paths.append(os.path.join(hl2vr_path, "episodicvr", "gameinfo.txt"))
        if episodes_status['ep2_available']:
            episode_paths.append(os.path.join(hl2vr_path, "ep2vr", "gameinfo.txt"))
        
        return episode_paths



    # === ANNIVERSARY UPDATE ===



    def install_anniversary_update(self):
        """Installs anniversary update content"""
        hl2vr_path = self.hl2vr_entry.text().strip()
        hl2_path = self.hl2_entry.text().strip()
        
        # Check paths
        if not hl2vr_path or not hl2_path:
            QMessageBox.critical(self, tr("Error"), 
                            tr("First specify paths to Half-Life 2 VR and Half-Life 2"))
            return
        
        # User warning
        reply = QMessageBox.warning(self, tr("Warning"),
            tr("This procedure will install Anniversary Update content into Half-Life 2: VR Mod and Episodes.\n\n"
            "⚠️ WARNING:\n"
            "• Current addons list will be cleared\n"
            "• Some game files will be modified\n"
            "• Current game saves will stop working\n"
            "• Instructions for returning to the original version are in the Help section\n\n"
            "Continue?"),
            QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            self.status_label.setText(tr("Operation cancelled"))
            log.info(tr("Anniversary Update installation cancelled by user"))
            return
        
        try:
            from anniversary_update import install_anniversary_update
            
            # Disable button during execution
            self.anniversary_btn.setEnabled(False)
            self.status_label.setText(tr("Installing anniversary update content..."))
            
            # Start installation
            success, message = install_anniversary_update(hl2vr_path, hl2_path)
            
            if success:
                QMessageBox.information(self, tr("Success"), message)
                
                # Update addons list (it will be empty)
                self.load_addons_list()
            else:
                log.error(tr("Error installing Anniversary Update: ") + message)
                self.status_label.setText(tr("❌ Error during installation"))
                QMessageBox.critical(self, tr("Error"), message)
                
        except ImportError as e:
            log.error(tr("Error importing anniversary_update module: ") + str(e))
            QMessageBox.critical(self, tr("Error"), 
                            tr("Failed to load anniversary_update module: {}").format(e))
        except Exception as e:
            log.error(tr("Unexpected error during Anniversary Update installation: ") + str(e))
            QMessageBox.critical(self, tr("Error"), 
                            tr("An unexpected error occurred: {}").format(e))
        finally:
            self.anniversary_btn.setEnabled(True)



    # === CHANGE HANDLERS ===



    def on_hl2vr_path_changed(self):
        self.update_episodes_checkbox_availability(force_enable=False)
        self.save_config()

    def on_url_change(self):
        self.save_config()

    def on_check_files_changed(self, state):
        self.save_config()

    def on_auto_check_maps_changed(self, state):
        self.save_config()

    def on_embed_episodes_changed(self, state):
        self.save_config()



    # === CLICK HANDLERS ===



    def on_table_cell_clicked(self, row, column):
        if column == 2:
            if row < len(self.current_addons):
                addon_id = self.current_addons[row]['id']
                if addon_id != tr("Unknown"):
                    
                    url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={addon_id}"
                    webbrowser.open(url)

    def select_folder(self, entry_widget, title):
        folder = QFileDialog.getExistingDirectory(self, title)
        if folder:
            entry_widget.setText(folder)
            self.save_config()
            
            if entry_widget == self.hl2vr_entry:
                self.load_addons_list()
                self.update_episodes_checkbox_availability(force_enable=True)

    def open_addon_folder(self, folder_path):
        """Opens addon folder in Windows Explorer"""
        try:
            
            
            # For all addons get addon folder (parent folder)
            # If path points to workshop_dir.vpk or workshop_dir, take parent folder
            if folder_path.endswith('workshop_dir.vpk') or folder_path.endswith('workshop_dir'):
                folder_dir = os.path.dirname(folder_path)
            else:
                # If path already points to addon folder, use it
                folder_dir = folder_path
            
            if os.path.exists(folder_dir):
                # Open addon folder in Windows Explorer
                subprocess.Popen(f'explorer "{folder_dir}"')
            else:
                # Try to find folder by addon ID
                addon_id = None
                for addon in self.current_addons:
                    if addon['path'] == folder_path:
                        addon_id = addon['id']
                        break
                
                if addon_id:
                    # Try to find folder in workshop by ID
                    hl2_path = self.hl2_entry.text().strip()
                    if hl2_path:
                        from path_utils import get_workshop_path
                        workshop_path = get_workshop_path(hl2_path)
                        alternative_path = os.path.join(workshop_path, addon_id)
                        
                        if os.path.exists(alternative_path):
                            subprocess.Popen(f'explorer "{alternative_path}"')
                            return
                
                QMessageBox.warning(self, tr("Error"), tr("Addon folder not found:\n{}").format(folder_dir))
                
        except Exception as e:
            QMessageBox.critical(self, tr("Error"), tr("Failed to open addon folder:\n{}").format(str(e)))



    # === MAP HANDLING ===



    def clear_extracted_maps(self):
        """Clears all extracted maps and returns paths to .vpk"""
        hl2vr_path = self.hl2vr_entry.text().strip()
        hl2_path = self.hl2_entry.text().strip()
        
        if not hl2vr_path or not hl2_path:
            QMessageBox.critical(self, tr("Error"), tr("First select Half-Life 2 VR and Half-Life 2 folders"))
            return
        
        # Confirmation request
        reply = QMessageBox.question(
            self, 
            tr("Clear Confirmation"), 
            tr("This action will delete all extracted map addon folders.\n\n"
            "Continue?"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            log.info(tr("Extracted maps clearing cancelled by user"))
            return
        
        try:
            log.info(tr("Starting extracted maps clearing..."))
            
            from path_utils import get_workshop_path
            workshop_path = get_workshop_path(hl2_path)
            gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
            
            if not workshop_path or not os.path.exists(workshop_path):
                log.error(tr("Failed to find workshop folder"))
                QMessageBox.critical(self, tr("Error"), tr("Failed to find workshop folder"))
                return
            
            if not os.path.exists(gameinfo_path):
                log.error(tr("gameinfo.txt not found"))
                QMessageBox.critical(self, tr("Error"), tr("gameinfo.txt not found"))
                return
            
            # Call clear function
            success, message = addon_manager.clear_extracted_maps(workshop_path, gameinfo_path)
            
            if success:
                # Sync with episodes
                sync_success, sync_message = self.sync_episodes_with_main()
                
                main_message = tr("Maps cleared!\n{}").format(message)
                if not sync_success:
                    log.warning(tr("Episode sync failed: {}").format(sync_message))
                    main_message += tr("\nWarning: {}").format(sync_message)
                
                QMessageBox.information(self, tr("Success"), main_message)
                
                # Update addons list
                self.load_addons_list()
            else:
                log.error(tr("Error clearing maps: ") + message)
                QMessageBox.critical(self, tr("Error"), message)
                    
        except Exception as e:
            log.error(tr("Unexpected error clearing maps: ") + str(e))
            QMessageBox.critical(self, tr("Error"), tr("An unexpected error occurred:\n{}").format(str(e)))

    def update_extraction_progress(self, current_map, total_maps, current_file, total_files, status):
        if total_files > 0:
            file_percent = int((current_file / total_files) * 100)

            overall_percent = int(((current_map - 1) / total_maps) * 100 + (file_percent / total_maps))
            self.extraction_progress.setValue(overall_percent)
            self.extraction_progress.setLabelText(tr("Map {}/{}: {}").format(current_map, total_maps, status))
        else:
            percent = int((current_map / total_maps) * 100)
            self.extraction_progress.setValue(percent)
            self.extraction_progress.setLabelText(status)
        
        QApplication.processEvents()

    def on_map_extraction_finished(self, success, result):
        """Handler for map extraction completion"""
        # Close progress dialog
        if hasattr(self, 'extraction_progress'):
            self.extraction_progress.close()
        
        # Check if cancellation occurred
        if isinstance(result, dict) and result.get('cancelled'):
            log.info(tr("Map extraction cancelled by user"))
            return
        
        if not success:
            # If general error occurred (not related to specific maps)
            if isinstance(result, str):
                log.error(tr("General error during map extraction: {}").format(result))
                QMessageBox.critical(self, tr("Extraction Error"), result)
            return
        
        # Handle successful extraction (existing code)
        hl2vr_path = self.hl2vr_entry.text().strip()
        gameinfo_path = os.path.join(hl2vr_path, "hlvr", "gameinfo.txt")
        
        if isinstance(result, dict) and 'updated_addons' in result:
            # REPLACE ENTIRE ADDONS LIST WITH UPDATED VERSION
            self.current_addons = result['updated_addons']
            
            # UPDATE GAMEINFO.TXT WITH UPDATED PATHS AND PREFIXES
            addons_with_paths = [(addon['path'], addon['title']) for addon in self.current_addons]
            update_success, message = gameinfo.update_gameinfo_order(gameinfo_path, addons_with_paths)
            
            if update_success:
                log.info(tr("Gameinfo.txt updated with new map paths"))
                
                # SYNC CHANGES WITH EPISODES
                sync_success, sync_message = self.sync_episodes_with_main(addons_with_paths)
                
                self.load_addons_list()
        
        # Show results dialog (only if no cancellation)
        if isinstance(result, dict):
            # Form summary for dialog
            total_maps = result.get('total_maps', 0)
            extracted_count = len(result.get('extracted', []))
            failed_count = len(result.get('failed', []))
            
            # Log final results
            log.info(tr("Extraction completed: {} successful, {} failed, total maps: {}").format(extracted_count, failed_count, total_maps))
            
            if extracted_count > 0 and failed_count == 0:
                summary = tr("Successfully extracted {} maps").format(extracted_count)
                title = tr("Extraction completed")
            elif extracted_count > 0 and failed_count > 0:
                summary = tr("Successful: {} maps\nFailed: {} maps").format(extracted_count, failed_count)
                title = tr("Extraction completed with errors")
            elif extracted_count == 0 and failed_count > 0:
                summary = tr("Failed to extract {} maps, see Help (Maps tab)").format(failed_count)
                title = tr("Error")
            else:
                summary = tr("Extraction completed. No maps to process.")
                title = tr("Extraction completed")
            
            # Show results dialog
            dialog = ConfirmAddonsDialog(
                parent=self,
                title=title,
                summary=summary,
                extraction_results=result,
                dialog_type="extraction_results"
            )
            dialog.exec_()



    # === ADDITIONAL FUNCTIONS ===



    def get_addon_folder_path(self, addon_path):
        if addon_path.endswith('workshop_dir.vpk') or addon_path.endswith('workshop_dir'):
            return os.path.dirname(addon_path)
        else:
            return addon_path

    def show_context_menu(self, position):
        """Shows context menu for selected addon"""
        # Get row index under cursor
        index = self.addons_table.indexAt(position)
        if not index.isValid():
            return
        
        row = index.row()
        if row >= len(self.current_addons):
            return
        
        # Get addon data
        addon = self.current_addons[row]
        
        # Create context menu with one option
        menu = QMenu(self)
        check_map_action = menu.addAction(tr("Check map"))
        check_map_action.triggered.connect(lambda: self.check_maps(specific_addon=addon))
        
        # Show menu at click position
        menu.exec_(self.addons_table.viewport().mapToGlobal(position))

    def show_help(self):
        """Shows help dialog"""
        try:
            help_dialog = HelpDialog(self)
            help_dialog.exec_()
        except ImportError as e:
            QMessageBox.critical(self, tr("Error"), tr("Failed to load help module: {}").format(e))

    def closeEvent(self, event):
        self.save_config()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("HL2:VR Workshop Extender")

    window = MainWindow()

    possible_paths = [
        "icon.ico",
        os.path.join(os.path.dirname(sys.executable), "icon.ico"),
        os.path.join(os.path.dirname(sys.executable), "_internal", "icon.ico"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            app.setWindowIcon(QIcon(path))
            break
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()