import imaplib
import email
from email.header import decode_header
import os
import tempfile
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class Mailman:
    def __init__(self):
        self.email_user = os.getenv("EMAIL_USER")
        self.email_pass = os.getenv("EMAIL_PASS")
        self.imap_server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        
        if not self.email_user or not self.email_pass:
            print("Aviso: Credenciais de e-mail não configuradas no .env")
        
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel('gemini-3-flash-preview')
        else:
            print("Aviso: GEMINI_API_KEY não configurada no .env")

    def analisar_documento_com_gemini(self, file_path, mime_type):
        """Envia o arquivo para o Gemini e retorna o resumo em JSON."""
        if not self.gemini_key:
            return None
            
        try:
            print(f"Enviando {file_path} para análise no Gemini...")
            # Upload do arquivo para a API do Gemini
            uploaded_file = genai.upload_file(file_path, mime_type=mime_type)
            
            # Espera o processamento do arquivo se necessário (geralmente rápido para arquivos pequenos)
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(2)
                uploaded_file = genai.get_file(uploaded_file.name)

            prompt = """
            Analise este documento (ofício) e extraia as seguintes informações em formato JSON puro:
            {
                "numero_oficio": "string",
                "data_documento": "string (data de criação mencionada no documento, formato DD/MM/AAAA)",
                "nome_unidade": "string",
                "assunto": "string",
                "resumo_pedido": "string"
            }
            Retorne apenas o JSON, sem markdown ou explicações.
            """
            
            response = self.model.generate_content([prompt, uploaded_file])
            
            # Limpeza básica da resposta para garantir JSON puro
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response.split("```json")[1].split("```")[0].strip()
            elif text_response.startswith("```"):
                text_response = text_response.split("```")[1].split("```")[0].strip()
                
            return json.loads(text_response)
        except Exception as e:
            print(f"Erro ao analisar com Gemini: {e}")
            return None

    def buscar_emails_nao_lidos(self) -> list:
        if not self.email_user or not self.email_pass:
            return []

        emails_data = []
        try:
            print(f"Conectando ao servidor {self.imap_server}...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_pass)
            mail.select("inbox")

            status, messages = mail.search(None, 'UNSEEN')
            if status != 'OK' or not messages[0]:
                print("Nenhum e-mail não lido encontrado.")
                mail.logout()
                return []

            msg_ids = messages[0].split()
            print(f"Total de e-mails não lidos: {len(msg_ids)}")

            for num in msg_ids:
                status, data = mail.fetch(num, '(RFC822)')
                if status != 'OK':
                    continue

                res, msg = data[0]
                if isinstance(msg, bytes):
                    email_msg = email.message_from_bytes(msg)
                    
                    subject, encoding = decode_header(email_msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    from_ = email_msg.get("From")
                    email_date = email_msg.get("Date")
                    body = ""
                    attachments_info = []
                    
                    if email_msg.is_multipart():
                        for part in email_msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                try:
                                    payload = part.get_payload(decode=True)
                                    charset = part.get_content_charset() or "utf-8"
                                    body = payload.decode(charset, errors="ignore")
                                except Exception:
                                    pass
                            
                            elif "attachment" in content_disposition:
                                filename = part.get_filename()
                                if filename:
                                    decoded_filename, encoding = decode_header(filename)[0]
                                    if isinstance(decoded_filename, bytes):
                                        filename = decoded_filename.decode(encoding if encoding else "utf-8")
                                    
                                    # Processa o anexo se for PDF ou Imagem para o Gemini
                                    if filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                                            tmp.write(part.get_payload(decode=True))
                                            tmp_path = tmp.name
                                        
                                        # Analisa com Gemini
                                        analise = self.analisar_documento_com_gemini(tmp_path, content_type)
                                        
                                        if isinstance(analise, dict):
                                            analise["data_entrada"] = email_date
                                        
                                        attachments_info.append({
                                            "filename": filename,
                                            "analysis": analise,
                                            "temp_path": tmp_path
                                        })
                                        
                                        # O arquivo temporário será removido no main.py após upload para o Drive
                                    else:
                                        attachments_info.append({
                                            "filename": filename,
                                            "analysis": "Tipo de arquivo não suportado para análise automática"
                                        })

                    else:
                        try:
                            payload = email_msg.get_payload(decode=True)
                            charset = email_msg.get_content_charset() or "utf-8"
                            body = payload.decode(charset, errors="ignore")
                        except Exception:
                            pass

                    emails_data.append({
                        "subject": subject,
                        "from": from_,
                        "date": email_msg.get("Date"),
                        "body": body.strip(),
                        "has_attachment": len(attachments_info) > 0,
                        "attachments": attachments_info,
                        "id": num.decode()
                    })

            mail.logout()
        except Exception as e:
            print(f"Erro ao acessar e-mail: {e}")
            
        #print(json.dumps(emails_data, indent=2, ensure_ascii=False))
        return emails_data
