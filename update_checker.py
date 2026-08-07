import requests
import re
from packaging import version
from logger import log
from i18n import tr


class UpdateChecker:
    def __init__(self, current_version, repo_owner, repo_name):
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    def check_for_updates(self):
        """
        Checks for a new version on GitHub
        Returns tuple (has_update, latest_version, release_info) or (False, None, None) if no updates
        """
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()

            release_data = response.json()
            # Extract version from tag, considering format v1.0
            tag_name = release_data.get('tag_name', '')
            latest_version = re.sub(r'^v', '', tag_name)

            if not latest_version:
                log.warning(tr("Could not get version information from GitHub"))
                return False, None, None

            # Compare versions
            if version.parse(self.current_version) < version.parse(latest_version):
                log.info(tr("New version available: {}").format(latest_version))
                return True, latest_version, release_data
            else:
                log.info(tr("Application is up to date"))
                return False, latest_version, release_data

        except requests.exceptions.RequestException as e:
            log.error(tr("Error checking for updates: {}").format(str(e)))
            return False, None, None
        except Exception as e:
            log.error(tr("Unexpected error during update check: {}").format(str(e)))
            return False, None, None