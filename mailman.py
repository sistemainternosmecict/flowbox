from email.header import decode_header
from email.utils import parsedate_to_datetime
import os, tempfile, json, time, imaplib, email, logging
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from document_processor import analisar_documento_com_gemini as processar_documento

load_dotenv()
meter = metrics.get_meter(__name__)
# 1. Contador para Documentos Processados
doc_counter = meter.create_counter(
    name="documentos_processados_total",
    description="Total de documentos processados pelo mailman",
    unit="1"
)

# 2. Contador de Requisições Feitas ao Gemini
gemini_requests_counter = meter.create_counter(
    name="gemini_requisicoes_total",
    description="Total de chamadas feitas à API do Gemini",
    unit="1"
)

# 3. Contador de Tokens Consumidos
gemini_tokens_counter = meter.create_counter(
    name="gemini_tokens_consumidos_total",
    description="Total de tokens consumidos no Gemini (Prompt e Resposta)",
    unit="1"
)


class Mailman:
    def __init__(self):
        self.email_user = os.getenv("EMAIL_USER")
        self.email_pass = os.getenv("EMAIL_PASS")
        self.imap_server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.model_name = "gemini-3-flash-preview"
        if not self.email_user or not self.email_pass:
            print("Aviso: Credenciais de e-mail não configuradas no .env")
        if self.gemini_key:
            self.client = genai.Client(api_key=self.gemini_key)
        else:
            print("Aviso: GEMINI_API_KEY não configurada no .env")

    def analisar_documento_com_gemini(self, file_path, mime_type=None):
        return processar_documento(
            file_path=file_path,
            mime_type=mime_type,
            api_key=self.gemini_key,
            model_name=self.model_name
        )

    def obter_id_original_email(self, email_msg, num):
        message_id = email_msg.get("Message-ID", "")
        body = ""
        if email_msg.is_multipart():
            for part in email_msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="ignore")
                        break
                    except Exception:
                        continue
        else:
            try:
                payload = email_msg.get_payload(decode=True)
                charset = email_msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="ignore")
            except Exception:
                pass

        import re

        all_emails = re.findall(
            r"[a-zA-Z0-9._%+-]+@smec\.saquarema\.rj\.gov\.br", body, re.IGNORECASE
        )
        sender_email = None
        for email_found in all_emails:
            email_lower = email_found.lower()
            if (
                "subsec.tecnologia" not in email_lower
                and "corporativo" not in email_lower
            ):
                sender_email = email_found
                break
        if not sender_email:
            from_header = email_msg.get("From", "")
            match_from = re.search(r"<(.*?)>", from_header)
            sender_email = match_from.group(1) if match_from else from_header
        return message_id.strip("<>"), sender_email

    def inserir_id_na_resposta(self, email_data, email_id, sender_email):
        email_data["id"] = email_id
        email_data["sender_email"] = sender_email
        return email_data

    def buscar_emails_nao_lidos(self) -> list:
        if not self.email_user or not self.email_pass:
            return []

        emails_data = []
        try:
            print(f"Conectando ao servidor {self.imap_server}...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_pass)
            mail.select("inbox")
            
            with tracer.start_as_current_span("buscar_emails_nao_lidos") as span:
                status, messages = mail.search(None, 'UNSEEN')
                if status != 'OK' or not messages[0]:
                    print("Nenhum e-mail não lido encontrado.")
                    mail.logout()
                    return []

            status, messages = mail.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                print("Nenhum e-mail não lido encontrado.")
                mail.logout()
                return []

            msg_ids = messages[0].split()
            print(f"Total de e-mails não lidos: {len(msg_ids)}")

            for num in msg_ids:
                status, data = mail.fetch(num, "(RFC822)")
                if status != "OK":
                    continue

                res, msg = data[0]
                if isinstance(msg, bytes):
                    email_msg = email.message_from_bytes(msg)
                    subject, encoding = decode_header(email_msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    from_ = email_msg.get("From")
                    email_date_raw = email_msg.get("Date")
                    email_date = email_date_raw
                    try:
                        dt = parsedate_to_datetime(email_date_raw)
                        email_date = dt.strftime("%d/%m/%Y")
                    except Exception:
                        pass
                    body = ""
                    attachments_info = []
                    if email_msg.is_multipart():
                        for part in email_msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if (
                                content_type == "text/plain"
                                and "attachment" not in content_disposition
                            ):
                                try:
                                    payload = part.get_payload(decode=True)
                                    charset = part.get_content_charset() or "utf-8"
                                    body = payload.decode(charset, errors="ignore")
                                except Exception:
                                    pass
                            elif "attachment" in content_disposition:
                                filename = part.get_filename()
                                if filename:
                                    decoded_filename, encoding = decode_header(
                                        filename
                                    )[0]
                                    if isinstance(decoded_filename, bytes):
                                        filename = decoded_filename.decode(
                                            encoding if encoding else "utf-8"
                                        )
                                    if filename.lower().endswith(
                                        (".pdf", ".png", ".jpg", ".jpeg", ".docx")
                                    ):
                                        with tempfile.NamedTemporaryFile(
                                            delete=False,
                                            suffix=os.path.splitext(filename)[1],
                                        ) as tmp:
                                            tmp.write(part.get_payload(decode=True))
                                            tmp_path = tmp.name
                                        analise = self.analisar_documento_com_gemini(
                                            tmp_path, content_type
                                        )
                                        if isinstance(analise, dict):
                                            analise["data_entrada"] = email_date
                                        attachments_info.append(
                                            {
                                                "filename": filename,
                                                "analysis": analise,
                                                "temp_path": tmp_path,
                                            }
                                        )
                                    else:
                                        attachments_info.append(
                                            {
                                                "filename": filename,
                                                "analysis": "Tipo de arquivo não suportado para análise automática",
                                            }
                                        )

                    else:
                        try:
                            payload = email_msg.get_payload(decode=True)
                            charset = email_msg.get_content_charset() or "utf-8"
                            body = payload.decode(charset, errors="ignore")
                        except Exception:
                            pass

                    email_entry = {
                        "subject": subject,
                        "from": from_,
                        "date": email_msg.get("Date"),
                        "body": body.strip(),
                        "has_attachment": len(attachments_info) > 0,
                        "attachments": attachments_info,
                    }
                    email_id, sender_email = self.obter_id_original_email(
                        email_msg, num
                    )
                    email_entry = self.inserir_id_na_resposta(
                        email_entry, email_id, sender_email
                    )

                    emails_data.append(email_entry)

            mail.logout()
        except Exception as e:
            print(f"Erro ao acessar e-mail: {e}")
        return emails_data
