import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from io import BytesIO

from config import get_main_css, COLORS
from auth_system import get_auth_manager
from google_services import get_google_services

# הכללת הלוגיקה מהמערכת הקיימת
from src.logic import (
    NAME_COL, PHONE_COL, COUNT_COL, SIDE_COL, GROUP_COL,
    AUTO_SELECT_TH, load_excel, to_buf,
    format_phone, normalize, compute_best_scores, full_score,
)

def main():
    """מערכת חיבור אנשי קשר מאוחדת"""
    
    # הגדרות דף
    st.set_page_config(
        page_title="חיבור אנשי קשר",
        page_icon="📱",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # טעינת CSS מאוחד
    st.markdown(get_main_css(), unsafe_allow_html=True)
    
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
    
    # בדיקה אם יש טוכן ב-URL
    token_from_url = st.query_params.get('token')
    
    if token_from_url and token_from_url != st.session_state.get('auth_token'):
        auth_manager = get_auth_manager()
        result = auth_manager.validate_token(token_from_url)
        
        if result.get('valid'):
            # ווידוא שזה טוכן של contacts_merge
            if result.get('type') == 'contacts_merge':
                st.session_state.auth_token = token_from_url
                st.session_state.user_group_id = result.get('group_id')
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
    <div style="
        background: linear-gradient(135deg, {COLORS['secondary']} 0%, {COLORS['accent']} 100%);
        color: {COLORS['primary']};
        padding: 25px;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    ">
        <h1 style="margin: 0 0 10px 0; font-size: 2.2rem;">📱 חיבור אנשי קשר למוזמנים</h1>
        <p style="margin: 0; opacity: 0.8; font-size: 1.1rem;">
            מיזוג חכם ומהיר של רשימת המוזמנים עם אנשי הקשר שלכם
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_file_upload_section(group_id: str, progress: Dict):
    """סקציית העלאת קבצים משופרת"""
    
    # בדיקה אם יש התקדמות קודמת
    if progress:
        st.markdown(f"""
        <div class="alert alert-warning">
            <h4>📂 נמצאה עבודה קודמת</h4>
            <p>נמצא פרויקט חיבור קיים. רוצים להמשיך מהמקום שעצרתם או להתחיל מחדש?</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ המשך מהמקום שעצרתי", use_container_width=True, type="primary"):
                # TODO: טעינת הקבצים הקיימים והמשך מהמקום הנכון
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
    with st.expander("📖 מדריך מהיר", expanded=False):
        col1, col2 = st.columns([2, 1])
        
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
            if st.button("📘 מדריך הורדת אנשי קשר", use_container_width=True):
                show_joni_guide()
    
    # העלאת קבצים
    st.markdown("### 📂 העלאת קבצים")
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div style="
                background: {COLORS['background']};
                padding: 20px;
                border-radius: 12px;
                border: 2px dashed {COLORS['secondary']};
                text-align: center;
                margin-bottom: 10px;
            ">
                <h4 style="color: {COLORS['primary']};">👥 קובץ אנשי קשר</h4>
                <p style="color: {COLORS['text_medium']}; font-size: 0.9rem;">
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
            <div style="
                background: {COLORS['background']};
                padding: 20px;
                border-radius: 12px;
                border: 2px dashed {COLORS['accent']};
                text-align: center;
                margin-bottom: 10px;
            ">
                <h4 style="color: {COLORS['primary']};">🎉 רשימת מוזמנים</h4>
                <p style="color: {COLORS['text_medium']}; font-size: 0.9rem;">
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
                        
                        # חישוב ציונים
                        guests_df["best_score"] = compute_best_scores(guests_df, contacts_df)
                        
                        # שמירת הקבצים בענן
                        save_files_to_cloud(group_id, contacts_file, guests_file)
                        
                        # שמירה ב-session state
                        st.session_state.contacts = contacts_df
                        st.session_state.guests = guests_df
                        st.session_state.upload_confirmed = True
                        st.session_state.idx = 0
                        
                        st.success("🎉 קבצים נטענו בהצלחה!")
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ שגיאה בטעינת הקבצים: {str(e)}")

def show_joni_guide():
    """מדריך מפורט לתוסף ג'וני"""
    
    st.markdown("""
    <div class="guide-modal">
        <h3>📱 מדריך הורדת אנשי קשר מWhatsApp</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📋 שלבי ההורדה:")
        
        steps = [
            "פתחו דפדפן **Chrome** במחשב (לא בטלפון!)",
            "התקינו את התוסף **[ג'וני](https://chromewebstore.google.com/detail/joni/aakppiadmnaeffmjijolmgmkcfhpglbh)**",
            "היכנסו ל-**WhatsApp Web** ונמצו בהתחברות",
            "לחצו על סמל **J** בסרגל הכלים של הדפדפן",
            "בחרו **אנשי קשר** ← **שמירה לקובץ Excel**",
            "הקובץ יורד אוטומטי למחשב שלכם"
        ]
        
        for i, step in enumerate(steps, 1):
            st.markdown(f"**{i}.** {step}")
        
        st.info("💡 **חשוב:** התוסף עובד רק בדפדפן Chrome במחשב!")
    
    with col2:
        # ניסיון להציג תמונה או placeholder
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
        # TODO: מימוש טעינת קבצים קיימים מהענן
        st.info("🔄 מימוש טעינת התקדמות קיימת - בפיתוח")
        
        # לעת עתה - נחזור לשלב העלאה
        st.session_state.upload_confirmed = False
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ שגיאה בטעינת התקדמות: {str(e)}")

def save_files_to_cloud(group_id: str, contacts_file, guests_file):
    """שמירת קבצים בענן של Google"""
    try:
        gs = get_google_services()
        
        # המרת קבצים ל-bytes
        contacts_bytes = contacts_file.read()
        contacts_file.seek(0)  # חזרה לתחילת הקובץ
        
        guests_bytes = guests_file.read()
        guests_file.seek(0)
        
        # שמירה עם התקדמות ריקה כרגע
        progress_data = {
            'started_at': datetime.now().isoformat(),
            'contacts_filename': contacts_file.name,
            'guests_filename': guests_file.name,
            'current_index': 0,
            'total_guests': 0
        }
        
        success = gs.save_contacts_files(group_id, contacts_bytes, guests_bytes, progress_data)
        
        if not success:
            st.warning("⚠️ שמירה בענן נכשלה, אך העבודה תמשיך מקומית")
        
    except Exception as e:
        st.warning(f"⚠️ שמירה בענן נכשלה: {str(e)}")

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
    render_filters_section(guests_df)
    
    # פילטרים פעילים
    filtered_df = apply_filters(guests_df)
    
    # התקדמות
    current_idx = st.session_state.get('idx', 0)
    total_guests = len(filtered_df)
    
    if current_idx >= total_guests:
        # סיימנו!
        render_completion_section(group_id, guests_df)
        return
    
    # המוזמן הנוכחי
    current_guest = filtered_df.iloc[current_idx]
    
    # מציג התקדמות
    render_progress_bar(current_idx, total_guests)
    
    # מציג פרופיל המוזמן
    render_guest_profile(current_guest)
    
    # מציג אפשרויות חיבור
    render_matching_section(current_guest, contacts_df, current_idx)
    
    # כפתורי ניווט
    render_navigation_buttons(current_idx, total_guests)

def render_filters_section(guests_df: pd.DataFrame):
    """סקציית פילטרים פשוטה"""
    
    with st.expander("🔧 פילטרים", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.checkbox(
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
        
        with col3:
            # פילטר קבוצה
            all_groups = guests_df[GROUP_COL].dropna().unique().tolist()
            if all_groups:
                selected_groups = st.multiselect(
                    "קבוצה:",
                    options=all_groups,
                    key="filter_groups"
                )

def apply_filters(guests_df: pd.DataFrame) -> pd.DataFrame:
    """החלת פילטרים"""
    
    filtered_df = guests_df.copy()
    
    # פילטר חסרי מספר
    if st.session_state.get("filter_no_phone", False):
        filtered_df = filtered_df[filtered_df[PHONE_COL].str.strip() == ""]
    
    # פילטר צד
    if st.session_state.get("filter_sides"):
        filtered_df = filtered_df[filtered_df[SIDE_COL].isin(st.session_state.filter_sides)]
    
    # פילטר קבוצה
    if st.session_state.get("filter_groups"):
        filtered_df = filtered_df[filtered_df[GROUP_COL].isin(st.session_state.filter_groups)]
    
    # מיון לפי ציון (הכי טובים ראשון)
    filtered_df = filtered_df.sort_values(["best_score", NAME_COL], ascending=[False, True])
    
    return filtered_df.reset_index(drop=True)

def render_progress_bar(current_idx: int, total_guests: int):
    """מציג בר התקדמות מעוצב"""
    
    progress = (current_idx / total_guests) if total_guests > 0 else 0
    
    st.markdown(f"""
    <div style="
        background: {COLORS['white']};
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <span style="font-weight: 600; color: {COLORS['primary']};">
                התקדמות: {current_idx}/{total_guests} מוזמנים
            </span>
            <span style="color: {COLORS['text_medium']};">
                {progress*100:.1f}%
            </span>
        </div>
        <div style="
            background: {COLORS['border']};
            height: 10px;
            border-radius: 5px;
            overflow: hidden;
        ">
            <div style="
                background: linear-gradient(90deg, {COLORS['secondary']}, {COLORS['accent']});
                height: 100%;
                width: {progress*100}%;
                border-radius: 5px;
                transition: width 0.3s ease;
            "></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_guest_profile(guest):
    """מציג פרופיל מוזמן מעוצב"""
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {COLORS['white']} 0%, {COLORS['background']} 100%);
        padding: 25px;
        border-radius: 15px;
        border-right: 5px solid {COLORS['accent']};
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    ">
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
                    <span style="color: {COLORS['text_medium']};">{guest[SIDE_COL]}</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.2rem;">🧩</span>
                <div>
                    <strong>קבוצה:</strong><br>
                    <span style="color: {COLORS['text_medium']};">{guest[GROUP_COL]}</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.2rem;">👥</span>
                <div>
                    <strong>כמות:</strong><br>
                    <span style="color: {COLORS['text_medium']};">{guest[COUNT_COL]}</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_matching_section(guest, contacts_df: pd.DataFrame, current_idx: int):
    """מציג אפשרויות התאמה למוזמן"""
    
    # חישוב התאמות
    matches = contacts_df.copy()
    matches["score"] = matches["norm_name"].map(lambda c: full_score(guest.norm_name, c))
    
    # סינון והכנת מועמדים
    best_score = matches["score"].max() if not matches.empty else 0
    
    if best_score >= 100:
        candidates = matches[matches["score"] >= 90].sort_values(["score", NAME_COL], ascending=[False, True]).head(3)
    else:
        candidates = matches[matches["score"] >= 70].sort_values(["score", NAME_COL], ascending=[False, True]).head(5)
    
    # יצירת אופציות
    options = create_radio_options(candidates)
    
    # בחירה אוטומטית חכמה
    auto_index = get_auto_select_index(candidates, options)
    
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
    
    # שמירת הבחירה ב-session
    st.session_state[f'choice_{current_idx}'] = choice
    st.session_state[f'manual_phone_{current_idx}'] = manual_phone
    st.session_state[f'search_phone_{current_idx}'] = search_phone

def create_radio_options(candidates: pd.DataFrame) -> List[str]:
    """יוצר רשימת אופציות לרדיו"""
    options = ["❌ ללא התאמה"]
    
    for _, candidate in candidates.iterrows():
        name = candidate[NAME_COL]
        phone = format_phone(candidate[PHONE_COL])
        score = int(candidate["score"])
        
        option_text = f"{name} | {phone}"
        
        if score == 100:
            options.append(f"🎯 {option_text}")
        else:
            options.append(option_text)
    
    options.extend(["➕ הזנה ידנית", "🔍 חיפוש באנשי קשר"])
    
    return options

def get_auto_select_index(candidates: pd.DataFrame, options: List[str]) -> int:
    """מחזיר אינדקס לבחירה אוטומטית"""
    if candidates.empty:
        return 0
    
    best_score = candidates.iloc[0]["score"]
    if best_score >= AUTO_SELECT_TH:
        best_name = candidates.iloc[0][NAME_COL]
        for i, option in enumerate(options):
            if best_name in option and not option.startswith(("❌", "➕", "🔍")):
                return i
    
    return 0

def handle_manual_input(current_idx: int) -> str:
    """טיפול בהזנה ידנית"""
    
    st.markdown(f"""
    <div style="
        background: {COLORS['background']};
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
        border-right: 4px solid {COLORS['accent']};
    ">
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
        clean_phone = ''.join(filter(str.isdigit, manual_phone))
        if len(clean_phone) == 10 and clean_phone.startswith('05'):
            st.success("✅ מספר תקין")
        else:
            st.error("❌ מספר לא תקין")
            manual_phone = ""
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    return manual_phone

def handle_contact_search(contacts_df: pd.DataFrame, current_idx: int) -> str:
    """טיפול בחיפוש באנשי קשר"""
    
    st.markdown(f"""
    <div style="
        background: {COLORS['background']};
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
        border-right: 4px solid {COLORS['secondary']};
    ">
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
        search_results = contacts_df[
            contacts_df.norm_name.str.contains(normalize(query), na=False, case=False) |
            contacts_df[PHONE_COL].str.contains(query, na=False)
        ].head(6)
        
        if not search_results.empty:
            st.markdown("**תוצאות חיפוש:**")
            
            search_options = ["בחר תוצאה..."] + [
                f"{row[NAME_COL]} | {format_phone(row[PHONE_COL])}"
                for _, row in search_results.iterrows()
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

def render_navigation_buttons(current_idx: int, total_guests: int):
    """כפתורי ניווט"""
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⬅️ הקודם", disabled=(current_idx == 0), use_container_width=True):
            st.session_state.idx = max(0, current_idx - 1)
            st.rerun()
    
    with col3:
        # בדיקה מה לשמור
        can_save = False
        save_value = None
        
        choice = st.session_state.get(f'choice_{current_idx}', '')
        manual_phone = st.session_state.get(f'manual_phone_{current_idx}', '')
        search_phone = st.session_state.get(f'search_phone_{current_idx}', '')
        
        if manual_phone:
            clean_phone = ''.join(filter(str.isdigit, manual_phone))
            if len(clean_phone) == 10 and clean_phone.startswith('05'):
                save_value = format_phone(manual_phone)
                can_save = True
        elif search_phone:
            save_value = search_phone
            can_save = True
        elif choice.startswith("❌"):
            save_value = ""
            can_save = True
        elif choice and not choice.startswith(("➕", "🔍")):
            save_value = extract_phone_from_choice(choice)
            can_save = True
        
        next_btn_text = "✅ הבא" if current_idx < total_guests - 1 else "🏁 סיום"
        
        if st.button(next_btn_text, disabled=not can_save, use_container_width=True, type="primary"):
            # שמירת הערך
            guests_df = st.session_state.guests
            
            # מציאת השורה הנכונה במקור
            current_guest = apply_filters(guests_df).iloc[current_idx]
            original_index = guests_df[guests_df[NAME_COL] == current_guest[NAME_COL]].index[0]
            
            # שמירת הטלפון
            st.session_state.guests.at[original_index, PHONE_COL] = save_value if save_value else ""
            
            # שמירה בענן (אסינכרונית)
            save_progress_to_cloud(st.session_state.user_group_id, current_idx + 1, total_guests)
            
            # מעבר הבא
            st.session_state.idx = current_idx + 1
            st.rerun()
    
    with col2:
        # מידע על הבחירה הנוכחית
        choice = st.session_state.get(f'choice_{current_idx}', '')
        if choice and not choice.startswith(("❌", "➕", "🔍")):
            st.info(f"✅ נבחר: {choice}")

def extract_phone_from_choice(choice: str) -> str:
    """מחלץ מספר טלפון מבחירת רדיו"""
    if choice.startswith("❌"):
        return ""
    elif choice.startswith(("➕", "🔍")):
        return ""
    else:
        # הסר את האמוג'י
        clean_choice = choice.replace("🎯 ", "")
        # חלץ מספר טלפון (החלק אחרי |)
        if "|" in clean_choice:
            return clean_choice.split("|")[-1].strip()
        return ""

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
    total_guests = len(guests_df)
    with_phone = len(guests_df[guests_df[PHONE_COL].str.strip() != ""])
    without_phone = total_guests - with_phone
    completion_rate = (with_phone / total_guests * 100) if total_guests > 0 else 0
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {COLORS['success']} 0%, {COLORS['secondary']} 100%);
        color: white;
        padding: 40px;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
    ">
        <h1 style="margin: 0 0 20px 0; font-size: 2.5rem;">🎉 כל הכבוד!</h1>
        <h2 style="margin: 0; font-weight: normal; opacity: 0.9;">סיימתם לחבר את אנשי הקשר</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # סטטיסטיקות סיום
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_guests}</div>
            <div class="metric-label">👥 סך המוזמנים</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {COLORS['success']};">{with_phone}</div>
            <div class="metric-label">📱 עם מספר טלפון</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {COLORS['warning']};">{without_phone}</div>
            <div class="metric-label">❌ ללא מספר</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
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
                excel_buffer = to_buf(guests_df)
                
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
            keys_to_clear = [k for k in st.session_state.keys() if k not in ['auth_token', 'user_group_id', 'user_phone']]
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
            keys_to_clear = [k for k in st.session_state.keys() if k not in ['auth_token', 'user_group_id', 'user_phone']]
            for key in keys_to_clear:
                if not key.startswith('auth'):
                    del st.session_state[key]
            
            st.info("🔄 מפנה לדשבורד...")
            st.markdown("👆 [לחץ כאן לחזרה לדשבורד](../dashboard)")


if __name__ == "__main__":
    main()