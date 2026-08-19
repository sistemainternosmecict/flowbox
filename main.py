import os
import uuid
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

from sheetman import Sheetman
from mailman import Mailman
import stats_tracker

load_dotenv()


class Flowbox:
    supabase_url: str
    supabase_key: str
    supabase_client: any
    spreadsheet_data: list
    mudancas: list
    emails_nao_lidos: list
    quantidade_emails: int
    linhas_escritas: int
    gemini_funcionou_bem: bool
    sincronizado: bool

    def __init__(self):
        self.start_time = time.time()
        self.quantidade_emails = 0
        self.linhas_escritas = 0
        self.sucessos_primeira_tentativa = 0
        self.sucessos_segunda_tentativa = 0
        self.emails_falhos = []
        self.gemini_funcionou_bem = True
        self.erro_banco = False
        self.sincronizado = True
        self.emails_processados_log = []

        print("""
===============================
              Flowbox iniciado!
===============================
              """)
        self.supabase_url = os.getenv("VITE_SUPABASE_URL")
        self.supabase_key = os.getenv("VITE_SUPABASE_SERVICE_KEY")

        self.mailids_url = os.getenv("MAILIDS_URL")
        self.mailids_key = os.getenv("MAILIDS_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise RuntimeError("Variáveis de ambiente do Supabase não configuradas")

        self.criar_cliente_supabase()

        # Cliente para tabela de mail_ids
        if self.mailids_url and self.mailids_key:
            self.mailids_client = create_client(self.mailids_url, self.mailids_key)
        else:
            self.mailids_client = None
            print("Aviso: Credenciais para mail_ids não configuradas.")

        self.processar_emails()
        self.carregar_dados_planilha()
        self.mudancas = self.buscar_mudancas()
        self.atualiza_banco()

        # Cálculo do status booleano de sincronização (emails, planilha e banco/tasks)
        if self.quantidade_emails > 0:
            self.sincronizado = (
                len(self.emails_falhos) == 0
                and not self.erro_banco
                and self.linhas_escritas > 0
            )
        else:
            self.sincronizado = not self.erro_banco

        print("Flowbox executado com sucesso!")

        tempo_execucao = time.time() - self.start_time
        tasks_adicionadas = len(self.mudancas) if self.mudancas else 0
        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Formatação compacta em bloco de até 3 linhas para visualização em celular
        l1 = f"[{data_hora}] Emails: {self.quantidade_emails} | Linhas: {self.linhas_escritas} | Tasks: {tasks_adicionadas} | Tempo: {tempo_execucao:.1f}s"
        gemini_status = "OK" if self.gemini_funcionou_bem else "Falha"
        sync_status = "True" if self.sincronizado else "False"
        l2 = f"Sync: {sync_status} | Gemini: {gemini_status} | 1ªTent: +{self.sucessos_primeira_tentativa} | 2ªTent: +{self.sucessos_segunda_tentativa}"

        if self.emails_processados_log:
            detalhes_str = " | ".join(self.emails_processados_log)
            if len(detalhes_str) > 75:
                detalhes_str = detalhes_str[:72] + "..."
            l3 = f"Ofícios: {detalhes_str}"
        elif self.emails_falhos:
            falhas_str = " | ".join(self.emails_falhos)
            if len(falhas_str) > 75:
                falhas_str = falhas_str[:72] + "..."
            l3 = f"Falhas: {falhas_str}"
        else:
            l3 = "Detalhes: Sem novos e-mails processados"

        bloco_log = f"{l1}\n{l2}\n{l3}\n---\n"

        try:
            with open(
                os.path.join(os.path.dirname(__file__), "exec_log.log"), "a", encoding="utf-8"
            ) as f:
                f.write(bloco_log)
        except Exception as e:
            print(f"Erro ao salvar log: {e}")

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
            self.quantidade_emails = len(self.emails_nao_lidos)
            print(
                f"\nForam encontrados {len(self.emails_nao_lidos)} e-mails não lidos."
            )
            for email in self.emails_nao_lidos:
                email_id = email.get("id")
                imap_num = email.get("imap_num")
                email_subject = email.get("subject", "")
                attachments = email.get("attachments", [])
                
                email_sucesso = True
                motivo_erro = ""

                try:
                    for att in attachments:
                        analysis = att.get("analysis")
                        tmp_path = att.get("temp_path")
                        filename = att.get("filename")

                        if analysis is None and tmp_path:
                            self.gemini_funcionou_bem = False
                            raise RuntimeError(f"Falha na análise Gemini do anexo '{filename}'")

                        if isinstance(analysis, dict) and tmp_path:
                            # Extrai a extensão original
                            ext = os.path.splitext(filename)[1]

                            # Define o novo nome padrão: [numero do oficio] - [nome da unidade]
                            numero_oficio = str(
                                analysis.get("numero_oficio", "S-N")
                            ).replace("/", "_")
                            nome_unidade = analysis.get(
                                "nome_unidade", "Unidade Desconhecida"
                            )
                            novo_nome = f"{numero_oficio} - {nome_unidade}{ext}"

                            # 1. Faz upload do anexo para o Google Drive
                            print(
                                f"Fazendo upload de '{filename}' como '{novo_nome}' para o Drive..."
                            )
                            link_drive = sm.upload_para_drive(tmp_path, novo_nome)
                            if not link_drive:
                                raise RuntimeError(f"Falha no upload para o Google Drive ({filename})")
                            print("link_drive: ", link_drive)

                            # 2. Insere os dados extraídos na planilha
                            print(
                                f"Registrando ofício {analysis.get('numero_oficio')} na planilha..."
                            )
                            inseriu = sm.inserir_novo_registro(
                                n_oficio=analysis.get("numero_oficio"),
                                data_doc=analysis.get("data_documento"),
                                escola=analysis.get("nome_unidade"),
                                pedido=analysis.get("assunto"),
                                data_entrada=analysis.get("data_entrada"),
                                resumo=analysis.get("resumo_pedido"),
                                link_arquivo=link_drive,
                            )
                            if not inseriu:
                                raise RuntimeError(f"Falha ao inserir registro na planilha ({numero_oficio})")

                            self.linhas_escritas += 1

                            # Registra o e-mail no Supabase
                            self.registra_mail_id(
                                mail_id=email_id,
                                numero_oficio=numero_oficio,
                                email_unidade=email.get("sender_email"),
                                unidade=nome_unidade,
                                assunto=email_subject,
                                url_anexo_drive=link_drive,
                            )
                            self.emails_processados_log.append(f"[{numero_oficio}] {email_subject}")

                            # 3. Remove o arquivo temporário local
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)

                    if email_sucesso:
                        tipo_sucesso = stats_tracker.registrar_sucesso(email_id)
                        if tipo_sucesso == "duas_tentativas":
                            self.sucessos_segunda_tentativa += 1
                        else:
                            self.sucessos_primeira_tentativa += 1
                        print(f"Email '{email_subject}' processado com sucesso ({tipo_sucesso}).")

                except Exception as e:
                    email_sucesso = False
                    motivo_erro = str(e)
                    print(f"Erro ao processar e-mail '{email_subject}': {e}. Remarcando como NÃO LIDO no IMAP...")
                    mm.marcar_como_nao_lido(num=imap_num, message_id=email_id)
                    stats_tracker.registrar_falha(email_id, motivo_erro)
                    self.emails_falhos.append(f"{email_subject} ({motivo_erro})")
                    self.gemini_funcionou_bem = False

            print("Todos os emails processados.")
            print("------------------------------\n")
        else:
            print("Nenhum e-mail novo encontrado.")

    def buscar_mudancas(self) -> list:
        print("Comparando dados e buscando mudanças...")
        mudancas = []
        if not self.spreadsheet_data:
            return []
        try:
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
                    dt = datetime.strptime(row[1], "%d/%m/%Y")
                    dt = dt.replace(tzinfo=timezone.utc)
                    data_iso = dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
                except (IndexError, ValueError):
                    print(
                        f"Aviso: Linha com formato inválido ignorada: {row[0] if row else 'Vazia'}"
                    )
                    continue

                data_exist = (
                    self.supabase_client.table("tasks")
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
        except Exception as e:
            print(f"Erro ao buscar mudanças no Supabase: {e}")
            self.erro_banco = True

        print(mudancas)
        return mudancas

    def atualiza_banco(self):
        if not self.mudancas == []:
            try:
                for data in self.mudancas:
                    print("Inserindo nova tarefa e log...")
                    self.supabase_client.table("tasks").insert(data[0]).execute()
                    self.supabase_client.table("user_logs").insert(data[1]).execute()
                    time.sleep(1)  # Delay solicitado de 1s
            except Exception as e:
                print(f"Erro ao atualizar tarefas no Supabase: {e}")
                self.erro_banco = True

    def registra_mail_id(
        self, mail_id, numero_oficio, email_unidade, unidade, assunto, url_anexo_drive
    ):
        if not self.mailids_client:
            print("Cliente para mail_ids não configurado, ignorando registro.")
            return

        data = {
            "mail_id": mail_id,
            "numero_oficio": numero_oficio,
            "email_unidade": email_unidade,
            "unidade": unidade,
            "assunto": assunto,
            "url_anexo_drive": url_anexo_drive,
        }

        try:
            self.mailids_client.table("mail_ids").insert(data).execute()
            print(f"E-mail {mail_id} registrado com sucesso no Supabase.")
        except Exception as e:
            print(f"Erro ao registrar e-mail {mail_id} no Supabase: {e}")


if __name__ == "__main__":
    flowbox = Flowbox()
