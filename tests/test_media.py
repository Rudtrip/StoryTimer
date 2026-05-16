from delayed_publishes.media import validate_story_media
from delayed_publishes.models import MediaType


def test_accepts_small_photo(tmp_path) -> None:
    path = tmp_path / "photo.jpg"
    path.write_bytes(b"x")

    validate_story_media(MediaType.PHOTO, path)
