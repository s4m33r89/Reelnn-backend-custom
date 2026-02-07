import re

# Enhanced patterns to catch Season Packs AND Bundled Episodes
BUNDLE_PATTERNS = [
    r"S\d+\s*Complete",                  # S01 Complete
    r"Season\s*\d+\s*Pack",              # Season 1 Pack
    r"Ep?\s*\d+\s*-\s*Ep?\s*\d+",        # E01-E10, Ep 1 - Ep 10
    r"Episodes\s*\d+\s*-\s*\d+",         # Episodes 1-10
    r"Ep\s*\d+\s*to\s*\d+",              # Ep 1 to 10
    r"\[\s*\d+\s*To\s*\d+\s*Eps?\s*\]",  # [01 To 10 Eps]
    r"\b\d+\s*-\s*\d+\s*Eps?\b",         # 1-10 Eps
    r"Complete\s+Series",
    r"Complete\s+Web\s+Series",
]

def is_bundle(title: str) -> bool:
    for pattern in BUNDLE_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return True
    return False

def extract_bundle_info(title: str) -> dict:
    """
    Extract bundle info including cleaned title for TMDB search
    """
    info = {
        "season": None,
        "episode_range": None,
        "clean_title": None,
        "raw_title": title,
        "note": "Auto-detected bundle"
    }

    # Extract season (Look for S01, Season 1, etc.)
    season_match = re.search(r"(?:S|Season)\s*(\d+)", title, re.IGNORECASE)
    if season_match:
        info["season"] = int(season_match.group(1))

    # Extract episode range (E01-E10, 1-10, etc.)
    # Catches: E01-E05, 1-10, Ep 1 to 5
    range_match = re.search(r"(?:E|Ep|Episodes?)\s*(\d+)\s*(?:-|to)\s*(?:E|Ep|Episodes?)?\s*(\d+)", title, re.IGNORECASE)
    if range_match:
        start = range_match.group(1)
        end = range_match.group(2)
        info["episode_range"] = f"E{start.zfill(2)}-E{end.zfill(2)}"

    # Clean title for TMDB
    clean = title
    
    # 1. Remove file extensions
    clean = re.sub(r'\.(mkv|mp4|avi|mov|webm)$', '', clean, flags=re.IGNORECASE)
    
    # 2. Remove Season/Episode info and everything after
    # Matches: S01, E01-E05, Season 1, [01-10]
    clean = re.sub(r'(?:[._\s\[(]|^)(?:S|Season)\s*\d+.*$', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'(?:[._\s\[(]|^)(?:E|Ep|Episodes?)\s*\d+\s*[-to].*$', '', clean, flags=re.IGNORECASE)
    
    # 3. Clean up separators
    clean = clean.replace('.', ' ').replace('_', ' ').replace('-', ' ').replace('[', '').replace(']', '').replace('(', '').replace(')', '')
    
    # 4. Remove quality tags commonly found before season info (optional but safe)
    clean = re.sub(r'\b(480p|720p|1080p|2160p|4k|WEB-DL|BluRay)\b.*', '', clean, flags=re.IGNORECASE)

    # 5. Remove extra whitespace
    info["clean_title"] = ' '.join(clean.split()).strip()

    return info
