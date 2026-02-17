from src.processing.matcher import SongMatcher


def test_clean_title_removes_cover_and_parentheses():
    matcher = SongMatcher()
    src = "Amr Diab - Tamally Maak (Piano Cover by X)"
    assert matcher.clean_title(src) == "Amr Diab Tamally Maak"


def test_clean_title_strips_hq_and_official():
    matcher = SongMatcher()
    src = "Fairuz - Habibi (Piano Cover) [HQ Official Audio]"
    assert matcher.clean_title(src) == "Fairuz Habibi"
