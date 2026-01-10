"""
Image Optimization Service for InstaSchool

Provides image compression and resizing to reduce curriculum file sizes
while maintaining visual quality for educational content.
"""

import base64
import io
from typing import Optional, Tuple, Dict, Any

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# Quality presets for different use cases
QUALITY_PRESETS = {
    "storage": {
        "max_size": (800, 800),      # Max dimensions for stored images
        "quality": 80,                # JPEG quality (balance size/quality)
        "format": "JPEG",
    },
    "thumbnail": {
        "max_size": (400, 400),
        "quality": 70,
        "format": "JPEG",
    },
    "high": {
        "max_size": (1200, 1200),
        "quality": 90,
        "format": "JPEG",
    },
    "web": {
        "max_size": (600, 600),
        "quality": 75,
        "format": "JPEG",
    },
}


def optimize_image(
    b64_data: str,
    preset: str = "storage",
    max_size: Optional[Tuple[int, int]] = None,
    quality: Optional[int] = None,
    output_format: Optional[str] = None,
) -> Optional[str]:
    """Optimize an image by resizing and compressing.

    Args:
        b64_data: Base64 encoded image (with or without data URI prefix)
        preset: Quality preset name ('storage', 'thumbnail', 'high', 'web')
        max_size: Override max dimensions (width, height)
        quality: Override JPEG quality (1-100)
        output_format: Override output format ('JPEG', 'PNG', 'WEBP')

    Returns:
        Optimized base64 string without data URI prefix, or None on error.
    """
    if not PIL_AVAILABLE:
        print("Warning: PIL not available, returning original image")
        return _strip_data_uri(b64_data)

    try:
        # Get preset settings
        settings = QUALITY_PRESETS.get(preset, QUALITY_PRESETS["storage"])
        max_w, max_h = max_size or settings["max_size"]
        qual = quality or settings["quality"]
        fmt = output_format or settings["format"]

        # Decode base64
        clean_b64 = _strip_data_uri(b64_data)
        image_data = base64.b64decode(clean_b64)

        # Open image
        img = Image.open(io.BytesIO(image_data))

        # Convert to RGB if needed (for JPEG)
        if fmt == "JPEG":
            if img.mode in ("RGBA", "P", "LA"):
                # Create white background for transparent images
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                if img.mode in ("RGBA", "LA"):
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert("RGB")
            elif img.mode != "RGB":
                img = img.convert("RGB")

        # Resize if larger than max dimensions
        original_size = img.size
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        new_size = img.size

        # Save optimized image
        buffer = io.BytesIO()
        save_kwargs = {"optimize": True}

        if fmt == "JPEG":
            save_kwargs["quality"] = qual
            save_kwargs["progressive"] = True
        elif fmt == "WEBP":
            save_kwargs["quality"] = qual
        elif fmt == "PNG":
            save_kwargs["compress_level"] = 9

        img.save(buffer, format=fmt, **save_kwargs)

        # Get size reduction info
        original_bytes = len(image_data)
        optimized_bytes = buffer.tell()
        reduction_pct = (1 - optimized_bytes / original_bytes) * 100 if original_bytes > 0 else 0

        if reduction_pct > 10:  # Only log significant reductions
            print(f"Image optimized: {original_size} -> {new_size}, "
                  f"{original_bytes:,} -> {optimized_bytes:,} bytes ({reduction_pct:.0f}% reduction)")

        # Return base64 encoded
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    except Exception as e:
        print(f"Error optimizing image: {e}")
        return _strip_data_uri(b64_data)  # Return original on error


def _strip_data_uri(b64_data: str) -> str:
    """Remove data URI prefix if present."""
    if b64_data and "," in b64_data and b64_data.startswith("data:"):
        return b64_data.split(",", 1)[1]
    return b64_data


def get_image_info(b64_data: str) -> Dict[str, Any]:
    """Get information about a base64 encoded image.

    Args:
        b64_data: Base64 encoded image

    Returns:
        Dict with width, height, format, size_bytes, etc.
    """
    if not PIL_AVAILABLE:
        clean_b64 = _strip_data_uri(b64_data)
        return {"size_bytes": len(base64.b64decode(clean_b64))}

    try:
        clean_b64 = _strip_data_uri(b64_data)
        image_data = base64.b64decode(clean_b64)

        img = Image.open(io.BytesIO(image_data))

        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
            "size_bytes": len(image_data),
            "size_kb": len(image_data) / 1024,
            "size_mb": len(image_data) / (1024 * 1024),
        }
    except Exception as e:
        return {"error": str(e)}


def optimize_curriculum_images(
    curriculum: Dict[str, Any],
    preset: str = "storage",
    in_place: bool = False,
) -> Dict[str, Any]:
    """Optimize all images in a curriculum.

    Args:
        curriculum: Curriculum dict with units
        preset: Quality preset to use
        in_place: If True, modify curriculum in place; else return copy

    Returns:
        Curriculum with optimized images
    """
    import copy

    if not in_place:
        curriculum = copy.deepcopy(curriculum)

    units = curriculum.get("units", [])
    images_optimized = 0
    total_saved_bytes = 0

    for unit in units:
        if not isinstance(unit, dict):
            continue

        # Optimize selected_image_b64
        if unit.get("selected_image_b64"):
            original_size = len(unit["selected_image_b64"])
            optimized = optimize_image(unit["selected_image_b64"], preset=preset)
            if optimized:
                unit["selected_image_b64"] = optimized
                new_size = len(optimized)
                total_saved_bytes += original_size - new_size
                images_optimized += 1

        # Optimize images list
        if unit.get("images") and isinstance(unit["images"], list):
            for img_dict in unit["images"]:
                if isinstance(img_dict, dict) and img_dict.get("b64"):
                    original_size = len(img_dict["b64"])
                    optimized = optimize_image(img_dict["b64"], preset=preset)
                    if optimized:
                        img_dict["b64"] = optimized
                        new_size = len(optimized)
                        total_saved_bytes += original_size - new_size
                        images_optimized += 1

        # Handle legacy field names
        for field in ["image_base64", "image"]:
            if unit.get(field) and isinstance(unit[field], str) and len(unit[field]) > 1000:
                original_size = len(unit[field])
                optimized = optimize_image(unit[field], preset=preset)
                if optimized:
                    unit[field] = optimized
                    new_size = len(optimized)
                    total_saved_bytes += original_size - new_size
                    images_optimized += 1

    if images_optimized > 0:
        print(f"Optimized {images_optimized} images, saved {total_saved_bytes / 1024:.0f}KB")

    return curriculum


# Singleton service instance
_service_instance = None


def get_image_optimization_service():
    """Get the image optimization service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ImageOptimizationService()
    return _service_instance


class ImageOptimizationService:
    """Service class for image optimization operations."""

    def __init__(self, default_preset: str = "storage"):
        self.default_preset = default_preset
        self.pil_available = PIL_AVAILABLE

    def optimize(self, b64_data: str, preset: str = None) -> Optional[str]:
        """Optimize a single image."""
        return optimize_image(b64_data, preset=preset or self.default_preset)

    def optimize_curriculum(self, curriculum: Dict[str, Any], preset: str = None) -> Dict[str, Any]:
        """Optimize all images in a curriculum."""
        return optimize_curriculum_images(curriculum, preset=preset or self.default_preset)

    def get_info(self, b64_data: str) -> Dict[str, Any]:
        """Get image information."""
        return get_image_info(b64_data)
