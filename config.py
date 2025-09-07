import os
from typing import List, Dict
from dotenv import load_dotenv

# טעינת משתני סביבה
load_dotenv()

# ===== הגדרות בסיסיות =====
APP_NAME = "מערכת חתונה מאוחדת"
VERSION = "2.0.0"

# ===== פלטת צבעים יוקרתית =====
COLORS = {
    'primary': '#3d405b',      # כהה יוקרתי
    'secondary': '#81b29a',    # ירוק עדין  
    'accent': '#f2cc8f',       # מוזהב
    'warning': '#e07a5f',      # כתום חם
    'background': '#f4f1de',   # בז' מינימלי
    'white': '#ffffff',
    'text_dark': '#3d405b',
    'text_medium': '#81b29a', 
    'text_light': '#999999',
    'border': '#e0e0e0',
    'success': '#81b29a',
    'error': '#e07a5f'
}

# ===== הגדרות CSS מאוחדות =====
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
        --success: {COLORS['success']};
        --error: {COLORS['error']};
    }}
    
    html, body, .stApp {{
        direction: rtl !important;
        font-family: 'Segoe UI', 'Heebo', Arial, sans-serif !important;
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
    
    .stButton > button:active {{
        transform: translateY(0px) !important;
    }}
    
    /* כפתורים מיוחדים */
    .primary-btn {{
        background: var(--primary) !important;
    }}
    
    .secondary-btn {{
        background: var(--secondary) !important;
    }}
    
    .accent-btn {{
        background: var(--accent) !important;
        color: var(--text-dark) !important;
    }}
    
    .warning-btn {{
        background: var(--warning) !important;
    }}
    
    /* שדות טקסט מעוצבים */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {{
        border: 2px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        background: var(--white) !important;
        transition: all 0.3s ease !important;
        font-family: inherit !important;
    }}
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(61, 64, 91, 0.1) !important;
        outline: none !important;
    }}
    
    /* כרטיסים יוקרתיים */
    .metric-card {{
        background: var(--white);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid var(--border);
        text-align: center;
        transition: all 0.3s ease;
        margin-bottom: 20px;
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
        line-height: 1;
    }}
    
    .metric-label {{
        color: var(--text-medium);
        font-size: 14px;
        font-weight: 500;
    }}
    
    /* כרטיס מידע */
    .info-card {{
        background: var(--white);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border-right: 4px solid var(--accent);
        margin-bottom: 15px;
    }}
    
    /* אזהרות והודעות */
    .alert {{
        padding: 16px;
        border-radius: 12px;
        margin: 16px 0;
        font-weight: 500;
        border-right: 4px solid;
    }}
    
    .alert-success {{
        background: rgba(129, 178, 154, 0.15);
        border-right-color: var(--success);
        color: var(--success);
    }}
    
    .alert-warning {{
        background: rgba(224, 122, 95, 0.15);
        border-right-color: var(--warning);
        color: var(--warning);
    }}
    
    .alert-info {{
        background: rgba(61, 64, 91, 0.1);
        border-right-color: var(--primary);
        color: var(--primary);
    }}
    
    /* טבלאות מעוצבות */
    .styled-table {{
        background: var(--white);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        width: 100%;
        border: 1px solid var(--border);
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
    
    /* DataFrame styling */
    .stDataFrame {{
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important;
    }}
    
    /* סייד בר מעוצב */
    .stSidebar > div:first-child {{
        background: var(--white) !important;
        border-left: 3px solid var(--accent) !important;
    }}
    
    /* עיצוב אימות */
    .auth-container {{
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: var(--white);
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid var(--border);
    }}
    
    .auth-title {{
        font-size: 28px;
        font-weight: 700;
        color: var(--primary);
        margin-bottom: 30px;
    }}
    
    /* כותרות דף */
    .page-header {{
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
        color: var(--white);
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
    }}
    
    .page-title {{
        margin: 0 0 10px 0;
        font-size: 2.5rem;
        font-weight: 700;
    }}
    
    .page-subtitle {{
        margin: 0;
        opacity: 0.9;
        font-weight: normal;
    }}
    
    /* בר התקדמות */
    .progress-container {{
        background: var(--white);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}
    
    .progress-bar {{
        background: var(--border);
        height: 10px;
        border-radius: 5px;
        overflow: hidden;
        margin-top: 10px;
    }}
    
    .progress-fill {{
        background: linear-gradient(90deg, var(--secondary), var(--accent));
        height: 100%;
        border-radius: 5px;
        transition: width 0.3s ease;
    }}
    
    /* פורמים */
    .form-section {{
        background: var(--white);
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 1px solid var(--border);
    }}
    
    .form-title {{
        color: var(--primary);
        margin: 0 0 20px 0;
        font-size: 1.3rem;
        font-weight: 600;
    }}
    
    /* גריד */
    .grid-container {{
        display: grid;
        gap: 20px;
        margin-bottom: 20px;
    }}
    
    .grid-2 {{
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    }}
    
    .grid-3 {{
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    }}
    
    .grid-4 {{
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    }}
    
    /* אייקונים */
    .icon {{
        font-size: 1.2rem;
        margin-left: 8px;
        vertical-align: middle;
    }}
    
    /* סטטוס */
    .status-active {{
        color: var(--success);
        font-weight: 600;
    }}
    
    .status-inactive {{
        color: var(--text-light);
        font-weight: 600;
    }}
    
    .status-warning {{
        color: var(--warning);
        font-weight: 600;
    }}
    
    /* Expander מותאם */
    .streamlit-expanderHeader {{
        background: var(--background) !important;
        border-radius: 8px !important;
        border: 1px solid var(--border) !important;
    }}
    
    /* רספונסיבי */
    @media (max-width: 768px) {{
        .metric-card {{
            padding: 16px;
            margin-bottom: 15px;
        }}
        
        .metric-value {{
            font-size: 2rem;
        }}
        
        .auth-container {{
            margin: 50px 20px;
            padding: 30px 20px;
        }}
        
        .page-title {{
            font-size: 2rem;
        }}
        
        .grid-2, .grid-3, .grid-4 {{
            grid-template-columns: 1fr;
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
DEFAULT_CURRENCY = "ILS"
DEFAULT_TIMEZONE = "Asia/Jerusalem"

# טלפונים מורשים - לאדמין בלבד
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
# גיליון זוגות
COUPLES_HEADERS = [
    "group_id",           # WhatsApp Group ID
    "phone1",            # טלפון ראשון
    "phone2",            # טלפון שני  
    "couple_name",       # שם הזוג
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

# ===== פורמט טלפונים =====
def normalize_phone(phone: str) -> str:
    """נרמול מספר טלפון לפורמט אחיד"""
    if not phone:
        return ""
    
    # ניקוי תווים לא רלוונטיים
    clean = ''.join(filter(str.isdigit, str(phone)))
    
    # המרה מפורמט בינלאומי לישראלי
    if clean.startswith('972'):
        clean = '0' + clean[3:]
    
    # הוספת 0 בתחילת אם חסר
    if len(clean) == 9 and clean.startswith('5'):
        clean = '0' + clean
    
    return clean

def format_phone_display(phone: str) -> str:
    """פורמט טלפון לתצוגה"""
    clean = normalize_phone(phone)
    
    if len(clean) == 10 and clean.startswith('05'):
        return f"{clean[:3]}-{clean[3:6]}-{clean[6:]}"
    
    return phone

def is_valid_phone(phone: str) -> bool:
    """בדיקת תקינות מספר טלפון"""
    clean = normalize_phone(phone)
    return len(clean) == 10 and clean.startswith('05')

# ===== פונקציות עזר =====
def validate_config() -> Dict[str, bool]:
    """בדיקת תקינות הגדרות"""
    return {
        "google_sheets": bool(GOOGLE_CREDENTIALS_JSON and GSHEETS_SPREADSHEET_ID),
        "whatsapp": bool(GREENAPI_INSTANCE_ID and GREENAPI_TOKEN),
        "openai": bool(OPENAI_API_KEY),
        "webhook_secret": bool(WEBHOOK_SHARED_SECRET),
        "admin_phones": bool(ALLOWED_PHONES),
        "admin_password": bool(ADMIN_PASSWORD)
    }

def is_admin_phone(phone: str) -> bool:
    """בדיקה האם הטלפון של אדמין"""
    if not ALLOWED_PHONES:
        return False
    
    clean_phone = normalize_phone(phone)
    
    for allowed in ALLOWED_PHONES:
        clean_allowed = normalize_phone(allowed)
        if clean_phone == clean_allowed:
            return True
    
    return False

# ===== הגדרות URL =====
# יש להחליף בהגדרות הפריסה
BASE_URL = os.getenv("BASE_URL", "http://localhost:8501")

def get_dashboard_url(group_id: str, token: str) -> str:
    """יצירת קישור לדשבורד"""
    return f"{BASE_URL}/?page=dashboard&group_id={group_id}&token={token}"

def get_contacts_merge_url(group_id: str, token: str) -> str:
    """יצירת קישור לחיבור אנשי קשר"""
    return f"{BASE_URL}/?page=contacts&group_id={group_id}&token={token}"

def get_admin_url() -> str:
    """יצירת קישור לדשבורד אדמין"""
    return f"{BASE_URL}/?page=admin"

if __name__ == "__main__":
    # בדיקה מהירה של הקונפיגורציה
    config_status = validate_config()
    print("📊 סטטוס הגדרות:")
    for service, status in config_status.items():
        emoji = "✅" if status else "❌"
        print(f"{emoji} {service}")
    
    print(f"\n📱 טלפוני אדמין: {len(ALLOWED_PHONES)}")
    print(f"🎨 צבעים: {len(COLORS)}")
    print(f"📋 קטגוריות: {len(CATEGORY_LIST)}")
    
    # בדיקת פורמט טלפונים
    test_phones = ["0507676706", "+972507676706", "507676706"]
    print(f"\n📞 בדיקת פורמט טלפונים:")
    for phone in test_phones:
        normalized = normalize_phone(phone)
        formatted = format_phone_display(phone)
        valid = is_valid_phone(phone)
        print(f"  {phone} → {normalized} → {formatted} (תקין: {valid})")