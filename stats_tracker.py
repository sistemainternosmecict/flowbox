import os
import json
from datetime import datetime
from typing import Dict, Any, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTADORES_FILE = os.path.join(BASE_DIR, "contadores.txt")
RETRIES_FILE = os.path.join(BASE_DIR, "email_retries.json")


def ler_contadores() -> Tuple[int, int]:
    """
    Lê os contadores acumulados do arquivo contadores.txt.
    Retorna (emails_primeira_tentativa, emails_duas_tentativas).
    """
    primeira = 0
    duas = 0
    if os.path.exists(CONTADORES_FILE):
        try:
            with open(CONTADORES_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    linha = line.strip()
                    if "sucesso de primeira:" in linha.lower() or "primeira_tentativa:" in linha.lower():
                        primeira = int(linha.split(":")[-1].strip())
                    elif "duas tentativas:" in linha.lower() or "duas_tentativas:" in linha.lower():
                        duas = int(linha.split(":")[-1].strip())
        except Exception as e:
            print(f"Aviso: Erro ao ler contadores.txt ({e}). Usando valores padrão.")
    return primeira, duas


def salvar_contadores(primeira: int, duas: int) -> None:
    """Salva os contadores acumulados no arquivo contadores.txt."""
    conteudo = (
        f"Emails lidos com sucesso de primeira: {primeira}\n"
        f"Emails lidos em duas tentativas: {duas}\n"
    )
    try:
        with open(CONTADORES_FILE, "w", encoding="utf-8") as f:
            f.write(conteudo)
    except Exception as e:
        print(f"Erro ao salvar contadores.txt: {e}")


def _ler_retries() -> Dict[str, Any]:
    """Lê o arquivo de estado de retries."""
    if os.path.exists(RETRIES_FILE):
        try:
            with open(RETRIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _salvar_retries(data: Dict[str, Any]) -> None:
    """Salva o arquivo de estado de retries."""
    try:
        with open(RETRIES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar {RETRIES_FILE}: {e}")


def registrar_falha(email_id: str, motivo: str = "") -> int:
    """
    Registra que o email falhou no processamento e foi remarcado como não lido.
    Retorna o número atual de tentativas registradas para este email.
    """
    if not email_id:
        return 1
    retries = _ler_retries()
    dados = retries.get(email_id, {"tentativas": 0})
    dados["tentativas"] = dados.get("tentativas", 0) + 1
    dados["ultimo_erro"] = datetime.now().isoformat()
    dados["motivo"] = str(motivo)
    retries[email_id] = dados
    _salvar_retries(retries)

    return dados["tentativas"]


def registrar_sucesso(email_id: str) -> str:
    """
    Registra o processamento com sucesso de um email.
    Se o email estava no histórico de falhas (tentativas >= 1), conta como
    sucesso de segunda tentativa e remove do controle de retry.
    Caso contrário, conta como sucesso de primeira tentativa.
    
    Retorna 'primeira_tentativa' ou 'duas_tentativas'.
    """
    primeira, duas = ler_contadores()
    retries = _ler_retries()

    if email_id and email_id in retries:
        # Passou em retry (segunda tentativa)
        duas += 1
        del retries[email_id]
        _salvar_retries(retries)
        salvar_contadores(primeira, duas)
        return "duas_tentativas"
    else:
        # Passou de primeira
        primeira += 1
        salvar_contadores(primeira, duas)
        return "primeira_tentativa"
