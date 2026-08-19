from email.header import decode_header
from email.utils import parsedate_to_datetime
import os, tempfile, json, time, imaplib, email, logging
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from document_processor import analisar_documento_com_gemini as processar_documento
import stats_tracker

load_dotenv()


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
        num_str = num.decode("utf-8") if isinstance(num, bytes) else str(num) if num else ""
        message_id = ""
        if hasattr(email_msg, "get"):
            header_val = str(email_msg.get("Message-ID") or "")
            from_val = str(email_msg.get("From") or "")
            if header_val and header_val != from_val and "@" in header_val:
                message_id = header_val.strip("<>")
        if not message_id:
            message_id = num_str

        body = ""
        if hasattr(email_msg, "is_multipart") and email_msg.is_multipart():
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

    def marcar_como_nao_lido(self, num: str = None, message_id: str = None) -> bool:
        r"""
        Remove a flag \Seen do e-mail no servidor IMAP para que ele volte ao status de NÃO LIDO.
        Pode receber o número da mensagem (num) ou o Message-ID.
        """
        if not self.email_user or not self.email_pass:
            return False
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_pass)
            mail.select("inbox")

            marcado = False
            if num:
                status, _ = mail.store(str(num), "-FLAGS", "\\Seen")
                if status == "OK":
                    marcado = True
            elif message_id:
                status, data = mail.search(None, f'HEADER Message-ID "<{message_id}>"')
                if (status != "OK" or not data[0]) and "@" in message_id:
                    status, data = mail.search(None, f'HEADER Message-ID "{message_id}"')
                if status == "OK" and data[0]:
                    for msg_num in data[0].split():
                        mail.store(msg_num, "-FLAGS", "\\Seen")
                    marcado = True

            mail.logout()
            if marcado:
                print(f"E-mail {num or message_id} marcado como NÃO LIDO com sucesso no IMAP.")
            return marcado
        except Exception as e:
            print(f"Erro ao remarcar e-mail {num or message_id} como não lido no IMAP: {e}")
            return False

    def buscar_emails_nao_lidos(self) -> list:
        if not self.email_user or not self.email_pass:
            return []

        emails_data = []
        try:
            print(f"Conectando ao servidor {self.imap_server}...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_pass)
            mail.select("inbox")

            status, messages = mail.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                print("Nenhum e-mail não lido encontrado.")
                mail.logout()
                return []

            msg_ids = messages[0].split()
            print(f"Total de e-mails não lidos: {len(msg_ids)}")

            for num in msg_ids:
                num_str = num.decode("utf-8") if isinstance(num, bytes) else str(num)
                status, data = mail.fetch(num, "(RFC822)")
                if status != "OK":
                    continue

                res, msg = data[0]
                if not isinstance(msg, bytes):
                    continue

                sucesso_email = True
                motivo_falha = ""

                try:
                    email_msg = email.message_from_bytes(msg)
                    subject_header = email_msg.get("Subject", "")
                    decoded_parts = decode_header(subject_header)
                    subject, encoding = decoded_parts[0] if decoded_parts else ("", None)
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                    from_ = email_msg.get("From")
                    email_date_raw = email_msg.get("Date")
                    email_date = email_date_raw
                    try:
                        dt = parsedate_to_datetime(email_date_raw)
                        email_date = dt.strftime("%d/%m/%Y")
                    except Exception:
                        pass

                    email_id, sender_email = self.obter_id_original_email(email_msg, num)
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
                                    decoded_header_res = decode_header(filename)
                                    decoded_filename, encoding = decoded_header_res[0] if decoded_header_res else (filename, None)
                                    if isinstance(decoded_filename, bytes):
                                        filename = decoded_filename.decode(
                                            encoding if encoding else "utf-8", errors="ignore"
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
                                            # Falha na análise do anexo pelo Gemini
                                            sucesso_email = False
                                            motivo_falha = f"Falha na análise Gemini do anexo '{filename}'"
                                            if os.path.exists(tmp_path):
                                                os.unlink(tmp_path)
                                            break
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

                    if not sucesso_email:
                        # Remarcar como não lido no IMAP imediatamente
                        print(f"Aviso: {motivo_falha}. Remarcando e-mail {num_str} ({subject}) como NÃO LIDO...")
                        mail.store(num, "-FLAGS", "\\Seen")
                        stats_tracker.registrar_falha(email_id, motivo_falha)
                        continue

                    email_entry = {
                        "subject": subject,
                        "from": from_,
                        "date": email_msg.get("Date"),
                        "body": body.strip(),
                        "has_attachment": len(attachments_info) > 0,
                        "attachments": attachments_info,
                        "imap_num": num_str,
                    }
                    email_entry = self.inserir_id_na_resposta(
                        email_entry, email_id, sender_email
                    )
                    emails_data.append(email_entry)

                except Exception as e:
                    print(f"Erro ao processar e-mail {num_str}: {e}. Remarcando como NÃO LIDO...")
                    mail.store(num, "-FLAGS", "\\Seen")
                    stats_tracker.registrar_falha(str(num_str), f"Erro no parsing: {e}")
                    continue

            mail.logout()
        except Exception as e:
            print(f"Erro ao acessar e-mail: {e}")
        return emails_data
