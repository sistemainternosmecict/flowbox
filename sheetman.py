from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

# Escopo apenas de leitura
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def ler_planilha(spreadsheet_id, range_name):
    creds = None

    # Se já tiver token salvo, reutiliza
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # Se não tiver ou estiver inválido, faz login
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES
        )
        #creds = flow.run_console()

        # Salva o token para próximas execuções
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)

    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    values = result.get('values', [])

    if not values:
        print('Nenhum dado encontrado.')
        return []

    return values
