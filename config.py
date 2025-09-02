import os
from typing import List, Dict
from dotenv import load_dotenv

# טעינת משתני סביבה
load_dotenv()

# ===== הגדרות בסיסיות =====
APP_NAME = "מערכת חתונה מאוחדת"
VERSION = "1.0.0"

# ===== פלטת צבעים יוקרתית =====
COLORS = {
    'primary': '#3d405b',      # כהה יוקרתי (כפתורים ראשיים)
    'secondary': '#81b29a',    # ירוק עדין (אקסנטים)
    'accent': '#f2cc8f',       # מוזהב (הדגשות חשובות)
    'warning': '#e07a5f',      # כתום חם (התראות)
    'background': '#f4f1de',   # בז' מינימלי (רקע)
    'white': '#ffffff',
    'text_dark': '#3d405b',
    'text_medium': '#81b29a',
    'text_light': '#999999',
    'border': '#e0e0e0',
    'success': '#81b29a',
    'error': '#e07a5f'
}

# ===== הגדרות CSS =====
def get_main_css():
    return f"""
    <style>
    /* בסיס מינימלי יוקרתי */
    :root {{
        --primary: {COLORS['primary']};
        --secondary: {COLORS['secondary']};
        --accent: {COLORS['accent']};
        --warning: {COLORS['warning']};
        --background: {COLORS['background']};
        --white: {COLORS['white']};
        --text-dark: {COLORS['text_dark']};
        --text-medium: {COLORS['text_medium']};
        --border: {COLORS['border']};
    }}
    
    html, body, .stApp {{
        direction: rtl !important;
        font-family: 'Segoe UI', 'Heebo', sans-serif !important;
        background-color: var(--background) !important;
        color: var(--text-dark) !important;
    }}
    
    /* הסתרת header של Streamlit */
    .stAppHeader, header[data-testid="stHeader"] {{
        display: none !important;
    }}
    
    /* כפתורים יוקרתיים */
    .stButton > button {{
        background: var(--primary) !important;
        color: var(--white) !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(61, 64, 91, 0.15) !important;
    }}
    
    .stButton > button:hover {{
        background: var(--secondary) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(61, 64, 91, 0.25) !important;
    }}
    
    /* שדות טקסט מעוצבים */
    .stTextInput > div > div > input {{
        border: 2px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        background: var(--white) !important;
        transition: all 0.3s ease !important;
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(61, 64, 91, 0.1) !important;
        outline: none !important;
    }}
    
    /* כרטיסים */
    .metric-card {{
        background: var(--white);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid var(--border);
        text-align: center;
        transition: all 0.3s ease;
    }}
    
    .metric-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }}
    
    .metric-value {{
        font-size: 2.5rem;
        font-weight: 800;
        color: var(--primary);
        margin-bottom: 8px;
    }}
    
    .metric-label {{
        color: var(--text-medium);
        font-size: 14px;
        font-weight: 500;
    }}
    
    /* אזהרות והודעות */
    .alert {{
        padding: 16px;
        border-radius: 12px;
        margin: 16px 0;
        font-weight: 500;
    }}
    
    .alert-success {{
        background: rgba(129, 178, 154, 0.15);
        border: 1px solid var(--secondary);
        color: var(--secondary);
    }}
    
    .alert-warning {{
        background: rgba(224, 122, 95, 0.15);
        border: 1px solid var(--warning);
        color: var(--warning);
    }}
    
    /* טבלאות מעוצבות */
    .styled-table {{
        background: var(--white);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        width: 100%;
    }}
    
    .styled-table th {{
        background: var(--primary);
        color: var(--white);
        padding: 16px;
        text-align: right;
        font-weight: 600;
    }}
    
    .styled-table td {{
        padding: 12px 16px;
        border-bottom: 1px solid var(--border);
    }}
    
    .styled-table tr:hover {{
        background: rgba(242, 204, 143, 0.05);
    }}
    
    /* סייד בר מעוצב */
    .stSidebar > div {{
        background: var(--white) !important;
        border-left: 3px solid var(--accent) !important;
    }}
    
    /* עיצוב לאימות */
    .auth-container {{
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: var(--white);
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        text-align: center;
    }}
    
    .auth-title {{
        font-size: 28px;
        font-weight: 700;
        color: var(--primary);
        margin-bottom: 30px;
    }}
    
    /* אייקונים */
    .icon {{
        font-size: 1.5rem;
        margin-left: 8px;
    }}
    
    /* רספונסיבי */
    @media (max-width: 768px) {{
        .metric-card {{
            padding: 16px;
        }}
        .metric-value {{
            font-size: 2rem;
        }}
        .auth-container {{
            margin: 50px 20px;
            padding: 30px 20px;
        }}
    }}
    </style>
    """

# ===== הגדרות Google Services =====
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GSHEETS_SPREADSHEET_ID = os.getenv("GSHEETS_SPREADSHEET_ID")

# ===== הגדרות WhatsApp (Green API) =====
GREENAPI_INSTANCE_ID = os.getenv("GREENAPI_INSTANCE_ID")
GREENAPI_TOKEN = os.getenv("GREENAPI_TOKEN")
WEBHOOK_SHARED_SECRET = os.getenv("WEBHOOK_SHARED_SECRET")

# ===== הגדרות OpenAI =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ===== הגדרות מערכת =====
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "ILS")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Jerusalem")

# טלפונים מורשים - חשוב מאוד!
ALLOWED_PHONES_STR = os.getenv("ALLOWED_PHONES", "")
ALLOWED_PHONES = set(phone.strip() for phone in ALLOWED_PHONES_STR.split(",") if phone.strip()) if ALLOWED_PHONES_STR else set()

# סיסמת אדמין
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# ===== קטגוריות הוצאות חתונה =====
WEDDING_CATEGORIES = {
    "אולם": "🏛️",
    "מזון": "🍽️", 
    "צילום": "📸",
    "לבוש": "👗",
    "עיצוב": "🌸",
    "הדפסות": "📄",
    "אקססוריז": "💍",
    "מוזיקה": "🎵",
    "הסעות": "🚗",
    "אחר": "📋"
}

CATEGORY_LIST = list(WEDDING_CATEGORIES.keys())

# ===== הגדרות AI =====
AI_SETTINGS = {
    "model": "gpt-4o-mini",
    "max_tokens": 500,
    "temperature": 0.1,
}

# ===== מבנה Google Sheets =====
# גיליון ראשי - זוגות
COUPLES_HEADERS = [
    "group_id",           # WhatsApp Group ID
    "phone1",            # טלפון חתן
    "phone2",            # טלפון כלה  
    "couple_name",       # שם הזוג (אופציונלי)
    "wedding_date",      # תאריך חתונה
    "budget",           # תקציב
    "created_at",       # תאריך יצירה
    "status",           # active/inactive
    "contacts_progress", # התקדמות חיבור אנשי קשר
    "last_activity"     # פעילות אחרונה
]

# גיליון הוצאות
EXPENSES_HEADERS = [
    "expense_id",        # מזהה ייחודי
    "group_id",         # קבוצת WhatsApp
    "amount",           # סכום
    "vendor",           # ספק
    "category",         # קטגוריה
    "date",             # תאריך ההוצאה
    "payment_method",   # אמצעי תשלום
    "description",      # תיאור
    "receipt_image_url", # קישור לתמונה בדרייב
    "created_at",       # תאריך הכנסה למערכת
    "updated_at",       # תאריך עדכון אחרון
    "status",           # active/deleted
    "confidence",       # רמת ביטחון של ה-AI
    "needs_review"      # צריך בדיקה ידנית
]

# ===== הודעות בוט =====
BOT_MESSAGES = {
    "welcome": """🎉 ברוכים הבאים למערכת ניהול החתונה החכמה!

✨ מה אני יכול לעשות בשבילכם:
📸 לנתח קבלות אוטומטית
💰 לעקוב אחר ההוצאות
📊 להציג דשבורד מפורט
📱 לחבר אנשי קשר למוזמנים

שלחו תמונת קבלה או כתבו הוצאה ואני אתחיל לעבוד!""",

    "receipt_saved": """✅ הקבלה נשמרה בהצלחה!

📋 **{vendor}**
💰 **{amount:,.0f} ₪**
📊 **{category}**

📱 לדשבורד המלא הקלידו: דשבורד""",

    "dashboard_link": """📊 **הדשבורד שלכם מוכן!**

🔗 [לחצו כאן לכניסה]({link})

*הקישור בתוקף למספר שעות בלבד""",

    "help": """🤖 **איך אני עוזר לכם:**

📸 **שליחת קבלות:**
שלחו תמונה של קבלה ואני אנתח הכל אוטומטית

✍️ **הכנסה ידנית:**
"שילמתי 2000 לצלם" או "מקדמה 5000 לאולם"

📊 **פקודות שימושיות:**
• דשבורד - קישור לדשבורד
• סיכום - סיכום הוצאות
• חבר אנשי קשר - למיזוג רשימות

💬 **עדכונים:**
"תקן ל-3000 במקום 2500" או "זה אולם לא מזון\"""",

    "expense_updated": """✏️ **עודכן בהצלחה!**
{vendor} - {amount:,.0f} ₪""",

    "contact_merge_ready": """📱 **חיבור אנשי קשר מוכן!**

🔗 [לחצו כאן להתחלה]({link})

העלו את קבצי אנשי הקשר והמוזמנים שלכם ואני אעזור לחבר ביניהם!""",

    "unauthorized": "",  # לא שולח כלום למי שלא מורשה

    "error": """😅 משהו השתבש...

נסו שוב או כתבו לי את הפרטים ידנית:
💰 סכום + 🏪 שם הספק

דוגמה: "שילמתי 1500 לצלם רון\""""
}

# ===== קבועים נוספים =====
MAX_FILE_SIZE_MB = 10
ALLOWED_IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.webp']
AUTH_TOKEN_EXPIRE_MINUTES = 120  # 2 שעות

# ===== פונקציות עזר =====
def validate_config() -> Dict[str, bool]:
    """בדיקת תקינות הגדרות"""
    return {
        "google_sheets": bool(GOOGLE_CREDENTIALS_JSON and GSHEETS_SPREADSHEET_ID),
        "whatsapp": bool(GREENAPI_INSTANCE_ID and GREENAPI_TOKEN),
        "openai": bool(OPENAI_API_KEY),
        "webhook_secret": bool(WEBHOOK_SHARED_SECRET),
        "allowed_phones": bool(ALLOWED_PHONES)
    }

def is_phone_allowed(phone: str) -> bool:
    """בדיקה האם הטלפון מורשה"""
    if not ALLOWED_PHONES:
        return False
    
    # נקה את המספר
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # בדוק מול כל המספרים המורשים
    for allowed in ALLOWED_PHONES:
        clean_allowed = ''.join(filter(str.isdigit, allowed))
        if clean_phone == clean_allowed or clean_phone.endswith(clean_allowed[-8:]):
            return True
    
    return False

if __name__ == "__main__":
    # בדיקה מהירה של הקונפיגורציה
    config_status = validate_config()
    print("📊 סטטוס הגדרות:")
    for service, status in config_status.items():
        emoji = "✅" if status else "❌"
        print(f"{emoji} {service}")
    
    print(f"\n📱 טלפונים מורשים: {len(ALLOWED_PHONES)}")
    print(f"🎨 צבעים: {len(COLORS)}")
    print(f"📋 קטגוריות: {len(CATEGORY_LIST)}")