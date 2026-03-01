from config.log import logger


LANGUAGE_DICT = {
    "en": "english",
    "zh": "chinese",
    "fr": "french",
    "de": "german",
    "it": "italian",
    "ja": "japanese",
    "ko": "korean",
    "ru": "russian",
    "es": "spanish",
    "pt": "portuguese",
    "nl": "dutch",
    "multilingual": "multilingual"
}

def validate_language(language: str | None)-> str | None:
    """ Validate the language and return the corresponding values """
    
    if not language:
        return "multilingual"
        
    lang = language.lower().strip()
    
    # Direct lookup
    if lang in LANGUAGE_DICT:
        return LANGUAGE_DICT[lang]
    
    if lang in LANGUAGE_DICT.values():
        return lang
        
    logger.error(f"Language {language} is not supported, switching to multilingual mode.")
    return None