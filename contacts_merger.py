import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from io import BytesIO
import json

from config import COLORS
from auth_system import get_auth_manager
from google_services import get_google_services

# הכללת הלוגיקה מהמערכת
from src.logic import (
    NAME_COL, PHONE_COL, COUNT_COL, SIDE_COL, GROUP_COL,
    AUTO_SELECT_TH, load_excel, to_buf,
    format_phone, normalize, compute_best_scores, full_score,
    get_top_matches, search_contacts, export_merged_data,
    get_matching_statistics
)

def main():
    """מערכת חיבור אנשי קשר מאוחדת"""
    
    # בדיקת אימות
    if not check_authentication():
        return
    
    # קבלת נתוני המשתמש
    group_id = st.session_state.user_group_id
    phone = st.session_state.user_phone
    
    if not group_id:
        st.error("❌ לא נמצא מזהה קבוצה. אנא חזור לדשבורד.")
        return
    
    # בדיקת התקדמות קיימת
    gs = get_google_services()
    progress = gs.get_contacts_progress(group_id)
    
    # כותרת
    render_header()
    
    # מצבי המערכת
    if not st.session_state.get('upload_confirmed', False):
        # שלב 1: העלאת קבצים
        render_file_upload_section(group_id, progress)
    else:
        # שלב 2: עבודה על המוזמנים
        render_contacts_merge_section(group_id)

def check_authentication() -> bool:
    """בדיקת אימות דומה לדשבורד הראשי"""
    
    # בדיקה אם יש טוכן מה-URL
    token_from_url = st.session_state.get('url_token') or st.query_params.get('token')
    group_from_url = st.session_state.get('url_group_id') or st.query_params.get('group_id')
    
    if token_from_url and token_from_url != st.session_state.get('auth_token'):
        auth_manager = get_auth_manager()
        result = auth_manager.validate_token(token_from_url)
        
        if result.get('valid'):
            # ווידוא שזה טוכן של contacts_merge
            token_type = result.get('type', 'user')
            if token_type == 'contacts_merge':
                st.session_state.auth_token = token_from_url
                st.session_state.user_group_id = group_from_url or result.get('group_id')
                st.session_state.user_phone = result.get('phone', '')
                return True
            else:
                st.error("🔒 קישור לא מתאים למערכת חיבור אנשי קשר")
                return False
        else:
            st.error("🔒 קישור לא תקף או פג תוקף")
            return False
    
    # בדיקת אימות קיים
    if st.session_state.get('auth_token'):
        auth_manager = get_auth_manager()
        result = auth_manager.validate_token(st.session_state.auth_token)
        
        if result.get('valid'):
            return True
        else:
            st.session_state.clear()
            st.error("🔒 סשן פג תוקף. אנא חזור לדשבורד ובקש קישור חדש.")
    
    st.error("🔒 נדרש קישור תקף ממערכת הדשבורד")
    return False

def render_header():
    """כותרת מערכת חיבור אנשי קשר"""
    
    st.markdown(f"""
    <div class="page-header">
        <h1 class="page-title">📱 חיבור אנשי קשר למוזמנים</h1>
        <h3 class="page-subtitle">מיזוג חכם ומהיר של רשימת המוזמנים עם אנשי הקשר שלכם</h3>
    </div>
    """, unsafe_allow_html=True)

def render_file_upload_section(group_id: str, progress: Dict):
    """סקציית העלאת קבצים משופרת"""
    
    # בדיקה אם יש התקדמות קודמת
    if progress:
        st.markdown(f"""
        <div class="alert alert-warning">
            <h4>📂 נמצאה עבודה קודמת</h4>
            <p>נמצא פרויקט חיבור קיים מתאריך {progress.get('started_at', 'לא ידוע')}.</p>
            <p>רוצים להמשיך מהמקום שעצרתם או להתחיל מחדש?</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ המשך מהמקום שעצרתי", use_container_width=True, type="primary"):
                st.info("🔄 טוען נתונים קיימים...")
                load_existing_progress(group_id, progress)
                return
        
        with col2:
            if st.button("🔄 התחל מחדש", use_container_width=True):
                # מחיקת התקדמות קודמת
                gs = get_google_services()
                gs.update_couple_field(group_id, 'contacts_progress', '')
                st.rerun()
    
    # מדריך קצר
    with st.expander("📖 מדריך מהיר", expanded=True):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("""
            #### 📋 שלבי החיבור:
            
            1. **📱 קובץ אנשי קשר** - הורידו מWhatsApp Web באמצעות תוסף ג'וני
            2. **🎉 קובץ מוזמנים** - רשימת המוזמנים שלכם (Excel/CSV)
            3. **🤖 חיבור אוטומטי** - המערכת תציע התאמות חכמות
            4. **✅ אישור ועריכה** - תוכלו לבדוק ולתקן כל התאמה
            5. **💾 שמירה** - הקובץ הסופי יישמר בענן
            
            💡 **טיפ:** המערכת שומרת את ההתקדמות אוטומטית!
            """)
        
        with col2:
            # כפתור מדריך מפורט לתוסף ג'וני
            if st.button("📘 מדריך הורדת\nאנשי קשר", use_container_width=True):
                show_joni_guide()
    
    st.markdown("---")
    
    # העלאת קבצים
    st.markdown("### 📂 העלאת קבצים")
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="form-section" style="border-right: 4px solid {COLORS['secondary']};">
                <h4 style="color: {COLORS['primary']}; text-align: center; margin-bottom: 15px;">
                    👥 קובץ אנשי קשר
                </h4>
                <p style="color: {COLORS['text_medium']}; text-align: center; font-size: 0.9rem;">
                    קובץ Excel שהורד מWhatsApp Web
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            contacts_file = st.file_uploader(
                "בחר קובץ אנשי קשר",
                type=['xlsx', 'xls', 'csv'],
                key='contacts_uploader',
                help="קובץ שהורד באמצעות תוסף ג'וני מWhatsApp Web",
                label_visibility="collapsed"
            )
            
            if contacts_file:
                st.success("✅ קובץ אנשי קשר נטען")
        
        with col2:
            st.markdown(f"""
            <div class="form-section" style="border-right: 4px solid {COLORS['accent']};">
                <h4 style="color: {COLORS['primary']}; text-align: center; margin-bottom: 15px;">
                    🎉 רשימת מוזמנים
                </h4>
                <p style="color: {COLORS['text_medium']}; text-align: center; font-size: 0.9rem;">
                    קובץ Excel/CSV עם רשימת המוזמנים
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            guests_file = st.file_uploader(
                "בחר רשימת מוזמנים",
                type=['xlsx', 'xls', 'csv'],
                key='guests_uploader',
                help="רשימת המוזמנים שלכם (Excel או CSV)",
                label_visibility="collapsed"
            )
            
            if guests_file:
                st.success("✅ רשימת מוזמנים נטענה")
    
    # כפתור אישור
    if contacts_file and guests_file:
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("🚀 התחל עבודה על החיבור", use_container_width=True, type="primary"):
                with st.spinner("⏳ טוען וממיין קבצים..."):
                    try:
                        # טעינת הקבצים
                        contacts_df = load_excel(contacts_file)
                        guests_df = load_excel(guests_file)
                        
                        # בדיקת תקינות
                        if len(contacts_df) == 0:
                            st.error("❌ קובץ אנשי הקשר ריק או לא תקין")
                            return
                        
                        if len(guests_df) == 0:
                            st.error("❌ קובץ המוזמנים ריק או לא תקין")
                            return
                        
                        # חישוב ציונים
                        guests_df["best_score"] = compute_best_scores(guests_df, contacts_df)
                        
                        # שמירת הבחירה ב-session
                        st.session_state[f'choice_{current_idx}'] = choice
                        st.session_state[f'manual_phone_{current_idx}'] = manual_phone
                        st.session_state[f'search_phone_{current_idx}'] = search_phone

def create_radio_options(matches: List[Dict]) -> List[str]:
    """יוצר רשימת אופציות לרדיו"""
    options = ["❌ ללא התאמה"]
    
    for match in matches:
        name = match['name']
        phone = match['phone']
        score = int(match['score'])
        
        option_text = f"{name} | {phone}"
        
        if score >= 95:
            options.append(f"🎯 {option_text} ({score}%)")
        elif score >= 80:
            options.append(f"✅ {option_text} ({score}%)")
        else:
            options.append(f"🤔 {option_text} ({score}%)")
    
    options.extend(["➕ הזנה ידנית", "🔍 חיפוש באנשי קשר"])
    
    return options

def get_auto_select_index(matches: List[Dict], options: List[str]) -> int:
    """מחזיר אינדקס לבחירה אוטומטית"""
    if not matches:
        return 0
    
    best_score = matches[0]['score']
    if best_score >= AUTO_SELECT_TH:
        best_name = matches[0]['name']
        for i, option in enumerate(options):
            if best_name in option and option.startswith("🎯"):
                return i
    
    return 0

def handle_manual_input(current_idx: int) -> str:
    """טיפול בהזנה ידנית"""
    
    st.markdown(f"""
    <div class="form-section" style="border-right: 4px solid {COLORS['accent']};">
        <h4 style="color: {COLORS['primary']}; margin: 0 0 10px 0;">📱 הזנת מספר ידנית</h4>
    """, unsafe_allow_html=True)
    
    manual_phone = st.text_input(
        "מספר טלפון:",
        placeholder="050-1234567",
        key=f"manual_input_{current_idx}",
        label_visibility="collapsed"
    )
    
    if manual_phone:
        # בדיקת תקינות בסיסית
        from config import is_valid_phone, format_phone_display
        
        if is_valid_phone(manual_phone):
            formatted = format_phone_display(manual_phone)
            st.success(f"✅ מספר תקין: {formatted}")
        else:
            st.error("❌ מספר לא תקין - הזן מספר ישראלי תקין")
            manual_phone = ""
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    return manual_phone

def handle_contact_search(contacts_df: pd.DataFrame, current_idx: int) -> str:
    """טיפול בחיפוש באנשי קשר"""
    
    st.markdown(f"""
    <div class="form-section" style="border-right: 4px solid {COLORS['secondary']};">
        <h4 style="color: {COLORS['primary']}; margin: 0 0 10px 0;">🔍 חיפוש באנשי קשר</h4>
    """, unsafe_allow_html=True)
    
    query = st.text_input(
        "חיפוש:",
        placeholder="הקלד שם או מספר טלפון",
        key=f"search_query_{current_idx}",
        label_visibility="collapsed"
    )
    
    selected_phone = ""
    
    if len(query) >= 2:
        # חיפוש באנשי קשר
        search_results = search_contacts(contacts_df, query, limit=8)
        
        if search_results:
            st.markdown("**תוצאות חיפוש:**")
            
            search_options = ["בחר תוצאה..."] + [
                f"{result['name']} | {result['phone']}"
                for result in search_results
            ]
            
            selected_result = st.selectbox(
                "בחר איש קשר:",
                search_options,
                key=f"search_result_{current_idx}",
                label_visibility="collapsed"
            )
            
            if selected_result and selected_result != "בחר תוצאה...":
                selected_phone = selected_result.split("|")[-1].strip()
        else:
            st.info("🔍 לא נמצאו תוצאות מתאימות")
    elif query:
        st.info("💡 הקלד לפחות 2 תווים לחיפוש")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    return selected_phone

def render_navigation_buttons(current_idx: int, total_guests: int, group_id: str):
    """כפתורי ניווט"""
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⬅️ הקודם", disabled=(current_idx == 0), use_container_width=True):
            st.session_state.idx = max(0, current_idx - 1)
            st.rerun()
    
    with col3:
        # בדיקה מה לשמור
        can_save, save_value = validate_current_choice(current_idx)
        
        next_btn_text = "✅ הבא" if current_idx < total_guests - 1 else "🏁 סיום"
        
        if st.button(next_btn_text, disabled=not can_save, use_container_width=True, type="primary"):
            # שמירת הערך
            save_current_choice(current_idx, save_value, group_id, total_guests)
            
            # מעבר הבא
            st.session_state.idx = current_idx + 1
            st.rerun()
    
    with col2:
        # מידע על הבחירה הנוכחית
        choice = st.session_state.get(f'choice_{current_idx}', '')
        if choice and not choice.startswith(("❌", "➕", "🔍")):
            st.info(f"✅ נבחר: {choice.replace('🎯 ', '').replace('✅ ', '').replace('🤔 ', '')}")
        elif choice == "❌ ללא התאמה":
            st.info("⚠️ נבחר: ללא התאמה")

def validate_current_choice(current_idx: int) -> tuple[bool, str]:
    """בדיקת תקינות הבחירה הנוכחית"""
    
    choice = st.session_state.get(f'choice_{current_idx}', '')
    manual_phone = st.session_state.get(f'manual_phone_{current_idx}', '')
    search_phone = st.session_state.get(f'search_phone_{current_idx}', '')
    
    from config import is_valid_phone, normalize_phone, format_phone_display
    
    # הזנה ידנית
    if manual_phone:
        if is_valid_phone(manual_phone):
            return True, format_phone_display(manual_phone)
        else:
            return False, ""
    
    # חיפוש
    elif search_phone:
        return True, search_phone
    
    # ללא התאמה
    elif choice == "❌ ללא התאמה":
        return True, ""
    
    # בחירה מהרשימה
    elif choice and not choice.startswith(("➕", "🔍")):
        phone = extract_phone_from_choice(choice)
        return True, phone
    
    return False, ""

def extract_phone_from_choice(choice: str) -> str:
    """מחלץ מספר טלפון מבחירת רדיו"""
    if choice.startswith("❌"):
        return ""
    elif choice.startswith(("➕", "🔍")):
        return ""
    else:
        # הסר את האמוג'י והציון
        clean_choice = choice.replace("🎯 ", "").replace("✅ ", "").replace("🤔 ", "")
        # חלץ מספר טלפון (החלק אחרי |)
        if "|" in clean_choice:
            phone_part = clean_choice.split("|")[-1].strip()
            # הסר ציון אם קיים
            if "(" in phone_part:
                phone_part = phone_part.split("(")[0].strip()
            return phone_part
        return ""

def save_current_choice(current_idx: int, save_value: str, group_id: str, total_guests: int):
    """שמירת הבחירה הנוכחית"""
    
    try:
        # עדכון ה-DataFrame
        filtered_df = render_filters_section(st.session_state.guests)
        current_guest = filtered_df.iloc[current_idx]
        
        # מציאת השורה הנכונה במקור
        original_guests = st.session_state.guests
        original_index = original_guests[original_guests[NAME_COL] == current_guest[NAME_COL]].index[0]
        
        # שמירת הטלפון
        st.session_state.guests.at[original_index, PHONE_COL] = save_value if save_value else ""
        
        # שמירה בענן (אסינכרונית)
        save_progress_to_cloud(group_id, current_idx + 1, total_guests)
        
    except Exception as e:
        st.error(f"❌ שגיאה בשמירת הבחירה: {str(e)}")

def save_progress_to_cloud(group_id: str, current_index: int, total_guests: int):
    """שמירת התקדמות בענן"""
    try:
        gs = get_google_services()
        
        progress_data = {
            'current_index': current_index,
            'total_guests': total_guests,
            'updated_at': datetime.now().isoformat(),
            'progress_percentage': (current_index / total_guests * 100) if total_guests > 0 else 0
        }
        
        # שמירה כJSON בשדה contacts_progress
        progress_json = json.dumps(progress_data)
        gs.update_couple_field(group_id, 'contacts_progress', progress_json)
        
    except Exception as e:
        st.warning(f"⚠️ שמירה בענן נכשלה: {str(e)}")

def render_completion_section(group_id: str, guests_df: pd.DataFrame):
    """סקציית סיום העבודה"""
    
    # חישוב סטטיסטיקות
    stats = get_matching_statistics(guests_df)
    
    st.markdown(f"""
    <div class="page-header">
        <h1 class="page-title">🎉 כל הכבוד!</h1>
        <h3 class="page-subtitle">סיימתם לחבר את אנשי הקשר למוזמנים</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # סטטיסטיקות סיום
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{stats['total']}</div>
            <div class="metric-label">👥 סך המוזמנים</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {COLORS['success']};">{stats['with_phone']}</div>
            <div class="metric-label">📱 עם מספר טלפון</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {COLORS['warning']};">{stats['without_phone']}</div>
            <div class="metric-label">❌ ללא מספר</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        completion_rate = stats.get('completion_percentage', 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {COLORS['primary']};">{completion_rate:.1f}%</div>
            <div class="metric-label">📊 שיעור השלמה</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # כפתורי פעולה סופיים
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # הורדת קובץ סופי
        if st.button("📥 הורד קובץ Excel סופי", use_container_width=True, type="primary"):
            try:
                # הכנת קובץ Excel
                export_df = export_merged_data(guests_df, format_phones=True)
                excel_buffer = to_buf(export_df)
                
                # שמירה בענן
                gs = get_google_services()
                file_url = gs.save_merged_file(
                    group_id, 
                    excel_buffer.getvalue(),
                    f"final_guests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                )
                
                if file_url:
                    st.success("✅ קובץ נשמר בענן בהצלחה!")
                    st.markdown(f"🔗 [צפה בקובץ בדרייב]({file_url})")
                
                # הורדה ישירה
                st.download_button(
                    label="💾 הורד למחשב",
                    data=excel_buffer.getvalue(),
                    file_name=f"רשימת_מוזמנים_מעודכנת_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"❌ שגיאה ביצירת הקובץ: {str(e)}")
    
    with col2:
        # עבודה מחדש
        if st.button("🔄 עבוד על פרויקט חדש", use_container_width=True):
            # מחיקת כל הנתונים
            keys_to_clear = [k for k in st.session_state.keys() 
                           if k not in ['auth_token', 'user_group_id', 'user_phone']]
            for key in keys_to_clear:
                del st.session_state[key]
            
            # מחיקת התקדמות בענן
            gs = get_google_services()
            gs.update_couple_field(group_id, 'contacts_progress', '')
            
            st.success("🔄 מערכת אופסה - מתחיל פרויקט חדש!")
            st.rerun()
    
    with col3:
        # חזרה לדשבורד
        if st.button("🏠 חזור לדשבורד", use_container_width=True):
            # מחיקת נתוני העבודה (לא האימות)
            keys_to_clear = [k for k in st.session_state.keys() 
                           if k not in ['auth_token', 'user_group_id', 'user_phone'] 
                           and not k.startswith('auth')]
            for key in keys_to_clear:
                del st.session_state[key]
            
            st.info("🔄 מפנה לדשבורד...")
            
            # ניתוב חזרה לדשבורד
            from config import get_dashboard_url
            dashboard_url = get_dashboard_url(group_id, st.session_state.auth_token)
            st.markdown(f"👆 [לחץ כאן לחזרה לדשבורד]({dashboard_url})")
    
    # תצוגת נתונים מפורטת
    st.markdown("---")
    st.markdown("### 📊 סיכום מפורט")
    
    # טבלת סטטיסטיקות
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📈 התפלגות התאמות")
        
        if "best_score" in guests_df.columns:
            perfect = len(guests_df[guests_df["best_score"] >= 95])
            good = len(guests_df[(guests_df["best_score"] >= 70) & (guests_df["best_score"] < 95)])
            medium = len(guests_df[(guests_df["best_score"] >= 50) & (guests_df["best_score"] < 70)])
            poor = len(guests_df[guests_df["best_score"] < 50])
            
            st.write(f"🎯 **התאמות מושלמות (95%+):** {perfect}")
            st.write(f"✅ **התאמות טובות (70-94%):** {good}")
            st.write(f"🤔 **התאמות בינוניות (50-69%):** {medium}")
            st.write(f"❌ **התאמות חלשות (<50%):** {poor}")
    
    with col2:
        st.markdown("#### 📱 פילוח טלפונים")
        
        with_phone = stats['with_phone']
        without_phone = stats['without_phone']
        total = stats['total']
        
        if total > 0:
            st.write(f"📞 **יש מספר:** {with_phone} ({with_phone/total*100:.1f}%)")
            st.write(f"❌ **אין מספר:** {without_phone} ({without_phone/total*100:.1f}%)")
            
            # פילוח לפי צד/קבוצה אם זמין
            if SIDE_COL in guests_df.columns:
                sides_with_phone = guests_df[guests_df[PHONE_COL].str.strip() != ""].groupby(SIDE_COL).size()
                if len(sides_with_phone) > 0:
                    st.write("**פילוח לפי צד:**")
                    for side, count in sides_with_phone.items():
                        st.write(f"  • {side}: {count}")


if __name__ == "__main__":
    main()ת הקבצים בענן
                        save_success = save_files_to_cloud(group_id, contacts_file, guests_file, guests_df)
                        
                        # שמירה ב-session state
                        st.session_state.contacts = contacts_df
                        st.session_state.guests = guests_df
                        st.session_state.upload_confirmed = True
                        st.session_state.idx = 0
                        
                        # הצגת סטטיסטיקות ראשוניות
                        stats = get_matching_statistics(guests_df)
                        
                        st.success("🎉 קבצים נטענו בהצלחה!")
                        
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        with col_stat1:
                            st.metric("👥 סך מוזמנים", stats['total'])
                        with col_stat2:
                            st.metric("📱 כבר עם מספר", stats['with_phone'])
                        with col_stat3:
                            st.metric("🎯 התאמות מושלמות", stats.get('perfect_matches', 0))
                        
                        if not save_success:
                            st.warning("⚠️ שמירה בענן נכשלה, אך העבודה תמשיך מקומית")
                        
                        time.sleep(2)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ שגיאה בטעינת הקבצים: {str(e)}")
                        st.exception(e)

def show_joni_guide():
    """מדריך מפורט לתוסף ג'וני"""
    
    st.markdown("""
    <div class="alert alert-info">
        <h3>📱 מדריך הורדת אנשי קשר מWhatsApp</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📋 שלבי ההורדה:")
        
        steps = [
            "פתחו דפדפן **Chrome** במחשב (לא בטלפון!)",
            "התקינו את התוסף **[ג'וני מחנות Chrome](https://chromewebstore.google.com/detail/joni/aakppiadmnaeffmjijolmgmkcfhpglbh)**",
            "היכנסו ל-**WhatsApp Web** והתחברו",
            "לחצו על סמל **J** בסרגל הכלים של הדפדפן",
            "בחרו **אנשי קשר** ← **שמירה לקובץ Excel**",
            "הקובץ יורד אוטומטית למחשב שלכם"
        ]
        
        for i, step in enumerate(steps, 1):
            st.markdown(f"**{i}.** {step}")
        
        st.info("💡 **חשוב:** התוסף עובד רק בדפדפן Chrome במחשב!")
    
    with col2:
        st.markdown(f"""
        <div style="
            background: {COLORS['background']};
            border: 2px dashed {COLORS['primary']};
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            color: {COLORS['primary']};
        ">
            <div style="font-size: 48px; margin-bottom: 15px;">🖼️</div>
            <strong>תמונת המדריך</strong><br>
            <small>התוסף ג'וני מופיע כסמל <strong>J</strong><br>
            בסרגל הכלים של Chrome</small>
        </div>
        """, unsafe_allow_html=True)

def load_existing_progress(group_id: str, progress: Dict):
    """טעינת התקדמות קיימת"""
    try:
        st.info("🔄 מימוש טעינת התקדמות קיימת - בפיתוח")
        
        # TODO: מימוש מלא - טעינת קבצים קיימים מהענן
        current_index = progress.get('current_index', 0)
        total_guests = progress.get('total_guests', 0)
        
        st.info(f"📊 התקדמות: {current_index}/{total_guests}")
        
        # לעת עתה - נחזור לשלב העלאה
        st.session_state.upload_confirmed = False
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ שגיאה בטעינת התקדמות: {str(e)}")

def save_files_to_cloud(group_id: str, contacts_file, guests_file, guests_df: pd.DataFrame) -> bool:
    """שמירת קבצים בענן של Google"""
    try:
        gs = get_google_services()
        
        # המרת קבצים ל-bytes
        contacts_file.seek(0)
        contacts_bytes = contacts_file.read()
        
        guests_file.seek(0)
        guests_bytes = guests_file.read()
        
        # שמירה עם התקדמות ריקה כרגע
        progress_data = {
            'started_at': datetime.now().isoformat(),
            'contacts_filename': contacts_file.name,
            'guests_filename': guests_file.name,
            'current_index': 0,
            'total_guests': len(guests_df),
            'completion_percentage': 0
        }
        
        success = gs.save_contacts_files(group_id, contacts_bytes, guests_bytes, progress_data)
        
        return success
        
    except Exception as e:
        st.warning(f"⚠️ שמירה בענן נכשלה: {str(e)}")
        return False

def render_contacts_merge_section(group_id: str):
    """סקציית חיבור אנשי הקשר"""
    
    # בדיקת נתונים ב-session
    if 'contacts' not in st.session_state or 'guests' not in st.session_state:
        st.error("❌ נתונים לא נמצאו. אנא העלו את הקבצים מחדש.")
        st.session_state.upload_confirmed = False
        st.rerun()
        return
    
    # קבלת הנתונים
    contacts_df = st.session_state.contacts
    guests_df = st.session_state.guests
    
    # פילטרים (בסיסיים)
    filtered_df = render_filters_section(guests_df)
    
    # התקדמות
    current_idx = st.session_state.get('idx', 0)
    total_guests = len(filtered_df)
    
    if current_idx >= total_guests:
        # סיימנו!
        render_completion_section(group_id, guests_df)
        return
    
    # המוזמן הנוכחי
    if total_guests > 0:
        current_guest = filtered_df.iloc[current_idx]
        
        # מציג התקדמות
        render_progress_bar(current_idx, total_guests)
        
        # מציג פרופיל המוזמן
        render_guest_profile(current_guest)
        
        # מציג אפשרויות חיבור
        render_matching_section(current_guest, contacts_df, current_idx, group_id, total_guests)
        
        # כפתורי ניווט
        render_navigation_buttons(current_idx, total_guests, group_id)
    else:
        st.info("📝 לא נמצאו מוזמנים מתאימים לפילטרים הנבחרים")

def render_filters_section(guests_df: pd.DataFrame) -> pd.DataFrame:
    """סקציית פילטרים פשוטה"""
    
    with st.expander("🔧 פילטרים", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            filter_no_phone = st.checkbox(
                "רק חסרי מספר",
                key="filter_no_phone",
                help="הצג רק מוזמנים ללא מספר טלפון"
            )
        
        with col2:
            # פילטר צד
            all_sides = guests_df[SIDE_COL].dropna().unique().tolist()
            if all_sides:
                selected_sides = st.multiselect(
                    "צד:",
                    options=all_sides,
                    key="filter_sides"
                )
            else:
                selected_sides = []
        
        with col3:
            # פילטר קבוצה
            all_groups = guests_df[GROUP_COL].dropna().unique().tolist()
            if all_groups:
                selected_groups = st.multiselect(
                    "קבוצה:",
                    options=all_groups,
                    key="filter_groups"
                )
            else:
                selected_groups = []
        
        with col4:
            # פילטר ציון התאמה
            min_score = st.slider(
                "ציון התאמה מינימלי:",
                min_value=0,
                max_value=100,
                value=0,
                key="filter_min_score"
            )
    
    # החלת פילטרים
    filtered_df = guests_df.copy()
    
    # פילטר חסרי מספר
    if filter_no_phone:
        filtered_df = filtered_df[filtered_df[PHONE_COL].str.strip() == ""]
    
    # פילטר צד
    if selected_sides:
        filtered_df = filtered_df[filtered_df[SIDE_COL].isin(selected_sides)]
    
    # פילטר קבוצה
    if selected_groups:
        filtered_df = filtered_df[filtered_df[GROUP_COL].isin(selected_groups)]
    
    # פילטר ציון
    if "best_score" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["best_score"] >= min_score]
    
    # מיון לפי ציון (הכי טובים ראשון)
    if "best_score" in filtered_df.columns:
        filtered_df = filtered_df.sort_values(["best_score", NAME_COL], ascending=[False, True])
    
    return filtered_df.reset_index(drop=True)

def render_progress_bar(current_idx: int, total_guests: int):
    """מציג בר התקדמות מעוצב"""
    
    progress = (current_idx / total_guests) if total_guests > 0 else 0
    
    st.markdown(f"""
    <div class="progress-container">
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <span style="font-weight: 600; color: {COLORS['primary']};">
                התקדמות: {current_idx + 1}/{total_guests} מוזמנים
            </span>
            <span style="color: {COLORS['text_medium']};">
                {progress*100:.1f}%
            </span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {progress*100}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_guest_profile(guest):
    """מציג פרופיל מוזמן מעוצב"""
    
    st.markdown(f"""
    <div class="form-section" style="border-right: 5px solid {COLORS['accent']};">
        <h2 style="color: {COLORS['primary']}; margin: 0 0 15px 0;">
            🎯 {guest[NAME_COL]}
        </h2>
        <div style="
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        ">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.2rem;">🧭</span>
                <div>
                    <strong>צד:</strong><br>
                    <span style="color: {COLORS['text_medium']};">{guest.get(SIDE_COL, 'לא מוגדר')}</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.2rem;">👥</span>
                <div>
                    <strong>קבוצה:</strong><br>
                    <span style="color: {COLORS['text_medium']};">{guest.get(GROUP_COL, 'לא מוגדר')}</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.2rem;">🔢</span>
                <div>
                    <strong>כמות:</strong><br>
                    <span style="color: {COLORS['text_medium']};">{guest.get(COUNT_COL, 1)}</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.2rem;">📱</span>
                <div>
                    <strong>מספר נוכחי:</strong><br>
                    <span style="color: {COLORS['text_medium']};">{guest.get(PHONE_COL, 'אין') or 'אין'}</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_matching_section(guest, contacts_df: pd.DataFrame, current_idx: int, group_id: str, total_guests: int):
    """מציג אפשרויות התאמה למוזמן"""
    
    # קבלת התאמות
    guest_name = guest.get(NAME_COL, '')
    matches = get_top_matches(guest_name, contacts_df, limit=5)
    
    # יצירת אופציות
    options = create_radio_options(matches)
    
    # בחירה אוטומטית חכמה
    auto_index = get_auto_select_index(matches, options)
    
    # מציג את האופציות
    st.markdown("### 📱 בחר איש קשר מתאים:")
    
    choice = st.radio(
        "בחירות:",
        options,
        index=auto_index,
        key=f"radio_choice_{current_idx}",
        label_visibility="collapsed"
    )
    
    # טיפול בבחירות מיוחדות
    manual_phone = ""
    search_phone = ""
    
    if choice.startswith("➕"):
        manual_phone = handle_manual_input(current_idx)
    elif choice.startswith("🔍"):
        search_phone = handle_contact_search(contacts_df, current_idx)
    
    # שמיר