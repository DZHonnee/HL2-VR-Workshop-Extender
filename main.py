import sys
import os

# Add current directory to path for module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from gui import main
    from logger import log
    
except ImportError:
    sys.exit(1)

if __name__ == "__main__":
    main()