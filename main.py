import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import MealLog, MealItem, FoodItem, User, Exercise

app = FastAPI(title="Fitness Coach API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Fitness Coach Backend running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response

# ===== Calorie and Meal Logging Endpoints =====
class LogMealRequest(BaseModel):
    user_id: str
    date: str  # YYYY-MM-DD
    items: List[MealItem]
    notes: Optional[str] = None

class LogMealResponse(BaseModel):
    log_id: str
    total_calories: float

@app.post("/api/meal/log", response_model=LogMealResponse)
def log_meal(payload: LogMealRequest):
    total = sum((item.calories or 0) * (item.quantity or 1) for item in payload.items)
    doc = MealLog(
        user_id=payload.user_id,
        date=payload.date,
        items=payload.items,
        total_calories=total,
        notes=payload.notes
    )
    inserted_id = create_document("meallog", doc)
    return {"log_id": inserted_id, "total_calories": total}

class DaySummary(BaseModel):
    date: str
    total_calories: float

@app.get("/api/meal/summary/{user_id}/{date}", response_model=DaySummary)
def daily_summary(user_id: str, date: str):
    docs = get_documents("meallog", {"user_id": user_id, "date": date})
    total = 0.0
    for d in docs:
        total += float(d.get("total_calories", 0))
    return {"date": date, "total_calories": total}

# ===== Diet Recommendation Endpoint =====
class DietRequest(BaseModel):
    age: int = Field(..., ge=0, le=120)
    sex: str = Field(..., description="male or female")
    height_cm: float = Field(..., ge=0)
    weight_kg: float = Field(..., ge=0)
    activity_level: str = Field(..., description="sedentary, light, moderate, active, very_active")
    goal: str = Field(..., description="lose, maintain, gain")

class DietPlan(BaseModel):
    target_calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    tips: List[str]

_activity_factors = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

@app.post("/api/diet/plan", response_model=DietPlan)
def diet_plan(req: DietRequest):
    sex = req.sex.lower()
    if sex not in ("male", "female"):
        raise HTTPException(status_code=400, detail="sex must be 'male' or 'female'")
    if req.activity_level not in _activity_factors:
        raise HTTPException(status_code=400, detail="invalid activity_level")

    # Mifflin-St Jeor BMR
    if sex == "male":
        bmr = 10 * req.weight_kg + 6.25 * req.height_cm - 5 * req.age + 5
    else:
        bmr = 10 * req.weight_kg + 6.25 * req.height_cm - 5 * req.age - 161

    tdee = bmr * _activity_factors[req.activity_level]

    if req.goal == "lose":
        target = tdee - 500
    elif req.goal == "gain":
        target = tdee + 300
    else:
        target = tdee

    target = max(1200, target)  # safety lower bound

    # Simple macro split: 30/40/30 (P/C/F)
    protein_cal = 0.30 * target
    carb_cal = 0.40 * target
    fat_cal = 0.30 * target

    plan = DietPlan(
        target_calories=int(round(target)),
        protein_g=int(round(protein_cal / 4)),
        carbs_g=int(round(carb_cal / 4)),
        fat_g=int(round(fat_cal / 9)),
        tips=[
            "Aim for whole foods: lean protein, veggies, fruits, whole grains",
            "Drink enough water (2-3L/day)",
            "Prioritize protein in each meal",
        ],
    )
    return plan

# ===== Exercise Form Guidance Endpoint =====
class FormGuideRequest(BaseModel):
    exercise: str

class FormGuideResponse(BaseModel):
    name: str
    cues: List[str]
    mistakes: List[str]

# A minimal in-code catalog (could be moved to DB later)
_form_library = {
    "squat": {
        "cues": [
            "Feet shoulder-width, toes slightly out",
            "Brace core, neutral spine",
            "Knees track over toes",
            "Sit back and down until thighs are parallel",
        ],
        "mistakes": [
            "Heels lifting",
            "Knees collapsing in",
            "Rounding the back",
        ],
    },
    "push-up": {
        "cues": [
            "Hands under shoulders",
            "Body in a straight line",
            "Elbows ~45 degrees",
            "Chest to floor, full lockout",
        ],
        "mistakes": [
            "Sagging hips",
            "Flaring elbows",
            "Half reps",
        ],
    },
    "deadlift": {
        "cues": [
            "Bar over mid-foot",
            "Hinge at hips, flat back",
            "Lats tight, bar close",
            "Push the floor, stand tall",
        ],
        "mistakes": [
            "Rounding lower back",
            "Jerking the bar",
            "Bar drifting forward",
        ],
    },
}

@app.post("/api/exercise/form", response_model=FormGuideResponse)
def exercise_form(req: FormGuideRequest):
    name = req.exercise.strip().lower()
    if name not in _form_library:
        raise HTTPException(status_code=404, detail="Exercise not found. Try squat, push-up, or deadlift")
    entry = _form_library[name]
    return {"name": name, "cues": entry["cues"], "mistakes": entry["mistakes"]}

# ===== Schema exposure for DB viewer/tools =====
@app.get("/schema")
def get_schema_definitions():
    # Simple reflection: list class names defined in schemas file
    return {
        "collections": [
            "user",
            "fooditem",
            "meallog",
            "exercise",
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
