#!/usr/bin/env python3
"""
מערכת חתונה מאוחדת - הרצה ראשית
מריץ גם את Streamlit וגם את שרת ה-Webhook במקביל
"""

import os
import sys
import subprocess
import threading
import time
import signal
import logging
from typing import List

# הגדרת logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemRunner:
    """מנהל הרצת המערכת המאוחדת"""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.running = False
        
    def run_streamlit(self):
        """הרצת Streamlit"""
        try:
            logger.info("🚀 Starting Streamlit...")
            
            # הגדרות Streamlit
            env = os.environ.copy()
            env.update({
                'STREAMLIT_SERVER_PORT': os.getenv('STREAMLIT_PORT', '8501'),
                'STREAMLIT_SERVER_ADDRESS': os.getenv('STREAMLIT_HOST', '0.0.0.0'),
                'STREAMLIT_SERVER_HEADLESS': 'true',
                'STREAMLIT_BROWSER_GATHER_USAGE_STATS': 'false',
                'STREAMLIT_SERVER_ENABLE_CORS': 'false',
                'STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION': 'false'
            })
            
            process = subprocess.Popen(
                [sys.executable, '-m', 'streamlit', 'run', 'main.py'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes.append(process)
            
            # מעקב אחר הלוגים
            for line in iter(process.stdout.readline, ''):
                if self.running:
                    if 'Local URL' in line or 'Network URL' in line:
                        logger.info(f"📊 Streamlit: {line.strip()}")
                    elif 'error' in line.lower() or 'exception' in line.lower():
                        logger.error(f"❌ Streamlit Error: {line.strip()}")
                else:
                    break
                    
        except Exception as e:
            logger.error(f"❌ Failed to start Streamlit: {e}")
    
    def run_webhook(self):
        """הרצת שרת Webhook"""
        try:
            logger.info("🌐 Starting Webhook server...")
            
            # הגדרות Webhook
            host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
            port = os.getenv('WEBHOOK_PORT', '8000')
            
            process = subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', 'webhook_handler:app', 
                 '--host', host, '--port', port, '--reload'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes.append(process)
            
            # מעקב אחר הלוגים
            for line in iter(process.stdout.readline, ''):
                if self.running:
                    if 'Uvicorn running' in line or 'started server process' in line:
                        logger.info(f"🌐 Webhook: {line.strip()}")
                    elif 'error' in line.lower() or 'exception' in line.lower():
                        logger.error(f"❌ Webhook Error: {line.strip()}")
                else:
                    break
                    
        except Exception as e:
            logger.error(f"❌ Failed to start Webhook server: {e}")
    
    def check_dependencies(self) -> bool:
        """בדיקת תלויות נדרשות"""
        try:
            logger.info("🔍 Checking dependencies...")
            
            # בדיקת Python
            python_version = sys.version_info
            if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
                logger.error("❌ Python 3.8+ required")
                return False
            
            logger.info(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
            
            # בדיקת חבילות חיוניות
            required_packages = [
                'streamlit',
                'fastapi', 
                'uvicorn',
                'pandas',
                'openai',
                'google_auth',  # תיקון: google_auth במקום google.auth (underscore במקום dot)
                'gspread'
            ]
            
            missing_packages = []
            
            for package in required_packages:
                try:
                    # טיפול מיוחד בחבילות Google
                    if package == 'google_auth':
                        __import__('google.auth')
                    else:
                        __import__(package)
                    logger.info(f"✅ {package}")
                except ImportError:
                    missing_packages.append(package)
                    logger.error(f"❌ {package}")
            
            if missing_packages:
                logger.error(f"❌ Missing packages: {', '.join(missing_packages)}")
                logger.error("💡 Run: pip install -r requirements.txt")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Dependency check failed: {e}")
            return False
    
    def check_config(self) -> bool:
        """בדיקת קונפיגורציה"""
        try:
            logger.info("⚙️ Checking configuration...")
            
            from config import validate_config
            config_status = validate_config()
            
            all_good = True
            for service, status in config_status.items():
                emoji = "✅" if status else "❌"
                logger.info(f"{emoji} {service}")
                if not status:
                    all_good = False
            
            if not all_good:
                logger.warning("⚠️ Some services are not configured properly")
                logger.warning("💡 Check your .env file and environment variables")
            
            return True  # נמשיך גם עם קונפיגורציה חלקית
            
        except Exception as e:
            logger.error(f"❌ Configuration check failed: {e}")
            return False
    
    def start(self):
        """התחלת המערכת"""
        try:
            logger.info("🚀 Starting Wedding System...")
            
            # בדיקות ראשוניות
            if not self.check_dependencies():
                return False
            
            if not self.check_config():
                return False
            
            self.running = True
            
            # הרצת השירותים במקביל
            streamlit_thread = threading.Thread(target=self.run_streamlit, daemon=True)
            webhook_thread = threading.Thread(target=self.run_webhook, daemon=True)
            
            streamlit_thread.start()
            webhook_thread.start()
            
            # המתנה קצרה לאתחול
            time.sleep(3)
            
            # הצגת מידע
            streamlit_port = os.getenv('STREAMLIT_PORT', '8501')
            webhook_port = os.getenv('WEBHOOK_PORT', '8000')
            
            print("\n" + "="*60)
            print("🎉 מערכת החתונה רצה בהצלחה!")
            print("="*60)
            print(f"📊 Streamlit Dashboard: http://localhost:{streamlit_port}")
            print(f"🌐 Webhook Server: http://localhost:{webhook_port}")
            print(f"🔍 Health Check: http://localhost:{webhook_port}/health")
            print(f"📈 System Stats: http://localhost:{webhook_port}/stats")
            print("="*60)
            print("💡 לעצירת המערכת הקש Ctrl+C")
            print("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start system: {e}")
            return False
    
    def stop(self):
        """עצירת המערכת"""
        logger.info("🛑 Stopping Wedding System...")
        
        self.running = False
        
        # עצירת כל התהליכים
        for process in self.processes:
            try:
                if process.poll() is None:  # תהליך עדיין רץ
                    process.terminate()
                    # המתנה לסגירה נקייה
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # כיבוי כפוי אם נדרש
                        process.kill()
                        process.wait()
            except Exception as e:
                logger.error(f"❌ Error stopping process: {e}")
        
        self.processes.clear()
        logger.info("✅ Wedding System stopped")
    
    def signal_handler(self, signum, frame):
        """טיפול באות עצירה"""
        logger.info(f"📨 Received signal {signum}")
        self.stop()
        sys.exit(0)

def main():
    """פונקציה ראשית"""
    
    # הצגת כותרת
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                 🎉 מערכת חתונה מאוחדת 🎉                 ║
    ║                                                          ║
    ║  📊 Streamlit Dashboard + 🤖 WhatsApp Bot + 📱 Contacts  ║
    ║                        Version 2.0.0                    ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # יצירת מנהל המערכת
    runner = SystemRunner()
    
    # הגדרת signal handlers
    signal.signal(signal.SIGINT, runner.signal_handler)
    signal.signal(signal.SIGTERM, runner.signal_handler)
    
    try:
        # התחלת המערכת
        if runner.start():
            # לולאה אינסופית - המתנה לעצירה
            while runner.running:
                time.sleep(1)
        else:
            logger.error("❌ Failed to start the system")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("👋 Shutting down gracefully...")
        runner.stop()
    
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        runner.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()