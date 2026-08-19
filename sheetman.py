from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv
import os

load_dotenv()


class Sheetman:
    spreadsheet_id: str
    cells_range: str
    google_scopes: list
    token_path: str
    credentials_path: str
    drive_folder_id: str

    def __init__(self):
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
        self.cells_range = os.getenv("RANGE")
        self.drive_folder_id = os.getenv("DRIVE_FOLDER_ID")

        if not self.spreadsheet_id or not self.cells_range:
            raise RuntimeError("Variáveis de ambiente da planilha não configuradas")

        self.google_scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        self.token_path = "token.json"
        self.credentials_path = "credentials.json"

    def obter_credenciais(self):
        creds = None
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(
                    self.token_path, self.google_scopes
                )
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

            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
        return creds

    def ler_planilha(self):
        creds = self.obter_credenciais()
        service = build("sheets", "v4", credentials=creds)

        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=self.spreadsheet_id, range=self.cells_range)
            .execute()
        )

        values = result.get("values", [])
        if not values:
            print("Nenhum dado encontrado.")
            return []
        return values

    def upload_para_drive(self, file_path, filename):
        """Faz upload de um arquivo para a pasta configurada no Drive e retorna o link."""
        if not self.drive_folder_id:
            print("Aviso: DRIVE_FOLDER_ID não configurado.")
            return None

        creds = self.obter_credenciais()
        service = build("drive", "v3", credentials=creds)

        file_metadata = {"name": filename, "parents": [self.drive_folder_id]}
        media = MediaFileUpload(file_path, resumable=True)

        try:
            file = (
                service.files()
                .create(body=file_metadata, media_body=media, fields="id, webViewLink")
                .execute()
            )
            print(f"Arquivo enviado para o Drive. ID: {file.get('id')}")
            return file.get("webViewLink")
        except Exception as e:
            print(f"Erro ao fazer upload para o Drive: {e}")
            return None

    def inserir_novo_registro(
        self, n_oficio, data_doc, escola, pedido, data_entrada, resumo, link_arquivo
    ):
        """Insere uma nova linha na planilha com os dados fornecidos."""
        creds = self.obter_credenciais()
        service = build("sheets", "v4", credentials=creds)

        # Colunas: n do oficio, data, escola, pedido, data de entrada, situacao, data de atendimento, resumo, link
        row_data = [
            n_oficio,
            data_doc,
            escola,
            pedido,
            data_entrada,
            "novo oficio",  # situação
            "",  # data de atendimento (vazio)
            resumo,
            link_arquivo,
        ]

        body = {"values": [row_data]}

        try:
            # Pega o nome da aba a partir do range (ex: 'Página1!A1' -> 'Página1')
            sheet_name = (
                self.cells_range.split("!")[0] if "!" in self.cells_range else "2026"
            )

            result = (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{sheet_name}!A:I",
                    valueInputOption="RAW",
                    body=body,
                )
                .execute()
            )

            print(
                f"Nova linha inserida na planilha: {result.get('updates').get('updatedRange')}"
            )
            return True
        except Exception as e:
            print(f"Erro ao inserir linha na planilha: {e}")
            return False
