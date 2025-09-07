import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from typing import Dict

from whatsapp_bot_handler import WhatsAppBotHandler
from config import validate_config

# הגדרת logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# יצירת אפליקציית FastAPI
app = FastAPI(
    title="Wedding System WhatsApp Bot",
    description="Webhook handler for WhatsApp Bot with AI receipt analysis",
    version="2.0.0"
)

# מופע הבוט
bot_handler = WhatsAppBotHandler()

@app.on_event("startup")
async def startup_event():
    """אתחול המערכת"""
    logger.info("🚀 Starting Wedding System WhatsApp Bot")
    
    # בדיקת הגדרות
    config_status = validate_config()
    logger.info("📊 Configuration Status:")
    
    for service, status in config_status.items():
        emoji = "✅" if status else "❌"
        logger.info(f"{emoji} {service}")
    
    if not all(config_status.values()):
        logger.warning("⚠️ Some services are not properly configured")
    else:
        logger.info("✅ All systems operational!")

@app.get("/")
async def root():
    """נקודת כניסה בסיסית"""
    return {
        "message": "Wedding System WhatsApp Bot is running!",
        "version": "2.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """בדיקת תקינות המערכת"""
    try:
        # בדיקת שירותי הבוט
        health_status = bot_handler.health_check()
        
        return {
            "status": "healthy" if all(health_status.values()) else "degraded",
            "services": health_status,
            "timestamp": "2024-01-01T00:00:00Z"  # יעודכן אוטומטית
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.post("/webhook")
async def webhook_handler(request: Request):
    """מטפל ב-webhook של WhatsApp"""
    
    try:
        # קבלת הנתונים
        payload = await request.json()
        
        # אימות webhook
        if not bot_handler.verify_webhook_signature(request):
            logger.warning("🚫 Unauthorized webhook request")
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # עיבוד ההודעה
        result = await bot_handler.process_webhook(payload)
        
        # לוג התוצאה
        if result.get("status") == "error":
            logger.error(f"❌ Webhook processing failed: {result.get('error')}")
        elif result.get("status") not in ["ignored", "regular_message"]:
            logger.info(f"✅ Webhook processed: {result.get('status')}")
        
        return JSONResponse(
            status_code=200,
            content={"success": True, "result": result}
        )
        
    except ValueError as e:
        logger.error(f"❌ Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    except Exception as e:
        logger.error(f"❌ Webhook handler error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/webhook")
async def webhook_verification(request: Request):
    """אימות webhook (לשירותים שדורשים GET verification)"""
    
    # אם יש פרמטר verification
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if verify_token and challenge:
        # כאן אפשר להוסיף בדיקת טוכן אימות
        return challenge
    
    return {"message": "Webhook endpoint is active", "method": "GET"}

@app.post("/test-message")
async def test_message(request: Request):
    """נקודת קצה לבדיקת שליחת הודעות (לפיתוח בלבד)"""
    
    try:
        data = await request.json()
        chat_id = data.get("chat_id")
        message = data.get("message")
        
        if not chat_id or not message:
            raise HTTPException(status_code=400, detail="Missing chat_id or message")
        
        # שליחת הודעת בדיקה
        success = await bot_handler._send_message(chat_id, message)
        
        if success:
            return {"success": True, "message": "Test message sent"}
        else:
            return {"success": False, "error": "Failed to send message"}
            
    except Exception as e:
        logger.error(f"Test message error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """סטטיסטיקות מערכת"""
    
    try:
        from google_services import get_google_services
        from auth_system import get_auth_manager
        
        gs = get_google_services()
        auth = get_auth_manager()
        
        # סטטיסטיקות מהמערכת
        system_stats = gs.get_statistics()
        auth_stats = auth.get_auth_statistics()
        
        return {
            "system": system_stats,
            "auth": auth_stats,
            "bot": {
                "active": True,
                "version": "2.0.0"
            }
        }
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stats")

# Error Handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """טיפול ב-404"""
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "path": str(request.url)}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """טיפול בשגיאות פנימיות"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

def run_webhook_server(host: str = "0.0.0.0", port: int = 8000):
    """הרצת שרת ה-webhook"""
    
    logger.info(f"🌐 Starting webhook server on {host}:{port}")
    
    uvicorn.run(
        "webhook_handler:app",
        host=host,
        port=port,
        reload=False,  # True לפיתוח, False לייצור
        log_level="info"
    )

if __name__ == "__main__":
    # הרצה ישירה
    import os
    
    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("WEBHOOK_PORT", "8000"))
    
    run_webhook_server(host, port)