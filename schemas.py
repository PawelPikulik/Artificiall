"""Pydantic schemas for scraped book data."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Book(BaseModel):
    """A scraped book record with validated fields."""

    title: str = Field(..., min_length=1, description="Book title")
    price: float = Field(..., gt=0, description="Price in GBP")
    availability: str = Field(..., description="Stock availability text")
    rating: int = Field(..., ge=1, le=5, description="Star rating 1-5")
    url: str = Field(..., description="Link to the book detail page")
    image_url: Optional[str] = Field(None, description="Cover image URL")

    @field_validator("price", mode="before")
    @classmethod
    def clean_price(cls, v):
        """Turn strings like '£51.77' or 'Â£51.77' into 51.77."""
        if isinstance(v, str):
            cleaned = v.strip()
            # Remove any non-ASCII currency prefix (e.g. Â£) by keeping only digits, dot, and comma
            import re
            cleaned = re.sub(r"[^0-9.,]", "", cleaned)
            return float(cleaned.replace(",", ""))
        return v

    @field_validator("rating", mode="before")
    @classmethod
    def clean_rating(cls, v):
        """Map word ratings (One, Two, Three, Four, Five) to integers."""
        mapping = {
            "One": 1,
            "Two": 2,
            "Three": 3,
            "Four": 4,
            "Five": 5,
        }
        if isinstance(v, str):
            return mapping.get(v.strip(), int(v))
        return v

    @field_validator("availability", mode="before")
    @classmethod
    def clean_availability(cls, v):
        """Strip whitespace from availability text."""
        if isinstance(v, str):
            return v.strip()
        return v
