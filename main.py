import os
from supabase import create_client
from sample import Sampledata
from sheetman import ler_planilha
from datetime import datetime, timezone
import uuid
import requests
from supapdfsaver import SupabaseImageUploader
from pathlib import Path

from dotenv import load_dotenv
# Carrega variáveis do .env
load_dotenv()

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_SERVICE_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
RANGE = os.getenv("RANGE")


if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Variáveis de ambiente do Supabase não configuradas")

# dados de exemplo
# sample_data = Sampledata().get_sample()
# print("Dados de exemplo obtidos:", sample_data)

# Cria cliente
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Cliente Supabase criado com sucesso")

# Exemplo de consulta simples
# data = supabase.table("tasks").select("*").execute()

# inserção de dados de exemplo na tabela "tasks"
# print("Resposta da inserção:", insert_response)

# insere um log de exemplo na tabela "logs"
# sample_log = Sampledata().get_sample_log()
# print("Resposta da inserção do log:", insert_log_response)

# Lê dados da planilha Google Sheets
if not SPREADSHEET_ID or not RANGE:
    raise RuntimeError("Variáveis de ambiente da planilha não configuradas")

sheet_data = ler_planilha(SPREADSHEET_ID, RANGE)


# row = sheet_data[-1]  # Pega uma linha específica da planilha

for row in sheet_data:
    id = uuid.uuid4()
    pedido = row[3]
    unidade = row[2]
    title = f"[{row[0]}]{pedido}_{unidade}"  # Pega a última linha lida
    desc = row[7]
    url = row[8]
    drive_file_id = url.split("/")[-2]
    
    supabase_image_uploader = SupabaseImageUploader(supabase)
    downloaded_file_path = supabase_image_uploader.download_from_google_drive(drive_file_id)
    print(f"Arquivo baixado para: {downloaded_file_path}")

    print(f"\n⬆️ Enviando arquivo para Supabase: {downloaded_file_path}")
    upload_response = supabase_image_uploader.upload_to_supabase(
        file_path=downloaded_file_path,
        bucket_name="tasks-files",
        destination_path=f"{id}.pdf",
        make_public=True
    )
    print("Resposta do upload:", upload_response)
    public_url = supabase_image_uploader.get_public_url(
        bucket_name="tasks-files",
        file_path=f"{id}.pdf"
    )
    print("URL pública do arquivo:", public_url)
    # Remove o arquivo temporário baixado
    os.remove(downloaded_file_path)

    dt = datetime.strptime(row[1], "%d/%m/%Y")
    dt = dt.replace(tzinfo=timezone.utc)
    data_iso = dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    # Verifica se a tarefa já existe no Supabase
    data_exist = (
        supabase
        .table("tasks")
        .select("*")
        .eq("created_at", str(data_iso))
        .eq("title", title)
        .execute()
    )

    # Se não existir, insere a nova tarefa e o log associado
    if not data_exist.data:
        print("Inserindo nova tarefa e log...")
        data_to_insert = {
            "assignee": None,
            "board_id": None,
            "completed_at": None,
            "created_at": str(data_iso),
            "description": f"{unidade}/ {desc} - [Tarefa criada automaticamente]",
            "duedate": None,
            "external_ref": None,
            "file_url": public_url,
            "id": str(id),
            "priority": "Média",
            "raw_metadata": None,
            "source": None,
            "status": "Pendentes",
            "title": title,
            "updated_at": None,
            "user_id": None,
        }

        log_to_insert = {
            "action": "create_task",
            "created_at": str(data_iso),
            "details": f"Tarefa vinda da planilha do cpd: {{'id': {str(id)}}} gerada automaticamente.",
            "metadata": None,
            "user_id": None,
        }

        insert_response = supabase.table("tasks").insert(data_to_insert).execute()
        insert_log_response = supabase.table("user_logs").insert(log_to_insert).execute()