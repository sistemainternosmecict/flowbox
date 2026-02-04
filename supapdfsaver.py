import os
import re
import requests
import img2pdf
import mimetypes
import pypandoc
from pathlib import Path
from PIL import Image
from supabase import create_client, Client
from dotenv import load_dotenv
import subprocess

load_dotenv()

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_SERVICE_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
RANGE = os.getenv("RANGE")


class SupabaseImageUploader:
    creds = None

    def __init__(self, supabase_client):
        self.supabase: Client = supabase_client

    def get_filename_from_response(self, response) -> str:
        content_disposition = response.headers.get('Content-Disposition', '')
        if content_disposition:
            matches = re.findall(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\n]+)["\']?', content_disposition)
            if matches:
                return matches[0]

        return None

    def get_extension_from_mime(self, mime_type: str) -> str:
        mime_to_ext = {
            'application/pdf': '.pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/msword': '.doc',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
            'image/webp': '.webp',
            'text/plain': '.txt',
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.ms-powerpoint': '.ppt',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        }

        return mime_to_ext.get(mime_type, '')

    def download_from_google_drive(self, drive_file_id: str, output_path: str = None, credentials_path: str = 'credentials.json') -> str:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
        import io

        SCOPES = ['https://www.googleapis.com/auth/drive']
        token_path = 'token.json'

        if os.path.exists(token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception as e:
                print(f"Erro ao ler token existente, será necessário reautenticar: {e}")
                self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except:
                    os.remove(token_path)
                    self.creds = None

            if not self.creds:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open(token_path, 'w') as token:
                token.write(self.creds.to_json())

        service = build('drive', 'v3', credentials=self.creds)

        file_metadata = service.files().get(fileId=drive_file_id, fields='name,mimeType').execute()
        original_filename = file_metadata['name']
        mime_type = file_metadata['mimeType']

        if output_path is None:
            output_path = f"temp_{original_filename}"
        else:
            if not Path(output_path).suffix and Path(original_filename).suffix:
                output_path = output_path + Path(original_filename).suffix

        request = service.files().get_media(fileId=drive_file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download {int(status.progress() * 100)}%")

        with open(output_path, 'wb') as f:
            f.write(fh.getvalue())

        print(f"📄 Nome original: {original_filename}")
        print(f"📄 MIME Type: {mime_type}")
        print(f"💾 Salvo como: {output_path}")

        return output_path

    def upload_to_supabase(
        self, 
        file_path: str, 
        bucket_name: str, 
        destination_path: str = None,
        make_public: bool = False
    ) -> dict:
        if destination_path is None:
            destination_path = Path(file_path).name

        if not destination_path.lower().endswith('.pdf'):
            destination_path = str(Path(destination_path).with_suffix('.pdf'))
        
        if file_path.lower().endswith(".docx"):
            pdf_path = f"{Path(file_path).stem}.pdf"
            # docx_convert(file_path, pdf_path)
            try:
                subprocess.run(["pandoc", "-f", "docx", "-t", "pdf", file_path, "-o", pdf_path])
            except subprocess.CalledProcessError as e:
                print(f"Erro ao converter o arquivo: {e}")
            file_path = pdf_path

        mime_type = 'application/pdf'

        with open(file_path, 'rb') as f:
            file_data = f.read()

        response = self.supabase.storage.from_(bucket_name).upload(
            path=destination_path,
            file=file_data,
            file_options={
                "content-type": mime_type,
                "upsert": "true"
            }
        )

        return response

    def get_public_url(self, bucket_name: str, file_path: str) -> str:
        return self.supabase.storage.from_(bucket_name).get_public_url(file_path)
    



if __name__ == "__main__":
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    uploader = SupabaseImageUploader(supabase)

    exemplos = [
        {
            "drive_id": "1C6j2RnGD6b5ZMAG4TaTCC2aHvfWDeEfB",
            "destination": "documento.pdf"
        }
    ]

    bucket = "tasks-files"

    for exemplo in exemplos:
        print(f"\n⬇️ Baixando arquivo do Drive ID: {exemplo['drive_id']}")
        local_path = uploader.download_from_google_drive(
            drive_file_id=exemplo['drive_id'],
            output_path=exemplo['destination']
        )

        print(f"\n⬆️ Enviando arquivo para Supabase: {local_path}")
        upload_response = uploader.upload_to_supabase(
            file_path=local_path,
            bucket_name=bucket,
            destination_path=exemplo['destination'],
            make_public=True
        )
        print("Resposta do upload:", upload_response)
        public_url = uploader.get_public_url(
            bucket_name=bucket,
            file_path=exemplo['destination']
        )
        print("URL pública do arquivo:", public_url)
        os.remove(local_path)