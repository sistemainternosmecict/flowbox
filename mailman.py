import imaplib
import email
from email.header import decode_header
import os
from dotenv import load_dotenv

load_dotenv()

class Mailman:
    def __init__(self):
        self.email_user = os.getenv("EMAIL_USER")
        self.email_pass = os.getenv("EMAIL_PASS")
        self.imap_server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
        
        if not self.email_user or not self.email_pass:
            print("Aviso: Credenciais de e-mail não configuradas no .env")
            
    def buscar_emails_nao_lidos(self) -> list:
        if not self.email_user or not self.email_pass:
            return []

        emails_data = []
        try:
            # Conecta ao servidor IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_pass)
            mail.select("inbox")

            # Busca por e-mails não lidos (UNSEEN)
            status, messages = mail.search(None, 'UNSEEN')
            if status != 'OK':
                return []

            for num in messages[0].split():
                status, data = mail.fetch(num, '(RFC822)')
                if status != 'OK':
                    continue

                res, msg = data[0]
                if isinstance(msg, bytes):
                    email_msg = email.message_from_bytes(msg)
                    
                    # Decodifica o assunto
                    subject, encoding = decode_header(email_msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    # Decodifica o remetente
                    from_ = email_msg.get("From")
                    
                    emails_data.append({
                        "subject": subject,
                        "from": from_,
                        "date": email_msg.get("Date"),
                        "id": num.decode()
                    })

            mail.logout()
        except Exception as e:
            print(f"Erro ao acessar e-mail: {e}")
            
        return emails_data
