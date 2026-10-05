import requests
import re
import time
from bs4 import BeautifulSoup
from logger import log
from i18n import tr, translator

# =====================================================================
# Constants
# =====================================================================

HL2_APPID = 220
_API_BASE = "https://api.steampowered.com/ISteamRemoteStorage"
_API_BATCH_SIZE = 50
_API_MAX_RETRIES = 5
_API_INITIAL_DELAY = 3  # seconds

# Only the User-Agent is set here on purpose. Claiming Chrome while also
# advertising Brotli support, but without the browser headers that come
# with that claim (sec-ch-ua, sec-fetch-*, Accept, Accept-Language), makes
# Steam answer 429 - measured on steamcommunity.com, which is where the
# unlisted-item HTML fallback goes. The API host accepts the same headers,
# which is why only unlisted addons were affected.
# Letting requests build Accept-Encoding itself also keeps the advertised
# compression within what this build can actually decode (no brotli here).
_API_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}


class SteamRateLimitException(Exception):
    """
    Raised when Steam answers with HTTP 429 (request rate limit).
    No backoff is used: the length of the limit window is unknown, so the
    operation is aborted and the user is asked to try again later.
    """
    pass


def rate_limit_message():
    """
    User-facing message for a Steam 429, pointing to the help topic.
    """
    return tr('Steam request limit exceeded! Open Help > Recommendations and issues,'
              ' scroll down to "Steam request limit exceeded" paragraph for more details'
              ' and solutions.')


# =====================================================================
# Internal helpers
# =====================================================================

def extract_id_from_url(url):
    """Extract numeric ID from Steam Workshop URL."""
    if not url:
        return None
    match = re.search(r'[?&]id=(\d+)', url)
    return match.group(1) if match else None


def _post_steam_api(endpoint, data, max_retries=_API_MAX_RETRIES):
    """
    POST request to Steam Web API.
    Raises SteamRateLimitException on HTTP 429 without any retry.
    Other request errors are retried a few times with a short backoff.
    Returns parsed JSON or None on failure.
    """
    url = f"{_API_BASE}/{endpoint}/v1/"
    delay = _API_INITIAL_DELAY
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, data=data, headers=_API_HEADERS, timeout=30)
            if resp.status_code == 429:
                # The limit window is unknown, so a blind retry only wastes
                # time: abort and let the caller report it to the user.
                log.error(tr("Steam rate limit exceeded"))
                raise SteamRateLimitException(rate_limit_message())
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                log.error(f"Steam API request failed: {e}")
                return None
            log.warning(f"Steam API error: {e}, retry in {delay}s")
            time.sleep(delay)
            delay *= 2
    return None


def _is_hl2_app(details):
    """Check that a published file belongs to Half-Life 2 workshop (appid 220)."""
    if not details:
        return False
    return (str(details.get('consumer_app_id')) == str(HL2_APPID)
            or str(details.get('creator_app_id')) == str(HL2_APPID))


def _is_map_by_tags(details):
    """Check if addon has 'map' or 'maps' tag."""
    if not details:
        return False
    for t in (details.get('tags') or []):
        if t.get('tag', '').lower() in ('map', 'maps'):
            return True
    return False


_HTML_FALLBACK_URL = "https://steamcommunity.com/sharedfiles/filedetails/?id={}"
_HTML_FALLBACK_DELAY = 2  # seconds to wait between HTML fallback requests
_HTML_PROBLEM_MARKER = "there was a problem accessing the item"

# Outcomes of a single HTML fallback attempt. These must stay distinct:
# collapsing "Steam is rate limiting us" into "this addon is gone" makes a
# Steam-side refusal look like a dead link, and the user acts on that.
_HTML_OK = 'ok'
_HTML_DELETED = 'deleted'            # Steam's own "item is gone" page
_HTML_RATE_LIMITED = 'rate_limited'  # Steam is throttling this client
_HTML_ERROR = 'error'                # Steam or the network let us down


def _fetch_addon_from_html(addon_id):
    """
    Last-resort lookup for an unlisted item: GetPublishedFileDetails reports
    result=9 for it, but its HTML page is still reachable and carries the
    title and the tags.

    Returns (outcome, data). outcome is one of the _HTML_* constants, and
    data is {'title': str, 'tags': [{'tag': str}, ...]} only for _HTML_OK,
    None otherwise.

    The caller needs that distinction: a deleted addon is dropped silently,
    while a rate-limited or broken request must be reported. Telling the
    user a live addon "is no longer available" because Steam refused us is
    both wrong and unactionable.
    One attempt only, no retries: the delay exists to stay polite, and
    hammering a 429 only makes the limit last longer.
    """
    # Several unlisted items in a row would otherwise hit the rate limiter.
    time.sleep(_HTML_FALLBACK_DELAY)

    try:
        resp = requests.get(_HTML_FALLBACK_URL.format(addon_id),
                            headers=_API_HEADERS, timeout=30)

        if resp.status_code == 429:
            # Steam is throttling us; the addon itself is not the problem.
            log.warning(tr("HTML fallback got 429 for {}").format(addon_id))
            return _HTML_RATE_LIMITED, None

        if resp.status_code == 404:
            log.info(tr("Addon {} is not available in Steam").format(addon_id))
            return _HTML_DELETED, None

        if resp.status_code != 200:
            # A server-side hiccup tells us nothing about the addon.
            log.warning(tr("HTML fallback got status {} for {}").format(
                resp.status_code, addon_id))
            return _HTML_ERROR, None

        html = resp.text
        if _HTML_PROBLEM_MARKER in html.lower():
            # Steam's placeholder page for deleted / fully hidden items.
            log.info(tr("Addon {} is not available in Steam").format(addon_id))
            return _HTML_DELETED, None

        soup = BeautifulSoup(html, 'html.parser')
        title_div = soup.find('div', class_='workshopItemTitle')
        if not title_div:
            # The item may well be hidden, but this can just as easily mean
            # Steam changed its layout. Reporting a failure is safer than
            # silently dropping an addon that is alive and mountable.
            log.warning(tr("HTML fallback found no title for {}").format(addon_id))
            return _HTML_ERROR, None

        title = title_div.get_text(strip=True)
        tags = [{'tag': a.get_text(strip=True)}
                for a in soup.select('div.workshopTags a')]

        log.info(tr("Loaded unlisted addon {} via HTML fallback").format(addon_id))
        return _HTML_OK, {'title': title, 'tags': tags}

    except Exception as e:
        # A failed request says nothing about the addon, so don't claim it does.
        log.warning(f"HTML fallback failed for {addon_id}: {e}")
        return _HTML_ERROR, None


def html_failure_reason(outcome):
    """
    Short user-facing reason for a failed HTML fallback attempt, so the user
    is told WHY an addon was not retrieved instead of being left to assume
    Steam no longer has it.
    """
    if outcome == _HTML_RATE_LIMITED:
        return tr("Steam request limit reached")
    return tr("Could not load unlisted addon")


def get_published_file_details(file_ids, hl2_only=False, progress_callback=None,
                              check_cancel=None, status_callback=None,
                              failures=None):
    """
    Batch-fetch details for a list of IDs (up to _API_BATCH_SIZE per HTTP request).
    If hl2_only=True, skip items not belonging to HL2.
    progress_callback: optional function(done, total) called after every batch.
    check_cancel: optional function() -> True stops fetching and returns
                  whatever was collected so far.
    status_callback: optional function(message) called before every HTML
                     fallback request, so the multi-second pause is visible.
    failures: optional dict, filled with {id_str: _HTML_* code} for items
              that could not be loaded for a reason the user can act on
              (rate limit, Steam error, network error). Deleted items are
              deliberately NOT recorded - nothing can be done about those,
              so they stay out of the way as before.
    Returns dict {id_str: details_dict}.
    """
    if not file_ids:
        return {}

    result = {}
    for i in range(0, len(file_ids), _API_BATCH_SIZE):
        if check_cancel and check_cancel():
            return result

        batch = file_ids[i:i + _API_BATCH_SIZE]
        data = {'itemcount': len(batch)}
        for j, fid in enumerate(batch):
            data[f'publishedfileids[{j}]'] = str(fid)

        json_resp = _post_steam_api('GetPublishedFileDetails', data)
        if not json_resp:
            continue

        for item in json_resp.get('response', {}).get('publishedfiledetails', []):
            # Checked per item, not per batch: the HTML fallback below is a
            # multi-second request, so a cancel must not wait for the rest.
            if check_cancel and check_cancel():
                return result

            fid = item.get('publishedfileid')
            if not fid:
                continue

            # Unlisted item: GetPublishedFileDetails reports result=9 for it,
            # but its HTML page still works, so fetch the data from there.
            # NOTE: this is the ONLY place the HTML fallback is triggered.
            # result=9 from GetCollectionDetails means "this is not a
            # collection" - a completely different meaning, and the normal
            # answer for every regular addon, so no fallback there.
            if item.get('result') == 9:
                if status_callback:
                    try:
                        status_callback(tr("Loading unlisted addon {}...").format(fid))
                    except Exception as e:
                        log.warning(f"Status callback failed: {str(e)}")
                outcome, html_data = _fetch_addon_from_html(fid)
                if outcome != _HTML_OK:
                    if outcome != _HTML_DELETED and failures is not None:
                        failures[str(fid)] = outcome
                    # Skipped either way, but a Steam-side failure is recorded
                    # above so the user is not left guessing what went wrong.
                    continue
                # Reshaped into an API-like dict so no downstream code changes.
                # The HL2 appid is assumed on purpose: the item either came
                # from an HL2 collection or was typed in by the user, and the
                # HTML page does not carry a reliable consumer_appid anyway.
                item = {
                    'publishedfileid': fid,
                    'result': 1,
                    'title': html_data['title'],
                    'tags': html_data['tags'],
                    'consumer_app_id': HL2_APPID,
                    'creator_app_id': HL2_APPID,
                    '_from_html': True,
                }

            if hl2_only and not _is_hl2_app(item):
                continue
            result[str(fid)] = item

        done = i + len(batch)
        if progress_callback:
            try:
                progress_callback(min(done, len(file_ids)), len(file_ids))
            except Exception as e:
                log.warning(f"Progress callback failed: {str(e)}")

        if done < len(file_ids):
            if check_cancel and check_cancel():
                return result
            time.sleep(0.5)

    return result


def get_collection_children(collection_id):
    """
    Get sorted children of an HL2 collection (by sortorder, ascending).
    Returns list of dicts [{'id': ..., 'sortorder': ...}, ...]
    or None if not a HL2 collection / error.
    """
    # Verify this collection belongs to HL2
    coll_details = get_published_file_details([collection_id], hl2_only=True)
    if str(collection_id) not in coll_details:
        log.warning(f"Collection {collection_id} is not for Half-Life 2 or not found")
        return None

    data = {
        'collectioncount': 1,
        'publishedfileids[0]': collection_id,
    }
    json_resp = _post_steam_api('GetCollectionDetails', data)
    if not json_resp:
        return None

    for coll in json_resp.get('response', {}).get('collectiondetails', []):
        if coll.get('publishedfileid') != collection_id:
            continue
        if coll.get('result') == 1:
            children = coll.get('children', []) or []
            return sorted(children, key=lambda c: c.get('sortorder', 0))
    return None


def get_workshop_item_type(item_id):
    """
    Determine what a workshop page actually is.
    Returns 'collection', 'addon', 'not_found', 'not_hl2', 'rate_limited',
    'error' or 'unknown'.
    """
    if not item_id:
        return 'unknown'

    item_id = str(item_id)

    # Step 1: fetch details WITHOUT the HL2 filter, otherwise "does not exist"
    # and "exists but belongs to another game" would collapse into one
    # outcome. The HTML fallback for result=9 happens inside this call.
    failures = {}
    details = get_published_file_details([item_id], hl2_only=False,
                                         failures=failures)
    d = details.get(item_id)

    if not d:
        # GetPublishedFileDetails said result=9 and the HTML page was no help.
        # Steam refusing to answer is NOT the same as a dead addon, and must
        # never be reported as one.
        if item_id in failures:
            if failures[item_id] == _HTML_RATE_LIMITED:
                return 'rate_limited'
            return 'error'
        return 'not_found'

    if not _is_hl2_app(d):
        # A real item with a real appid, just not from the HL2 workshop.
        return 'not_hl2'

    # Step 2: check collection status.
    # IMPORTANT: result=9 here means "this is not a collection", which is the
    # NORMAL answer for any regular addon. Never add an HTML fallback here:
    # it would fire once per addon in the list and hit the rate limiter.
    data = {
        'collectioncount': 1,
        'publishedfileids[0]': item_id,
    }
    json_resp = _post_steam_api('GetCollectionDetails', data)
    if not json_resp:
        return 'unknown'

    for coll in json_resp.get('response', {}).get('collectiondetails', []):
        if coll.get('publishedfileid') != item_id:
            continue
        result_code = coll.get('result')
        if result_code == 1:
            return 'collection'
        elif result_code == 9:
            return 'addon'

    return 'unknown'


# =====================================================================
# Public API (same signatures as before - no caller changes needed)
# =====================================================================

def get_page_type(url):
    """
    Determines page type.
    Returns: 'collection', 'addon' or 'unknown'
    """
    item_id = extract_id_from_url(url)
    return get_workshop_item_type(item_id)


def get_collection_addons(collection_url, check_cancel=None, progress_callback=None,
                         status_callback=None, failures=None):
    """
    Gets addons list from Steam Workshop collection.
    progress_callback: optional function(done, total) called after every batch
                       of addon details.
    status_callback: optional function(message) called before every HTML
                     fallback request for an unlisted addon.
    check_cancel: optional function() -> True aborts the request.
    Returns list of tuples (id, title, is_map) in REVERSE ORDER,
    or None if the caller cancelled the operation.
    """
    log.info(tr("Getting addons from collection: {}").format(collection_url))

    coll_id = extract_id_from_url(collection_url)
    if not coll_id:
        log.error(f"Could not extract ID from URL: {collection_url}")
        return []

    children = get_collection_children(coll_id)
    if not children:
        log.error(f"Failed to get collection children for {coll_id}")
        return []

    if check_cancel and check_cancel():
        return None

    child_ids = [c['publishedfileid'] for c in children]
    details = get_published_file_details(child_ids, hl2_only=True,
                                         progress_callback=progress_callback,
                                         check_cancel=check_cancel,
                                         status_callback=status_callback,
                                         failures=failures)

    if check_cancel and check_cancel():
        return None

    addons = []
    for child in children:
        cid = child['publishedfileid']
        # details is keyed by the string form of the id, like every other
        # caller; do not depend on the JSON type of publishedfileid.
        detail = details.get(str(cid))
        if not detail:
            continue
        title = detail.get('title') or tr("Unknown title")
        is_map = _is_map_by_tags(detail)
        addons.append((cid, title, is_map))

    addons.reverse()

    log.info(tr("Got {} addons from collection (in reverse order)").format(len(addons)))
    return addons


def get_single_addon(addon_url):
    """
    Gets information about a single addon from Steam Workshop (HL2 only).
    Returns tuple (id, title, is_map) or (None, None, False) on error.
    """
    addon_id = extract_id_from_url(addon_url)
    if not addon_id:
        return None, None, False

    details = get_published_file_details([addon_id], hl2_only=True)
    detail = details.get(addon_id)
    if not detail:
        return None, None, False

    title = detail.get('title') or tr("Unknown title")
    is_map = _is_map_by_tags(detail)
    return addon_id, title, is_map


def validate_workshop_url(url, expected_type):
    """
    Checks Steam Workshop URL correctness.
    expected_type: 'collection' or 'addon'
    Returns tuple (is_valid, error_message).
    """
    if not url:
        return False, tr("Enter URL")

    if 'steamcommunity.com' not in url:
        return False, tr("Invalid URL")

    try:
        page_type = get_page_type(url)
    except SteamRateLimitException:
        return False, tr("Steam rate limit exceeded. Please wait and try again.")

    if page_type == 'rate_limited':
        # Said plainly, without alarming the user: the addon is fine, the
        # workaround that unlisted items need is what Steam is throttling.
        return False, tr("This addon is unlisted, so it is loaded from its own "
                         "page instead of the API. Steam is currently limiting "
                         "these requests. Please try again later.")

    if page_type == 'error':
        return False, tr("Failed to load this unlisted addon from its page. "
                         "Please try again later.")

    if page_type == 'not_found':
        return False, tr("Addon is no longer available in Steam Workshop")

    if page_type == 'not_hl2':
        return False, tr("Addon is not from Half-Life 2 Workshop")

    if page_type == 'unknown':
        return False, tr("Failed to determine page")

    if expected_type == 'collection' and page_type != 'collection':
        return False, tr("Page is not a collection")

    if expected_type == 'addon' and page_type != 'addon':
        return False, tr("Page is not an addon")

    return True, ""


def get_addon_by_id(addon_id):
    """
    Gets addon information by its ID (HL2 only).
    Returns tuple (id, title, is_map) or (None, None, False) on error.
    """
    aid = str(addon_id)
    details = get_published_file_details([aid], hl2_only=True)
    detail = details.get(aid)
    if not detail:
        return None, None, False

    title = detail.get('title') or tr("Unknown title")
    is_map = _is_map_by_tags(detail)
    return aid, title, is_map


def is_addon_map(addon_url):
    """
    Checks if addon is a map by its tags (HL2 only).
    Returns True or False.
    """
    addon_id = extract_id_from_url(addon_url)
    if not addon_id:
        return False

    details = get_published_file_details([addon_id], hl2_only=True)
    detail = details.get(addon_id)
    if not detail:
        return False

    return _is_map_by_tags(detail)


# =====================================================================
# Batch API (for Stage 2 - addon_manager integration)
# =====================================================================

def get_multiple_addons_info(addon_ids, progress_callback=None,
                             status_callback=None, failures=None,
                             check_cancel=None):
    """
    Batch-fetch title + is_map flag for many HL2 addons in one call.
    progress_callback: optional function(done, total) forwarded to the API layer.
    status_callback: optional function(message) forwarded to the API layer,
                     for unlisted addons resolved through the HTML fallback.
    failures: optional dict, filled with {id_str: _HTML_* code} for items
              that failed for a reason worth reporting, as documented in
              get_published_file_details.
    check_cancel: optional function() -> True stops fetching and returns
                  whatever was collected so far. Without it the whole network
                  phase runs to completion before the caller can react.
    This is the function that will replace the ThreadPoolExecutor loop
    in addon_manager.prepare_addons_from_workshop_txt (Stage 2).
    Returns dict {id_str: {'title': ..., 'is_map': bool} or None}.
    None means: not found, not HL2, or API error.
    """
    if not addon_ids:
        return {}

    id_strs = [str(a) for a in addon_ids]
    details = get_published_file_details(id_strs, hl2_only=True,
                                         progress_callback=progress_callback,
                                         check_cancel=check_cancel,
                                         status_callback=status_callback,
                                         failures=failures)

    result = {}
    for aid in id_strs:
        detail = details.get(aid)
        if not detail:
            result[aid] = None
            continue
        result[aid] = {
            'title': detail.get('title') or tr("Unknown title"),
            'is_map': _is_map_by_tags(detail),
        }
    return result