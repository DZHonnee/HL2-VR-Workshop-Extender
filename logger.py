from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
from PyQt5.QtCore import QTimer



class Logger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance.widget = None
        return cls._instance
    
    def set_widget(self, widget):
        self.widget = widget
        if self.widget:
            self.widget.setFont(QFont("Consolas", 8))
            self.widget.setReadOnly(True)
    
    def info(self, message):
        self._log("INFO", message)
    
    def warning(self, message):
        self._log("WARNING", message)
    
    def error(self, message):
        self._log("ERROR", message)

    def _log(self, level, message):
        if not self.widget:
            return
        
        log_entry = f"[{level}] {message}"
        
        # Use Qt::QueuedConnection for cross-thread calls
        if hasattr(self.widget, 'append'):
            QMetaObject.invokeMethod(
                self.widget,
                "append",
                Qt.QueuedConnection,
                Q_ARG(str, log_entry)
            )
        
        # Use timer for delayed scrolling - this is the key fix!
        def delayed_scroll():
            if self.widget:
                scrollbar = self.widget.verticalScrollBar()
                # Set value to maximum but with a small delay
                scrollbar.setValue(scrollbar.maximum())
        
        # Start timer with small delay (10 ms)
        QTimer.singleShot(10, delayed_scroll)

# Global logger instance
log = Logger()