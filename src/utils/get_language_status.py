def get_language_status(languages: list[str]) -> tuple[bool, bool]:
    """Returns a tuple indicating whether English and French are present in the list of languages."""
    return ("en" in languages, "fr" in languages)