from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from .models import Product, ProductItem
from .api import router as commerce_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Puja Kit Store API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(commerce_router)

PRODUCT = {
    "name": "Premium Puja Doshokorma Samagri Kit",
    "slug": "premium-puja-doshokorma-samagri-kit",
    "description": "Celebrate your rituals with ease using our complete Premium Puja Doshokorma Samagri Kit. Carefully curated for all auspicious occasions, this budget-friendly spiritual kit includes 20 essential high-quality dry puja items packed neatly to ensure zero spillage during transit.",
    "price": 200.0,
    "festival": "All Auspicious Occasions",
    "stock": 100,
    "featured": True,
}
ITEMS = [
("Mini Sindoor Packet", "মিনি সিন্দুর"),
("Akshat Rice Packet", "অক্ষত চাল"),
("Roli / Abir Packet", "রুলি / আবির"),
("Mauli Thread Roll", "মৌলি সুতো"),
("Dhupkathi / Incense Sticks", "ধূপকাঠি"),
("Kaudi Shells / Cowrie", "কড়ি"),
("Black til", None),
("Kamal Gatta Seeds", "কমল গট্টা"),
("Pancha sashya", None),
("Chandmala", None),
("Ghee / Clarified Butter", "ঘৃত"),
("Modhu / Pure Honey mini pack", "মধু"),
("Pradip salte", None),
("Panchagiri", "পঞ্চগিরি"),
("Pancharatna", "পঞ্চরত্ন"),
    ("Poite", None),
    ("Durba Grass", "দূর্বা ঘাস"),
    ("Mouli Thread", "মৌলি সুতো"),
    ("Chandan Powder", "চন্দন গুঁড়ো"),
    ("Flower Offering Mix", "পুষ্প নিবেদন"),
]

def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/products")
def products(session: Session = Depends(db)):
    rows = session.query(Product).all()
    result = []
    for p in rows:
        items = session.query(ProductItem).filter(ProductItem.product_id == p.id).order_by(ProductItem.item_no).all()
        result.append({
            "id": p.id, "name": p.name, "slug": p.slug,
            "description": p.description, "price": p.price,
            "festival": p.festival, "stock": p.stock,
            "featured": p.featured,
            "items": [{"item_no": x.item_no, "name": x.name, "bengali": x.bengali} for x in items]
        })
    return result

@app.post("/api/seed")
def seed(session: Session = Depends(db)):
    existing = session.query(Product).filter_by(slug=PRODUCT["slug"]).first()
    if existing:
        existing.price = PRODUCT["price"]
        existing.stock = PRODUCT["stock"]
        existing.description = PRODUCT["description"]
        existing_items = session.query(ProductItem).filter(ProductItem.product_id == existing.id).count()
        for i, (name, bengali) in enumerate(ITEMS[existing_items:], existing_items + 1):
            session.add(ProductItem(product_id=existing.id, item_no=i, name=name, bengali=bengali))
        session.commit()
        return {"message": "Product updated", "id": existing.id, "items": len(ITEMS)}
    p = Product(**PRODUCT)
    session.add(p)
    session.flush()
    for i, (name, bengali) in enumerate(ITEMS, 1):
        session.add(ProductItem(product_id=p.id, item_no=i, name=name, bengali=bengali))
    session.commit()
    return {"message": "Seeded", "id": p.id}

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
