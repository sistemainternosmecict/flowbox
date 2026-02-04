# 📄 Sincronizador de Backup para Banco Oficial

## 📌 Visão Geral

Este micro projeto em **Python** tem como objetivo garantir a **consistência entre uma planilha de backup (Google Sheets)** e um **banco de dados oficial (Supabase/PostgreSQL)**.

O script lê periodicamente os registros de uma planilha de backup, verifica se existem **dados novos** e, caso esses dados **ainda não estejam presentes no banco oficial**, realiza a inserção automática.

O projeto foi pensado para rodar de forma **automatizada**, sendo ideal para execução via **`systemd timer`** ou **cron**, garantindo sincronização contínua e confiável.

---

## ⚙️ Funcionalidades

* 📥 Leitura de dados a partir de uma **planilha Google Sheets**
* 🔍 Verificação de existência dos registros no banco oficial
* 🧠 Prevenção de duplicidade de dados
* 📤 Inserção automática apenas de registros novos
* 🕒 Execução periódica (ex: a cada 1 minuto)
* 📜 Logs centralizados via `journalctl`

---

## 🏗️ Arquitetura do Fluxo

```text
Google Sheets (Backup)
        ↓
Leitura dos registros
        ↓
Verificação no Banco Oficial
        ↓
Já existe? ──► Sim → Ignora
        │
        └──────► Não → Insere no Banco Oficial
```

---

## 🛠️ Tecnologias Utilizadas

* **Python 3.10+**
* **uv** — Gerenciador de dependências
* **Google Sheets API** — Leitura da planilha
* **Supabase (PostgreSQL)** — Banco de dados oficial
* **systemd + timer** — Agendamento da execução

---

## 📂 Estrutura do Projeto

```text
flowbox/
├── main.py               # Script principal
├── pyproject.toml        # Configuração do projeto
├── uv.lock               # Lockfile do uv
├── credentials.json      # Credenciais Google (NÃO versionar)
├── .env                  # Variáveis de ambiente
└── .venv/                # Ambiente virtual (gerado pelo uv)
```

---

## 🔐 Variáveis de Ambiente

Crie um arquivo `.env` com as seguintes variáveis:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=chave_secreta
SPREADSHEET_ID=ID_DA_PLANILHA
SPREADSHEET_RANGE=A2:Z
```

> ⚠️ Nunca versionar arquivos sensíveis como `.env` e `credentials.json`.

---

## ▶️ Execução Manual

```bash
cd /opt/flowbox
uv sync
uv run main.py
```

---

## ⏱️ Execução Automática (systemd)

O projeto foi projetado para rodar como um **serviço agendado**, garantindo sincronização constante.

* `flowbox.service` → Executa o script
* `flowbox.timer` → Agenda a execução (ex: a cada 1 minuto)

Logs podem ser acompanhados com:

```bash
journalctl -u flowbox.service -f
```

---

## 🧪 Comportamento Esperado

* O script **não insere registros duplicados**
* A verificação é feita com base em campos-chave (ex: `file_url`)
* Pode ser executado múltiplas vezes sem causar inconsistências

---

## 🚀 Boas Práticas Aplicadas

* Execução idempotente
* Separação de ambientes
* Logs centralizados
* Uso de UUIDs gerados pelo banco
* Controle de dependências com `uv`

---

## 🧑‍💻 Autor

Projeto desenvolvido para automação e confiabilidade na sincronização de dados entre backups e banco oficial.
Programador: Thyéz de Oliveira Monteiro
Cargo: Assessor de Informática
Local de trabalho: SMECICT - Sala 25

---

## 📄 Licença

Uso interno / sob demanda.
