import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from config import get_main_css, COLORS, WEDDING_CATEGORIES, BOT_MESSAGES
from auth_system import require_auth, get_auth_manager
from google_services import get_google_services

def main():
    """הדשבורד הראשי של המערכת"""
    
    # הגדרות דף
    st.set_page_config(
        page_title="דשבורד חתונה",
        page_icon="💒",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # טעינת CSS
    st.markdown(get_main_css(), unsafe_allow_html=True)
    
    # דרישת אימות
    if not check_authentication():
        return
    
    # קבלת נתוני המשתמש
    group_id = st.session_state.user_group_id
    
    if not group_id:
        st.error("❌ לא נמצא מזהה קבוצה. אנא פנה לתמיכה.")
        return
    
    # טעינת נתונים
    gs = get_google_services()
    couple_data = gs.get_couple_by_group_id(group_id)
    expenses_data = gs.get_expenses_by_group(group_id)
    
    if not couple_data:
        st.error("❌ לא נמצאו נתוני הזוג. אנא פנה לתמיכה.")
        return
    
    # בניית הדשבורד
    render_dashboard(couple_data, expenses_data, group_id)

def check_authentication() -> bool:
    """בדיקת אימות מתקדמת"""
    
    # בדיקה אם יש טוכן ב-URL
    token_from_url = st.query_params.get('token')
    
    if token_from_url and token_from_url != st.session_state.get('auth_token'):
        # טוכן חדש מה-URL - נבדק אותו
        auth_manager = get_auth_manager()
        result = auth_manager.validate_token(token_from_url)
        
        if result.get('valid'):
            st.session_state.auth_token = token_from_url
            st.session_state.user_group_id = result.get('group_id')
            st.session_state.user_phone = result.get('phone', '')
            st.session_state.auth_expires = result.get('expires_at')
            return True
        else:
            st.error("🔒 קישור לא תקף או פג תוקף")
            show_auth_form()
            return False
    
    # בדיקה אם יש אימות קיים
    if st.session_state.get('auth_token'):
        auth_manager = get_auth_manager()
        result = auth_manager.validate_token(st.session_state.auth_token)
        
        if result.get('valid'):
            return True
        else:
            # טוכן פג תוקף
            st.session_state.clear()
            st.error("🔒 סשן פג תוקף. אנא התחבר שוב.")
    
    # אין אימות - הצג טופס
    show_auth_form()
    return False

def show_auth_form():
    """טופס אימות מעוצב"""
    
    st.markdown("""
    <div class="auth-container">
        <h1 class="auth-title">💒 דשבורד החתונה שלכם</h1>
        <p style="color: """ + COLORS['text_medium'] + """; margin-bottom: 30px;">
            הזינו את מספר הטלפון לקבלת קוד אימות
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # איתחול שלב האימות
    if 'auth_step' not in st.session_state:
        st.session_state.auth_step = 'phone'
    
    # שלב 1: הזנת טלפון
    if st.session_state.auth_step == 'phone':
        with st.form("phone_form", clear_on_submit=False):
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                phone = st.text_input(
                    "מספר טלפון:",
                    placeholder="050-1234567",
                    help="הזינו את המספר הרשום במערכת",
                    key="phone_input"
                )
                
                submitted = st.form_submit_button(
                    "📱 שליחת קוד אימות", 
                    use_container_width=True
                )
                
                if submitted and phone:
                    auth_manager = get_auth_manager()
                    result = auth_manager.request_auth_code(phone)
                    
                    if result.get('success'):
                        st.session_state.auth_phone = phone
                        st.session_state.auth_step = 'code'
                        st.success("✅ קוד אימות נשלח לWhatsApp")
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error', 'שגיאה בשליחת קוד')}")
    
    # שלב 2: הזנת קוד
    elif st.session_state.auth_step == 'code':
        st.info(f"📱 קוד אימות נשלח ל-{st.session_state.auth_phone}")
        
        with st.form("code_form", clear_on_submit=False):
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                code = st.text_input(
                    "קוד אימות:",
                    placeholder="1234",
                    max_chars=4,
                    help="הזינו את הקוד מWhatsApp",
                    key="code_input"
                )
                
                col_verify, col_back = st.columns(2)
                
                with col_verify:
                    verify_btn = st.form_submit_button("🔓 אימות", use_container_width=True)
                
                with col_back:
                    back_btn = st.form_submit_button("↩️ חזור", use_container_width=True)
                
                if verify_btn and code:
                    auth_manager = get_auth_manager()
                    result = auth_manager.verify_auth_code(st.session_state.auth_phone, code)
                    
                    if result.get('success'):
                        st.session_state.auth_token = result['token']
                        st.session_state.user_group_id = result.get('group_id')
                        st.session_state.user_phone = st.session_state.auth_phone
                        st.session_state.auth_expires = result.get('expires_at')
                        st.success("✅ התחברתם בהצלחה!")
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error', 'קוד שגוי')}")
                
                if back_btn:
                    st.session_state.auth_step = 'phone'
                    st.rerun()

def render_dashboard(couple_data: Dict, expenses_data: List[Dict], group_id: str):
    """רינדור הדשבורד הראשי"""
    
    # כותרת עליונה
    render_header(couple_data)
    
    # סטטיסטיקות עליונות
    render_statistics_cards(expenses_data, couple_data)
    
    # גרפים
    if expenses_data:
        render_charts(expenses_data)
    
    # טבלת הוצאות אחרונות
    render_recent_expenses(expenses_data)
    
    # כפתורי פעולה
    render_action_buttons(group_id)
    
    # סייד בר עם פילטרים
    render_sidebar(expenses_data, couple_data, group_id)

def render_header(couple_data: Dict):
    """כותרת הדשבורד"""
    
    wedding_date = couple_data.get('wedding_date', '')
    couple_name = couple_data.get('couple_name', 'הזוג החמוד')
    
    # חישוב ימים לחתונה
    days_left = ""
    if wedding_date:
        try:
            wedding_dt = datetime.strptime(wedding_date, '%Y-%m-%d')
            today = datetime.now()
            delta = (wedding_dt - today).days
            
            if delta > 0:
                days_left = f"נותרו {delta} ימים לחתונה! 🎉"
            elif delta == 0:
                days_left = "החתונה היום! 🥳"
            else:
                days_left = f"עברו {abs(delta)} ימים מהחתונה 💕"
        except:
            pass
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        color: white;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
    ">
        <h1 style="margin: 0 0 10px 0; font-size: 2.5rem;">💒 {couple_name}</h1>
        <h3 style="margin: 0; opacity: 0.9; font-weight: normal;">{days_left}</h3>
    </div>
    """, unsafe_allow_html=True)

def render_statistics_cards(expenses_data: List[Dict], couple_data: Dict):
    """כרטיסי סטטיסטיקות"""
    
    # חישוב סטטיסטיקות
    active_expenses = [exp for exp in expenses_data if exp.get('status') == 'active']
    total_amount = sum(float(exp.get('amount', 0)) for exp in active_expenses)
    total_count = len(active_expenses)
    avg_amount = total_amount / total_count if total_count > 0 else 0
    
    # תקציב
    budget_str = couple_data.get('budget', '')
    budget_amount = 0
    budget_percentage = 0
    
    if budget_str and budget_str not in ['אין עדיין', '']:
        try:
            budget_amount = float(budget_str)
            budget_percentage = (total_amount / budget_amount * 100) if budget_amount > 0 else 0
        except:
            pass
    
    # צבע לפי סטטוס תקציב
    if budget_percentage < 50:
        budget_color = COLORS['success']
    elif budget_percentage < 80:
        budget_color = COLORS['accent']
    else:
        budget_color = COLORS['warning']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="border-right: 4px solid {COLORS['primary']};">
            <div class="metric-value">{total_amount:,.0f} ₪</div>
            <div class="metric-label">💰 סך ההוצאות</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="border-right: 4px solid {COLORS['secondary']};">
            <div class="metric-value">{total_count}</div>
            <div class="metric-label">📋 מספר קבלות</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="border-right: 4px solid {COLORS['accent']};">
            <div class="metric-value">{avg_amount:,.0f} ₪</div>
            <div class="metric-label">📊 ממוצע לקבלה</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        if budget_amount > 0:
            st.markdown(f"""
            <div class="metric-card" style="border-right: 4px solid {budget_color};">
                <div class="metric-value" style="color: {budget_color};">{budget_percentage:.1f}%</div>
                <div class="metric-label">🎯 מהתקציב</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="metric-card" style="border-right: 4px solid {COLORS['text_light']};">
                <div class="metric-value">—</div>
                <div class="metric-label">🎯 אין תקציב</div>
            </div>
            """, unsafe_allow_html=True)

def render_charts(expenses_data: List[Dict]):
    """גרפים של ההוצאות"""
    
    st.markdown("## 📊 ניתוח הוצאות")
    
    active_expenses = [exp for exp in expenses_data if exp.get('status') == 'active']
    
    if not active_expenses:
        st.info("📝 עדיין לא נוספו הוצאות")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # גרף קטגוריות
        st.markdown("### 🏷️ הוצאות לפי קטגוריה")
        
        categories_data = {}
        for exp in active_expenses:
            category = exp.get('category', 'אחר')
            amount = float(exp.get('amount', 0))
            categories_data[category] = categories_data.get(category, 0) + amount
        
        if categories_data:
            # הכנת DataFrame
            df_categories = pd.DataFrame([
                {'קטגוריה': f"{WEDDING_CATEGORIES.get(cat, '📋')} {cat}", 'סכום': amount}
                for cat, amount in categories_data.items()
            ])
            
            fig_pie = px.pie(
                df_categories,
                values='סכום',
                names='קטגוריה',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            fig_pie.update_layout(
                font=dict(size=12),
                showlegend=True,
                height=400,
                margin=dict(t=20, b=20, l=20, r=20)
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # גרף זמן
        st.markdown("### 📅 הוצאות לאורך זמן")
        
        # הכנת נתונים לפי תאריך
        monthly_data = {}
        for exp in active_expenses:
            date_str = exp.get('date', '')
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    month_key = date_obj.strftime('%Y-%m')
                    amount = float(exp.get('amount', 0))
                    monthly_data[month_key] = monthly_data.get(month_key, 0) + amount
                except:
                    continue
        
        if monthly_data:
            # מיון לפי תאריך
            sorted_months = sorted(monthly_data.items())
            
            df_monthly = pd.DataFrame([
                {'חודש': month, 'סכום': amount}
                for month, amount in sorted_months
            ])
            
            fig_line = px.bar(
                df_monthly,
                x='חודש',
                y='סכום',
                color_discrete_sequence=[COLORS['primary']]
            )
            
            fig_line.update_layout(
                xaxis_title="חודש",
                yaxis_title="סכום (₪)",
                font=dict(size=12),
                height=400,
                margin=dict(t=20, b=20, l=20, r=20)
            )
            
            st.plotly_chart(fig_line, use_container_width=True)

def render_recent_expenses(expenses_data: List[Dict]):
    """טבלת הוצאות אחרונות"""
    
    st.markdown("## 📋 הוצאות אחרונות")
    
    active_expenses = [exp for exp in expenses_data if exp.get('status') == 'active']
    
    if not active_expenses:
        st.info("📝 עדיין לא נוספו הוצאות. שלחו קבלות לבוט בWhatsApp!")
        return
    
    # מיון לפי תאריך יצירה (חדשים ראשון)
    sorted_expenses = sorted(
        active_expenses, 
        key=lambda x: x.get('created_at', ''), 
        reverse=True
    )
    
    # הכנת DataFrame לתצוגה
    display_data = []
    for exp in sorted_expenses[:10]:  # 10 אחרונות
        vendor = exp.get('vendor', 'לא מזוהה')
        amount = float(exp.get('amount', 0))
        category = exp.get('category', 'אחר')
        date = exp.get('date', '')
        emoji = WEDDING_CATEGORIES.get(category, '📋')
        
        # עיצוב תאריך
        if date:
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d/%m/%Y')
            except:
                formatted_date = date
        else:
            formatted_date = ''
        
        display_data.append({
            'קטגוריה': f"{emoji} {category}",
            'ספק': vendor,
            'סכום': f"{amount:,.0f} ₪",
            'תאריך': formatted_date
        })
    
    if display_data:
        df_display = pd.DataFrame(display_data)
        
        # עיצוב הטבלה
        st.markdown("""
        <style>
        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "קטגוריה": st.column_config.TextColumn("קטגוריה", width="small"),
                "ספק": st.column_config.TextColumn("ספק", width="medium"),
                "סכום": st.column_config.TextColumn("סכום", width="small"),
                "תאריך": st.column_config.TextColumn("תאריך", width="small")
            }
        )

def render_action_buttons(group_id: str):
    """כפתורי פעולה מרכזיים"""
    
    st.markdown("## 🛠️ פעולות")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📱 חיבור אנשי קשר", use_container_width=True, type="primary"):
            # יצירת קישור למערכת חיבור אנשי קשר
            auth_manager = get_auth_manager()
            phone = st.session_state.get('user_phone', '')
            
            # כאן נצטרך להוסיף את base_url הנכון
            base_url = "https://your-domain.com"  # TODO: להחליף עם URL אמיתי
            
            merge_link = auth_manager.get_contacts_merge_link(group_id, phone, base_url)
            
            if merge_link:
                st.success("🔗 קישור נוצר!")
                st.markdown(f"[👆 לחץ כאן לחיבור אנשי קשר]({merge_link})")
            else:
                st.error("שגיאה ביצירת קישור")
    
    with col2:
        if st.button("💰 הוסף הוצאה", use_container_width=True):
            show_manual_expense_form(group_id)
    
    with col3:
        if st.button("📊 ייצא נתונים", use_container_width=True):
            export_data(group_id)
    
    with col4:
        if st.button("⚙️ הגדרות", use_container_width=True):
            show_settings_form(group_id)

def show_manual_expense_form(group_id: str):
    """טופס הוספת הוצאה ידנית"""
    
    with st.expander("💰 הוספת הוצאה ידנית", expanded=True):
        with st.form("manual_expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                vendor = st.text_input("שם הספק:", placeholder="לדוגמה: צלם דני")
                amount = st.number_input("סכום:", min_value=0.0, step=10.0)
            
            with col2:
                category = st.selectbox("קטגוריה:", options=list(WEDDING_CATEGORIES.keys()))
                date = st.date_input("תאריך:", value=datetime.now())
            
            description = st.text_input("תיאור (אופציונלי):", placeholder="תיאור קצר של ההוצאה")
            
            submitted = st.form_submit_button("💾 שמור הוצאה", use_container_width=True)
            
            if submitted and vendor and amount > 0:
                gs = get_google_services()
                
                expense_data = {
                    'vendor': vendor.strip(),
                    'amount': amount,
                    'category': category,
                    'date': date.strftime('%Y-%m-%d'),
                    'description': description.strip(),
                    'group_id': group_id,
                    'payment_method': None,
                    'confidence': 100,
                    'needs_review': False,
                    'source': 'manual_dashboard'
                }
                
                if gs.save_expense(expense_data):
                    st.success(f"✅ הוצאה נשמרה: {vendor} - {amount:,.0f} ₪")
                    st.rerun()
                else:
                    st.error("❌ שגיאה בשמירת ההוצאה")

def export_data(group_id: str):
    """ייצוא נתונים"""
    gs = get_google_services()
    expenses = gs.get_expenses_by_group(group_id)
    
    if not expenses:
        st.warning("אין נתונים לייצוא")
        return
    
    # הכנת DataFrame
    export_data = []
    for exp in expenses:
        if exp.get('status') == 'active':
            export_data.append({
                'תאריך': exp.get('date', ''),
                'ספק': exp.get('vendor', ''),
                'קטגוריה': exp.get('category', ''),
                'סכום': float(exp.get('amount', 0)),
                'תיאור': exp.get('description', ''),
                'אמצעי תשלום': exp.get('payment_method', ''),
                'תאריך יצירה': exp.get('created_at', '')
            })
    
    if export_data:
        df_export = pd.DataFrame(export_data)
        
        # הורדה כ-CSV
        csv = df_export.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 הורד כ-CSV",
            data=csv,
            file_name=f"expenses_{group_id}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def show_settings_form(group_id: str):
    """טופס הגדרות"""
    
    with st.expander("⚙️ הגדרות זוג", expanded=True):
        gs = get_google_services()
        couple_data = gs.get_couple_by_group_id(group_id)
        
        if not couple_data:
            st.error("לא נמצאו נתוני זוג")
            return
        
        with st.form("settings_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                couple_name = st.text_input(
                    "שם הזוג:", 
                    value=couple_data.get('couple_name', ''),
                    placeholder="הזוג החמוד"
                )
                
                wedding_date = st.date_input(
                    "תאריך חתונה:",
                    value=datetime.strptime(couple_data.get('wedding_date', '2024-12-31'), '%Y-%m-%d') if couple_data.get('wedding_date') else datetime.now()
                )
            
            with col2:
                budget = st.number_input(
                    "תקציב כולל:",
                    value=float(couple_data.get('budget', 0)) if couple_data.get('budget') and couple_data.get('budget') != 'אין עדיין' else 0.0,
                    min_value=0.0,
                    step=1000.0
                )
            
            submitted = st.form_submit_button("💾 שמור הגדרות", use_container_width=True)
            
            if submitted:
                updates = {}
                
                if couple_name.strip():
                    updates['couple_name'] = couple_name.strip()
                
                updates['wedding_date'] = wedding_date.strftime('%Y-%m-%d')
                
                if budget > 0:
                    updates['budget'] = str(budget)
                else:
                    updates['budget'] = 'אין עדיין'
                
                success = True
                for field, value in updates.items():
                    if not gs.update_couple_field(group_id, field, value):
                        success = False
                        break
                
                if success:
                    st.success("✅ הגדרות נשמרו בהצלחה!")
                    st.rerun()
                else:
                    st.error("❌ שגיאה בשמירת הגדרות")

def render_sidebar(expenses_data: List[Dict], couple_data: Dict, group_id: str):
    """סייד בר עם מידע נוסף"""
    
    with st.sidebar:
        st.markdown(f"""
        <div style="
            background: {COLORS['accent']};
            color: {COLORS['primary']};
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 20px;
        ">
            <h3 style="margin: 0;">💒 מידע כללי</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # נתוני זוג
        st.markdown("### 👫 פרטי הזוג")
        st.write(f"**שם:** {couple_data.get('couple_name', 'לא הוגדר')}")
        st.write(f"**תאריך חתונה:** {couple_data.get('wedding_date', 'לא הוגדר')}")
        st.write(f"**תקציב:** {couple_data.get('budget', 'לא הוגדר')}")
        
        st.markdown("---")
        
        # סטטיסטיקות מהירות
        st.markdown("### 📊 סטטיסטיקות")
        
        active_expenses = [exp for exp in expenses_data if exp.get('status') == 'active']
        
        if active_expenses:
            # הוצאה הגבוהה ביותר
            max_expense = max(active_expenses, key=lambda x: float(x.get('amount', 0)))
            st.write(f"**הוצאה הגבוהה ביותר:**")
            st.write(f"{max_expense.get('vendor', 'לא מזוהה')} - {float(max_expense.get('amount', 0)):,.0f} ₪")
            
            # קטגוריה הכי יקרה
            categories_sum = {}
            for exp in active_expenses:
                cat = exp.get('category', 'אחר')
                amount = float(exp.get('amount', 0))
                categories_sum[cat] = categories_sum.get(cat, 0) + amount
            
            if categories_sum:
                top_category = max(categories_sum.items(), key=lambda x: x[1])
                emoji = WEDDING_CATEGORIES.get(top_category[0], '📋')
                st.write(f"**קטגוריה יקרה ביותר:**")
                st.write(f"{emoji} {top_category[0]} - {top_category[1]:,.0f} ₪")
            
            # הוצאות החודש
            current_month = datetime.now().strftime('%Y-%m')
            month_expenses = [
                exp for exp in active_expenses 
                if exp.get('date', '').startswith(current_month)
            ]
            
            if month_expenses:
                month_total = sum(float(exp.get('amount', 0)) for exp in month_expenses)
                st.write(f"**הוצאות החודש:**")
                st.write(f"{month_total:,.0f} ₪ ({len(month_expenses)} קבלות)")
        
        st.markdown("---")
        
        # קישורים מהירים
        st.markdown("### 🔗 קישורים מהירים")
        
        if st.button("🔄 רענן נתונים", use_container_width=True):
            st.rerun()
        
        if st.button("🚪 יציאה", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        # מידע על הסשן
        st.markdown("---")
        st.markdown("### ℹ️ מידע טכני")
        
        if 'auth_expires' in st.session_state:
            try:
                expires_dt = datetime.fromisoformat(st.session_state.auth_expires.replace('Z', '+00:00'))
                time_left = expires_dt - datetime.now(expires_dt.tzinfo)
                
                if time_left.total_seconds() > 0:
                    hours_left = int(time_left.total_seconds() // 3600)
                    minutes_left = int((time_left.total_seconds() % 3600) // 60)
                    st.write(f"**זמן סשן נותר:** {hours_left}:{minutes_left:02d}")
                else:
                    st.write("**סשן פג תוקף** - יש להתחבר מחדש")
            except:
                st.write("**זמן סשן:** לא ידוע")
        
        st.write(f"**מזהה קבוצה:** {group_id[:8]}...")


if __name__ == "__main__":
    main()