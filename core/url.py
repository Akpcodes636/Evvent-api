def build_file_url(base_url: str, path: str) -> str:
    """
    Convert a stored relative file path into an absolute URL.

    Example:
        base_url = "https://evvent-api.onrender.com/"
        path = "/uploads/events/image.jpg"

        returns:
        "https://evvent-api.onrender.com/uploads/events/image.jpg"
    """
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"