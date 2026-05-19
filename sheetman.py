from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

load_dotenv()

class Sheetman:
    spreadsheet_id:str
    cells_range:str
    google_scopes:list
    token_path:str
    credentials_path:str

    def __init__(self):
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
        self.cells_range = os.getenv("RANGE")
        if not self.spreadsheet_id or not self.cells_range:
            raise RuntimeError("Variáveis de ambiente da planilha não configuradas")

        self.google_scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive'
        ]
        self.token_path = 'token.json'
        self.credentials_path = 'credentials.json'

    def ler_planilha(self):
        creds = None

        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.google_scopes)
            except Exception as e:
                print(f"Erro ao ler token existente: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Erro ao refresh token: {e}")
                    creds = None

            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.google_scopes
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        service = build('sheets', 'v4', credentials=creds)

        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=self.cells_range
        ).execute()

        values = result.get('values', [])

        if not values:
            print('Nenhum dado encontrado.')
            return []

        return values
