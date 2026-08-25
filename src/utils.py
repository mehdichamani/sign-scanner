"""Utility helper functions."""
import os
import pandas as pd
import arabic_reshaper
from bidi.algorithm import get_display

def fix_persian_text(text: str) -> str:
    """Format and reshape Persian/Arabic text for correct right-to-left display."""
    if not text or pd.isna(text):
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)
