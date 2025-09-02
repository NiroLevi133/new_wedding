import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from io import BytesIO
import hashlib

# Google services
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import gspread

from config import (
    GOOGLE_CREDENTIALS_JSON, 
    GSHEETS_SPREADSHEET_ID,
    COUPLES_HEADERS,
    EXPENSES_HEADERS,
    COLORS
)

logger = logging.getLogger(__name__)

class GoogleServicesManager:
    """מנהל את כל הפעילויות עם Google Sheets ו-Drive"""
    
    def __init__(self):
        self.credentials = None
        self.sheets_service = None
        self.drive_service = None
        self.gspread_client = None
        self.spreadsheet = None
        
        self._init_services()
    
    def _init_services(self):
        """אתחול שירותי Google"""
        try:
            if not GOOGLE_CREDENTIALS_JSON:
                raise ValueError("Google credentials not found")
            
            # Parse credentials
            creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
            
            # יצירת credentials
            SCOPES = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            self.credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=SCOPES
            )
            
            # אתחול שירותים
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.gspread_client = gspread.authorize(self.credentials)
            
            # פתיחת הגיליון הראשי
            self.spreadsheet = self.gspread_client.open_by_key(GSHEETS_SPREADSHEET_ID)
            
            # וידוא שקיימים הגיליונות הנחוצים
            self._ensure_worksheets_exist()
            
            logger.info("✅ Google services initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google services: {e}")
            raise
    
    def _ensure_worksheets_exist(self):
        """וידוא שקיימים כל הגיליונות הנחוצים"""
        try:
            worksheets = {ws.title for ws in self.spreadsheet.worksheets()}
            
            # גיליון זוגות
            if 'couples' not in worksheets:
                couples_sheet = self.spreadsheet.add_worksheet(
                    title='couples', 
                    rows=1000, 
                    cols=len(COUPLES_HEADERS)
                )
                couples_sheet.append_row(COUPLES_HEADERS)
                logger.info("Created 'couples' worksheet")
            
            # גיליון הוצאות
            if 'expenses' not in worksheets:
                expenses_sheet = self.spreadsheet.add_worksheet(
                    title='expenses', 
                    rows=5000, 
                    cols=len(EXPENSES_HEADERS)
                )
                expenses_sheet.append_row(EXPENSES_HEADERS)
                logger.info("Created 'expenses' worksheet")
            
        except Exception as e:
            logger.error(f"Failed to ensure worksheets exist: {e}")
            raise
    
    def _get_timestamp(self) -> str:
        """מחזיר timestamp נוכחי"""
        return datetime.now(timezone.utc).isoformat()
    
    def _generate_id(self, prefix: str = "") -> str:
        """יצירת ID ייחודי"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_part = hashlib.md5(os.urandom(16)).hexdigest()[:8]
        return f"{prefix}{timestamp}_{random_part}"
    
    # ===== ניהול זוגות =====
    
    def create_couple(self, phone1: str, phone2: str, group_id: str, 
                     couple_name: str = "", wedding_date: str = "", 
                     budget: float = 0) -> Dict:
        """יצירת זוג חדש במערכת"""
        try:
            couples_sheet = self.spreadsheet.worksheet('couples')
            
            # בדיקה שהקבוצה לא קיימת כבר
            existing = self._find_couple_by_group_id(group_id)
            if existing:
                return {"success": False, "error": "Group already exists"}
            
            # יצירת רשומה חדשה
            couple_data = [
                group_id,                    # group_id
                phone1,                      # phone1
                phone2,                      # phone2
                couple_name or f"זוג {group_id[:8]}",  # couple_name
                wedding_date,                # wedding_date
                str(budget) if budget > 0 else "",  # budget
                self._get_timestamp(),       # created_at
                "active",                    # status
                "",                          # contacts_progress
                self._get_timestamp()        # last_activity
            ]
            
            couples_sheet.append_row(couple_data)
            
            # יצירת תיקיה ב-Drive
            self._create_couple_folder(group_id)
            
            logger.info(f"Created couple: {group_id}")
            
            return {
                "success": True,
                "group_id": group_id,
                "couple_name": couple_data[3]
            }
            
        except Exception as e:
            logger.error(f"Failed to create couple: {e}")
            return {"success": False, "error": str(e)}
    
    def get_couple_by_group_id(self, group_id: str) -> Optional[Dict]:
        """קבלת נתוני זוג לפי group_id"""
        return self._find_couple_by_group_id(group_id)
    
    def _find_couple_by_group_id(self, group_id: str) -> Optional[Dict]:
        """חיפוש זוג לפי group_id"""
        try:
            couples_sheet = self.spreadsheet.worksheet('couples')
            records = couples_sheet.get_all_records()
            
            for record in records:
                if record.get('group_id') == group_id:
                    return record
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find couple: {e}")
            return None
    
    def get_all_active_couples(self) -> List[Dict]:
        """קבלת כל הזוגות הפעילים"""
        try:
            couples_sheet = self.spreadsheet.worksheet('couples')
            records = couples_sheet.get_all_records()
            
            active_couples = [
                record for record in records 
                if record.get('status') == 'active'
            ]
            
            return active_couples
            
        except Exception as e:
            logger.error(f"Failed to get active couples: {e}")
            return []
    
    def update_couple_field(self, group_id: str, field: str, value: Any) -> bool:
        """עדכון שדה בודד של זוג"""
        try:
            couples_sheet = self.spreadsheet.worksheet('couples')
            
            # מציאת השורה
            cell = couples_sheet.find(group_id)
            if not cell:
                return False
            
            row_num = cell.row
            
            # מציאת העמודה
            if field not in COUPLES_HEADERS:
                return False
            
            col_num = COUPLES_HEADERS.index(field) + 1
            
            # עדכון הערך
            couples_sheet.update_cell(row_num, col_num, str(value))
            
            # עדכון last_activity
            last_activity_col = COUPLES_HEADERS.index('last_activity') + 1
            couples_sheet.update_cell(row_num, last_activity_col, self._get_timestamp())
            
            logger.info(f"Updated couple {group_id}: {field} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update couple field: {e}")
            return False
    
    # ===== ניהול הוצאות =====
    
    def save_expense(self, expense_data: Dict) -> bool:
        """שמירת הוצאה חדשה"""
        try:
            expenses_sheet = self.spreadsheet.worksheet('expenses')
            
            # יצירת ID ייחודי אם לא קיים
            if not expense_data.get('expense_id'):
                expense_data['expense_id'] = self._generate_id('EXP_')
            
            # מילוי ערכי ברירת מחדל
            current_time = self._get_timestamp()
            expense_data.setdefault('created_at', current_time)
            expense_data.setdefault('updated_at', current_time)
            expense_data.setdefault('status', 'active')
            expense_data.setdefault('needs_review', False)
            expense_data.setdefault('confidence', 85)
            
            # יצירת שורה לפי הסדר של EXPENSES_HEADERS
            row_data = []
            for header in EXPENSES_HEADERS:
                value = expense_data.get(header, '')
                row_data.append(str(value) if value is not None else '')
            
            expenses_sheet.append_row(row_data)
            
            # עדכון last_activity של הזוג
            group_id = expense_data.get('group_id')
            if group_id:
                self.update_couple_field(group_id, 'last_activity', current_time)
            
            logger.info(f"Saved expense: {expense_data.get('expense_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save expense: {e}")
            return False
    
    def get_expenses_by_group(self, group_id: str, 
                             include_deleted: bool = False) -> List[Dict]:
        """קבלת כל ההוצאות של קבוצה"""
        try:
            expenses_sheet = self.spreadsheet.worksheet('expenses')
            records = expenses_sheet.get_all_records()
            
            group_expenses = []
            for record in records:
                if record.get('group_id') != group_id:
                    continue
                
                # סינון מחוקים אם נדרש
                if not include_deleted and record.get('status') == 'deleted':
                    continue
                
                group_expenses.append(record)
            
            # מיון לפי תאריך יצירה (החדש ביותר ראשון)
            group_expenses.sort(
                key=lambda x: x.get('created_at', ''), 
                reverse=True
            )
            
            return group_expenses
            
        except Exception as e:
            logger.error(f"Failed to get expenses for group {group_id}: {e}")
            return []
    
    def update_expense(self, expense_id: str, updates: Dict) -> bool:
        """עדכון הוצאה קיימת"""
        try:
            expenses_sheet = self.spreadsheet.worksheet('expenses')
            
            # מציאת השורה
            cell = expenses_sheet.find(expense_id)
            if not cell:
                return False
            
            row_num = cell.row
            
            # עדכון updated_at
            updates['updated_at'] = self._get_timestamp()
            
            # עדכון כל השדות
            for field, value in updates.items():
                if field in EXPENSES_HEADERS:
                    col_num = EXPENSES_HEADERS.index(field) + 1
                    expenses_sheet.update_cell(row_num, col_num, str(value))
            
            logger.info(f"Updated expense: {expense_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update expense: {e}")
            return False
    
    def delete_expense(self, expense_id: str) -> bool:
        """מחיקה רכה של הוצאה"""
        return self.update_expense(expense_id, {
            'status': 'deleted',
            'updated_at': self._get_timestamp()
        })
    
    # ===== ניהול קבצים ב-Drive =====
    
    def _create_couple_folder(self, group_id: str) -> str:
        """יצירת תיקיית זוג ב-Drive"""
        try:
            # יצירת תיקיה ראשית אם לא קיימת
            main_folder_id = self._get_or_create_main_folder()
            
            # יצירת תיקיית הזוג
            couple_folder_metadata = {
                'name': f'couple_{group_id}',
                'parents': [main_folder_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            couple_folder = self.drive_service.files().create(
                body=couple_folder_metadata,
                fields='id'
            ).execute()
            
            couple_folder_id = couple_folder.get('id')
            
            # יצירת תת-תיקיות
            subfolders = ['receipts', 'contacts', 'merged_files']
            for subfolder in subfolders:
                subfolder_metadata = {
                    'name': subfolder,
                    'parents': [couple_folder_id],
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                self.drive_service.files().create(
                    body=subfolder_metadata,
                    fields='id'
                ).execute()
            
            logger.info(f"Created folder structure for couple: {group_id}")
            return couple_folder_id
            
        except Exception as e:
            logger.error(f"Failed to create couple folder: {e}")
            return ""
    
    def _get_or_create_main_folder(self) -> str:
        """קבלת או יצירת התיקיה הראשית"""
        try:
            # חיפוש התיקיה הראשית
            query = "name='Wedding_System' and mimeType='application/vnd.google-apps.folder'"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                return files[0]['id']
            
            # יצירת התיקיה הראשית
            folder_metadata = {
                'name': 'Wedding_System',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"Failed to get/create main folder: {e}")
            return ""
    
    def upload_receipt_image(self, group_id: str, image_data: bytes, 
                           filename: str = None) -> str:
        """העלאת תמונת קבלה ל-Drive"""
        try:
            if not filename:
                filename = f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            # מציאת תיקיית הקבלות
            receipts_folder_id = self._get_receipts_folder_id(group_id)
            if not receipts_folder_id:
                return ""
            
            # העלאת הקובץ
            media = MediaIoBaseUpload(
                BytesIO(image_data),
                mimetype='image/jpeg'
            )
            
            file_metadata = {
                'name': filename,
                'parents': [receipts_folder_id]
            }
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            
            # קבלת קישור לצפייה
            file_url = f"https://drive.google.com/file/d/{file_id}/view"
            
            logger.info(f"Uploaded receipt image: {filename}")
            return file_url
            
        except Exception as e:
            logger.error(f"Failed to upload receipt image: {e}")
            return ""
    
    def _get_receipts_folder_id(self, group_id: str) -> str:
        """מציאת תיקיית הקבלות של זוג"""
        try:
            # חיפוש תיקיית הזוג
            couple_query = f"name='couple_{group_id}' and mimeType='application/vnd.google-apps.folder'"
            couple_results = self.drive_service.files().list(
                q=couple_query,
                fields='files(id)'
            ).execute()
            
            couple_files = couple_results.get('files', [])
            if not couple_files:
                return ""
            
            couple_folder_id = couple_files[0]['id']
            
            # חיפוש תיקיית הקבלות
            receipts_query = f"name='receipts' and parents in '{couple_folder_id}'"
            receipts_results = self.drive_service.files().list(
                q=receipts_query,
                fields='files(id)'
            ).execute()
            
            receipts_files = receipts_results.get('files', [])
            if receipts_files:
                return receipts_files[0]['id']
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to get receipts folder: {e}")
            return ""
    
    # ===== ניהול קבצי חיבור אנשי קשר =====
    
    def save_contacts_files(self, group_id: str, contacts_data: bytes, 
                           guests_data: bytes, progress: Dict) -> bool:
        """שמירת קבצי אנשי קשר ומוזמנים + התקדמות"""
        try:
            contacts_folder_id = self._get_contacts_folder_id(group_id)
            if not contacts_folder_id:
                return False
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # שמירת קובץ אנשי קשר
            contacts_media = MediaIoBaseUpload(
                BytesIO(contacts_data),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            contacts_metadata = {
                'name': f'contacts_{timestamp}.xlsx',
                'parents': [contacts_folder_id]
            }
            
            self.drive_service.files().create(
                body=contacts_metadata,
                media_body=contacts_media,
                fields='id'
            ).execute()
            
            # שמירת קובץ מוזמנים
            guests_media = MediaIoBaseUpload(
                BytesIO(guests_data),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            guests_metadata = {
                'name': f'guests_{timestamp}.xlsx',
                'parents': [contacts_folder_id]
            }
            
            self.drive_service.files().create(
                body=guests_metadata,
                media_body=guests_media,
                fields='id'
            ).execute()
            
            # שמירת התקדמות בגיליון
            progress_json = json.dumps(progress)
            self.update_couple_field(group_id, 'contacts_progress', progress_json)
            
            logger.info(f"Saved contacts files for group: {group_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save contacts files: {e}")
            return False
    
    def get_contacts_progress(self, group_id: str) -> Dict:
        """קבלת התקדמות חיבור אנשי קשר"""
        try:
            couple = self.get_couple_by_group_id(group_id)
            if not couple:
                return {}
            
            progress_json = couple.get('contacts_progress', '')
            if not progress_json:
                return {}
            
            return json.loads(progress_json)
            
        except Exception as e:
            logger.error(f"Failed to get contacts progress: {e}")
            return {}
    
    def _get_contacts_folder_id(self, group_id: str) -> str:
        """מציאת תיקיית אנשי הקשר של זוג"""
        try:
            # חיפוש תיקיית הזוג
            couple_query = f"name='couple_{group_id}' and mimeType='application/vnd.google-apps.folder'"
            couple_results = self.drive_service.files().list(
                q=couple_query,
                fields='files(id)'
            ).execute()
            
            couple_files = couple_results.get('files', [])
            if not couple_files:
                return ""
            
            couple_folder_id = couple_files[0]['id']
            
            # חיפוש תיקיית אנשי הקשר
            contacts_query = f"name='contacts' and parents in '{couple_folder_id}'"
            contacts_results = self.drive_service.files().list(
                q=contacts_query,
                fields='files(id)'
            ).execute()
            
            contacts_files = contacts_results.get('files', [])
            if contacts_files:
                return contacts_files[0]['id']
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to get contacts folder: {e}")
            return ""
    
    def save_merged_file(self, group_id: str, merged_data: bytes, 
                        filename: str = None) -> str:
        """שמירת קובץ מוזמנים מחובר סופי"""
        try:
            if not filename:
                filename = f"merged_guests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # מציאת תיקיית הקבצים המחוברים
            merged_folder_id = self._get_merged_folder_id(group_id)
            if not merged_folder_id:
                return ""
            
            # העלאת הקובץ
            media = MediaIoBaseUpload(
                BytesIO(merged_data),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            file_metadata = {
                'name': filename,
                'parents': [merged_folder_id]
            }
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            file_url = f"https://drive.google.com/file/d/{file_id}/view"
            
            logger.info(f"Saved merged file: {filename}")
            return file_url
            
        except Exception as e:
            logger.error(f"Failed to save merged file: {e}")
            return ""
    
    def _get_merged_folder_id(self, group_id: str) -> str:
        """מציאת תיקיית הקבצים המחוברים"""
        try:
            couple_query = f"name='couple_{group_id}' and mimeType='application/vnd.google-apps.folder'"
            couple_results = self.drive_service.files().list(
                q=couple_query,
                fields='files(id)'
            ).execute()
            
            couple_files = couple_results.get('files', [])
            if not couple_files:
                return ""
            
            couple_folder_id = couple_files[0]['id']
            
            merged_query = f"name='merged_files' and parents in '{couple_folder_id}'"
            merged_results = self.drive_service.files().list(
                q=merged_query,
                fields='files(id)'
            ).execute()
            
            merged_files = merged_results.get('files', [])
            if merged_files:
                return merged_files[0]['id']
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to get merged folder: {e}")
            return ""
    
    # ===== פונקציות עזר ובדיקות =====
    
    def health_check(self) -> Dict[str, bool]:
        """בדיקת תקינות השירותים"""
        checks = {
            "sheets_connection": False,
            "drive_connection": False,
            "spreadsheet_access": False,
            "couples_sheet_exists": False,
            "expenses_sheet_exists": False
        }
        
        try:
            # בדיקת חיבור Sheets
            if self.sheets_service:
                checks["sheets_connection"] = True
            
            # בדיקת חיבור Drive
            if self.drive_service:
                checks["drive_connection"] = True
            
            # בדיקת גישה לגיליון
            if self.spreadsheet:
                checks["spreadsheet_access"] = True
                
                # בדיקת קיום גיליונות
                worksheets = {ws.title for ws in self.spreadsheet.worksheets()}
                checks["couples_sheet_exists"] = 'couples' in worksheets
                checks["expenses_sheet_exists"] = 'expenses' in worksheets
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        
        return checks
    
    def get_statistics(self) -> Dict:
        """קבלת סטטיסטיקות כלליות של המערכת"""
        try:
            stats = {
                "total_couples": 0,
                "active_couples": 0,
                "total_expenses": 0,
                "total_amount": 0,
                "last_activity": None
            }
            
            # סטטיסטיקות זוגות
            couples = self.get_all_active_couples()
            stats["active_couples"] = len(couples)
            
            couples_sheet = self.spreadsheet.worksheet('couples')
            all_couples = couples_sheet.get_all_records()
            stats["total_couples"] = len(all_couples)
            
            # סטטיסטיקות הוצאות
            expenses_sheet = self.spreadsheet.worksheet('expenses')
            all_expenses = expenses_sheet.get_all_records()
            
            active_expenses = [
                exp for exp in all_expenses 
                if exp.get('status') == 'active'
            ]
            
            stats["total_expenses"] = len(active_expenses)
            
            # חישוב סכום כולל
            total_amount = 0
            for expense in active_expenses:
                try:
                    amount = float(expense.get('amount', 0))
                    total_amount += amount
                except (ValueError, TypeError):
                    continue
            
            stats["total_amount"] = total_amount
            
            # פעילות אחרונה
            if active_expenses:
                latest_expense = max(
                    active_expenses,
                    key=lambda x: x.get('created_at', ''),
                    default=None
                )
                if latest_expense:
                    stats["last_activity"] = latest_expense.get('created_at')
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


# ===== מופע גלובלי =====
_google_services = None

def get_google_services() -> GoogleServicesManager:
    """קבלת מופע יחיד של GoogleServicesManager"""
    global _google_services
    if _google_services is None:
        _google_services = GoogleServicesManager()
    return _google_services


# ===== בדיקה =====
if __name__ == "__main__":
    print("🧪 Testing Google Services...")
    
    try:
        gs = GoogleServicesManager()
        health = gs.health_check()
        
        print("📊 Health Check Results:")
        for service, status in health.items():
            emoji = "✅" if status else "❌"
            print(f"{emoji} {service}")
        
        if all(health.values()):
            print("\n✅ All systems operational!")
            stats = gs.get_statistics()
            print(f"📈 Statistics: {stats}")
        else:
            print("\n⚠️ Some services have issues")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")