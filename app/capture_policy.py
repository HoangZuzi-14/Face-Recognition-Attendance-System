MIN_CAPTURE_IMAGES = 8
RECOMMENDED_CAPTURE_IMAGES = 15


def can_finalize_capture(valid_count):
    return valid_count >= MIN_CAPTURE_IMAGES


def capture_progress_text(valid_count):
    return f"Hop le phien nay: {valid_count}/{MIN_CAPTURE_IMAGES} (khuyen nghi {RECOMMENDED_CAPTURE_IMAGES})"
