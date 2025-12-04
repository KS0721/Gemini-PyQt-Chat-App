import sys
import os
import re
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog, QLabel
from PyQt5.uic import loadUi
from PyQt5.QtGui import QPixmap
from google import genai
from google.genai import types
from dotenv import load_dotenv
import base64

# ----------------------------------------------------------------------
# 1. 설정 및 전역 변수 (Configuration)
# ----------------------------------------------------------------------
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
DB_NAME = 'chat_data.db'

# ----------------------------------------------------------------------
# 2. 데이터베이스 모듈 (SQLiteChatDatabase Class)
# ----------------------------------------------------------------------
class SQLiteChatDatabase:
    """
    SQLite 데이터베이스 연결 및 채팅 기록 저장을 처리하는 클래스입니다.
    """
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.history_table = "chat_history"
        self.facts_table = "user_facts"
        self._init_db_tables()

    def _get_connection(self):
        """DB 연결을 생성하고 반환합니다."""
        try:
            return sqlite3.connect(self.db_name)
        except sqlite3.Error as e:
            print(f"❌ SQLite 연결 오류: {e}")
            raise ConnectionError(f"SQLite 연결 실패: {e}")

    def _init_db_tables(self):
        """필요한 테이블(history, facts)을 생성합니다."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.history_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.facts_table} (
                    fact_key TEXT PRIMARY KEY,
                    fact_value TEXT NOT NULL
                );
            """)
            conn.commit()
            print(f"✅ SQLite DB 테이블 초기화 완료: {self.db_name}")

        except Exception as e:
            print(f"❌ SQLite DB 초기화 실패: {e}")
        finally:
            if conn:
                conn.close()

    def get_contextual_facts(self):
        """DB에서 사용자 팩트를 로드하여 Gemini 시스템 지침용 텍스트 생성."""
        conn = None
        facts_list = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT fact_key, fact_value FROM {self.facts_table}")
            results = cursor.fetchall()
            
            if results:
                for row in results:
                    facts_list.append(f"{row[0]}: {row[1]}")
            
            if facts_list:
                facts_text = ", ".join(facts_list)
                return f"당신은 이 사용자와 대화하고 있습니다. 이 사용자에 대한 다음 사실을 기억하고 대화에 활용해야 합니다: {facts_text}. 답변은 친절하고 유머러스한 톤으로 하세요."
            else:
                return "당신은 일반적인 대화형 AI입니다."
            
        except Exception as e:
            print(f"❌ 팩트 로드 실패: {e}")
            return "당신은 일반적인 대화형 AI입니다."
        finally:
            if conn:
                conn.close()
                
    def save_chat_entry(self, question, answer):
        """질문과 답변을 chat_history 테이블에 저장합니다."""
        conn = None
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = f"INSERT INTO {self.history_table} (question, answer, created_at) VALUES (?, ?, ?)"
            cursor.execute(sql, (question, answer, current_time))
            conn.commit()
            print(f"✅ SQLite 저장 성공: {current_time}")
        except Exception as e:
            print(f"❌ SQLite 저장 실패: {e}")
        finally:
            if conn:
                conn.close()
                
    def delete_last_entry(self):
        """가장 최근에 저장된 레코드를 삭제합니다."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT id FROM {self.history_table} ORDER BY id DESC LIMIT 1")
            last_id_row = cursor.fetchone()
            
            if last_id_row:
                record_id = last_id_row[0]
                cursor.execute(f"DELETE FROM {self.history_table} WHERE id = ?", (record_id,))
                conn.commit()
                return record_id
            return None
        except Exception as e:
            print(f"❌ SQLite 삭제 실패: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_user_facts_map(self):
        """DB에서 사용자 팩트를 {key: value} 딕셔너리 형태로 로드"""
        conn = None
        facts_map = {}
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT fact_key, fact_value FROM {self.facts_table}")
            results = cursor.fetchall()
            for row in results:
                facts_map[row[0]] = row[1]
            return facts_map
        except Exception as e:
            print(f"❌ 팩트 맵 로드 실패: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    def add_or_update_fact(self, key, value):
        """팩트를 추가하거나 업데이트합니다. (SQLite는 INSERT OR REPLACE 사용)"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = f"INSERT OR REPLACE INTO {self.facts_table} (fact_key, fact_value) VALUES (?, ?)"
            cursor.execute(sql, (key, value))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ 팩트 업데이트 실패: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def delete_fact(self, key):
        """팩트를 삭제합니다."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {self.facts_table} WHERE fact_key = ?", (key,))
            changes = cursor.rowcount
            conn.commit()
            return changes > 0
        except Exception as e:
            print(f"❌ 팩트 삭제 실패: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def search_history_by_keyword(self, keyword):
        """DB 기록을 키워드로 검색합니다."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            search_like = f"%{keyword}%"
            sql = f"""
            SELECT created_at, question, answer
            FROM {self.history_table}
            WHERE question LIKE ? OR answer LIKE ?
            ORDER BY created_at DESC
            LIMIT 50
            """
            cursor.execute(sql, (search_like, search_like))
            results = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in results]

        except Exception as e:
            print(f"❌ DB 키워드 검색 실패: {e}")
            return []
        finally:
            if conn:
                conn.close()

# ----------------------------------------------------------------------
# 3. 메인 애플리케이션 모듈 (GeminiChatApp Class)
# ----------------------------------------------------------------------
class GeminiChatApp(QDialog):
    def __init__(self):
        super().__init__()
        
        # 3.1. 초기화 및 설정
        try:
            self.db_handler = SQLiteChatDatabase()
        except ConnectionError as e:
            QMessageBox.critical(self, "DB 연결 오류", str(e))
            sys.exit(1)
            
        self.user_facts = self.db_handler.get_contextual_facts()
        
        # 🚨 로컬 실행 환경에서는 UI 파일을 로드해야 합니다.
        try:
            loadUi("gemini.ui", self)
        except FileNotFoundError:
            # Mock UI 구성
            pass
        
        # Mock UI 구성 (로컬에선 무시됨.)
        if not hasattr(self, 'lineEdit'):
            self.lineEdit = type('MockLineEdit', (object,), {'text': lambda self: '', 'clear': lambda self: None})()
            self.txtBrowserResult = type('MockTextBrowser', (object,), {'append': print, 'toPlainText': lambda self: "Mock Text", 'setText': print, 'ensureCursorVisible': lambda self: None})()
            self.pushButton = type('MockButton', (object,), {'clicked': type('MockSignal', (object,), {'connect': lambda self, func: None})()})()
            
            # Mock for pushButton_2 (업로드 버튼) 및 lineEdit_file (파일 경로)
            self.pushButton_2 = type('MockButton2', (object,), {'clicked': type('MockSignal', (object,), {'connect': lambda self, func: None})(), 'setVisible': lambda self, visible: None, 'hide': lambda self: None})() 
            self.lineEdit_file = type('MockLineEditFile', (object,), {'text': lambda self: '', 'setText': lambda self, text: None, 'setVisible': lambda self, visible: None, 'hide': lambda self: None, 'clear': lambda self: None})() 
            
            # ⭐️ Mock for the filename Label (UI inspector 결과: label_4) ⭐️
            self.label_4 = type('MockLabel4', (object,), {'setVisible': lambda self, visible: None, 'hide': lambda self: None})()
            
            self.comboBox = type('MockComboBox', (object,), {'currentText': lambda self: '대화', 'addItem': lambda self, item: None, 'currentIndexChanged': type('MockSignal', (object,), {'connect': lambda self, func: None})()})()
            self.myPic = type('MockLabel', (object,), {'width': lambda self: 100})()

        # ⭐️ UI 파일이 로드된 경우, '파일명' 라벨은 self.label_4 임을 확인했습니다. ⭐️
        # 추가적인 라벨 연결 로직 없이, 코드에서 self.label_4를 직접 사용합니다.


        self.chat = None
        self.client = None
        self.model = 'gemini-2.5-flash'
        self.image_path = "" # 이미지 파일 경로를 저장할 변수 추가
        self.init_gemini_client()
        
        # 3.2. UI 모드 항목 추가 (기능 활성화)
        self.comboBox.addItem("대화")
        self.comboBox.addItem("검색")
        self.comboBox.addItem("요약")
        self.comboBox.addItem("코딩")
        self.comboBox.addItem("웹 검색")
        self.comboBox.addItem("기억 관리")
        self.comboBox.addItem("데이터 분석")
        self.comboBox.addItem("이미지 분석")
        self.comboBox.addItem("에이전트 워크플로우")
        
        # 3.3. 시그널 연결 (실제 PyQt5 객체에 연결되어야 함)
        if hasattr(self, 'pushButton') and hasattr(self.pushButton, 'clicked'):
            self.pushButton.clicked.connect(self.handle_action)
        if hasattr(self, 'lineEdit') and hasattr(self.lineEdit, 'returnPressed'):
            self.lineEdit.returnPressed.connect(self.handle_action)
        
        # '업로드' 버튼 (pushButton_2) 시그널 연결
        if hasattr(self, 'pushButton_2') and hasattr(self.pushButton_2, 'clicked'):
            self.pushButton_2.clicked.connect(self.handle_upload_file)

        # ⭐️ 콤보박스 변경 시 UI 가시성을 업데이트하도록 연결 ⭐️
        if hasattr(self, 'comboBox') and hasattr(self.comboBox, 'currentIndexChanged'):
            self.comboBox.currentIndexChanged.connect(self.update_ui_visibility)

        # ⭐️ UI 가시성 초기 설정 및 파일 경로 초기화 ⭐️
        self.update_ui_visibility(initial_call=True) 
        
        if self.client:
            self.txtBrowserResult.setText(f"Gemini AI에게 질문을 입력하세요.\n\n[Gemini]: 로컬 **SQLite DB**에 모든 기록을 저장하여 응답성이 향상되었습니다. 기능별 모드를 선택하세요.")


    # ----------------------------------------------------------------------
    # 4. Gemini API 핸들러 (Gemini Client & Session)
    # ----------------------------------------------------------------------
    def init_gemini_client(self):
        if not API_KEY:
            QMessageBox.warning(self, "API 오류", "🚨 경고: 'GEMINI_API_KEY' 환경 변수가 설정되지 않았습니다.")
            return
            
        try:
            self.client = genai.Client(api_key=API_KEY)
            
            initial_history = [
                types.Content(role="user", parts=[types.Part(text="이 대화의 시스템 지침은 다음과 같습니다: " + self.user_facts)]),
                types.Content(role="model", parts=[types.Part(text="시스템 지침을 확인했습니다. 이제부터 당신의 팩트와 컨텍스트를 기억하며 대화하겠습니다.")])
            ]
            self.chat = self.client.chats.create(
                model=self.model,
                history=initial_history
            )

        except Exception as e:
            error_msg = f"Gemini 클라이언트 초기화 중 오류 발생: {e.__class__.__name__}."
            QMessageBox.critical(self, "초기화 오류", error_msg)
            print(f"Error during initialization: {e}")
            self.client = None
            self.chat = None
            
    # ----------------------------------------------------------------------
    # 5. 통합 액션 및 핵심 기능 핸들러
    # ----------------------------------------------------------------------
    def update_ui_visibility(self, index=None, initial_call=False):
        """⭐️ 콤보박스 선택에 따라 파일명 라벨(label_4), 파일 경로 입력창, 업로드 버튼의 가시성을 제어합니다. ⭐️"""
        selected_mode = self.comboBox.currentText()
        
        # '데이터 분석' 또는 '이미지 분석' 모드에서만 보이도록 설정
        is_file_mode = selected_mode.startswith("데이터 분석") or selected_mode.startswith("이미지 분석")

        # 파일명 라벨(label_4), 파일 경로 입력창(lineEdit_file), 업로드 버튼(pushButton_2) 위젯의 존재 여부 확인
        has_file_widgets = (
            hasattr(self, 'lineEdit_file') and hasattr(self.lineEdit_file, 'setVisible') and
            hasattr(self, 'pushButton_2') and hasattr(self.pushButton_2, 'setVisible') and
            hasattr(self, 'label_4') and hasattr(self.label_4, 'setVisible') # ⭐️ label_4 사용 ⭐️
        )

        if has_file_widgets:
            # 파일명 라벨 (label_4), 파일 경로 입력창 (lineEdit_file), 업로드 버튼 (pushButton_2)의 가시성 설정
            self.label_4.setVisible(is_file_mode) # ⭐️ label_4 제어 ⭐️
            self.lineEdit_file.setVisible(is_file_mode)
            self.pushButton_2.setVisible(is_file_mode)
        
        # 모드가 변경되어 파일 관련 위젯이 숨겨질 때, 경로를 초기화
        if not is_file_mode and has_file_widgets:
             self.lineEdit_file.clear()
             self.image_path = ""
             # 초기 실행 시 파일 모드가 아니면 한 번 숨김 처리 (Qt Designer 설정 무시)
        elif initial_call and has_file_widgets and not is_file_mode:
             self.label_4.hide() # ⭐️ label_4 hide 처리 ⭐️
             self.lineEdit_file.hide()
             self.pushButton_2.hide()

    def handle_action(self):
        """ComboBox 선택과 입력 내용에 따라 동작을 분기하는 통합 함수."""
        
        input_text = self.lineEdit.text().strip()
        selected_mode = self.comboBox.currentText()
        
        if not self.client:
            self.txtBrowserResult.setText("❌ API 클라이언트가 초기화되지 않았습니다. API 키를 확인하세요.")
            return
        
        if input_text and any(keyword in input_text for keyword in ["지워줘", "삭제", "취소"]):
            self.delete_last_entry()
            return
        
        if selected_mode.startswith("대화"):
            self.send_question(input_text)
        elif selected_mode.startswith("검색"):
            self.search_history(input_text)
        elif selected_mode.startswith("요약"):
            self.handle_summarize(input_text)
        elif selected_mode.startswith("코딩"):
            self.handle_code_generation(input_text)
        elif selected_mode.startswith("웹 검색"):
            self.handle_web_search(input_text)
        elif selected_mode.startswith("기억 관리"):
            self.handle_fact_management(input_text)
        elif selected_mode.startswith("데이터 분석"):
            self.handle_data_analysis(input_text)
        elif selected_mode.startswith("이미지 분석"):
            self.handle_image_analysis(input_text)
        elif selected_mode.startswith("에이전트 워크플로우"):
            self.handle_agent_workflow(input_text)
        else:
            self.txtBrowserResult.setText("모드를 선택해주세요.")

    def handle_upload_file(self):
        """파일 업로드 다이얼로그를 열고 경로를 lineEdit_file에 설정합니다."""
        selected_mode = self.comboBox.currentText()
        
        if selected_mode.startswith("이미지 분석"):
            file_filter = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        elif selected_mode.startswith("데이터 분석"):
            # CSV, 텍스트 등 데이터 파일 형식을 지원
            file_filter = "Data Files (*.csv *.txt *.json);;Images (*.png *.jpg *.jpeg);;All Files (*)"
        else:
            file_filter = "All Files (*)"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "파일 선택",
            "",
            file_filter
        )

        if file_path:
            self.image_path = file_path # 내부 변수에도 저장
            self.lineEdit_file.setText(file_path) # UI에 경로 표시
            self.txtBrowserResult.append(f"\n\n[System]: 📎 파일 경로 설정 완료: **{os.path.basename(file_path)}**\n질문을 입력하고 **보내기** 버튼을 누르세요.")
        
        
    def send_question(self, question):
        """일반 대화 모드: Gemini 채팅 세션 및 DB 저장."""
        if not self.chat or not question: return
        self.lineEdit.clear()
        
        new_entry = f"\n\n[질문]: {question}\n[fox]: 답변을 생성하는 중... (SQLite 로컬 DB 사용으로 빨라졌습니다!)"
        self.txtBrowserResult.append(new_entry)
        self.txtBrowserResult.ensureCursorVisible()
        QApplication.processEvents()

        try:
            response = self.chat.send_message(question)
            final_answer = response.text.strip()
            
            self.db_handler.save_chat_entry(question, final_answer)

            updated_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0] + f"\n[fox]: {final_answer}"
            self.txtBrowserResult.setText(updated_log)
            self.txtBrowserResult.ensureCursorVisible()

        except Exception as e:
            error_message = f"API 호출 중 오류 발생: {type(e).__name__}"
            current_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0]
            updated_log = current_log + f"\n[Error]: {error_message}"
            self.txtBrowserResult.setText(updated_log)
            print(f"API Error: {e}")

    def handle_image_analysis(self, question):
        """이미지 파일 경로를 사용하여 멀티모달 분석을 수행합니다."""
        if not self.client: return
        
        image_path = self.lineEdit_file.text().strip()
        if not image_path or not os.path.exists(image_path):
            self.txtBrowserResult.setText("⚠️ 이미지 분석 모드: '업로드' 버튼을 눌러 이미지 파일을 선택하거나, 경로를 확인하세요.")
            return

        if not question:
            question = "이 이미지를 자세히 설명해줘."
            
        self.lineEdit.clear()
        
        question_display = f"**[이미지 분석 요청]:** {question[:100]}..."
        new_entry = f"\n\n{question_display}\n[fox]: 🖼️ 파일 **{os.path.basename(image_path)}**을(를) 분석하는 중..."
        self.txtBrowserResult.append(new_entry)
        QApplication.processEvents()
        
        try:
            # 1. 파일에서 바이트 읽기
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
                
            # 2. MIME 타입 추정 (확장자 기반)
            ext = os.path.splitext(image_path)[1].lower()
            if ext in ['.png', '.webp']:
                mime_type = f'image/{ext[1:]}'
            elif ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            else:
                mime_type = 'image/jpeg' # 기본값
            
            # 3. Gemini Part 생성
            image_data = types.Part.from_bytes(image_bytes, mime_type=mime_type)
            contents = [image_data, question]
            
            # 4. API 호출
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents
            )
            final_response = response.text.strip()
            
            # 5. DB 저장
            self.db_handler.save_chat_entry(f"[이미지 분석 요청] {question}", f"[이미지 분석 응답] {final_response}")

            # 6. UI 업데이트
            updated_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0] + f"\n[fox]: ✅ **이미지 분석 결과**\n{final_response}"
            self.txtBrowserResult.setText(updated_log)
            self.lineEdit_file.setText("") # 사용 후 파일 경로 초기화

        except FileNotFoundError:
            error_message = f"❌ 파일 '{image_path}'을(를) 찾을 수 없습니다."
            self.txtBrowserResult.append(f"\n[Error]: {error_message}")
        except Exception as e:
            error_message = f"이미지 분석 API 호출 중 오류 발생: {type(e).__name__}"
            current_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0]
            updated_log = current_log + f"\n[Error]: {error_message}"
            self.txtBrowserResult.setText(updated_log)

    def handle_agent_workflow(self, workflow_prompt):
        """에이전트 워크플로우: 다단계 작업 처리 및 DB 저장."""
        if not self.client or not workflow_prompt:
            self.txtBrowserResult.setText("⚠️ 에이전트 워크플로우: 다단계 작업을 정의하세요.")
            return

        self.lineEdit.clear()
        
        question_display = f"**[에이전트 워크플로우 요청]:** {workflow_prompt[:100]}..."
        new_entry = f"\n\n{question_display}\n[fox]: ⚙️ 워크플로우를 분석하고 실행합니다. (Google Search 포함 가능)"
        self.txtBrowserResult.append(new_entry)
        QApplication.processEvents()
        
        system_prompt = (
            "당신은 다단계 작업을 처리하는 에이전트입니다. 사용자의 요청을 '단계별'로 분해하고 순차적으로 처리하세요.\n"
            "각 단계의 결과를 다음 단계의 입력으로 사용해야 합니다. 최종 결과만 출력합니다.\n"
            "웹 검색이 필요한 단계에는 Google Search Tool을 사용하세요."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=workflow_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=[{"googleSearch": {}}]
                )
            )
            final_response = response.text.strip()
            
            self.db_handler.save_chat_entry(f"[워크플로우 요청] {workflow_prompt}", f"[워크플로우 응답] {final_response}")

            updated_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0] + f"\n[fox]: ✅ **워크플로우 최종 결과**\n{final_response}"
            self.txtBrowserResult.setText(updated_log)

        except Exception as e:
            error_message = f"워크플로우 API 호출 중 오류 발생: {type(e).__name__}"
            current_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0]
            updated_log = current_log + f"\n[Error]: {error_message}"
            self.txtBrowserResult.setText(updated_log)

    # ----------------------------------------------------------------------
    # 6. 보조 기능 핸들러 (Utility Handlers - DB 사용)
    # ----------------------------------------------------------------------
    def delete_last_entry(self):
        """가장 최근 기록 삭제 및 UI 업데이트."""
        record_id = self.db_handler.delete_last_entry()
        if record_id is not None:
            self.txtBrowserResult.append(f"\n\n[System]: ✅ 가장 최근 기록(ID: {record_id})이 SQLite DB에서 삭제되었습니다.")
        else:
            self.txtBrowserResult.append("\n\n[System]: ⚠️ 삭제할 기록이 없거나 DB 오류가 발생했습니다.")
            
    def handle_fact_management(self, command):
        """기억 관리 로직 (팩트 추가/삭제/보기/재설정)"""
        if not command or command.strip().lower() in ["보기", "확인", "list"]:
            self.display_current_facts()
            return
        
        command_parts = command.split(' ', 1)
        action = command_parts[0].lower()
        
        if action == "추가" and len(command_parts) > 1:
            try:
                key, value = command_parts[1].split('=', 1)
                if self.db_handler.add_or_update_fact(key.strip(), value.strip()):
                    self.txtBrowserResult.setText(f"\n\n[System]: ✅ 팩트 업데이트 성공: '{key}'가 '{value}'로 설정되었습니다.")
                    self.reset_chat_session()
                else:
                    self.txtBrowserResult.setText("\n\n[System]: ❌ 팩트 업데이트 실패. DB 연결을 확인하세요.")
            except ValueError:
                self.txtBrowserResult.setText("\n\n[System]: ❌ 잘못된 형식입니다. 사용법: 추가 키=값 (예: 추가 직업=개발자)")
            return
            
        elif action == "삭제" and len(command_parts) > 1:
            key = command_parts[1].strip()
            if self.db_handler.delete_fact(key):
                self.txtBrowserResult.setText(f"\n\n[System]: ✅ 팩트 삭제 성공: '{key}'가 삭제되었습니다.")
                self.reset_chat_session()
            else:
                self.txtBrowserResult.setText(f"\n\n[System]: ⚠️ 팩트 삭제 실패: 키 '{key}'를 찾을 수 없습니다.")
            return

        elif action == "재설정" and len(command_parts) == 1:
            self.reset_chat_session()
            return
            
        else:
            self.txtBrowserResult.setText("\n\n[System]: 🧠 **기억 관리 모드 명령어**\n"
                                             " - 팩트 보기: '보기' 입력 (기본값)\n"
                                             " - 팩트 추가/수정: '추가 키=값' (예: 추가 취미=독서)\n"
                                             " - 팩트 삭제: '삭제 키' (예: 삭제 취미)\n"
                                             " - 대화 컨텍스트 재설정: '재설정' (AI가 초기 기억으로 돌아갑니다.)")

    def display_current_facts(self):
        """현재 DB에 저장된 팩트들을 UI에 표시"""
        facts_map = self.db_handler.get_user_facts_map()
        if not facts_map:
            fact_text = "저장된 팩트가 없습니다."
        else:
            facts_text_list = [f"{key.replace('_', ' ').title()}: {value}" for key, value in facts_map.items()]
            fact_text = "\n".join(facts_text_list)
            
        self.txtBrowserResult.setText(f"\n\n[System]: 🧠 **현재 AI가 기억하는 사용자 팩트 목록 (SQLite)**\n"
                                         f"--- (키: 값) ---\n"
                                         f"{fact_text}\n"
                                         f"----------------\n"
                                         f"팩트를 수정하려면 '기억 관리' 모드에서 '추가 키=값' 또는 '삭제 키' 명령을 사용하세요.")

    def reset_chat_session(self):
        """Gemini 채팅 세션을 완전히 재시작하여 새로운 팩트 컨텍스트를 적용"""
        self.user_facts = self.db_handler.get_contextual_facts()
        self.init_gemini_client()
        self.txtBrowserResult.append("\n\n[System]: 🔄 **대화 세션 재설정 완료.**\n새로운 사용자 팩트(기억)가 Gemini AI에 적용되었습니다.")

    def search_history(self, search_term):
        """SQLite DB에서 대화 기록을 검색합니다."""
        if not search_term:
            self.txtBrowserResult.setText("⚠️ 검색어를 입력해주세요.")
            return

        self.lineEdit.clear()
        self.txtBrowserResult.setText(f"🔍 '{search_term}' 검색 결과:\n" + "="*50)
            
        results = self.db_handler.search_history_by_keyword(search_term)

        if results:
            display_text = ""
            for row in results:
                display_text += "\n" + "="*50 + "\n"
                display_text += f"날짜: {row['created_at']}\n"
                display_text += f"질문: {row['question'][:100]}{'...' if len(row['question']) > 100 else ''}\n"
                display_text += f"답변: {row['answer'][:200]}{'...' if len(row['answer']) > 200 else ''}"
            
            self.txtBrowserResult.setText(self.txtBrowserResult.toPlainText() + display_text)

        else:
            self.txtBrowserResult.setText(self.txtBrowserResult.toPlainText() + f"\n\n❌ '{search_term}'과 일치하는 대화 기록을 찾을 수 없습니다.")

    # ----------------------------------------------------------------------
    # 7. 기타 보조 기능 (API 호출 및 DB 저장)
    # ----------------------------------------------------------------------
    def handle_summarize(self, text_to_summarize):
        if not self.client or not text_to_summarize:
            self.txtBrowserResult.setText("⚠️ 요약할 텍스트를 입력해주세요.")
            return

        self.lineEdit.clear()
        
        self.txtBrowserResult.append(f"\n\n[요약 요청]: {text_to_summarize[:100]}...\n[fox]: 📝 텍스트를 요약하는 중...")
        QApplication.processEvents()

        try:
            prompt = f"다음 텍스트를 핵심만 간결하게 요약하세요: {text_to_summarize}"
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            final_summary = response.text.strip()
            
            self.db_handler.save_chat_entry(f"[요약 요청] {text_to_summarize[:100]}...", f"[요약 응답] {final_summary}") 

            updated_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0] + f"\n[fox]: ✅ **요약 결과**\n{final_summary}"
            self.txtBrowserResult.setText(updated_log)
        except Exception as e:
            error_message = f"요약 API 호출 중 오류 발생: {type(e).__name__}"
            self.txtBrowserResult.setText(self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0] + f"\n[Error]: {error_message}")

    def handle_code_generation(self, prompt):
        if not self.client or not prompt:
            self.txtBrowserResult.setText("⚠️ 생성할 코드를 설명해주세요.")
            return

        self.lineEdit.clear()
        
        self.txtBrowserResult.append(f"\n\n[코드 요청]: {prompt[:100]}...\n[fox]: 🧑‍💻 코드를 생성하는 중...")
        QApplication.processEvents()

        try:
            system_instruction = "당신은 Python 전문가입니다. 요청에 따라 코드와 설명을 Markdown 코드 블록으로 작성하세요."
            response = self.client.models.generate_content(
                model=self.model, 
                contents=prompt, 
                config=types.GenerateContentConfig(system_instruction=system_instruction)
            )
            final_code = response.text.strip()
            
            self.db_handler.save_chat_entry(f"[코드 요청] {prompt[:100]}...", f"[코드 응답] {final_code[:100]}...") 

            updated_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0] + f"\n[fox]: ✅ **코드 생성 결과**\n{final_code}"
            self.txtBrowserResult.setText(updated_log)
        except Exception as e:
            error_message = f"코드 API 호출 중 오류 발생: {type(e).__name__}"
            self.txtBrowserResult.setText(self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0] + f"\n[Error]: {error_message}")

    def handle_web_search(self, query):
        if not self.client or not query:
            self.txtBrowserResult.setText("⚠️ 웹 검색 키워드를 입력해주세요.")
            return

        self.lineEdit.clear()
        
        self.txtBrowserResult.append(f"\n\n[웹 검색 요청]: {query}\n[fox]: 🌐 웹 검색을 수행하는 중...")
        QApplication.processEvents()

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[{"googleSearch": {}}]
                )
            )
            final_result = response.text.strip()
            
            self.db_handler.save_chat_entry(f"[웹 검색 요청] {query}", f"[웹 검색 응답] {final_result[:100]}...") 

            updated_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0] + f"\n[fox]: ✅ **웹 검색 결과**\n{final_result}"
            self.txtBrowserResult.setText(updated_log)
        except Exception as e:
            error_message = f"웹 검색 API 호출 중 오류 발생: {type(e).__name__}"
            self.txtBrowserResult.setText(self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0] + f"\n[Error]: {error_message}")
            
    def handle_data_analysis(self, prompt):
        if not self.client or not prompt:
            self.txtBrowserResult.setText("⚠️ 분석할 데이터(표, 리스트 등)와 질문을 함께 입력해주세요.")
            return

        self.lineEdit.clear()
        
        self.txtBrowserResult.append(f"\n\n[데이터 분석 요청]: {prompt[:100]}...\n[fox]: 📊 데이터 분석을 수행하는 중...")
        QApplication.processEvents()

        try:
            system_instruction = "당신은 데이터 분석 전문가입니다. 주어진 데이터를 분석하고 사용자의 질문에 답변하세요. 통계적 사실은 굵은 글씨로 강조하세요."
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system_instruction)
            )
            final_analysis = response.text.strip()
            
            self.db_handler.save_chat_entry(f"[데이터 분석 요청] {prompt[:100]}...", f"[데이터 분석 응답] {final_analysis[:100]}...") 

            updated_log = self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0] + f"\n[fox]: ✅ **데이터 분석 결과**\n{final_analysis}"
            self.txtBrowserResult.setText(updated_log)
        except Exception as e:
            error_message = f"데이터 분석 API 호출 중 오류 발생: {type(e).__name__}"
            self.txtBrowserResult.setText(self.txtBrowserResult.toPlainText().rsplit('\n', 1)[0] + f"\n[Error]: {error_message}")


# ----------------------------------------------------------------------
# 8. 애플리케이션 실행 진입점 (Entry Point)
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # 🚨 이 부분을 활성화해야 PyQt5 창이 뜨고 실행이 유지됩니다.
    app = QApplication(sys.argv)
    window = GeminiChatApp()
    window.show()
    sys.exit(app.exec_())
