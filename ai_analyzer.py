import re
import json
import base64
import logging
from datetime import datetime
from typing import Dict, Optional, List
from openai import OpenAI

from config import (
    OPENAI_API_KEY,
    AI_SETTINGS,
    WEDDING_CATEGORIES,
    CATEGORY_LIST,
    COLORS
)

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """מנתח תמונות קבלות והודעות טקסט עם OpenAI"""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        
        if not self.client:
            logger.warning("⚠️ OpenAI client not initialized - API key missing")
        else:
            logger.info("✅ AI Analyzer initialized successfully")
    
    def analyze_receipt_image(self, image_bytes: bytes, group_id: str = None) -> Dict:
        """מנתח תמונת קבלה ומחזיר נתונים מובנים"""
        
        if not self.client:
            logger.error("OpenAI client not available")
            return self._create_fallback_receipt()
        
        try:
            # המרה ל-base64
            b64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # הכנת פרומפט מפורט
            system_prompt = self._get_receipt_analysis_prompt()
            user_prompt = "נתח את תמונת הקבלה הזו ותחזיר JSON עם כל הנתונים הרלוונטיים:"
            
            # קריאה ל-OpenAI
            response = self.client.chat.completions.create(
                model=AI_SETTINGS["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            expense_data = self._parse_ai_response(content)
            
            if expense_data.get('is_expense'):
                # ניקוי והכנת הנתונים
                cleaned_data = self._clean_and_validate_receipt(expense_data)
                cleaned_data['source'] = 'text_analysis'
                cleaned_data['analyzed_at'] = datetime.now().isoformat()
                if group_id:
                    cleaned_data['group_id'] = group_id
                
                logger.info(f"✅ Successfully analyzed text expense: {cleaned_data.get('vendor', 'Unknown')}")
                return cleaned_data
            else:
                logger.debug("Text message is not an expense")
                return None
                
        except Exception as e:
            logger.error(f"❌ Text expense analysis failed: {e}")
            # נסה ניתוח בסיסי כגיבוי
            return self._parse_manual_text_basic(message)
    
    def _get_text_analysis_prompt(self) -> str:
        """פרומפט לניתוח הודעות טקסט"""
        categories_text = ", ".join(CATEGORY_LIST)
        
        return f"""אתה מומחה בזיהוי הוצאות מטקסט חופשי לחתונות בישראל.

זהה אם ההודעה מתארת הוצאה והחלץ את הפרטים.

דוגמאות להוצאות:
- "שילמתי 2000 שח לצלם"
- "5000 מקדמה לאולם בני ברק"  
- "עלה לנו 800 שקל בפרחים"
- "DJ קיבל 3500"
- "נתתי 1200 למעצבת השמלה"

דוגמאות לא הוצאות:
- "מתי החתונה?"
- "איך מגיעים לאולם?"
- "תודה רבה"

קטגוריות זמינות: {categories_text}

JSON נדרש:
{{
  "is_expense": true/false,
  "vendor": "שם הספק או null",
  "amount": מספר או null,
  "category": "קטגוריה מהרשימה",
  "payment_method": "card/cash/bank או null",
  "description": "תיאור קצר",
  "confidence": מספר 0-100
}}

אם זה לא הוצאה, החזר: {{"is_expense": false}}

החזר רק JSON תקין!"""
    
    def _parse_manual_text_basic(self, message: str) -> Optional[Dict]:
        """ניתוח בסיסי של טקסט ללא AI"""
        try:
            text = message.strip().lower()
            
            # בדיקה שזה נראה כמו הוצאה
            expense_indicators = [
                'שילמתי', 'שילמנו', 'עלה', 'עולה', 'היה', 'עלות',
                'נתתי', 'נתנו', 'קיבל', 'קבל', 'מקדמה', 'תשלום'
            ]
            
            if not any(indicator in text for indicator in expense_indicators):
                return None
            
            # חיפוש סכום
            amount_patterns = [
                r'(\d+(?:,?\d{3})*(?:\.\d+)?)\s*(?:ש"ח|שח|שקל|שקלים|₪)',
                r'(?:שילמתי|שילמנו|עלה|עולה|היה|עלות|נתתי|קיבל)\s+(\d+(?:,?\d{3})*(?:\.\d+)?)',
                r'(\d+(?:,?\d{3})*(?:\.\d+)?)\s+(?:ל|עבור|בשביל)',
                r'(\d{4,})',  # מספר של לפחות 4 ספרות
            ]
            
            amount = None
            for pattern in amount_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        amount_str = match.group(1).replace(',', '')
                        amount = float(amount_str)
                        if amount > 0:
                            break
                    except (ValueError, AttributeError):
                        continue
            
            if not amount:
                return None
            
            # חיפוש ספק
            vendor_patterns = [
                r'(?:ל|עבור|בשביל|אצל|ב|מ|של)\s*([א-ת\s]+?)(?:\s+|$)',
                r'(צלם|אולם|דיג׳יי|קייטרינג|להקה|זמר|פרחים|שמלה|חליפה|עוגה|הזמנות)',
            ]
            
            vendor = None
            for pattern in vendor_patterns:
                match = re.search(pattern, text)
                if match:
                    potential_vendor = match.group(1).strip()
                    if potential_vendor and len(potential_vendor) > 1:
                        stop_words = ['שילמתי', 'שילמנו', 'עלה', 'עולה', 'ש"ח', 'שקל', 'שקלים']
                        if not any(word in potential_vendor for word in stop_words):
                            vendor = potential_vendor
                            break
            
            if not vendor:
                vendor = 'ספק לא מוגדר'
            
            # זיהוי קטגוריה
            category_keywords = {
                'צלם': 'צילום',
                'צילום': 'צילום',
                'אולם': 'אולם',
                'גן': 'אולם',
                'דיג׳יי': 'מוזיקה',
                'dj': 'מוזיקה',
                'להקה': 'מוזיקה',
                'זמר': 'מוזיקה',
                'קייטרינג': 'מזון',
                'אוכל': 'מזון',
                'עוגה': 'מזון',
                'פרחים': 'עיצוב',
                'עיצוב': 'עיצוב',
                'שמלה': 'לבוש',
                'חליפה': 'לבוש',
                'הזמנות': 'הדפסות'
            }
            
            category = 'אחר'
            for keyword, cat in category_keywords.items():
                if keyword in text:
                    category = cat
                    break
            
            # זיהוי סוג תשלום
            payment_type_keywords = {
                'מקדמה': 'advance',
                'קדימה': 'advance',
                'ראשון': 'advance',
                'סופי': 'final',
                'אחרון': 'final',
                'יתרה': 'final'
            }
            
            payment_type = 'full'
            for keyword, ptype in payment_type_keywords.items():
                if keyword in text:
                    payment_type = ptype
                    break
            
            return {
                'vendor': vendor,
                'amount': amount,
                'category': category,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'payment_method': None,
                'description': f'תשלום {payment_type}',
                'confidence': 70,
                'needs_review': False,
                'source': 'manual_text_basic'
            }
            
        except Exception as e:
            logger.error(f"Basic text parsing failed: {e}")
            return None
    
    def analyze_message_for_updates(self, message: str, recent_expense: Dict) -> Optional[Dict]:
        """מנתח הודעה לזיהוי בקשות עדכון לקבלה אחרונה"""
        
        if not self.client or not message.strip():
            return self._analyze_updates_basic(message, recent_expense)
        
        try:
            prompt = f"""אנתח הודעה לזיהוי בקשות עדכון לקבלה אחרונה.

הקבלה האחרונה:
ספק: {recent_expense.get('vendor', 'לא ידוע')}
סכום: {recent_expense.get('amount', 0)} ש"ח
קטגוריה: {recent_expense.get('category', 'אחר')}

ההודעה: "{message}"

קטגוריות זמינות: {', '.join(CATEGORY_LIST)}

אם זה בקשת עדכון, החזר JSON:
{{
  "is_update": true,
  "update_type": "vendor/amount/category/delete",
  "new_value": "הערך החדש או null למחיקה",
  "confidence": מספר 0-100
}}

אם זה לא בקשת עדכון:
{{
  "is_update": false
}}

דוגמאות לעדכונים:
- "זה בגדים לא צילום" → update_type: "category", new_value: "לבוש"
- "2500 לא 2000" → update_type: "amount", new_value: "2500"
- "זה רמי לוי" → update_type: "vendor", new_value: "רמי לוי"
- "מחק את זה" → update_type: "delete", new_value: null

החזר רק JSON תקין!"""

            response = self.client.chat.completions.create(
                model=AI_SETTINGS["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            result = self._parse_ai_response(content)
            
            if result.get('is_update') and result.get('confidence', 0) > 60:
                logger.info(f"✅ Detected update request: {result.get('update_type')}")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Message analysis failed: {e}")
            return self._analyze_updates_basic(message, recent_expense)
    
    def _analyze_updates_basic(self, message: str, recent_expense: Dict) -> Optional[Dict]:
        """ניתוח בסיסי של בקשות עדכון"""
        try:
            text = message.strip().lower()
            
            # זיהוי מחיקה
            delete_patterns = [
                'מחק', 'מחק את זה', 'תמחק', 'בטל', 'הסר', 'delete', 'remove'
            ]
            if any(pattern in text for pattern in delete_patterns):
                return {
                    "is_update": True,
                    "update_type": "delete",
                    "new_value": None,
                    "confidence": 90
                }
            
            # זיהוי עדכון סכום
            amount_patterns = [
                r'(\d+(?:,?\d{3})*(?:\.\d+)?)\s*(?:לא|במקום)',
                r'(?:לא|במקום)\s*(\d+(?:,?\d{3})*(?:\.\d+)?)',
                r'(?:תקן ל|שנה ל|צריך להיות)\s*(\d+(?:,?\d{3})*(?:\.\d+)?)',
                r'זה\s*(\d+(?:,?\d{3})*(?:\.\d+)?)'
            ]
            
            for pattern in amount_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        amount = float(match.group(1).replace(',', ''))
                        if amount > 0:
                            return {
                                "is_update": True,
                                "update_type": "amount",
                                "new_value": str(amount),
                                "confidence": 85
                            }
                    except ValueError:
                        continue
            
            # זיהוי עדכון קטגוריה
            for category in CATEGORY_LIST:
                category_lower = category.lower()
                patterns = [
                    f'זה {category_lower}',
                    f'{category_lower} לא',
                    f'לא {category_lower}',
                    f'צריך להיות {category_lower}'
                ]
                
                for pattern in patterns:
                    if pattern in text:
                        return {
                            "is_update": True,
                            "update_type": "category",
                            "new_value": category,
                            "confidence": 80
                        }
            
            # זיהוי עדכון ספק
            vendor_patterns = [
                r'זה\s+([א-ת\s]+?)(?:\s|$)',
                r'(?:לא|במקום)\s+([א-ת\s]+?)(?:\s|$)',
                r'(?:צריך להיות|שנה ל)\s+([א-ת\s]+?)(?:\s|$)'
            ]
            
            for pattern in vendor_patterns:
                match = re.search(pattern, text)
                if match:
                    vendor = match.group(1).strip()
                    if len(vendor) >= 2 and vendor not in ['זה', 'לא', 'במקום']:
                        return {
                            "is_update": True,
                            "update_type": "vendor",
                            "new_value": vendor,
                            "confidence": 75
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Basic update analysis failed: {e}")
            return None
    
    # ===== פונקציות עזר =====
    
    def health_check(self) -> Dict[str, bool]:
        """בדיקת תקינות מנוע ה-AI"""
        checks = {
            "openai_configured": bool(self.client),
            "can_analyze_text": False,
            "can_analyze_images": False,
            "model_accessible": False
        }
        
        if self.client:
            try:
                # בדיקה בסיסית
                response = self.client.chat.completions.create(
                    model=AI_SETTINGS["model"],
                    messages=[{"role": "user", "content": "Test message"}],
                    max_tokens=10
                )
                
                if response.choices:
                    checks["can_analyze_text"] = True
                    checks["can_analyze_images"] = True  # אם טקסט עובד, גם תמונות
                    checks["model_accessible"] = True
                    
            except Exception as e:
                logger.error(f"AI health check failed: {e}")
        
        return checks
    
    def get_ai_statistics(self) -> Dict:
        """סטטיסטיקות שימוש ב-AI"""
        return {
            "model_name": AI_SETTINGS["model"],
            "max_tokens": AI_SETTINGS["max_tokens"],
            "temperature": AI_SETTINGS["temperature"],
            "categories_count": len(CATEGORY_LIST),
            "configured": bool(self.client)
        }


# ===== מופע גלובלי =====
_ai_analyzer = None

def get_ai_analyzer() -> AIAnalyzer:
    """קבלת מופע יחיד של AIAnalyzer"""
    global _ai_analyzer
    if _ai_analyzer is None:
        _ai_analyzer = AIAnalyzer()
    return _ai_analyzer


# ===== בדיקה =====
if __name__ == "__main__":
    print("🧪 Testing AI Analyzer...")

    try:
        ai = AIAnalyzer()
        
        # בדיקת תקינות
        health = ai.health_check()
        print("📊 Health Check Results:")
        for service, status in health.items():
            emoji = "✅" if status else "❌"
            print(f"{emoji} {service}")
        
        # בדיקת ניתוח טקסט
        if health.get("can_analyze_text"):
            test_message = "שילמתי 2000 שח לצלם דני"
            result = ai.analyze_text_expense(test_message)
            print(f"📝 Text analysis test: {result}")
        
        # סטטיסטיקות
        stats = ai.get_ai_statistics()
        print(f"📈 AI Statistics: {stats}")
        
        print("✅ AI Analyzer test completed")

    except Exception as e:
        print(f"❌ AI test failed: {e}")


    # שימוש ב־OpenAI API עם תמונה + טקסט
    response = client.chat.completions.create(
        model=AI_SETTINGS["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_image}",
                    "detail": "high"
                }}
            ]}
        ],
        temperature=AI_SETTINGS["temperature"],
        max_tokens=AI_SETTINGS["max_tokens"]
    )

    # עיבוד התשובה
    content = response.choices[0].message.content.strip()
    receipt_data = self._parse_ai_response(content)

    # ניקוי ואימות הנתונים
    receipt_data = self._clean_and_validate_receipt(receipt_data)

    # הוספת מידע נוסף
    receipt_data['analyzed_at'] = datetime.now().isoformat()
    receipt_data['source'] = 'image_analysis'
    if group_id:
        receipt_data['group_id'] = group_id

    logger.info(f"✅ Successfully analyzed receipt: {receipt_data.get('vendor', 'Unknown')}")
    return receipt_data

        
    
    def _get_receipt_analysis_prompt(self) -> str:
        """יוצר פרומפט מפורט לניתוח קבלות"""
        categories_text = ", ".join(CATEGORY_LIST)
        
        return f"""אתה מומחה בניתוח קבלות ותמונות חשבוניות לחתונות בישראל.

חוקי ניתוח קריטיים:
1. תאריך - בישראל התאריך הוא יום/חודש/שנה (DD/MM/YYYY)
2. סכום - חפש את הסכום הסופי בלבד! מילים כמו "סה״כ", "סך הכל", "לתשלום", "Total"
3. ספק - שם העסק הראשי בראש הקבלה או על החשבונית
4. מטבע - ₪, שקל, NIS = ILS; $ = USD; € = EUR
5. קטגוריה - בחר מהרשימה: {categories_text}

כללי קטגוריזציה לחתונות:
- אולם: אולמות אירועים, גנים, מתחמי אירועים, השכרת מקום
- מזון: קייטרינג, מסעדות, עוגות, פירות, משקאות, יין, שף אישי
- צילום: צלמים, וידאו, דרונים, עריכה, אלבומים, הדפסת תמונות
- לבוש: שמלות כלה, חליפות חתן, נעליים, בגדים מיוחדים לחתונה
- עיצוב: פרחים, זרים, דקורציה, קישוטים, עיצוב שולחנות
- הדפסות: הזמנות, שלטים, תפריטים, כרטיסי ברכה
- אקססוריז: תכשיטים, שעונים, תיקים, עניבות, חפצים אישיים
- מוזיקה: דיג'יי, להקות, זמרים, כלי נגינה, הגברה, תאורה
- הסעות: מוניות, אוטובוסים, השכרת רכב, לינה למוזמנים
- אחר: כל דבר שלא מתאים לקטגוריות האחרות

חוקים חשובים:
- אם לא בטוח - תן null ולא תמציא מידע
- סכום חייב להיות מספר חיובי או null
- תאריך בפורמט YYYY-MM-DD או null
- ספק - שם נקי ללא "בע״מ", "ש.מ", "Ltd" או תוספות מיותרות
- תמיד נסה לזהות את אמצעי התשלום

JSON נדרש:
{{
  "vendor": "שם הספק נקי או null",
  "amount": מספר_חיובי או null,
  "date": "YYYY-MM-DD" או null,
  "category": "קטגוריה מהרשימה המדויקת",
  "payment_method": "card/cash/bank/check או null",
  "description": "תיאור קצר של השירות או המוצר",
  "invoice_number": "מספר חשבונית או null",
  "confidence": מספר בין 0-100 (כמה אתה בטוח בניתוח)
}}

חשוב: החזר רק JSON תקין, בלי טקסט נוסף כלל!"""
    
    def _parse_ai_response(self, content: str) -> Dict:
        """מפרסר תשובת AI ומחזיר dict"""
        try:
            # ניקוי מארקדאון וטקסט מיותר
            content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
            content = re.sub(r"\s*```$", "", content)
            content = content.strip()
            
            # ניסיון לפרסר JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # ניסיון תיקון בסיסי של JSON
                content = content.replace("'", '"')  # החלפת גרשיים
                content = re.sub(r',\s*}', '}', content)  # הסרת פסיק לפני }
                content = re.sub(r',\s*]', ']', content)  # הסרת פסיק לפני ]
                data = json.loads(content)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.debug(f"Raw content: {content}")
            return {}
    
    def _clean_and_validate_receipt(self, data: Dict) -> Dict:
        """מנקה ומאמת נתוני קבלה"""
        cleaned = {}
        
        # ניקוי ספק
        vendor = data.get('vendor')
        if vendor and len(str(vendor).strip()) >= 2:
            vendor = str(vendor).strip()
            # הסר ביטויים מיותרים
            vendor = re.sub(r'(בע"מ|בעמ|ש\.מ|ltd|inc|corp).*$', '', vendor, flags=re.IGNORECASE).strip()
            cleaned['vendor'] = vendor[:100]  # הגבלת אורך
        else:
            cleaned['vendor'] = self._generate_fallback_vendor_name(data)
        
        # ניקוי סכום
        amount = data.get('amount')
        if amount is not None:
            try:
                if isinstance(amount, str):
                    # הסר כל מה שלא מספר או נקודה עשרונית
                    amount = re.sub(r'[^\d.]', '', amount.replace(',', ''))
                amount = float(amount)
                cleaned['amount'] = round(amount, 2) if amount > 0 else 0
            except (ValueError, TypeError):
                cleaned['amount'] = 0
        else:
            cleaned['amount'] = 0
        
        # ניקוי תאריך
        date_str = data.get('date')
        cleaned['date'] = self._normalize_date(date_str)
        
        # ניקוי קטגוריה
        category = data.get('category', 'אחר')
        if category in CATEGORY_LIST:
            cleaned['category'] = category
        else:
            # ניסיון למצוא קטגוריה קרובה
            category_lower = category.lower() if category else ''
            for valid_category in CATEGORY_LIST:
                if valid_category.lower() in category_lower or category_lower in valid_category.lower():
                    cleaned['category'] = valid_category
                    break
            else:
                cleaned['category'] = 'אחר'
        
        # ניקוי אמצעי תשלום
        payment = data.get('payment_method')
        cleaned['payment_method'] = self._normalize_payment_method(payment)
        
        # תיאור
        description = data.get('description', '')
        if description and len(str(description).strip()) > 3:
            cleaned['description'] = str(description).strip()[:200]  # הגבלת אורך
        else:
            cleaned['description'] = ''
        
        # מספר חשבונית
        invoice = data.get('invoice_number')
        if invoice and len(str(invoice).strip()) >= 2:
            cleaned['invoice_number'] = str(invoice).strip()[:50]
        else:
            cleaned['invoice_number'] = ''
        
        # רמת ביטחון
        confidence = data.get('confidence', 80)
        try:
            cleaned['confidence'] = max(0, min(100, int(confidence)))
        except:
            cleaned['confidence'] = 80
        
        # קביעת needs_review
        cleaned['needs_review'] = (
            cleaned['amount'] == 0 or 
            not cleaned['vendor'] or
            cleaned['confidence'] < 70
        )
        
        return cleaned
    
    def _generate_fallback_vendor_name(self, data: Dict) -> str:
        """יוצר שם ספק כשלא מזהה"""
        category = data.get('category', 'אחר')
        
        fallbacks = {
            'אולם': 'אולם אירועים',
            'מזון': 'ספק מזון', 
            'צילום': 'צלם',
            'לבוש': 'חנות בגדים',
            'עיצוב': 'מעצב פרחים',
            'הדפסות': 'דפוס',
            'אקססוריז': 'חנות אקססוריז',
            'מוזיקה': 'מוזיקאי',
            'הסעות': 'הסעות',
            'אחר': 'ספק לא מזוהה'
        }
        
        return fallbacks.get(category, 'ספק לא מזוהה')
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """מנרמל תאריך לפורמט ISO"""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')
        
        try:
            date_str = str(date_str).strip()
            
            # פטרנים ישראליים שונים
            patterns = [
                (r'(\d{1,2})[/./-](\d{1,2})[/./-](\d{4})', 'DMY'),    # DD/MM/YYYY
                (r'(\d{4})[/./-](\d{1,2})[/./-](\d{1,2})', 'YMD'),    # YYYY/MM/DD
                (r'(\d{1,2})[/./-](\d{1,2})[/./-](\d{2})', 'DMY2'),   # DD/MM/YY
                (r'(\d{4})(\d{2})(\d{2})', 'YMD_NO_SEP'),             # YYYYMMDD
                (r'(\d{2})(\d{2})(\d{4})', 'DMY_NO_SEP'),             # DDMMYYYY
            ]
            
            for pattern, format_type in patterns:
                match = re.search(pattern, date_str)
                if match:
                    groups = [int(g) for g in match.groups()]
                    
                    if format_type in ['DMY', 'DMY2', 'DMY_NO_SEP']:
                        day, month, year = groups
                        if format_type == 'DMY2':
                            year = 2000 + year if year < 50 else 1900 + year
                    else:  # YMD formats
                        year, month, day = groups
                    
                    # אימות תאריך
                    if (1 <= day <= 31 and 1 <= month <= 12 and 
                        2020 <= year <= 2030):
                        return f"{year:04d}-{month:02d}-{day:02d}"
            
            # אם לא הצליח - השתמש בהיום
            return datetime.now().strftime('%Y-%m-%d')
            
        except Exception as e:
            logger.debug(f"Date normalization failed: {e}")
            return datetime.now().strftime('%Y-%m-%d')
    
    def _normalize_payment_method(self, payment: str) -> Optional[str]:
        """מנרמל אמצעי תשלום"""
        if not payment:
            return None
        
        payment = str(payment).lower().strip()
        
        # כרטיס אשראי
        if any(word in payment for word in ['אשראי', 'כרטיס', 'card', 'ויזה', 'מאסטר', 'visa', 'master', 'credit']):
            return 'card'
        
        # מזומן
        elif any(word in payment for word in ['מזומן', 'cash', 'כסף']):
            return 'cash'
        
        # העברה בנקאית
        elif any(word in payment for word in ['העברה', 'בנק', 'bank', 'ביט', 'bit', 'פיי', 'pay']):
            return 'bank'
        
        # צ'ק
        elif any(word in payment for word in ['צק', 'צ\'ק', 'check', 'cheque']):
            return 'check'
        
        return None
    
    def _create_fallback_receipt(self) -> Dict:
        """יוצר קבלה בסיסית כשה-AI נכשל"""
        return {
            'vendor': 'ספק לא מזוהה',
            'amount': 0,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'category': 'אחר',
            'payment_method': None,
            'description': 'נדרש עדכון ידני',
            'invoice_number': '',
            'confidence': 0,
            'needs_review': True,
            'source': 'fallback'
        }
    
    # ===== ניתוח הודעות טקסט =====
    
    def analyze_text_expense(self, message: str, group_id: str = None) -> Optional[Dict]:
        """מנתח הודעת טקסט להוצאה"""
        
        if not self.client:
            logger.error("OpenAI client not available for text analysis")
            return self._parse_manual_text_basic(message)
        
        try:
            system_prompt = self._get_text_analysis_prompt()
            user_prompt = f'נתח את ההודעה הזו לזיהוי הוצאה: "{message}"'
            
            response = self.client.chat.completions.create(
            model=AI_SETTINGS["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=300
        )