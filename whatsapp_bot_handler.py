import re
import json
import logging
import httpx
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from fastapi import Request
import hashlib

from config import (
    GREENAPI_INSTANCE_ID, 
    GREENAPI_TOKEN,
    WEBHOOK_SHARED_SECRET,
    BOT_MESSAGES,
    COLORS,
    get_dashboard_url,
    get_contacts_merge_url
)
from google_services import get_google_services
from ai_analyzer import get_ai_analyzer
from auth_system import get_auth_manager

logger = logging.getLogger(__name__)

class WhatsAppBotHandler:
    """מטפל בוט WhatsApp מאוחד"""
    
    def __init__(self):
        self.gs = get_google_services()
        self.ai = get_ai_analyzer()
        self.auth = get_auth_manager()
        
        # cache לזיכרון קצר מועד
        self.recent_expenses = {}  # {group_id: last_expense}
        self.last_messages = {}    # {group_id: last_message_time}
        
        logger.info("✅ WhatsApp Bot Handler initialized")
    
    def verify_webhook_signature(self, request: Request) -> bool:
        """אימות webhook"""
        if not WEBHOOK_SHARED_SECRET:
            logger.warning("⚠️ No webhook secret configured - allowing all requests")
            return True
        
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        
        if not auth_header:
            return False
        
        return (
            auth_header.endswith(WEBHOOK_SHARED_SECRET) or 
            auth_header == f"Bearer {WEBHOOK_SHARED_SECRET}"
        )
    
    async def process_webhook(self, payload: Dict) -> Dict:
        """עיבוד webhook נכנס מWhatsApp"""
        
        try:
            # חילוץ נתונים בסיסיים
            message_data = payload.get("messageData", {})
            sender_data = payload.get("senderData", {})
            
            message_type = message_data.get("typeMessage")
            chat_id = sender_data.get("chatId", "")
            sender_phone = sender_data.get("sender", "")
            
            logger.info(f"📩 Received {message_type} from {chat_id}")
            
            if not chat_id:
                return {"status": "ignored", "reason": "no_chat_id"}
            
            # בדיקה שהקבוצה קיימת במערכת - זה הביטחון שלנו!
            couple = self.gs.get_couple_by_group_id(chat_id)
            if not couple:
                logger.info(f"📝 Group not found in system: {chat_id}")
                # לא שולח הודעה - פשוט מתעלם (זה מה שביקשת!)
                return {"status": "group_not_found", "chat_id": chat_id}
            
            # עיבוד לפי סוג הודעה
            if message_type == "textMessage":
                return await self._handle_text_message(chat_id, message_data, couple)
            
            elif message_type == "imageMessage":
                return await self._handle_image_message(chat_id, message_data, couple)
            
            else:
                logger.debug(f"Unsupported message type: {message_type}")
                return {"status": "ignored", "message_type": message_type}
            
        except Exception as e:
            logger.error(f"❌ Webhook processing failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_text_message(self, chat_id: str, message_data: Dict, couple: Dict) -> Dict:
        """טיפול בהודעות טקסט"""
        
        try:
            text_message_data = message_data.get("textMessageData", {})
            text = text_message_data.get("textMessage", "").strip()
            
            if not text:
                return {"status": "empty_message"}
            
            logger.info(f"📝 Processing text: {text[:50]}...")
            
            # פקודות מערכת
            if await self._handle_system_commands(chat_id, text, couple):
                return {"status": "system_command_handled"}
            
            # בדיקת עדכון להוצאה אחרונה
            recent_expense = self.recent_expenses.get(chat_id)
            if recent_expense and await self._handle_update_request(chat_id, text, recent_expense):
                return {"status": "update_handled"}
            
            # ניתוח הודעה כהוצאה חדשה
            expense_data = self.ai.analyze_text_expense(text, chat_id)
            
            if expense_data:
                # נמצאה הוצאה חדשה
                success = self.gs.save_expense(expense_data)
                
                if success:
                    # שליחת אישור
                    message = BOT_MESSAGES["receipt_saved"].format(
                        vendor=expense_data.get('vendor', 'ספק'),
                        amount=expense_data.get('amount', 0),
                        category=expense_data.get('category', 'אחר')
                    )
                    
                    await self._send_message(chat_id, message)
                    
                    # שמירה בזיכרון לעדכונים
                    self.recent_expenses[chat_id] = expense_data
                    
                    return {"status": "expense_saved", "expense": expense_data}
                else:
                    await self._send_message(chat_id, BOT_MESSAGES["error"])
                    return {"status": "save_failed"}
            
            # אם זה לא פקודה ולא הוצאה - עזרה עדינה רק אם נראה שמנסה
            if any(word in text.lower() for word in ['שילמתי', 'עלה', 'קיבל', 'תשלום', 'מקדמה']):
                await self._send_message(chat_id, BOT_MESSAGES["help"])
                return {"status": "help_sent"}
            
            # הודעה רגילה - לא מגיב
            return {"status": "regular_message"}
            
        except Exception as e:
            logger.error(f"❌ Text message handling failed: {e}")
            await self._send_message(chat_id, BOT_MESSAGES["error"])
            return {"status": "error", "error": str(e)}
    
    async def _handle_image_message(self, chat_id: str, message_data: Dict, couple: Dict) -> Dict:
        """טיפול בתמונות קבלות"""
        
        try:
            # הורדת התמונה
            image_data = await self._download_image(message_data)
            
            if not image_data:
                await self._send_message(chat_id, "שגיאה בהורדת התמונה. אנא נסה שוב 📸")
                return {"status": "download_failed"}
            
            logger.info(f"📸 Processing image ({len(image_data)} bytes)")
            
            # ניתוח עם AI
            receipt_data = self.ai.analyze_receipt_image(image_data, chat_id)
            
            # העלאה לדרייב
            receipt_url = self.gs.upload_receipt_image(
                chat_id, 
                image_data, 
                f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            )
            
            if receipt_url:
                receipt_data['receipt_image_url'] = receipt_url
            
            # בדיקה אם התמונה לא ברורה
            if receipt_data.get('needs_review') or receipt_data.get('amount', 0) == 0:
                # תמונה לא ברורה - בקש פרטים
                await self._send_message(chat_id, """😅 התמונה קצת לא ברורה...

רק תכתבו לי:
💰 כמה שילמתם?
🏪 לאיזה ספק?

ואני אדאג לשמור!""")
                
                # שמור בכל זאת עם needs_review
                receipt_data['needs_review'] = True
                self.gs.save_expense(receipt_data)
                
                return {"status": "image_unclear", "expense": receipt_data}
            
            # שמירה בדאטא בייס
            success = self.gs.save_expense(receipt_data)
            
            if success:
                # הודעת אישור מעוצבת
                message = BOT_MESSAGES["receipt_saved"].format(
                    vendor=receipt_data.get('vendor', 'ספק'),
                    amount=receipt_data.get('amount', 0),
                    category=receipt_data.get('category', 'אחר')
                )
                
                await self._send_message(chat_id, message)
                
                # שמירה בזיכרון
                self.recent_expenses[chat_id] = receipt_data
                
                logger.info(f"✅ Receipt processed successfully: {receipt_data.get('vendor')}")
                return {"status": "receipt_processed", "expense": receipt_data}
            else:
                await self._send_message(chat_id, BOT_MESSAGES["error"])
                return {"status": "save_failed"}
            
        except Exception as e:
            logger.error(f"❌ Image processing failed: {e}")
            await self._send_message(chat_id, BOT_MESSAGES["error"])
            return {"status": "error", "error": str(e)}
    
    async def _handle_system_commands(self, chat_id: str, text: str, couple: Dict) -> bool:
        """טיפול בפקודות מערכת"""
        
        text_lower = text.lower().strip()
        
        # פקודת דשבורד
        if any(word in text_lower for word in ['דשבורד', 'דש', 'dashboard']):
            dashboard_url = self.auth.get_dashboard_link(chat_id, "http://localhost:8501")  # TODO: החלף עם BASE_URL אמיתי
            
            if dashboard_url:
                message = BOT_MESSAGES["dashboard_link"].format(link=dashboard_url)
                await self._send_message(chat_id, message)
            else:
                await self._send_message(chat_id, "שגיאה ביצירת קישור דשבורד")
            
            return True
        
        # פקודת חיבור אנשי קשר
        elif any(word in text_lower for word in ['חבר אנשי קשר', 'אנשי קשר', 'מוזמנים', 'contacts']):
            merge_url = self.auth.get_contacts_merge_link(chat_id, "", "http://localhost:8501")  # TODO: החלף עם BASE_URL אמיתי
            
            if merge_url:
                message = BOT_MESSAGES["contact_merge_ready"].format(link=merge_url)
                await self._send_message(chat_id, message)
            else:
                await self._send_message(chat_id, "שגיאה ביצירת קישור חיבור אנשי קשר")
            
            return True
        
        # פקודת עזרה
        elif any(word in text_lower for word in ['עזרה', 'help', 'הוראות']):
            await self._send_message(chat_id, BOT_MESSAGES["help"])
            return True
        
        # פקודת סיכום
        elif any(word in text_lower for word in ['סיכום', 'summary', 'סך הכל']):
            await self._send_summary(chat_id)
            return True
        
        return False
    
    async def _handle_update_request(self, chat_id: str, text: str, recent_expense: Dict) -> bool:
        """טיפול בבקשות עדכון"""
        
        try:
            update_data = self.ai.analyze_message_for_updates(text, recent_expense)
            
            if not update_data or not update_data.get('is_update'):
                return False
            
            update_type = update_data.get('update_type')
            new_value = update_data.get('new_value')
            
            if update_type == 'delete':
                # מחיקת הוצאה
                success = self.gs.delete_expense(recent_expense.get('expense_id'))
                if success:
                    await self._send_message(chat_id, "✅ ההוצאה נמחקה")
                    self.recent_expenses[chat_id] = None
                else:
                    await self._send_message(chat_id, "❌ שגיאה במחיקת ההוצאה")
            
            else:
                # עדכון הוצאה
                updates = {update_type: new_value}
                success = self.gs.update_expense(recent_expense.get('expense_id'), updates)
                
                if success:
                    # עדכון הזיכרון המקומי
                    recent_expense[update_type] = new_value
                    
                    message = BOT_MESSAGES["expense_updated"].format(
                        vendor=recent_expense.get('vendor', 'ספק'),
                        amount=recent_expense.get('amount', 0)
                    )
                    await self._send_message(chat_id, message)
                else:
                    await self._send_message(chat_id, "❌ שגיאה בעדכון ההוצאה")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Update handling failed: {e}")
            return False
    
    async def _send_summary(self, chat_id: str):
        """שליחת סיכום הוצאות"""
        
        try:
            expenses = self.gs.get_expenses_by_group(chat_id)
            active_expenses = [exp for exp in expenses if exp.get('status') == 'active']
            
            if not active_expenses:
                await self._send_message(chat_id, "📝 עדיין אין הוצאות רשומות")
                return
            
            total_amount = sum(float(exp.get('amount', 0)) for exp in active_expenses)
            total_count = len(active_expenses)
            
            # הוצאה הגדולה ביותר
            max_expense = max(active_expenses, key=lambda x: float(x.get('amount', 0)))
            
            # קטגוריות
            categories = {}
            for exp in active_expenses:
                cat = exp.get('category', 'אחר')
                categories[cat] = categories.get(cat, 0) + float(exp.get('amount', 0))
            
            top_category = max(categories.items(), key=lambda x: x[1]) if categories else ('אחר', 0)
            
            summary_message = f"""📊 **סיכום הוצאות החתונה**

💰 **סך הכל**: {total_amount:,.0f} ₪
📋 **מספר קבלות**: {total_count}
📊 **ממוצע לקבלה**: {total_amount/total_count:,.0f} ₪

🔝 **הוצאה הגדולה ביותר**:
{max_expense.get('vendor', 'לא ידוע')} - {float(max_expense.get('amount', 0)):,.0f} ₪

🏷️ **קטגוריה יקרה ביותר**:
{top_category[0]} - {top_category[1]:,.0f} ₪

📱 לדשבורד מפורט הקלידו: דשבורד"""
            
            await self._send_message(chat_id, summary_message)
            
        except Exception as e:
            logger.error(f"❌ Summary generation failed: {e}")
            await self._send_message(chat_id, "❌ שגיאה ביצירת סיכום")
    
    async def _download_image(self, message_data: Dict) -> Optional[bytes]:
        """הורדת תמונה מWhatsApp"""
        
        try:
            # חילוץ נתוני התמונה
            image_data = message_data.get("fileMessageData", {})
            download_url = image_data.get("downloadUrl", "")
            
            if not download_url:
                logger.error("No download URL found in image message")
                return None
            
            # הורדת התמונה
            async with httpx.AsyncClient() as client:
                response = await client.get(download_url, timeout=30)
                
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"Failed to download image: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Image download failed: {e}")
            return None
    
    async def _send_message(self, chat_id: str, message: str) -> bool:
        """שליחת הודעה לWhatsApp"""
        
        try:
            if not GREENAPI_INSTANCE_ID or not GREENAPI_TOKEN:
                logger.error("WhatsApp credentials not configured")
                return False
            
            url = f"https://api.green-api.com/waInstance{GREENAPI_INSTANCE_ID}/sendMessage/{GREENAPI_TOKEN}"
            
            payload = {
                "chatId": chat_id,
                "message": message
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    logger.info(f"✅ Message sent to {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to send message: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error sending message: {e}")
            return False
    
    def health_check(self) -> Dict[str, bool]:
        """בדיקת תקינות הבוט"""
        
        checks = {
            "whatsapp_configured": bool(GREENAPI_INSTANCE_ID and GREENAPI_TOKEN),
            "google_services": False,
            "ai_analyzer": False,
            "auth_system": False
        }
        
        try:
            # בדיקת Google Services
            if self.gs:
                gs_health = self.gs.health_check()
                checks["google_services"] = all(gs_health.values())
            
            # בדיקת AI
            if self.ai:
                ai_health = self.ai.health_check()
                checks["ai_analyzer"] = all(ai_health.values())
            
            # בדיקת Auth
            if self.auth:
                checks["auth_system"] = True
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        
        return checks


# ===== מופע גלובלי =====
_bot_handler = None

def get_bot_handler() -> WhatsAppBotHandler:
    """קבלת מופע יחיד של הבוט"""
    global _bot_handler
    if _bot_handler is None:
        _bot_handler = WhatsAppBotHandler()
    return _bot_handler


# ===== בדיקה =====
if __name__ == "__main__":
    print("🧪 Testing WhatsApp Bot Handler...")
    
    try:
        bot = WhatsAppBotHandler()
        
        # בדיקת תקינות
        health = bot.health_check()
        print("📊 Health Check Results:")
        for service, status in health.items():
            emoji = "✅" if status else "❌"
            print(f"{emoji} {service}")
        
        print("✅ WhatsApp Bot Handler test completed")
        
    except Exception as e:
        print(f"❌ Bot test failed: {e}")