import streamlit as st
import pandas as pd
import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from config import (
    COLORS, ADMIN_PASSWORD, GREENAPI_INSTANCE_ID, GREENAPI_TOKEN,
    normalize_phone, format_phone_display, is_valid_phone,
    get_dashboard_url, BOT_MESSAGES
)
from google_services import get_google_services
from auth_system import get_auth_manager

logger = logging.getLogger(__name__)

def main():
    """דשבורד אדמין ראשי"""
    
    # בדיקת אימות אדמין
    if not check_admin_auth():
        return
    
    # כותרת
    st.markdown(f"""
    <div class="page-header">
        <h1 class="page-title">👨‍💼 דשבורד מנהל</h1>
        <h3 class="page-subtitle">ניהול מערכת חתונות ובוט WhatsApp</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # טאבים ראשיים
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏠 סקירה כללית", 
        "👫 ניהול זוגות", 
        "📊 סטטיסטיקות", 
        "⚙️ הגדרות מערכת"
    ])
    
    with tab1:
        show_overview_section()
    
    with tab2:
        show_couples_management()
    
    with tab3:
        show_system_statistics()
    
    with tab4:
        show_system_settings()

def check_admin_auth() -> bool:
    """בדיקת אימות אדמין"""
    
    # אם כבר מאומת
    if st.session_state.get('admin_authenticated'):
        return True
    
    # טופס אימות
    st.markdown("""
    <div class="auth-container">
        <h2 class="auth-title">🔐 כניסת מנהל</h2>
        <p>הזן סיסמת אדמין לכניסה למערכת הניהול</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("admin_login"):
        password = st.text_input(
            "סיסמת אדמין:",
            type="password",
            placeholder="הזן סיסמה"
        )
        
        submitted = st.form_submit_button("🔑 כניסה", use_container_width=True)
        
        if submitted:
            if password == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.success("✅ התחברת בהצלחה!")
                st.rerun()
            else:
                st.error("❌ סיסמה שגויה")
    
    return False

def show_overview_section():
    """סקירה כללית של המערכת"""
    
    # סטטיסטיקות מהירות
    gs = get_google_services()
    auth = get_auth_manager()
    
    # קבלת נתונים
    stats = gs.get_statistics()
    sessions = auth.get_active_sessions_count()
    system_health = gs.health_check()
    
    # כרטיסי סטטיסטיקות
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{stats.get('active_couples', 0)}</div>
            <div class="metric-label">👫 זוגות פעילים</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{stats.get('total_expenses', 0)}</div>
            <div class="metric-label">🧾 סך הוצאות</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        total_amount = stats.get('total_amount', 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_amount:,.0f} ₪</div>
            <div class="metric-label">💰 סכום כולל</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        total_sessions = sessions.get('total', 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_sessions}</div>
            <div class="metric-label">👥 סשנים פעילים</div>
        </div>
        """, unsafe_allow_html=True)
    
    # מצב המערכת
    st.markdown("### 🔍 מצב המערכת")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔧 שירותים")
        for service, status in system_health.items():
            status_class = "status-active" if status else "status-inactive"
            status_text = "פעיל" if status else "לא פעיל"
            emoji = "✅" if status else "❌"
            service_name = service.replace("_", " ").title()
            
            st.markdown(f'{emoji} **{service_name}**: <span class="{status_class}">{status_text}</span>', 
                       unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 👥 סשנים")
        for session_type, count in sessions.items():
            if session_type != 'total':
                session_name = session_type.replace("_", " ").title()
                st.write(f"📊 {session_name}: {count}")
    
    # פעילות אחרונה
    if stats.get('last_activity'):
        st.markdown("### 📅 פעילות אחרונה")
        try:
            last_activity = datetime.fromisoformat(stats['last_activity'].replace('Z', '+00:00'))
            time_ago = datetime.now().replace(tzinfo=last_activity.tzinfo) - last_activity
            
            if time_ago.days > 0:
                time_text = f"לפני {time_ago.days} ימים"
            elif time_ago.seconds > 3600:
                hours = time_ago.seconds // 3600
                time_text = f"לפני {hours} שעות"
            else:
                minutes = time_ago.seconds // 60
                time_text = f"לפני {minutes} דקות"
            
            st.info(f"🕐 פעילות אחרונה: {time_text}")
        except:
            st.info(f"🕐 פעילות אחרונה: {stats['last_activity']}")

def show_couples_management():
    """ניהול זוגות"""
    
    gs = get_google_services()
    
    # כפתורי פעולה
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ הוסף זוג חדש", use_container_width=True, type="primary"):
            st.session_state.show_add_couple_form = True
    
    with col2:
        if st.button("🔄 רענן רשימה", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("📊 ייצא נתונים", use_container_width=True):
            export_couples_data()
    
    # טופס הוספת זוג
    if st.session_state.get('show_add_couple_form', False):
        show_add_couple_form()
    
    st.markdown("---")
    
    # רשימת זוגות קיימים
    st.markdown("### 👫 זוגות קיימים")
    
    couples = gs.get_all_active_couples()
    
    if not couples:
        st.info("📝 עדיין לא נוספו זוגות למערכת")
        return
    
    # הכנת DataFrame לתצוגה
    display_data = []
    for couple in couples:
        phone1 = format_phone_display(couple.get('phone1', ''))
        phone2 = format_phone_display(couple.get('phone2', ''))
        
        # חישוב סטטיסטיקות
        expenses = gs.get_expenses_by_group(couple['group_id'])
        active_expenses = [exp for exp in expenses if exp.get('status') == 'active']
        total_amount = sum(float(exp.get('amount', 0)) for exp in active_expenses)
        
        display_data.append({
            'שם הזוג': couple.get('couple_name', ''),
            'טלפון 1': phone1,
            'טלפון 2': phone2,
            'תאריך חתונה': couple.get('wedding_date', ''),
            'תקציב': f"{float(couple.get('budget', 0)):,.0f} ₪" if couple.get('budget') and couple.get('budget') != 'אין עדיין' else 'לא הוגדר',
            'הוצאות': f"{total_amount:,.0f} ₪",
            'קבלות': len(active_expenses),
            'סטטוס': '🟢 פעיל' if couple.get('status') == 'active' else '🔴 לא פעיל',
            'group_id': couple['group_id']
        })
    
    if display_data:
        df_display = pd.DataFrame(display_data)
        
        # תצוגת הטבלה
        st.dataframe(
            df_display.drop(columns=['group_id']),
            use_container_width=True,
            hide_index=True
        )
        
        # פעולות על זוגות
        st.markdown("#### ⚙️ פעולות")
        
        selected_couple = st.selectbox(
            "בחר זוג לפעולות:",
            options=[f"{row['שם הזוג']} ({row['group_id'][:8]}...)" for row in display_data],
            key="selected_couple_for_actions"
        )
        
        if selected_couple:
            # מציאת הזוג הנבחר
            selected_group_id = None
            for row in display_data:
                if f"{row['שם הזוג']} ({row['group_id'][:8]}...)" == selected_couple:
                    selected_group_id = row['group_id']
                    break
            
            if selected_group_id:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("📊 צפה בדשבורד", key=f"view_{selected_group_id}"):
                        # יצירת קישור דשבורד
                        auth = get_auth_manager()
                        dashboard_url = create_dashboard_link(selected_group_id)
                        if dashboard_url:
                            st.success("🔗 קישור נוצר!")
                            st.markdown(f"[👆 לחץ כאן לדשבורד]({dashboard_url})")
                
                with col2:
                    if st.button("📱 שלח קישור דשבורד", key=f"send_{selected_group_id}"):
                        send_dashboard_link_to_couple(selected_group_id)
                
                with col3:
                    if st.button("📋 צפה בהוצאות", key=f"expenses_{selected_group_id}"):
                        show_couple_expenses(selected_group_id)
                
                with col4:
                    if st.button("🗑️ השבת זוג", key=f"deactivate_{selected_group_id}"):
                        deactivate_couple(selected_group_id)

def show_add_couple_form():
    """טופס הוספת זוג חדש"""
    
    st.markdown("### ➕ הוספת זוג חדש")
    
    with st.form("add_couple_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            phone1 = st.text_input(
                "טלפון ראשון:",
                placeholder="050-1234567 או +972501234567",
                help="מספר טלפון של בן/בת הזוג הראשון"
            )
            
            couple_name = st.text_input(
                "שם הזוג (אופציונלי):",
                placeholder="דוד ושרה"
            )
        
        with col2:
            phone2 = st.text_input(
                "טלפון שני:",
                placeholder="052-7654321 או +972527654321",
                help="מספר טלפון של בן/בת הזוג השני"
            )
            
            wedding_date = st.date_input(
                "תאריך חתונה (אופציונלי):",
                value=None
            )
        
        budget = st.number_input(
            "תקציב משוער (אופציונלי):",
            min_value=0.0,
            value=0.0,
            step=1000.0,
            help="תקציב כולל לחתונה"
        )
        
        submitted = st.form_submit_button("🚀 צור זוג וקבוצה", use_container_width=True, type="primary")
        cancel = st.form_submit_button("❌ ביטול", use_container_width=True)
        
        if cancel:
            st.session_state.show_add_couple_form = False
            st.rerun()
        
        if submitted:
            # בדיקת תקינות
            errors = []
            
            if not phone1 or not is_valid_phone(phone1):
                errors.append("טלפון ראשון לא תקין")
            
            if not phone2 or not is_valid_phone(phone2):
                errors.append("טלפון שני לא תקין")
            
            if normalize_phone(phone1) == normalize_phone(phone2):
                errors.append("שני הטלפונים זהים")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # יצירת הזוג והקבוצה
                create_couple_and_group(phone1, phone2, couple_name, wedding_date, budget)

def create_couple_and_group(phone1: str, phone2: str, couple_name: str, wedding_date, budget: float):
    """יצירת זוג חדש וקבוצת WhatsApp"""
    
    with st.spinner("יוצר קבוצה בWhatsApp..."):
        try:
            # נרמול טלפונים
            clean_phone1 = normalize_phone(phone1)
            clean_phone2 = normalize_phone(phone2)
            
            # יצירת קבוצה בWhatsApp
            group_result = create_whatsapp_group([clean_phone1, clean_phone2], couple_name)
            
            if not group_result.get('success'):
                st.error(f"❌ שגיאה ביצירת קבוצה: {group_result.get('error', 'לא ידוע')}")
                return
            
            group_id = group_result['group_id']
            
            # שמירה במערכת
            gs = get_google_services()
            
            couple_result = gs.create_couple(
                phone1=clean_phone1,
                phone2=clean_phone2,
                group_id=group_id,
                couple_name=couple_name or f"זוג {group_id[:8]}",
                wedding_date=wedding_date.strftime('%Y-%m-%d') if wedding_date else "",
                budget=budget
            )
            
            if couple_result.get('success'):
                st.success(f"✅ זוג נוצר בהצלחה!")
                st.success(f"📱 קבוצת WhatsApp נוצרה: {group_id[:8]}...")
                
                # שליחת הודעת ברכה
                send_welcome_message(group_id)
                
                # איפוס הטופס
                st.session_state.show_add_couple_form = False
                st.rerun()
            else:
                st.error(f"❌ שגיאה בשמירת הזוג: {couple_result.get('error', 'לא ידוע')}")
                
        except Exception as e:
            logger.error(f"Error creating couple: {e}")
            st.error(f"❌ שגיאה כללית: {str(e)}")

def create_whatsapp_group(phone_numbers: List[str], group_name: str = None) -> Dict:
    """יצירת קבוצת WhatsApp עם הטלפונים הנתונים"""
    
    try:
        if not GREENAPI_INSTANCE_ID or not GREENAPI_TOKEN:
            return {"success": False, "error": "WhatsApp API לא מוגדר"}
        
        # הכנת שם קבוצה
        if not group_name:
            timestamp = datetime.now().strftime('%d/%m %H:%M')
            group_name = f"חתונה חכמה {timestamp}"
        
        # הכנת רשימת משתתפים (פורמט WhatsApp)
        participants = []
        for phone in phone_numbers:
            clean_phone = normalize_phone(phone)
            if clean_phone.startswith('0'):
                whatsapp_id = '972' + clean_phone[1:] + '@c.us'
            else:
                whatsapp_id = clean_phone + '@c.us'
            participants.append(whatsapp_id)
        
        # יצירת הקבוצה
        url = f"https://api.green-api.com/waInstance{GREENAPI_INSTANCE_ID}/createGroup/{GREENAPI_TOKEN}"
        
        payload = {
            "groupName": group_name,
            "chatIds": participants
        }
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            group_id = data.get('chatId', '')
            
            if group_id:
                logger.info(f"WhatsApp group created: {group_id}")
                return {
                    "success": True,
                    "group_id": group_id,
                    "group_name": group_name
                }
            else:
                return {"success": False, "error": "לא התקבל group_id"}
        else:
            error_msg = f"API Error: {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get('message', error_msg)
            except:
                pass
            
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        logger.error(f"Error creating WhatsApp group: {e}")
        return {"success": False, "error": str(e)}

def send_welcome_message(group_id: str):
    """שליחת הודעת ברכה לקבוצה החדשה"""
    
    try:
        url = f"https://api.green-api.com/waInstance{GREENAPI_INSTANCE_ID}/sendMessage/{GREENAPI_TOKEN}"
        
        payload = {
            "chatId": group_id,
            "message": BOT_MESSAGES["welcome"]
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Welcome message sent to group: {group_id}")
        else:
            logger.warning(f"Failed to send welcome message: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

def create_dashboard_link(group_id: str) -> str:
    """יצירת קישור דשבורד לזוג"""
    
    try:
        auth = get_auth_manager()
        base_url = st.session_state.get('base_url', 'http://localhost:8501')
        return auth.get_dashboard_link(group_id, base_url)
    except Exception as e:
        logger.error(f"Error creating dashboard link: {e}")
        return ""

def send_dashboard_link_to_couple(group_id: str):
    """שליחת קישור דשבורד לזוג בWhatsApp"""
    
    try:
        # יצירת קישור
        dashboard_url = create_dashboard_link(group_id)
        
        if not dashboard_url:
            st.error("❌ שגיאה ביצירת קישור")
            return
        
        # שליחת הודעה
        message = BOT_MESSAGES["dashboard_link"].format(link=dashboard_url)
        
        url = f"https://api.green-api.com/waInstance{GREENAPI_INSTANCE_ID}/sendMessage/{GREENAPI_TOKEN}"
        
        payload = {
            "chatId": group_id,
            "message": message
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            st.success("✅ קישור דשבורד נשלח לזוג בWhatsApp")
        else:
            st.error(f"❌ שגיאה בשליחת הודעה: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error sending dashboard link: {e}")
        st.error(f"❌ שגיאה: {str(e)}")

def show_couple_expenses(group_id: str):
    """הצגת הוצאות זוג"""
    
    gs = get_google_services()
    expenses = gs.get_expenses_by_group(group_id)
    
    if not expenses:
        st.info("📝 עדיין אין הוצאות לזוג זה")
        return
    
    active_expenses = [exp for exp in expenses if exp.get('status') == 'active']
    
    st.markdown(f"### 💰 הוצאות זוג ({len(active_expenses)} קבלות)")
    
    # סיכום מהיר
    total_amount = sum(float(exp.get('amount', 0)) for exp in active_expenses)
    st.metric("סכום כולל", f"{total_amount:,.0f} ₪")
    
    # טבלת הוצאות
    display_data = []
    for exp in active_expenses:
        display_data.append({
            'תאריך': exp.get('date', ''),
            'ספק': exp.get('vendor', ''),
            'קטגוריה': exp.get('category', ''),
            'סכום': f"{float(exp.get('amount', 0)):,.0f} ₪",
            'תיאור': exp.get('description', ''),
            'ביטחון AI': f"{exp.get('confidence', 0)}%"
        })
    
    if display_data:
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

def deactivate_couple(group_id: str):
    """השבתת זוג"""
    
    if st.button(f"⚠️ אישור השבתה", key=f"confirm_deactivate_{group_id}"):
        gs = get_google_services()
        success = gs.update_couple_field(group_id, 'status', 'inactive')
        
        if success:
            st.success("✅ זוג הושבת בהצלחה")
            st.rerun()
        else:
            st.error("❌ שגיאה בהשבתת הזוג")

def export_couples_data():
    """ייצוא נתוני זוגות"""
    
    gs = get_google_services()
    couples = gs.get_all_active_couples()
    
    if not couples:
        st.warning("אין נתונים לייצוא")
        return
    
    # הכנת DataFrame
    export_data = []
    for couple in couples:
        expenses = gs.get_expenses_by_group(couple['group_id'])
        active_expenses = [exp for exp in expenses if exp.get('status') == 'active']
        total_amount = sum(float(exp.get('amount', 0)) for exp in active_expenses)
        
        export_data.append({
            'מזהה קבוצה': couple['group_id'],
            'שם זוג': couple.get('couple_name', ''),
            'טלפון 1': couple.get('phone1', ''),
            'טלפון 2': couple.get('phone2', ''),
            'תאריך חתונה': couple.get('wedding_date', ''),
            'תקציב': couple.get('budget', ''),
            'סכום הוצאות': total_amount,
            'מספר קבלות': len(active_expenses),
            'תאריך יצירה': couple.get('created_at', ''),
            'פעילות אחרונה': couple.get('last_activity', ''),
            'סטטוס': couple.get('status', '')
        })
    
    if export_data:
        df_export = pd.DataFrame(export_data)
        
        csv = df_export.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 הורד נתוני זוגות (CSV)",
            data=csv,
            file_name=f"couples_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def show_system_statistics():
    """סטטיסטיקות מערכת מפורטות"""
    
    gs = get_google_services()
    couples = gs.get_all_active_couples()
    
    if not couples:
        st.info("📊 אין עדיין נתונים לסטטיסטיקות")
        return
    
    # חישוב סטטיסטיקות מתקדמות
    all_expenses = []
    couples_with_expenses = 0
    
    for couple in couples:
        expenses = gs.get_expenses_by_group(couple['group_id'])
        active_expenses = [exp for exp in expenses if exp.get('status') == 'active']
        
        if active_expenses:
            couples_with_expenses += 1
            all_expenses.extend(active_expenses)
    
    # כרטיסי סטטיסטיקות
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_expenses_per_couple = len(all_expenses) / len(couples) if couples else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{avg_expenses_per_couple:.1f}</div>
            <div class="metric-label">📊 ממוצע קבלות לזוג</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_amount = sum(float(exp.get('amount', 0)) for exp in all_expenses)
        avg_amount = total_amount / len(couples) if couples else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{avg_amount:,.0f} ₪</div>
            <div class="metric-label">💰 ממוצע הוצאות לזוג</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        activity_rate = (couples_with_expenses / len(couples) * 100) if couples else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{activity_rate:.1f}%</div>
            <div class="metric-label">📈 שיעור פעילות</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        high_confidence = len([exp for exp in all_expenses if exp.get('confidence', 0) >= 90])
        confidence_rate = (high_confidence / len(all_expenses) * 100) if all_expenses else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{confidence_rate:.1f}%</div>
            <div class="metric-label">🎯 דיוק AI</div>
        </div>
        """, unsafe_allow_html=True)
    
    # גרף קטגוריות
    if all_expenses:
        st.markdown("### 📊 התפלגות קטגוריות")
        
        import plotly.express as px
        
        categories_data = {}
        for exp in all_expenses:
            category = exp.get('category', 'אחר')
            amount = float(exp.get('amount', 0))
            categories_data[category] = categories_data.get(category, 0) + amount
        
        if categories_data:
            fig = px.pie(
                values=list(categories_data.values()),
                names=list(categories_data.keys()),
                title="התפלגות הוצאות לפי קטגוריה"
            )
            st.plotly_chart(fig, use_container_width=True)

def show_system_settings():
    """הגדרות מערכת"""
    
    st.markdown("### ⚙️ הגדרות מערכת")
    
    # בדיקת מצב שירותים
    gs = get_google_services()
    health = gs.health_check()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔍 מצב שירותים")
        for service, status in health.items():
            emoji = "✅" if status else "❌"
            status_text = "פעיל" if status else "לא פעיל"
            service_name = service.replace("_", " ").title()
            st.write(f"{emoji} {service_name}: {status_text}")
    
    with col2:
        st.markdown("#### 🔧 כלי ניהול")
        
        if st.button("🧹 נקה סשנים פגי תוקף"):
            auth = get_auth_manager()
            auth.cleanup_expired()
            st.success("✅ ניקוי הושלם")
        
        if st.button("📊 רענן נתונים"):
            st.rerun()
        
        if st.button("🚪 יציאה מאדמין"):
            st.session_state.admin_authenticated = False
            st.rerun()
    
    # מידע טכני
    st.markdown("---")
    st.markdown("#### ℹ️ מידע טכני")
    
    st.code(f"""
WhatsApp Instance: {GREENAPI_INSTANCE_ID[:10] if GREENAPI_INSTANCE_ID else 'לא מוגדר'}...
Google Sheets: {'מחובר' if health.get('sheets_connection') else 'לא מחובר'}
OpenAI: {'מוגדר' if health.get('openai_configured') else 'לא מוגדר'}
""", language="yaml")

if __name__ == "__main__":
    main()