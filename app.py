import streamlit as st
import requests
import json
import subprocess
import time
import logging
from typing import Tuple
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('chatbot.log')]
)
logger = logging.getLogger(__name__)

class OllamaServiceHandler:
    """Handles Ollama service status, restart, and validation."""

    def __init__(self):
        self.systemd_available = self._check_systemd()
        self.base_url = 'http://localhost:11434'
        self.session = self._create_retry_session()
        
    def _check_systemd(self) -> bool:
        """Check if the system is using systemd."""
        try:
            return subprocess.run(['systemctl', '--version'], capture_output=True).returncode == 0
        except FileNotFoundError:
            return False

    def _create_retry_session(self):
        """Create a requests session with retry logic."""
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def restart_ollama(self) -> Tuple[bool, str]:
        """Restart the Ollama service."""
        try:
            if self.systemd_available:
                subprocess.run(['sudo', 'systemctl', 'restart', 'ollama'], check=True, capture_output=True)
            else:
                subprocess.run(['sudo', 'pkill', 'ollama'], check=False, capture_output=True)
                time.sleep(2)
                subprocess.Popen(['ollama', 'serve'])
            time.sleep(10)  # Increased wait time after restart
            return True, "Service restarted successfully"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to restart service: {e.stderr.decode() if e.stderr else str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def check_service_status(self) -> Tuple[bool, str]:
        """Check if the Ollama service is running."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                return True, "Service is running"
            return False, "Service is not responding"
        except requests.exceptions.RequestException as e:
            logger.error(f"Service status check failed: {str(e)}")
            return False, "Service is not running"

    def validate_model(self) -> Tuple[bool, str]:
        """Validate if the Mistral model is available and functioning."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={'model': 'mistral', 'prompt': 'test', 'stream': False},
                timeout=15
            )
            if response.status_code == 200:
                return True, "Model is working"
            elif response.status_code == 404:
                return False, "Model not found"
            else:
                return False, f"Model validation failed: {response.status_code}"
        except Exception as e:
            logger.error(f"Model validation error: {str(e)}")
            return False, f"Model validation error: {str(e)}"

class ChatbotApp:
    """Main Chatbot application using Streamlit."""

    def __init__(self):
        st.set_page_config(page_title="ChatGPT Lokal dengan Ollama", page_icon="🤖", layout="wide")
        self.service_handler = OllamaServiceHandler()
        self.initialize_session_state()

    def initialize_session_state(self):
        """Initialize session state variables."""
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'error_count' not in st.session_state:
            st.session_state.error_count = 0
        if 'temperature' not in st.session_state:
            st.session_state.temperature = 0.7
        if 'top_p' not in st.session_state:
            st.session_state.top_p = 0.9

    def get_ollama_response(self, prompt: str, system_prompt: str = "", context: str = "") -> str:
        """Get response from the Ollama API."""
        start_time = time.time()

        # Validate service and model
        service_ok, service_msg = self.service_handler.check_service_status()
        if not service_ok:
            logger.error(f"Service validation failed: {service_msg}")
            return f"Error: {service_msg}"

        model_ok, model_msg = self.service_handler.validate_model()
        if not model_ok:
            logger.error(f"Model validation failed: {model_msg}")
            return f"Error: {model_msg}"

        try:
            payload = {
                'model': 'mistral',
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': st.session_state.temperature,
                    'top_p': st.session_state.top_p,
                }
            }
            if system_prompt:
                payload['system'] = system_prompt
            if context:
                payload['context'] = context

            response = self.service_handler.session.post(f'{self.service_handler.base_url}/api/generate', json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()['response']
            elif response.status_code == 400:
                return f"Error: {response.json().get('error', 'Invalid request')}"
            else:
                return f"Error: Unexpected response (status code: {response.status_code})"
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return "Error: Connection failed"
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Response time: {elapsed_time:.2f}s")

    def render_sidebar(self) -> str:
        """Render the sidebar with settings."""
        with st.sidebar:
            st.title("Pengaturan")
            service_ok, service_msg = self.service_handler.check_service_status()
            model_ok, model_msg = self.service_handler.validate_model()

            st.subheader("Status Sistem")
            if service_ok and model_ok:
                st.success("✅ Sistem siap")
            else:
                st.error(f"❌ Status: {service_msg}")
                if st.button("Restart Service"):
                    success, msg = self.service_handler.restart_ollama()
                    if success:
                        st.success("Service berhasil di-restart!")
                        time.sleep(5)  # Give some time for the service to fully start
                        st.experimental_rerun()
                    else:
                        st.error(msg)

            st.subheader("Parameter Model")
            st.session_state.temperature = st.slider(
                "Temperature", 0.0, 1.0, st.session_state.temperature, 0.1,
                help="Mengontrol kreativitas output (0=konsisten, 1=kreatif)"
            )
            st.session_state.top_p = st.slider(
                "Top P", 0.0, 1.0, st.session_state.top_p, 0.1, help="Nucleus sampling probability"
            )
            system_prompt = st.text_area(
                "System Prompt",
                value="Kamu adalah asisten AI yang helpful dan jujur. Berikan jawaban yang singkat dan jelas."
            )

            st.subheader("Riwayat Chat")
            if st.button("Bersihkan Riwayat"):
                st.session_state.messages = []
                st.experimental_rerun()

            return system_prompt

    def run(self):
        """Main application loop."""
        system_prompt = self.render_sidebar()

        st.title("💬 ChatGPT Lokal dengan Ollama")
        st.markdown("Chatbot ini menggunakan model Mistral yang berjalan secara lokal melalui Ollama.")

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ketik pesan Anda di sini..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.spinner("Menghasilkan respons..."):
                response = self.get_ollama_response(prompt, system_prompt)
            if response.startswith("Error:"):
                st.error(response)
                st.session_state.error_count += 1
                if st.session_state.error_count >= 3:
                    st.warning("Terjadi beberapa kesalahan berturut-turut. Mohon periksa koneksi Anda atau coba restart layanan.")
            else:
                st.session_state.messages.append({"role": "assistant", "content": response})
                with st.chat_message("assistant"):
                    st.markdown(response)
                st.session_state.error_count = 0  # Reset error count on successful response

        st.markdown("---")
        st.markdown("Dibuat dengan Streamlit dan Ollama")

if __name__ == "__main__":
    app = ChatbotApp()
    app.run()