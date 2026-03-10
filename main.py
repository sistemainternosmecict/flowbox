import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from supabase import create_client

from sheetman import ler_planilha
from supapdfsaver import SupabaseImageUploader

load_dotenv()

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_SERVICE_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
RANGE = os.getenv("RANGE")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Variáveis de ambiente do Supabase não configuradas")

<<<<<<< HEAD
=======
# Cria cliente
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Cliente Supabase criado com sucesso")

# Lê dados da planilha Google Sheets
>>>>>>> drive_to_supabase
if not SPREADSHEET_ID or not RANGE:
    raise RuntimeError("Variáveis de ambiente da planilha não configuradas")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Cliente Supabase criado com sucesso")

sheet_data = ler_planilha(SPREADSHEET_ID, RANGE)

for row in sheet_data:
    id = uuid.uuid4()
    unidade = row[2]
    pedido = row[3]
    title = f"[{row[0]}]{pedido}_{unidade}"
    desc = row[7]
    url = row[8]
    drive_file_id = url.split("/")[-2]
<<<<<<< HEAD
    
    supabase_image_uploader = SupabaseImageUploader(supabase)
    downloaded_file_path = supabase_image_uploader.download_from_google_drive(drive_file_id)
    print(f"Arquivo baixado para: {downloaded_file_path}")

    # pdf_path = supabase_image_uploader.convert_to_pdf(downloaded_file_path)
    # print(f"Arquivo convertido para: {pdf_path}")

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
    
    os.remove(downloaded_file_path)

=======
>>>>>>> drive_to_supabase
    dt = datetime.strptime(row[1], "%d/%m/%Y")
    dt = dt.replace(tzinfo=timezone.utc)
    data_iso = dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    data_exist = (
        supabase
        .table("tasks")
        .select("*")
        .eq("created_at", str(data_iso))
        .eq("title", title)
        .execute()
    )

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
            "file_url": drive_file_id,
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
