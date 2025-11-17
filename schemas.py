"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- MealLog -> "meallog" collection
- FoodItem -> "fooditem" collection (reference catalog)

Only define classes here that represent persisted collections.
Use request/response models inline in routes if they are not persisted.
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class User(BaseModel):
    """Users collection schema"""
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    height_cm: Optional[float] = Field(None, ge=0, description="Height in centimeters")
    weight_kg: Optional[float] = Field(None, ge=0, description="Weight in kilograms")
    is_active: bool = Field(True, description="Whether user is active")

class FoodItem(BaseModel):
    """Food catalog items for calorie/macros reference"""
    name: str = Field(..., description="Food name")
    calories: float = Field(..., ge=0, description="Calories per serving")
    protein_g: Optional[float] = Field(0, ge=0, description="Protein per serving in grams")
    carbs_g: Optional[float] = Field(0, ge=0, description="Carbs per serving in grams")
    fat_g: Optional[float] = Field(0, ge=0, description="Fat per serving in grams")
    serving: Optional[str] = Field(None, description="Serving size, e.g., 100g, 1 cup")

class MealItem(BaseModel):
    """An item within a meal log"""
    name: str
    calories: float = Field(..., ge=0)
    quantity: Optional[float] = Field(1, ge=0, description="Number of servings")

class MealLog(BaseModel):
    """Daily meal logs per user. Collection name: meallog"""
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD")
    items: List[MealItem] = Field(default_factory=list, description="Food items consumed in this log entry")
    total_calories: float = Field(0, ge=0, description="Total calories for this log entry")
    notes: Optional[str] = Field(None, description="Optional notes")

class Exercise(BaseModel):
    """Exercise reference library with form cues"""
    name: str
    muscle_group: str
    cues: List[str] = Field(default_factory=list)
    common_mistakes: List[str] = Field(default_factory=list)
