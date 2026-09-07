from pydantic import BaseModel, ConfigDict
from typing import List

class ProductItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    item_no: int
    name: str
    bengali: str | None = None

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    description: str
    price: float
    festival: str
    stock: int
    featured: bool
    items: List[ProductItemOut] = []
