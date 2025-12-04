import sys
import os
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt5.uic import loadUi
from google import genai
from google.genai import types
from dotenv import load_dotenv # 🚨 추가: .env 파일 로드를 위한 라이브러리

# -----------------
# 1. 환경 변수 로드 및 API 키 설정
# -----------------
# .env 파일에서 환경 변수를 로드합니다.
load_dotenv() 

# 환경 변수에서 'GEMINI_API_KEY' 값을 가져옵니다.
API_KEY = os.environ.get("GEMINI_API_KEY") 

# -----------------
# 2. 메인 애플리케이션 클래스 (QDialog 상속)
# -----------------
class GeminiChatApp(QDialog):
    def __init__(self):
        super().__init__()
        
        # UI 파일 로드
        try:
            loadUi("gemini.ui", self) 
        except FileNotFoundError:
            QMessageBox.critical(self, "오류", 
                                 "Error: 'gemini.ui' 파일을 찾을 수 없습니다. "
                                 "파일 경로와 이름을 다시 확인하세요.")
            sys.exit(1)

        # Gemini 클라이언트 및 채팅 세션 초기화
        self.chat = None
        self.client = None
        self.model = 'gemini-2.5-flash'
        self.init_gemini_client()
        
        # UI 요소 연결 및 초기 설정
        self.pushButton.clicked.connect(self.send_question)
        self.lineEdit.returnPressed.connect(self.send_question)
        
        self.apply_circular_mask()
        
        if self.client:
            self.txtBrowserResult.setText("Gemini AI에게 질문을 입력하고 '보내기'를 누르세요.")

    def init_gemini_client(self):
        # API 키가 설정되어 있는지 확인
        if not API_KEY:
            # 키가 없으면 사용자에게 경고를 표시하고 클라이언트 초기화를 중단합니다.
            QMessageBox.critical(self, "API 오류", 
                                 "🚨 오류: 'GEMINI_API_KEY' 환경 변수가 설정되지 않았습니다.\n"
                                 "프로젝트 폴더의 .env 파일을 확인해주세요.")
            self.txtBrowserResult.setText("Gemini API 키 오류. .env 파일을 확인하세요.")
            return
            
        try:
            # 유효한 키로 클라이언트 초기화 시도
            self.client = genai.Client(api_key=API_KEY)
            
            # 대화 이력을 위한 채팅 세션 생성 (모델 지정)
            self.chat = self.client.chats.create(model=self.model)
            
        except Exception as e:
            error_msg = f"Gemini 클라이언트 초기화 중 오류 발생: {e.__class__.__name__}. 키 또는 네트워크를 확인해주세요."
            self.txtBrowserResult.setText(error_msg)
            QMessageBox.critical(self, "초기화 오류", error_msg)
            self.client = None
            self.chat = None

    # -----------------
    # 3. 질문 전송 및 답변 수신 함수 (대화 이력 활용)
    # -----------------
    def send_question(self):
        if not self.chat: 
            self.txtBrowserResult.append("\n\n[Error]: Gemini 서비스가 초기화되지 않았습니다. 키를 확인하세요.")
            return

        question = self.lineEdit.text().strip()
        if not question:
            return

        self.lineEdit.clear()
        
        # 질문 로그 기록 및 GUI 업데이트
        new_entry = f"\n\n[질문]: {question}\n[fox]: 답변을 생성하는 중..."
        self.txtBrowserResult.append(new_entry)
        self.txtBrowserResult.ensureCursorVisible()
        QApplication.processEvents() # GUI 업데이트 멈춤 방지

        try:
            # 채팅 세션을 통해 대화 이력 유지
            response = self.chat.send_message(question)
            
            final_answer = response.text.strip()
            
            # QTextBrowser 내용 업데이트 (대기 메시지 -> 응답으로 대체)
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
    # 4. QLabel 원형 마스크 적용 함수 (유지)
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
# 5. 애플리케이션 실행
# -----------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GeminiChatApp()
    window.show()
    sys.exit(app.exec_())
