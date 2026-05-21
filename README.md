# 🚀 Flowbox - Automação Inteligente de Ofícios

## 📌 Visão Geral

O **Flowbox** é um sistema de automação inteligente projetado para simplificar a triagem e o registro de ofícios recebidos por e-mail. Ele utiliza Inteligência Artificial (Gemini) para ler anexos, extrair informações críticas e organizar tudo automaticamente em uma planilha do Google e no banco de dados oficial (Supabase).

O objetivo principal é eliminar o trabalho manual de baixar anexos, renomear arquivos, extrair números de documentos e preencher planilhas.

---

## ⚙️ Funcionalidades

*   **📬 Triagem Automática**: Busca e-mails não lidos em uma conta IMAP específica.
*   **🧠 Processamento com IA**: Utiliza o **Gemini 1.5 Flash** para analisar PDFs e imagens, extraindo número do ofício, datas, unidade e resumo do pedido.
*   **📁 Gestão de Arquivos**: Faz upload automático dos anexos para uma pasta organizada no **Google Drive**.
*   **📊 Registro em Planilha**: Insere novos registros no **Google Sheets** com links diretos para o arquivo no Drive.
*   **🔄 Sincronização Supabase**: Integra os dados com o sistema de tarefas oficial, gerando logs de auditoria e evitando duplicidade.

---

## 🏗️ Arquitetura do Fluxo

```text
E-mail (Anexo) ──► Gemini AI (Análise) ──► Google Drive (Upload)
                                              │
      ┌───────────────────────────────────────┘
      ▼
Google Sheets (Registro) ──► Supabase (Tasks & Logs)
```

---

## 🛠️ Tecnologias Utilizadas

*   **Python 3.13+**
*   **uv** — Gerenciador de dependências e ambiente de alto desempenho.
*   **Google Gemini API** — Extração inteligente de dados de documentos.
*   **Google Sheets & Drive API** — Armazenamento e registro de dados.
*   **Supabase (PostgreSQL)** — Banco de dados oficial de tarefas.
*   **IMAP** — Monitoramento de caixa de entrada de e-mail.

---

## 📂 Estrutura do Projeto

```text
flowbox/
├── main.py               # Orquestrador principal do fluxo
├── mailman.py            # Módulo de e-mail e integração com Gemini
├── sheetman.py           # Módulo de integração com Google Sheets e Drive
├── credentials.json      # Credenciais do Google Cloud (NÃO versionar)
├── token.json            # Token de acesso gerado após o login (NÃO versionar)
├── .env                  # Configurações e chaves secretas
└── pyproject.toml        # Configuração de dependências (uv)
```

---

## 🔐 Configuração do Ambiente (.env)

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# --- Google Integration ---
SPREADSHEET_ID=seu_id_da_planilha_aqui
RANGE=Página1!A:I
DRIVE_FOLDER_ID=seu_id_da_pasta_no_drive

# --- E-mail (IMAP) ---
EMAIL_USER=seu-email@gmail.com
EMAIL_PASS=sua_senha_de_app_aqui
EMAIL_IMAP_SERVER=imap.gmail.com

# --- Gemini AI ---
GEMINI_API_KEY=sua_chave_gemini_aqui

# --- Supabase ---
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_SERVICE_KEY=sua_chave_service_role
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

# Primeira execução (abrirá o navegador para autenticar no Google)
uv run main.py
```

---

## ⏱️ Automação (systemd)

Para garantir que o Flowbox processe e-mails continuamente, recomenda-se o uso de um timer do systemd:

```bash
# Ver status do serviço
journalctl -u flowbox.service -f
```

---

## 🧑‍💻 Autor

Projeto desenvolvido para modernizar e automatizar o fluxo de entrada de documentos oficiais.

- **Programador**: Thyéz de Oliveira Monteiro
- **Cargo**: Assessor de Informática
- **Local**: SMECICT - Sala 25

---

## 📄 Licença

Uso interno / sob demanda.
