# 🚀 Flowbox - Automação Inteligente de Ofícios

## 📌 Visão Geral

O **Flowbox** é um sistema de automação inteligente projetado para simplificar a triagem e o registro de ofícios recebidos por e-mail. Ele utiliza Inteligência Artificial (Gemini) para ler anexos, extrair informações críticas e organizar tudo automaticamente em uma planilha do Google e no banco de dados oficial (Supabase).

O objetivo principal é eliminar o trabalho manual de baixar anexos, renomear arquivos, extrair números de documentos e preencher planilhas.

---

## ⚙️ Funcionalidades

*   **📬 Triagem Automática**: Busca e-mails não lidos em uma conta IMAP específica.
*   **🧠 Processamento com IA**: Utiliza o **Gemini 1.5 Flash** para analisar PDFs e imagens, extraindo número do ofício, data do documento, unidade, assunto e gerando um resumo.
*   **📁 Gestão de Arquivos**: Renomeia automaticamente os anexos para o padrão `[NÚMERO_OFICIO] - [NOME_UNIDADE]` (higienizando caracteres especiais) e faz upload para uma pasta organizada no **Google Drive**.
*   **📊 Registro em Planilha**: Insere novos registros no **Google Sheets** na aba correspondente ao ano vigente (ex: `2026`), incluindo links diretos para o arquivo no Drive.
*   **🔄 Sincronização Supabase**: Compara os dados da planilha com o banco de dados de tarefas do Supabase, inserindo automaticamente novos registros detectados e garantindo a integridade dos dados.

**Novo:** O sistema agora integra uma tabela dedicada `mail_ids` no Supabase para registrar todos os e-mails recebidos, facilitando o rastreio, mesmo quando não há anexos processáveis.

---

## 🏗️ Arquitetura do Fluxo

1.  **Monitoramento**: O sistema acessa a caixa de entrada via IMAP e identifica e-mails não lidos.
2.  **Extração**: Anexos (PDF/Imagens) são enviados temporariamente para a API do **Gemini 1.5 Flash** para extração de metadados em formato JSON.
3.  **Renomeação e Armazenamento**: O arquivo é renomeado seguindo o padrão definido e enviado ao **Google Drive**. O arquivo temporário local é excluído após o sucesso.
4.  **Registro**: As informações extraídas + o link do Drive são inseridos como uma nova linha no **Google Sheets**.
5.  **Integração**: O sistema lê a planilha, identifica linhas ainda não presentes no **Supabase** e as insere na tabela de tarefas. Além disso, registra cada e-mail recebido na tabela `mail_ids` do **Supabase**.

---

## 🛠️ Tecnologias Utilizadas

*   **Python 3.13+**
*   **uv** — Gerenciador de dependências e ambiente de alto desempenho.
*   **Google Gemini API** — Extração inteligente de dados de documentos.
*   **Google Sheets & Drive API** — Armazenamento e registro de dados.
*   **Supabase (PostgreSQL)** — Banco de dados oficial de tarefas e e-mails.
*   **IMAP** — Monitoramento de caixa de entrada de e-mail.

---

## 📂 Estrutura do Projeto

```text
flowbox/
├── main.py               # Orquestrador principal (Loop de e-mail -> Drive -> Sheets -> Supabase)
├── mailman.py            # Módulo de e-mail e integração com Gemini (Análise de documentos)
├── sheetman.py           # Módulo de integração com APIs do Google (Sheets e Drive)
├── credentials.json      # Credenciais do Google Cloud (OAuth 2.0 - NÃO versionar)
├── token.json            # Token de acesso persistente (NÃO versionar)
├── .env                  # Configurações de chaves e acessos
└── pyproject.toml        # Configuração de dependências (uv)
```

---

## 🔐 Configuração do Ambiente (.env)

Certifique-se de que o seu `.env` contenha:

```env
# --- Google Integration ---
SPREADSHEET_ID=seu_id_da_planilha_aqui
RANGE=2026!A:I
DRIVE_FOLDER_ID=seu_id_da_pasta_no_drive

# --- E-mail (IMAP) ---
EMAIL_USER=seu-email@gmail.com
EMAIL_PASS=sua_senha_de_app_aqui
EMAIL_IMAP_SERVER=imap.gmail.com

# --- Gemini AI ---
GEMINI_API_KEY=sua_chave_gemini_aqui

# --- Supabase (Tarefas) ---
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_SERVICE_KEY=sua_chave_service_role

# --- Supabase (Registro de E-mails) ---
MAILIDS_URL=https://yyyy.supabase.co
MAILIDS_KEY=sua_chave_service_role_para_mailids
```

---

## 🚀 Instalação e Uso

### 1. Requisitos Prévios
*   Ter o [uv](https://github.com/astral-sh/uv) instalado.
*   Habilitar as APIs do Google Sheets e Google Drive no [Google Cloud Console](https://console.cloud.google.com/).
*   Baixar o arquivo `credentials.json` (OAuth 2.0 Desktop) e colocar na raiz do projeto.

### 2. Configuração
```bash
# Sincronizar dependências
uv sync

# Execução do fluxo
uv run main.py
```

---

## 🧑‍💻 Autor

Projeto desenvolvido para modernizar e automatizar o fluxo de entrada de documentos oficiais na SMECICT.

- **Programador**: Thyéz de Oliveira Monteiro
- **Cargo**: Assessor de Informática
- **Local**: SMECICT - Sala 25

---

## 📄 Licença

Uso interno / sob demanda.
