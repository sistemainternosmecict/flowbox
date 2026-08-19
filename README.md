# 🚀 Flowbox — Sistema Inteligente de Processamento e Sincronização de Ofícios

> **Versão v1.2** — Automação institucional de alta performance para triagem de e-mails, conversão e análise documental com Inteligência Artificial, gestão em nuvem e sincronização de tarefas.

---

## 👨‍💻 Dados Institucionais e Autoria

| Atributo | Detalhe |
| :--- | :--- |
| **Autor & Engenheiro Responsável** | Thyéz de Oliveira Monteiro |
| **Cargo** | Assessor de Informática |
| **Função** | Engenheiro de Software |
| **Matrícula Funcional** | `9506219-2` |
| **Órgão** | Secretaria Municipal de Educação |
| **Setor / Lotação** | Subsecretaria de Tecnologia — Sala 25 |
| **Versão do Software** | `v1.2` |
| **Data de Homologação** | 17 de agosto de 2026 |

> ⚠️ **Aviso de Confidencialidade e Uso Restrito:**  
> Este software é de **uso exclusivo e restrito interno da Subsecretaria de Tecnologia** da Secretaria Municipal de Educação. É vedada a reprodução, distribuição ou utilização não autorizada fora dos propósitos e sistemas oficiais do setor.

---

## 📌 Visão Geral da Solução

O **Flowbox** é uma solução corporativa de automação desenvolvida para eliminar o processamento manual de ofícios e comunicações oficiais recebidos por e-mail na Subsecretaria de Tecnologia. 

O sistema orquestra de ponta a ponta o fluxo de trabalho:
1. Conecta à caixa de entrada institucional via protocolo IMAP seguro.
2. Identifica e processa anexos nos formatos **PDF, DOCX, PNG, JPG e JPEG**.
3. Converte documentos `.docx` em PDF com fidelidade visual completa via LibreOffice Headless.
4. Extrai metadados estruturados (número de ofício, data, unidade emissora, assunto e resumo do pedido) utilizando o modelo **Google Gemini**.
5. Renomeia, padroniza e armazena os documentos no **Google Drive**.
6. Insere os registros na planilha corporativa do **Google Sheets**.
7. Sincroniza tarefas pendentes e histórico de comunicações no **Supabase (PostgreSQL)**.
8. Implementa política de retry com **remarcação automática como Não Lido** em caso de falhas, métricas de tentativas e logs compactos otimizados para acompanhamento mobile.

---

## ⚙️ Funcionalidades Principais

*   📬 **Triagem IMAP Inteligente**: Captura e-mails não lidos e extrai remetentes reais mesmo em fluxos de encaminhamento (`Fwd:`).
*   📄 **Suporte Multi-Formato & Conversão DOCX**: Processamento nativo de PDFs e imagens, e conversão automatizada de arquivos `.docx` para PDF através do módulo desacoplado `document_processor`.
*   🧠 **Análise Documental com IA (Gemini)**: Extração precisa em JSON estruturado contendo informações essenciais do ofício.
*   🔄 **Resiliência e Auto-Recuperação (Retry)**: Em caso de falha em qualquer etapa (IA, Drive, Sheets ou Banco), o e-mail é automaticamente remarcado como **Não Lido** no servidor IMAP para reprocessamento na execução seguinte.
*   📈 **Controle de Tentativas (`contadores.txt`)**: Contabilização auditável de e-mails processados de primeira tentativa versus e-mails recuperados na segunda tentativa (retries).
*   ☁️ **Armazenamento no Google Drive**: Upload automático com nomenclatura higienizada no padrão `[NÚMERO_OFICIO] - [NOME_UNIDADE]`.
*   📊 **Registro no Google Sheets**: Atualização da planilha anual (aba `2026`) com link direto para o arquivo armazenado.
*   🗄️ **Sincronização com Supabase**: Inserção automática de tarefas no board e registro de rastreabilidade na tabela `mail_ids`.
*   📱 **Logs Estruturados Compactos (`exec_log.log`)**: Formato de log visual em blocos de até 3 linhas com indicador booleano de sincronização (`Sync: True/False`), ideal para visualização rápida em dispositivos móveis.

---

## 🏗️ Arquitetura do Sistema

```text
                                 [ E-MAIL RECEBIDO (IMAP) ]
                                              │
                                              ▼
                             ┌─────────────────────────────────┐
                             │    Mailman (mailman.py)         │
                             │  - Leitura de cabeçalhos/corpo  │
                             │  - Extração de anexos           │
                             └────────────────┬────────────────┘
                                              │
                                              ▼
                             ┌─────────────────────────────────┐
                             │  DocumentProcessor              │
                             │  - DOCX -> PDF (LibreOffice)    │
                             │  - Análise com Google Gemini    │
                             └────────────────┬────────────────┘
                                              │
                                              ▼
                      ┌───────────────────────┴───────────────────────┐
                      ▼                                               ▼
          [ Upload Google Drive ]                         [ Inserção Google Sheets ]
                      │                                               │
                      └───────────────────────┬───────────────────────┘
                                              │
                                              ▼
                             ┌─────────────────────────────────┐
                             │      Flowbox (main.py)          │
                             │  - Sincronização Supabase Tasks │
                             │  - Registro tabela mail_ids     │
                             │  - Gestão de Contadores e Logs  │
                             └────────────────┬────────────────┘
                                              │
                 ┌────────────────────────────┴────────────────────────────┐
                 ▼                                                         ▼
     [ contadores.txt ]                                            [ exec_log.log ]
     - Sucesso 1ª Tentativa                                        - Status Execução & Sync
     - Sucesso 2ª Tentativa                                        - Resumo Ofícios (3 linhas)
```

---

## 📂 Estrutura de Diretórios

```text
flowbox/
├── main.py                   # Orquestrador principal do ciclo de execução
├── mailman.py                # Módulo de gestão IMAP e remarcação de status
├── document_processor.py     # Módulo desacoplado de conversão DOCX e análise Gemini
├── sheetman.py               # Integração com Google Sheets API e Google Drive API
├── stats_tracker.py          # Gestão de contadores de tentativas e retry state
├── contadores.txt            # Contadores acumulados de sucesso (1ª e 2ª tentativa)
├── exec_log.log              # Logs compactos de execução (otimizados para mobile)
├── test_mailman.py           # Testes unitários do módulo de e-mail
├── test_main.py              # Testes unitários do fluxo principal
├── credentials.json          # Credenciais OAuth 2.0 do Google Cloud (Confidencial)
├── token.json                # Token de autorização persistente (Confidencial)
├── .env                      # Variáveis de ambiente e chaves secretas
└── pyproject.toml            # Especificação de dependências e metadados (uv)
```

---

## 🔐 Configuração do Ambiente (`.env`)

Crie o arquivo `.env` na raiz do projeto com as seguintes variáveis institucionais:

```env
# --- Integração Google (Drive e Planilhas) ---
SPREADSHEET_ID=seu_id_da_planilha_aqui
RANGE=2026!A:I
DRIVE_FOLDER_ID=seu_id_da_pasta_no_drive

# --- Correio Eletrônico Institucional (IMAP) ---
EMAIL_USER=seu-email@dominio.gov.br
EMAIL_PASS=sua_senha_de_aplicativo
EMAIL_IMAP_SERVER=imap.gmail.com

# --- Inteligência Artificial (Google Gemini) ---
GEMINI_API_KEY=sua_chave_gemini_aqui

# --- Banco de Dados Supabase (Tarefas) ---
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_SERVICE_KEY=sua_chave_service_role

# --- Banco de Dados Supabase (Registro de E-mails) ---
MAILIDS_URL=https://yyyy.supabase.co
MAILIDS_KEY=sua_chave_service_role_para_mailids
```

---

## 🚀 Instalação e Execução

### 1. Pré-requisitos
* **Linux (Ubuntu/Debian recomendado)**
* **Python 3.13+**
* **[uv](https://github.com/astral-sh/uv)** (Gerenciador de pacotes de alta velocidade)
* **LibreOffice Headless** (necessário para conversão de DOCX):
  ```bash
  sudo apt-get update && sudo apt-get install -y libreoffice-writer-nogui
  ```

### 2. Sincronização do Ambiente
```bash
uv sync
```

### 3. Execução dos Testes Automatizados
```bash
uv run pytest
```

### 4. Execução Manual do Flowbox
```bash
uv run main.py
```

### 5. Agendamento Periódico (Cron)
Para executar automaticamente a cada 5 minutos:
```bash
*/5 * * * * cd /home/thyez/Documentos/softwares/flowbox && /home/thyez/.local/bin/uv run main.py >> /home/thyez/Documentos/softwares/flowbox/cron_output.log 2>&1
```

---

## 📋 Padrão dos Registros de Log (`exec_log.log`)

Formato compacto em blocos de até 3 linhas desenvolvido para consulta ágil via smartphone:

```text
[2026-08-19 14:24:18] Emails: 1 | Linhas: 1 | Tasks: 1 | Tempo: 82.4s
Sync: True | Gemini: OK | 1ªTent: +1 | 2ªTent: +0
Ofícios: [079_2026] Fwd: Segue em anexo ofício 079
---
```

---

## 📄 Licença e Termos de Uso

**Uso Interno e Institucional.**  
Desenvolvido exclusivamente para a **Subsecretaria de Tecnologia — Secretaria Municipal de Educação**.  
Todos os direitos reservados © 2026.
