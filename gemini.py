import sys
import os
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt5.uic import loadUi
from google import genai
from google.genai import types
from dotenv import load_dotenv

# -----------------
# 1. 환경 변수 로드 및 API 키/DB 정보 설정
# -----------------
load_dotenv() 
API_KEY = os.environ.get("GEMINI_API_KEY") 

# DB 설정: SQLite 파일 경로
DB_FILE = 'chat_history.db' 

# -----------------
# 2. 메인 애플리케이션 클래스 (QDialog 상속)
# -----------------
class GeminiChatApp(QDialog):
    def __init__(self):
        super().__init__()
        
        # 🚨 DB 초기화: 앱 시작 시 DB 파일과 테이블 생성
        self.init_sqlite_db() 
        
        # UI 파일 로드
        try:
            loadUi("gemini.ui", self) 
        except FileNotFoundError:
            QMessageBox.critical(self, "오류", "Error: 'gemini.ui' 파일을 찾을 수 없습니다.")
            sys.exit(1)

        # Gemini 클라이언트 및 채팅 세션 초기화
        self.chat = None
        self.client = None
        self.model = 'gemini-2.5-flash'
        self.init_gemini_client()
        
        # 🚨 UI 요소 연결 및 초기 설정 (통합 로직 적용)
        
        # 1. ComboBox 초기 설정 (위젯 이름: self.comboBox)
        # UI에 추가된 드롭다운 박스에 항목 추가
        self.comboBox.addItem("대화") # 인덱스 0
        self.comboBox.addItem("검색") # 인덱스 1
        
        # 2. 하나의 버튼과 Enter 키를 통합 핸들러에 연결
        # 버튼과 엔터 키 모두 handle_action을 호출하여 모드에 따라 동작을 분기합니다.
        self.pushButton.clicked.connect(self.handle_action)
        self.lineEdit.returnPressed.connect(self.handle_action)
        
        # 3. 기존의 pushButton_2 (검색 버튼) 연결은 제거됨

        self.apply_circular_mask()
        
        if self.client:
            self.txtBrowserResult.setText("Gemini AI에게 질문을 입력하세요. 드롭다운으로 '검색' 모드를 선택해 대화 기록을 찾을 수 있습니다.")

    # -----------------
    # 3. SQLite DB 초기화 함수 (테이블 생성)
    # -----------------
    def init_sqlite_db(self):
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()
            print(f"✅ SQLite DB 파일({DB_FILE}) 및 테이블 준비 완료.")
        except Exception as e:
            print(f"❌ SQLite DB 초기화 실패: {e}")

    def init_gemini_client(self):
        if not API_KEY:
            QMessageBox.warning(self, "API 오류", "🚨 경고: 'GEMINI_API_KEY' 환경 변수가 설정되지 않았습니다. API 기능은 작동하지 않습니다.")
            self.txtBrowserResult.setText("Gemini API 키 오류. .env 파일을 확인하세요.")
            return
            
        try:
            self.client = genai.Client(api_key=API_KEY)
            self.chat = self.client.chats.create(model=self.model)
        except Exception as e:
            error_msg = f"Gemini 클라이언트 초기화 중 오류 발생: {e.__class__.__name__}."
            self.txtBrowserResult.setText(error_msg)
            QMessageBox.critical(self, "초기화 오류", error_msg)
            self.client = None
            self.chat = None

    # -----------------
    # 4. 🚨 통합 액션 핸들러 함수 (ComboBox 모드 분기)
    # -----------------
    def handle_action(self):
        """ComboBox 선택에 따라 대화 또는 검색 함수를 호출하는 통합 함수."""
        
        selected_mode = self.comboBox.currentText()
        
        if selected_mode.startswith("대화"):
            # '대화' 모드인 경우: Gemini 질문 전송
            self.send_question()
            
        elif selected_mode.startswith("검색"):
            # '검색' 모드인 경우: DB 검색 실행
            self.search_history()
            
        else:
            QMessageBox.warning(self, "경고", "모드를 선택해주세요: 대화 또는 검색")

    # -----------------
    # 5. 질문 전송 및 답변 수신 함수 (handle_action에서 호출)
    # -----------------
    def send_question(self):
        if not self.chat: 
            self.txtBrowserResult.append("\n\n[Error]: Gemini 서비스가 초기화되지 않았습니다.")
            return

        question = self.lineEdit.text().strip()
        if not question:
            return

        self.lineEdit.clear()
        
        new_entry = f"\n\n[질문]: {question}\n[fox]: 답변을 생성하는 중..."
        self.txtBrowserResult.append(new_entry)
        self.txtBrowserResult.ensureCursorVisible()
        QApplication.processEvents()

        try:
            response = self.chat.send_message(question)
            final_answer = response.text.strip()
            
            # SQLite DB 저장 함수 호출
            self.save_to_sqlite(question, final_answer)

            current_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)
            updated_log = current_log[0] + f"\n[fox]: {final_answer}"

            self.txtBrowserResult.setText(updated_log)
            self.txtBrowserResult.ensureCursorVisible()

        except Exception as e:
            error_message = f"API 호출 중 오류 발생: {type(e).__name__}"
            current_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)
            updated_log = current_log[0] + f"\n[Error]: {error_message}"

            self.txtBrowserResult.setText(updated_log)
            print(f"API Error: {e}")
            
    # -----------------
    # 6. SQLite 데이터베이스 저장 함수
    # -----------------
    def save_to_sqlite(self, question, answer):
        conn = None 
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            sql = "INSERT INTO chat_history (question, answer, created_at) VALUES (?, ?, ?)"
            cursor.execute(sql, (question, answer, current_time))
            
            conn.commit()
            print(f"✅ SQLite 저장 성공: {current_time}")

        except Exception as e:
            print(f"❌ SQLite 저장 실패: {e}")
        finally:
            if conn:
                conn.close()

    # -----------------
    # 7. SQLite 데이터베이스 검색 함수 (handle_action에서 호출)
    # -----------------
    def search_history(self):
        search_term = self.lineEdit.text().strip()
        
        if not search_term:
            self.txtBrowserResult.setText("⚠️ 검색어를 입력해주세요.")
            return
            
        self.txtBrowserResult.setText(f"🔍 '{search_term}' 검색 결과:")
        conn = None
        
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # SQL LIKE 검색 쿼리
            search_like = f"%{search_term}%" 
            sql = """
            SELECT created_at, question, answer 
            FROM chat_history 
            WHERE question LIKE ? OR answer LIKE ?
            ORDER BY created_at DESC
            LIMIT 50
            """
            cursor.execute(sql, (search_like, search_like))
            results = cursor.fetchall()

            self.lineEdit.clear() # 검색 후 입력창 비우기

            if results:
                display_text = f"🔍 총 {len(results)}건의 기록이 검색되었습니다 (검색어: '{search_term}'):\n"
                for row in results:
                    # SQLite 결과는 인덱스로 접근합니다. (0: created_at, 1: question, 2: answer)
                    date_str = row[0]
                    question_text = row[1]
                    answer_text = row[2]
                    
                    display_text += "\n" + "="*50 + "\n"
                    display_text += f"날짜: {date_str}\n" 
                    display_text += f"질문: {question_text[:100]}{'...' if len(question_text) > 100 else ''}\n"
                    display_text += f"답변: {answer_text[:200]}{'...' if len(answer_text) > 200 else ''}"
                
                self.txtBrowserResult.setText(display_text)
            else:
                self.txtBrowserResult.setText(f"❌ '{search_term}'과 일치하는 기록을 찾을 수 없습니다.")

        except Exception as e:
            self.txtBrowserResult.setText(f"❌ 검색 중 알 수 없는 오류 발생: {e}")
        finally:
            if conn:
                conn.close()


    # -----------------
    # 8. QLabel 원형 마스크 적용 함수 
    # -----------------
    def apply_circular_mask(self):
        profile_label = self.myPic 
        label_size = profile_label.width() 
        
        if label_size == 0:
              label_size = 100 
              
        radius = label_size // 2 
        
        profile_label.setStyleSheet(f"""
            QLabel {{
                border: 3px solid #6699FF;
                border-radius: {radius}px;
                background-color: white; 
                padding: 0px; 
            }}
        """)

# -----------------
# 9. 애플리케이션 실행
# -----------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GeminiChatApp()
    window.show()
    sys.exit(app.exec_())