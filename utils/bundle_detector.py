import re

BUNDLE_PATTERNS = [
    r"E\d+\s*-\s*E\d+",            # E07-E12
    r"S\d+\s*Complete",            # S01 Complete
    r"Complete\s+Series",
    r"Complete\s+Web\s+Series",
    r"\[\s*\d+\s*To\s*\d+\s*Eps?\s*\]",
    r"\b\d+\s*-\s*\d+\s*Eps?\b",
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
        "clean_title": None,  # NEW: Clean show title for TMDB
        "raw_title": title,   # NEW: Keep original for reference
        "note": "Auto-detected bundle"
    }

    # Extract season
    season_match = re.search(r"S(\d+)", title, re.IGNORECASE)
    if season_match:
        info["season"] = int(season_match.group(1))

    # Extract episode range
    range_match = re.search(r"E(\d+)\s*-\s*E(\d+)", title, re.IGNORECASE)
    if range_match:
        info["episode_range"] = f"E{range_match.group(1)}-E{range_match.group(2)}"

    # Extract clean title for TMDB search (NEW)
    clean = title
    
    # Remove file extension
    clean = re.sub(r'\.(mkv|mp4|avi|mov|webm)$', '', clean, flags=re.IGNORECASE)
    
    # Remove season/episode info and everything after (S01, E01-E06, etc.)
    clean = re.sub(r'\.S\d+.*$', '', clean, flags=re.IGNORECASE)
    
    # Replace dots, underscores, hyphens with spaces
    clean = clean.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    
    # Remove extra whitespace and strip
    info["clean_title"] = ' '.join(clean.split()).strip()

    return info
