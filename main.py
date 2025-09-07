import streamlit as st
import logging
from typing import Optional

# הגדרת logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from config import get_main_css, COLORS, APP_NAME, VERSION
from auth_system import get_auth_manager
from google_services import get_google_services

def main():
    """נקודת הכניסה הראשית של המערכת"""
    
    # הגדרות דף בסיסיות
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="💒",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # טעינת CSS מאוחד
    st.markdown(get_main_css(), unsafe_allow_html=True)
    
    # קבלת פרמטרים מה-URL
    page = st.query_params.get('page', 'home')
    group_id = st.query_params.get('group_id')
    token = st.query_params.get('token')
    
    try:
        # ניתוב לפי דף
        if page == 'admin':
            show_admin_dashboard()
        elif page == 'dashboard' and group_id:
            show_couple_dashboard(group_id, token)
        elif page == 'contacts' and group_id:
            show_contacts_merger(group_id, token)
        else:
            show_home_page()
            
    except Exception as e:
        logging.error(f"Error in main app: {e}")
        st.error("שגיאה במערכת. אנא נסה שוב מאוחר יותר.")
        st.exception(e)

def show_home_page():
    """דף בית עם הסבר על המערכת"""
    
    st.markdown(f"""
    <div class="page-header">
        <h1 class="page-title">💒 {APP_NAME}</h1>
        <h3 class="page-subtitle">מערכת חכמה לניהול חתונות עם WhatsApp Bot</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="info-card">
            <h3>🤖 בוט WhatsApp חכם</h3>
            <p>שלחו קבלות והבוט ינתח אותן אוטומטית עם AI</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="info-card">
            <h3>📊 דשבורד מתקדם</h3>
            <p>עקבו אחר הוצאות, תקציב וקבלו תובנות</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="info-card">
            <h3>📱 חיבור אנשי קשר</h3>
            <p>חברו בקלות בין רשימת המוזמנים לאנשי הקשר</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # מידע טכני
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔧 איך זה עובד?")
        st.markdown("""
        1. **רישום** - האדמין יוצר לכם קבוצה עם הבוט
        2. **שליחה** - שלחו קבלות או כתבו הוצאות בקבוצה
        3. **ניתוח** - הבוט מנתח עם AI ושומר הכל
        4. **דשבורד** - קבלו קישור לדשבורד מפורט
        5. **חיבור אנשי קשר** - חברו מוזמנים לאנשי הקשר
        """)
    
    with col2:
        st.markdown("### 📈 יכולות המערכת")
        st.markdown("""
        - 🤖 **AI חכם** - ניתוח קבלות אוטומטי
        - 💰 **עקיבת תקציב** - השוואה מול התקציב המתוכנן
        - 📊 **גרפים מתקדמים** - ויזואליזציה של הנתונים
        - 🔒 **אבטחה** - אימות דרך WhatsApp
        - ☁️ **גיבוי בענן** - כל הנתונים נשמרים בגוגל
        """)
    
    # כפתורי גישה
    st.markdown("---")
    st.markdown("### 🚪 כניסה למערכת")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("👨‍💼 דשבורד מנהל", use_container_width=True, type="primary"):
            st.query_params.update({"page": "admin"})
            st.rerun()
    
    with col2:
        st.markdown("""
        <div style="text-align: center; color: """ + COLORS['text_medium'] + """;">
            <strong>👫 זוגות</strong><br>
            קבלו קישור מהאדמין או מהבוט
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # בדיקת מצב המערכת
        if st.button("🔍 בדיקת מצב מערכת", use_container_width=True):
            check_system_status()

def check_system_status():
    """בדיקת מצב המערכת"""
    
    with st.spinner("בודק מצב המערכת..."):
        try:
            # בדיקת Google Services
            gs = get_google_services()
            gs_health = gs.health_check()
            
            # בדיקת Auth System
            auth = get_auth_manager()
            auth_sessions = auth.get_active_sessions_count()
            
            # הצגת תוצאות
            st.success("✅ בדיקת מערכת הושלמה")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🔧 שירותי Google")
                for service, status in gs_health.items():
                    emoji = "✅" if status else "❌"
                    service_name = service.replace("_", " ").title()
                    st.write(f"{emoji} {service_name}")
            
            with col2:
                st.markdown("#### 👥 סשנים פעילים")
                st.write(f"👫 זוגות: {auth_sessions.get('user_sessions', 0)}")
                st.write(f"📊 דשבורדים: {auth_sessions.get('dashboard_sessions', 0)}")
                st.write(f"📱 חיבור אנשי קשר: {auth_sessions.get('contacts_merge_sessions', 0)}")
                st.write(f"👨‍💼 אדמין: {auth_sessions.get('admin_sessions', 0)}")
            
        except Exception as e:
            st.error(f"❌ שגיאה בבדיקת המערכת: {str(e)}")

def show_admin_dashboard():
    """דשבורד אדמין"""
    from admin_dashboard import main as admin_main
    admin_main()

def show_couple_dashboard(group_id: str, token: Optional[str]):
    """דשבורד זוג"""
    from main_dashboard import main as dashboard_main
    
    # העברת פרמטרים לדשבורד
    if token:
        st.session_state['url_token'] = token
        st.session_state['url_group_id'] = group_id
    
    dashboard_main()

def show_contacts_merger(group_id: str, token: Optional[str]):
    """מערכת חיבור אנשי קשר"""
    from contacts_merger import main as contacts_main
    
    # העברת פרמטרים
    if token:
        st.session_state['url_token'] = token
        st.session_state['url_group_id'] = group_id
    
    contacts_main()

# Footer
def show_footer():
    """פוטר המערכת"""
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: {COLORS['text_light']}; padding: 20px;">
        <small>
            {APP_NAME} v{VERSION} | 
            Made with ❤️ for beautiful weddings
        </small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
    show_footer()