import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv

# We will import models later to register them with Beanie
import models

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/udx")

# Health check uchun global client
motor_client = None

async def init_db():
    print(f"[DB] Attempting connection to MongoDB at {MONGODB_URL.split('@')[-1] if '@' in MONGODB_URL else MONGODB_URL}...")
    try:
        global motor_client
        client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        motor_client = client
        
        # Verify connection
        await client.server_info()
        print("[DB] Connected to MongoDB successfully")
        
        # Get database
        db_name = MONGODB_URL.split('/')[-1].split('?')[0]
        if not db_name:
            db_name = "udx"
            
        db = client[db_name]
        
        await init_beanie(database=db, document_models=[
            models.User,
            models.Category,
            models.Product,
            models.PriceHistory,
            models.Order,
            models.Chat,
            models.Message,
            models.Contract,
            models.ProductInteraction,
            models.Transaction,
            models.IdempotencyKey,
            models.AuditLog,
            models.Review,
            models.FraudReport,
        ])
        
        return client, db
        
    except Exception as e:
        print(f"[DB] MongoDB connection failed: {e}")
        # In a real app we might want to raise here to prevent startup
        # if the database is strictly required
        raise e
