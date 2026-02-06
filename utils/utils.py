from re import search as rsearch
import re


def get_readable_file_size(size_in_bytes):
    size_in_bytes = int(size_in_bytes) if str(size_in_bytes).isdigit() else 0
    if not size_in_bytes:
        return "0B"
    index, SIZE_UNITS = 0, ["B", "KB", "MB", "GB", "TB", "PB"]

    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return (
        f"{size_in_bytes:.2f}{SIZE_UNITS[index]}"
        if index > 0
        else f"{size_in_bytes:.2f}B"
    )


def check_quality(stdout):

    quality_map = [
        (360, "360p"),
        (480, "480p"),
        (540, "540p"),
        (720, "720p"),
        (1080, "1080p"),
        (2160, "2160p"),
        (4320, "4320p"),
        (float("inf"), "8640p"),
    ]

    for line in stdout.split("\n"):
        if "Image height" in line:
            match = rsearch(r"(\d+)", line)
            if match:
                height = int(match.group())

                for threshold, label in quality_map:
                    if height <= threshold:
                        return label

    return None


def remove_redandent(filename):
    """
    Remove common username patterns from a filename while preserving the content title.

    Args:
        filename (str): The input filename

    Returns:
        str: Filename with usernames removed
    """
    filename = filename.replace("\n", "\\n")

    patterns = [
        r"^@[\w\.-]+?(?=_)",
        r"_@[A-Za-z]+_|@[A-Za-z]+_|[\[\]\s@]*@[^.\s\[\]]+[\]\[\s@]*",  
        r"^[\w\.-]+?(?=_Uploads_)",  
        r"^(?:by|from)[\s_-]+[\w\.-]+?(?=_)",  
        r"^\[[\w\.-]+?\][\s_-]*",  
        r"^\([\w\.-]+?\)[\s_-]*",  
    ]

    result = filename
    for pattern in patterns:
        match = re.search(pattern, result)
        if match:
            result = re.sub(pattern, " ", result)
            break  

    
    result = re.sub(r"^[_\s-]+|[_\s-]+$", " ", result)

    return result


def get_official_trailer_url(videos):
    """
    Extract the official YouTube trailer URL from TMDB video results.

    Args:
        videos: The videos response from TMDB API

    Returns:
        str: YouTube URL of the official trailer, or empty string if none found
    """
    
    youtube_trailers = [
        video
        for video in videos.results
        if video.site.lower() == "youtube" and video.type.lower() == "trailer"
    ]

    if not youtube_trailers:
        return ""

    
    for trailer in youtube_trailers:
        if "official" in trailer.name.lower():
            return f"https://www.youtube.com/watch?v={trailer.key}"

    
    return f"https://www.youtube.com/watch?v={youtube_trailers[0].key}"
