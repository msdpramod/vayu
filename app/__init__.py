"""Vayu application package and built-in organ initialization."""

# Import built-in organs for their explicit executor registration.
# External side effects are still blocked by the durable approval lifecycle.
from app.social import social as social_media_organ

__all__ = ["social_media_organ"]
