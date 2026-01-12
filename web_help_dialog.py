from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser,
                             QPushButton, QApplication, QTabWidget, QWidget)
from PyQt5.QtCore import QThread, pyqtSignal, QUrl, Qt
from i18n import tr
import requests
import markdown
import sys
import json


class ConfigLoader(QThread):
    """
    Thread to load configuration from help_config.json
    """
    config_loaded = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, config_url):
        super().__init__()
        self.config_url = config_url
        
    def run(self):
        try:
            # Get raw config content
            raw_url = self.config_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            response = requests.get(raw_url)
            response.raise_for_status()
            
            # Parse JSON config
            config_data = json.loads(response.text)
            self.config_loaded.emit(config_data)
        except Exception as e:
            error_msg = f"{tr('Could not load configuration from GitHub:')} {str(e)}"
            self.error_occurred.emit(error_msg)


class HelpContentLoader(QThread):
    """
    Thread to load help content for a specific tab
    """
    content_loaded = pyqtSignal(str, str)  # emits content and tab_id
    error_occurred = pyqtSignal(str, str)  # emits error message and tab_id
    
    def __init__(self, url, tab_id, language):
        super().__init__()
        self.url = url
        self.tab_id = tab_id
        self.language = language
        
    def run(self):
        try:
            # Get raw content from GitHub
            raw_url = self.url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            response = requests.get(raw_url)
            response.raise_for_status()
            
            # Convert Markdown to HTML
            html_content = markdown.markdown(response.text, extensions=['tables', 'fenced_code'])
            
            # Add basic styles for better display
            styled_content = f"""
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
                pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
            {html_content}
            """
            
            self.content_loaded.emit(styled_content, self.tab_id)
        except Exception as e:
            error_msg = f"""
            <h2>{tr("Error loading help content")}</h2>
            <p>{tr("Could not load help content from GitHub. Error details:")}:</p>
            <p style="color: red;">{str(e)}</p>
            """
            self.error_occurred.emit(error_msg, self.tab_id)


class WebHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load config to get language
        self.config = self.load_current_app_config()
        self.language = self.config.get("language", "en") if self.config else "en"
        
        # Set window title based on language
        self.setWindowTitle(tr("Help"))
            
        self.setMinimumSize(800, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # Initialize variables
        self.tabs_config = []
        self.tab_widgets = {}
        self.tab_loaders = {}
        
        self.setup_ui()
        self.load_config()
        
    def load_current_app_config(self):
        """
        Load the current application config to get language setting
        """
        try:
            from config import load_config
            return load_config()
        except ImportError:
            # If config module is not available, return default
            return {"language": "en"}
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Set close button text based on language
        close_btn = QPushButton(tr("Close"))
            
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
    def load_config(self):
        """
        Load help configuration from GitHub
        """
        config_url = "https://github.com/DZHonnee/HL2-VR-Workshop-Extender/blob/main/help_config.json"
        
        self.config_loader = ConfigLoader(config_url)
        self.config_loader.config_loaded.connect(self.on_config_loaded)
        self.config_loader.error_occurred.connect(self.on_config_error)
        self.config_loader.start()
        
    def on_config_loaded(self, config_data):
        """
        Handle configuration loading completion
        """
        self.tabs_config = config_data.get("tabs", [])
        self.create_tabs()
        
    def on_config_error(self, error_msg):
        """
        Handle configuration loading error
        """
        # Create a single tab with error message
        error_tab = QWidget()
        error_layout = QVBoxLayout(error_tab)
        error_text = QTextBrowser()
        error_text.setOpenExternalLinks(True)
        error_text.setHtml(f"<p>{tr('Error loading help configuration:')} {error_msg}</p>")
        error_layout.addWidget(error_text)
        
        # Set tab title based on language
        self.tabs.addTab(error_tab, tr("Error"))
        
    def create_tabs(self):
        """
        Create tabs based on configuration
        """
        for tab_info in self.tabs_config:
            tab_id = tab_info["id"]
            
            # Get tab title for current language
            title = tab_info["title"].get(self.language, tab_info["title"].get("en", tab_id))
            
            # Create tab widget
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            
            # Create text browser for this tab
            text_browser = QTextBrowser()
            text_browser.setOpenExternalLinks(True)
            text_browser.setHtml(f"<p>{tr('Loading help content...')}</p>")
            tab_layout.addWidget(text_browser)
            
            # Store reference to the text browser
            self.tab_widgets[tab_id] = text_browser
            
            # Add tab to the tab widget
            self.tabs.addTab(tab_widget, title)
            
            # Load content for this tab
            self.load_tab_content(tab_id)
    
    def load_tab_content(self, tab_id):
        """
        Load content for a specific tab
        """
        # Construct URL for the specific help file
        url = f"https://github.com/DZHonnee/HL2-VR-Workshop-Extender/blob/main/help/{self.language}/{tab_id}.md"
        
        loader = HelpContentLoader(url, tab_id, self.language)
        loader.content_loaded.connect(self.on_content_loaded)
        loader.error_occurred.connect(self.on_content_error)
        loader.start()
        
        # Store reference to loader to prevent garbage collection
        self.tab_loaders[tab_id] = loader
        
    def on_content_loaded(self, content, tab_id):
        """
        Handle content loading completion for a specific tab
        """
        if tab_id in self.tab_widgets:
            self.tab_widgets[tab_id].setHtml(content)
        
    def on_content_error(self, error_msg, tab_id):
        """
        Handle content loading error for a specific tab
        """
        if tab_id in self.tab_widgets:
            self.tab_widgets[tab_id].setHtml(error_msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = WebHelpDialog()
    dialog.show()
    sys.exit(app.exec_())