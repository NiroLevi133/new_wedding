import secrets
import time
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import requests
from config import (
    GREENAPI_INSTANCE_ID, 
    GREENAPI_TOKEN,
    AUTH_TOKEN_EXPIRE_MINUTES,
    ADMIN_PASSWORD,
    is_phone_allowed,
    COLORS
)

logger = logging.getLogger(__name__)

class AuthManager:
    """מנהל אימות פשוט עם WhatsApp"""
    
    def __init__(self):
        self.auth_codes = {}  # {phone: {code, timestamp, attempts}}
        self.active_tokens = {}  # {token: {group_id, phone, expires_at}}
        self.admin_sessions = {}  # {token: {expires_at}}
    
    def _clean_expired_codes(self):
        """ניקוי קודים שפג תוקפם"""
        current_time = time.time()
        expired_phones = []
        
        for phone, data in self.auth_codes.items():
            if current_time - data['timestamp'] > 300:  # 5 דקות
                expired_phones.append(phone)
        
        for phone in expired_phones:
            del self.auth_codes[phone]
    
    def _clean_expired_tokens(self):
        """ניקוי טוכנים שפג תוקפם"""
        current_time = datetime.now()
        expired_tokens = []
        
        for token, data in self.active_tokens.items():
            if current_time > data['expires_at']:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.active_tokens[token]
        
        # ניקוי סשנים של אדמין
        expired_admin_tokens = []
        for token, data in self.admin_sessions.items():
            if current_time > data['expires_at']:
                expired_admin_tokens.append(token)
        
        for token in expired_admin_tokens:
            del self.admin_sessions[token]
    
    def _normalize_phone(self, phone: str) -> str:
        """נרמול מספר טלפון"""
        # הסר כל מה שלא ספרה
        clean = ''.join(filter(str.isdigit, phone))
        
        # המר מפורמט בינלאומי לישראלי
        if clean.startswith('972'):
            clean = '0' + clean[3:]
        
        return clean
    
    def _send_whatsapp_message(self, phone: str, message: str) -> bool:
        """שליחת הודעה בWhatsApp"""
        try:
            if not GREENAPI_INSTANCE_ID or not GREENAPI_TOKEN:
                logger.error("WhatsApp credentials not configured")
                return False
            
            # נרמול מספר לפורמט WhatsApp
            clean_phone = self._normalize_phone(phone)
            if clean_phone.startswith('0'):
                whatsapp_id = '972' + clean_phone[1:] + '@c.us'
            else:
                whatsapp_id = clean_phone + '@c.us'
            
            url = f"https://api.green-api.com/waInstance{GREENAPI_INSTANCE_ID}/sendMessage/{GREENAPI_TOKEN}"
            
            payload = {
                "chatId": whatsapp_id,
                "message": message
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"WhatsApp message sent successfully to {phone}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp message: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False
    
    def request_auth_code(self, phone: str, group_id: str = None) -> Dict:
        """בקשת קוד אימות"""
        try:
            # ניקוי קודים ישנים
            self._clean_expired_codes()
            
            # נרמול טלפון
            clean_phone = self._normalize_phone(phone)
            
            # בדיקת הרשאה
            if not is_phone_allowed(clean_phone):
                logger.warning(f"Unauthorized auth attempt from: {clean_phone}")
                return {
                    "success": False, 
                    "error": "מספר לא מורשה",
                    "code": "UNAUTHORIZED"
                }
            
            # בדיקת ניסיונות חוזרים
            if clean_phone in self.auth_codes:
                attempts = self.auth_codes[clean_phone]['attempts']
                if attempts >= 3:
                    return {
                        "success": False,
                        "error": "יותר מדי ניסיונות. נסה שוב מאוחר יותר",
                        "code": "TOO_MANY_ATTEMPTS"
                    }
            
            # יצירת קוד אימות
            auth_code = ''.join(secrets.choice('0123456789') for _ in range(4))
            
            # שמירת הקוד
            self.auth_codes[clean_phone] = {
                'code': auth_code,
                'timestamp': time.time(),
                'attempts': self.auth_codes.get(clean_phone, {}).get('attempts', 0) + 1,
                'group_id': group_id
            }
            
            # הכנת הודעה
            if group_id:
                message = f"""🔐 קוד אימות לדשבורד החתונה

קוד: {auth_code}

הקוד תקף ל-5 דקות בלבד."""
            else:
                message = f"""🔐 קוד אימות למערכת החתונה

קוד: {auth_code}

הקוד תקף ל-5 דקות בלבד."""
            
            # שליחת הקוד
            if self._send_whatsapp_message(clean_phone, message):
                logger.info(f"Auth code sent to: {clean_phone}")
                return {
                    "success": True,
                    "message": "קוד אימות נשלח בהצלחה"
                }
            else:
                return {
                    "success": False,
                    "error": "שגיאה בשליחת הקוד",
                    "code": "SEND_FAILED"
                }
                
        except Exception as e:
            logger.error(f"Error in request_auth_code: {e}")
            return {
                "success": False,
                "error": "שגיאה במערכת",
                "code": "SYSTEM_ERROR"
            }
    
    def verify_auth_code(self, phone: str, code: str) -> Dict:
        """אימות קוד ויצירת טוכן"""
        try:
            # ניקוי קודים ישנים
            self._clean_expired_codes()
            self._clean_expired_tokens()
            
            clean_phone = self._normalize_phone(phone)
            
            # בדיקה שהקוד קיים
            if clean_phone not in self.auth_codes:
                return {
                    "success": False,
                    "error": "קוד לא נמצא או פג תוקף",
                    "code": "CODE_NOT_FOUND"
                }
            
            auth_data = self.auth_codes[clean_phone]
            
            # בדיקת תוקף זמן
            if time.time() - auth_data['timestamp'] > 300:  # 5 דקות
                del self.auth_codes[clean_phone]
                return {
                    "success": False,
                    "error": "קוד פג תוקף",
                    "code": "CODE_EXPIRED"
                }
            
            # בדיקת הקוד
            if auth_data['code'] != code.strip():
                return {
                    "success": False,
                    "error": "קוד שגוי",
                    "code": "INVALID_CODE"
                }
            
            # יצירת טוכן גישה
            access_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(minutes=AUTH_TOKEN_EXPIRE_MINUTES)
            
            self.active_tokens[access_token] = {
                'phone': clean_phone,
                'group_id': auth_data.get('group_id'),
                'expires_at': expires_at,
                'created_at': datetime.now()
            }
            
            # מחיקת הקוד הזמני
            del self.auth_codes[clean_phone]
            
            logger.info(f"Auth successful for: {clean_phone}")
            
            return {
                "success": True,
                "token": access_token,
                "expires_at": expires_at.isoformat(),
                "group_id": auth_data.get('group_id')
            }
            
        except Exception as e:
            logger.error(f"Error in verify_auth_code: {e}")
            return {
                "success": False,
                "error": "שגיאה במערכת",
                "code": "SYSTEM_ERROR"
            }
    
    def validate_token(self, token: str) -> Dict:
        """בדיקת תוקף טוכן"""
        try:
            self._clean_expired_tokens()
            
            if token not in self.active_tokens:
                return {
                    "valid": False,
                    "error": "טוכן לא תקף",
                    "code": "INVALID_TOKEN"
                }
            
            token_data = self.active_tokens[token]
            
            if datetime.now() > token_data['expires_at']:
                del self.active_tokens[token]
                return {
                    "valid": False,
                    "error": "טוכן פג תוקף",
                    "code": "TOKEN_EXPIRED"
                }
            
            return {
                "valid": True,
                "phone": token_data['phone'],
                "group_id": token_data['group_id'],
                "expires_at": token_data['expires_at'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in validate_token: {e}")
            return {
                "valid": False,
                "error": "שגיאה במערכת",
                "code": "SYSTEM_ERROR"
            }
    
    def revoke_token(self, token: str) -> bool:
        """ביטול טוכן"""
        try:
            if token in self.active_tokens:
                del self.active_tokens[token]
                return True
            return False
        except Exception as e:
            logger.error(f"Error in revoke_token: {e}")
            return False
    
    def get_dashboard_link(self, group_id: str, base_url: str) -> str:
        """יצירת קישור לדשבורד עם טוכן"""
        try:
            # יצירת טוכן מיוחד לדשבורד
            dashboard_token = secrets.token_urlsafe(16)
            expires_at = datetime.now() + timedelta(hours=2)  # 2 שעות
            
            self.active_tokens[dashboard_token] = {
                'phone': '',  # לא נדרש לדשבורד
                'group_id': group_id,
                'expires_at': expires_at,
                'created_at': datetime.now(),
                'type': 'dashboard'
            }
            
            dashboard_url = f"{base_url}/dashboard/{group_id}?token={dashboard_token}"
            return dashboard_url
            
        except Exception as e:
            logger.error(f"Error creating dashboard link: {e}")
            return ""
    
    def get_contacts_merge_link(self, group_id: str, phone: str, base_url: str) -> str:
        """יצירת קישור למיזוג אנשי קשר"""
        try:
            # יצירת טוכן מיוחד למיזוג
            merge_token = secrets.token_urlsafe(16)
            expires_at = datetime.now() + timedelta(hours=4)  # 4 שעות למיזוג
            
            self.active_tokens[merge_token] = {
                'phone': phone,
                'group_id': group_id,
                'expires_at': expires_at,
                'created_at': datetime.now(),
                'type': 'contacts_merge'
            }
            
            merge_url = f"{base_url}/contacts-merge/{group_id}?token={merge_token}"
            return merge_url
            
        except Exception as e:
            logger.error(f"Error creating contacts merge link: {e}")
            return ""
    
    # ===== אימות אדמין =====
    
    def admin_login(self, password: str) -> Dict:
        """כניסת אדמין"""
        try:
            if password != ADMIN_PASSWORD:
                return {
                    "success": False,
                    "error": "סיסמה שגויה",
                    "code": "INVALID_PASSWORD"
                }
            
            # יצירת טוכן אדמין
            admin_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=8)  # 8 שעות לאדמין
            
            self.admin_sessions[admin_token] = {
                'expires_at': expires_at,
                'created_at': datetime.now()
            }
            
            logger.info("Admin login successful")
            
            return {
                "success": True,
                "token": admin_token,
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in admin_login: {e}")
            return {
                "success": False,
                "error": "שגיאה במערכת",
                "code": "SYSTEM_ERROR"
            }
    
    def validate_admin_token(self, token: str) -> bool:
        """בדיקת תוקף טוכן אדמין"""
        try:
            self._clean_expired_tokens()
            
            if token not in self.admin_sessions:
                return False
            
            session_data = self.admin_sessions[token]
            
            if datetime.now() > session_data['expires_at']:
                del self.admin_sessions[token]
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in validate_admin_token: {e}")
            return False
    
    def admin_logout(self, token: str) -> bool:
        """יציאת אדמין"""
        try:
            if token in self.admin_sessions:
                del self.admin_sessions[token]
                return True
            return False
        except Exception as e:
            logger.error(f"Error in admin_logout: {e}")
            return False
    
    # ===== פונקציות עזר =====
    
    def get_active_sessions_count(self) -> Dict:
        """קבלת מספר סשנים פעילים"""
        try:
            self._clean_expired_tokens()
            
            user_sessions = len([
                token for token, data in self.active_tokens.items()
                if data.get('type', 'user') == 'user'
            ])
            
            dashboard_sessions = len([
                token for token, data in self.active_tokens.items()
                if data.get('type') == 'dashboard'
            ])
            
            contacts_merge_sessions = len([
                token for token, data in self.active_tokens.items()
                if data.get('type') == 'contacts_merge'
            ])
            
            admin_sessions = len(self.admin_sessions)
            
            return {
                "user_sessions": user_sessions,
                "dashboard_sessions": dashboard_sessions,
                "contacts_merge_sessions": contacts_merge_sessions,
                "admin_sessions": admin_sessions,
                "total": user_sessions + dashboard_sessions + contacts_merge_sessions + admin_sessions
            }
            
        except Exception as e:
            logger.error(f"Error getting active sessions count: {e}")
            return {}
    
    def cleanup_expired(self):
        """ניקוי כללי של כל המידע שפג תוקף"""
        self._clean_expired_codes()
        self._clean_expired_tokens()
    
    def get_auth_statistics(self) -> Dict:
        """סטטיסטיקות מערכת האימות"""
        try:
            current_time = time.time()
            
            # קודי אימות פעילים
            active_codes = len([
                phone for phone, data in self.auth_codes.items()
                if current_time - data['timestamp'] <= 300
            ])
            
            # סשנים פעילים
            sessions = self.get_active_sessions_count()
            
            return {
                "active_auth_codes": active_codes,
                "sessions": sessions,
                "total_auth_attempts": sum(
                    data['attempts'] for data in self.auth_codes.values()
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting auth statistics: {e}")
            return {}


# ===== Decorators לStreamlit =====

def require_auth(func):
    """דקורטור לדרישת אימות בדפי Streamlit"""
    def wrapper(*args, **kwargs):
        import streamlit as st
        
        # קבלת טוכן מ-URL או session
        token = st.query_params.get('token') or st.session_state.get('auth_token')
        
        if not token:
            show_auth_page()
            st.stop()
        
        # בדיקת תוקף הטוכן
        auth_result = get_auth_manager().validate_token(token)
        
        if not auth_result.get('valid'):
            st.error("🔒 סשן פג תוקף. אנא התחבר שוב.")
            if 'auth_token' in st.session_state:
                del st.session_state['auth_token']
            show_auth_page()
            st.stop()
        
        # שמירת מידע המשתמש
        st.session_state.auth_token = token
        st.session_state.user_phone = auth_result.get('phone')
        st.session_state.user_group_id = auth_result.get('group_id')
        
        return func(*args, **kwargs)
    
    return wrapper

def require_admin_auth(func):
    """דקורטור לדרישת אימות אדמין"""
    def wrapper(*args, **kwargs):
        import streamlit as st
        
        admin_token = st.session_state.get('admin_token')
        
        if not admin_token or not get_auth_manager().validate_admin_token(admin_token):
            show_admin_login_page()
            st.stop()
        
        return func(*args, **kwargs)
    
    return wrapper

def show_auth_page():
    """דף אימות מעוצב"""
    import streamlit as st
    
    st.markdown(f"""
    <div class="auth-container">
        <h1 class="auth-title">🔐 כניסה למערכת</h1>
        
        <p style="color: {COLORS['text_medium']}; margin-bottom: 30px;">
            הזן את מספר הטלפון שלך לקבלת קוד אימות
        </p>
    """, unsafe_allow_html=True)
    
    # שלב 1: הזנת טלפון
    if 'auth_step' not in st.session_state:
        st.session_state.auth_step = 'phone'
    
    if st.session_state.auth_step == 'phone':
        with st.form("phone_form"):
            phone = st.text_input(
                "מספר טלפון:",
                placeholder="050-1234567",
                help="הזן את מספר הטלפון הרשום במערכת"
            )
            
            submitted = st.form_submit_button("📱 שלח קוד אימות")
            
            if submitted and phone:
                result = get_auth_manager().request_auth_code(phone)
                
                if result['success']:
                    st.session_state.auth_phone = phone
                    st.session_state.auth_step = 'code'
                    st.success("✅ קוד אימות נשלח לWhatsApp")
                    st.rerun()
                else:
                    st.error(f"❌ {result['error']}")
    
    # שלב 2: הזנת קוד
    elif st.session_state.auth_step == 'code':
        st.info(f"📱 קוד אימות נשלח ל-{st.session_state.auth_phone}")
        
        with st.form("code_form"):
            code = st.text_input(
                "קוד אימות:",
                placeholder="1234",
                max_chars=4,
                help="הזן את הקוד שנשלח אליך בWhatsApp"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                verify_submitted = st.form_submit_button("🔓 אמת קוד")
            
            with col2:
                back_submitted = st.form_submit_button("↩️ חזור")
            
            if verify_submitted and code:
                result = get_auth_manager().verify_auth_code(st.session_state.auth_phone, code)
                
                if result['success']:
                    st.session_state.auth_token = result['token']
                    st.session_state.user_group_id = result.get('group_id')
                    st.success("✅ התחברת בהצלחה!")
                    st.rerun()
                else:
                    st.error(f"❌ {result['error']}")
            
            if back_submitted:
                st.session_state.auth_step = 'phone'
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

def show_admin_login_page():
    """דף כניסת אדמין"""
    import streamlit as st
    
    st.markdown(f"""
    <div class="auth-container">
        <h1 class="auth-title">👨‍💼 כניסת אדמין</h1>
    """, unsafe_allow_html=True)
    
    with st.form("admin_login_form"):
        password = st.text_input(
            "סיסמת אדמין:",
            type="password",
            placeholder="הזן סיסמת אדמין"
        )
        
        submitted = st.form_submit_button("🔑 כניסה")
        
        if submitted and password:
            result = get_auth_manager().admin_login(password)
            
            if result['success']:
                st.session_state.admin_token = result['token']
                st.success("✅ התחברת כאדמין!")
                st.rerun()
            else:
                st.error("❌ סיסמה שגויה")
    
    st.markdown("</div>", unsafe_allow_html=True)


# ===== מופע גלובלי =====
_auth_manager = None

def get_auth_manager() -> AuthManager:
    """קבלת מופע יחיד של AuthManager"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


# ===== בדיקה =====
if __name__ == "__main__":
    print("🧪 Testing Auth System...")
    
    try:
        auth = AuthManager()
        
        # בדיקת בקשת קוד
        result = auth.request_auth_code("0501234567")
        print(f"📱 Request code result: {result}")
        
        # סטטיסטיקות
        stats = auth.get_auth_statistics()
        print(f"📊 Auth statistics: {stats}")
        
        print("✅ Auth system test completed")
        
    except Exception as e:
        print(f"❌ Auth test failed: {e}")