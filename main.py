import os, uuid, time
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client
from sheetman import Sheetman
from mailman import Mailman

load_dotenv()

class Flowbox:
    supabase_url: str
    supabase_key: str
    supabase_client: any
    spreadsheet_data: list
    mudancas: list
    emails_nao_lidos: list

    def __init__(self):
        print("""
===============================
              Flowbox iniciado!
===============================
              """)
        self.supabase_url = os.getenv("VITE_SUPABASE_URL")
        self.supabase_key = os.getenv("VITE_SUPABASE_SERVICE_KEY")
        if not self.supabase_url or not self.supabase_key:
            raise RuntimeError("Variáveis de ambiente do Supabase não configuradas")
        self.criar_cliente_supabase()
        self.processar_emails()
        self.carregar_dados_planilha()
        self.mudancas = self.buscar_mudancas()
        self.atualiza_banco()
        print("Flowbox executado com sucesso!")

    def criar_cliente_supabase(self):
        self.supabase_client = create_client(self.supabase_url, self.supabase_key)
        print("Cliente Supabase criado com sucesso!")

    def carregar_dados_planilha(self):
        sm = Sheetman()
        self.spreadsheet_data = sm.ler_planilha()
        print("Leitura da planilha realizada com sucesso!")

    def processar_emails(self):
        mm = Mailman()
        sm = Sheetman()
        self.emails_nao_lidos = mm.buscar_emails_nao_lidos()
        if self.emails_nao_lidos:
            print(f"\nForam encontrados {len(self.emails_nao_lidos)} e-mails não lidos.")
            for email in self.emails_nao_lidos:
                for att in email.get("attachments", []):
                    analysis = att.get("analysis")
                    tmp_path = att.get("temp_path")
                    filename = att.get("filename")

                    if isinstance(analysis, dict) and tmp_path:
                        # Extrai a extensão original
                        ext = os.path.splitext(filename)[1]
                        
                        # Define o novo nome padrão: [numero do oficio] - [nome da unidade]
                        numero_oficio = str(analysis.get("numero_oficio", "S-N")).replace("/", "_")
                        nome_unidade = analysis.get("nome_unidade", "Unidade Desconhecida")
                        novo_nome = f"{numero_oficio} - {nome_unidade}{ext}"

                        # 1. Faz upload do anexo para o Google Drive
                        print(f"Fazendo upload de '{filename}' como '{novo_nome}' para o Drive...")
                        link_drive = sm.upload_para_drive(tmp_path, novo_nome)
                        print("link_drive: ", link_drive)

                        # 2. Insere os dados extraídos na planilha
                        if link_drive:
                            print(f"Registrando ofício {analysis.get('numero_oficio')} na planilha...")
                            sm.inserir_novo_registro(
                                n_oficio=analysis.get("numero_oficio"),
                                data_doc=analysis.get("data_documento"),
                                escola=analysis.get("nome_unidade"),
                                pedido=analysis.get("assunto"),
                                data_entrada=analysis.get("data_entrada"),
                                resumo=analysis.get("resumo_pedido"),
                                link_arquivo=link_drive
                            )
                        
                        # 3. Remove o arquivo temporário local
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                
                print(f"Email '{email['subject']}' processado com sucesso.")
            print("Todos os emails processados.")
            print("------------------------------\n")
        else:
            print("Nenhum e-mail novo encontrado.")

    def buscar_mudancas(self) -> list:
        print("Comparando dados e buscando mudanças...")
        mudancas = []
        for row in self.spreadsheet_data:
            # Verifica se a linha possui colunas suficientes para evitar IndexError
            if len(row) < 9:
                continue
                
            id = uuid.uuid4()
            unidade = row[2]
            pedido = row[3]
            title = f"[{row[0]}]{pedido}_{unidade}"
            desc = row[7]
            url = row[8]
            
            # Tenta extrair o ID do drive com segurança
            try:
                drive_file_id = url.split("/")[-2]
                dt = datetime.strptime(row[1], "%d/%m/%Y")
                dt = dt.replace(tzinfo=timezone.utc)
                data_iso = dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
            except (IndexError, ValueError):
                print(f"Aviso: Linha com formato inválido ignorada: {row[0] if row else 'Vazia'}")
                continue

            data_exist = (
                self.supabase_client
                .table("tasks")
                .select("*")
                .eq("created_at", str(data_iso))
                .eq("title", title)
                .execute()
            )

            if not data_exist.data:
                print(f"Encontrado novo registro. {str(data_iso)}")
                data_to_insert = {
                    "assignee": None,
                    "board_id": None,
                    "completed_at": None,
                    "created_at": str(data_iso),
                    "description": f"{unidade}/ {desc} - [Tarefa criada automaticamente]",
                    "duedate": None,
                    "external_ref": None,
                    "file_url": url,
                    "id": str(id),
                    "priority": "Média",
                    "raw_metadata": None,
                    "source": None,
                    "status": "Pendentes",
                    "title": title,
                    "updated_at": str(datetime.now().isoformat()),
                    "user_id": None,
                }

                log_to_insert = {
                    "action": "create_task",
                    "created_at": str(data_iso),
                    "details": f"Tarefa vinda da planilha do cpd: {{'id': {str(id)}}} gerada automaticamente.",
                    "metadata": None,
                    "user_id": None,
                }

                mudancas.append([data_to_insert, log_to_insert])
        print(mudancas)
        return mudancas

    def atualiza_banco(self):
        if not self.mudancas == []:
            for data in self.mudancas:
                print("Inserindo nova tarefa e log...")
                self.supabase_client.table("tasks").insert(data[0]).execute()
                self.supabase_client.table("user_logs").insert(data[1]).execute()
                time.sleep(1) # Delay solicitado de 1s

flowbox = Flowbox()
