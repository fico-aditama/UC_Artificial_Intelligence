import streamlit as st
import requests
import json
import subprocess
import platform
import logging
from typing import Tuple, Optional

class OllamaConnection:
    def __init__(self):
        self.base_url = "http://localhost:11434"
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def check_ollama_installation(self) -> bool:
        """Check if Ollama is installed on the system"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(['where', 'ollama'], capture_output=True, text=True)
            else:
                result = subprocess.run(['which', 'ollama'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error checking Ollama installation: {e}")
            return False

    def check_model_availability(self) -> bool:
        """Check if Mistral model is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(model.get('name') == 'mistral' for model in models)
            return False
        except requests.exceptions.RequestException:
            return False

    def test_connection(self) -> Tuple[bool, str]:
        """Test connection to Ollama server"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                return True, "Koneksi ke Ollama berhasil"
            return False, f"Error status code: {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Tidak dapat terhubung ke server Ollama"
        except Exception as e:
            return False, f"Error tidak terduga: {str(e)}"

    def get_response(self, prompt: str, system_prompt: str = "", context: str = "") -> Tuple[bool, str]:
        """Get response from Ollama with better error handling"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    'model': 'mistral',
                    'prompt': prompt,
                    'system': system_prompt,
                    'context': context,
                    'stream': False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return True, response.json()['response']
            elif response.status_code == 404:
                return False, "Model Mistral tidak ditemukan. Jalankan 'ollama pull mistral' terlebih dahulu."
            elif response.status_code == 400:
                return False, "Request tidak valid. Pastikan format prompt benar."
            else:
                return False, f"Error dari server Ollama (Status: {response.status_code})"
                
        except requests.exceptions.Timeout:
            return False, "Timeout - Server terlalu lama merespon"
        except requests.exceptions.ConnectionError:
            return False, "Tidak dapat terhubung ke server Ollama. Pastikan Ollama sedang berjalan."
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return False, f"Error tidak terduga: {str(e)}"

def setup_ollama_diagnostic():
    """Setup diagnostic information in Streamlit sidebar"""
    st.sidebar.title("Diagnostik Ollama")
    
    ollama = OllamaConnection()
    
    # Check Ollama installation
    is_installed = ollama.check_ollama_installation()
    st.sidebar.write("Status Instalasi:", 
                     "✅ Terinstall" if is_installed else "❌ Tidak terinstall")
    
    # Check server connection
    is_connected, conn_message = ollama.test_connection()
    st.sidebar.write("Status Server:", 
                     "✅ Terhubung" if is_connected else "❌ Tidak terhubung")
    
    # Check model availability
    if is_connected:
        has_model = ollama.check_model_availability()
        st.sidebar.write("Model Mistral:", 
                        "✅ Tersedia" if has_model else "❌ Tidak tersedia")
    
    # Show troubleshooting steps if there are issues
    if not is_installed or not is_connected or (is_connected and not has_model):
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Langkah Perbaikan:")
        if not is_installed:
            st.sidebar.markdown("""
            1. Install Ollama:
            ```bash
            curl https://ollama.ai/install.sh | sh
            ```
            """)
        if not is_connected:
            st.sidebar.markdown("""
            2. Jalankan server Ollama:
            ```bash
            ollama serve
            ```
            """)
        if is_connected and not has_model:
            st.sidebar.markdown("""
            3. Download model Mistral:
            ```bash
            ollama pull mistral
            ```
            """)

    return ollama