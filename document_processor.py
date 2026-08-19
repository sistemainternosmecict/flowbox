import os
import time
import json
import logging
import subprocess
import tempfile
import shutil
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from google import genai

load_dotenv()


def obter_comando_libreoffice() -> str:
    """Localiza o binário do LibreOffice ou soffice disponível no sistema."""
    for cmd in ["libreoffice", "soffice"]:
        if shutil.which(cmd):
            return cmd
    raise RuntimeError(
        "LibreOffice não encontrado no sistema. Instale com: sudo apt install libreoffice-writer"
    )


def converter_docx_para_pdf(caminho_docx: str, diretorio_saida: Optional[str] = None) -> str:
    """
    Converte um arquivo .docx para .pdf usando o LibreOffice em modo headless.
    
    Args:
        caminho_docx: Caminho do arquivo DOCX original.
        diretorio_saida: Diretório onde o PDF será salvo. Se None, cria um diretório temporário.
        
    Returns:
        Caminho absoluto do arquivo PDF gerado.
    """
    if not os.path.exists(caminho_docx):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_docx}")

    cmd = obter_comando_libreoffice()
    
    if diretorio_saida is None:
        diretorio_saida = tempfile.mkdtemp(prefix="docx_pdf_")
    else:
        os.makedirs(diretorio_saida, exist_ok=True)

    resultado = subprocess.run(
        [cmd, "--headless", "--convert-to", "pdf", "--outdir", diretorio_saida, caminho_docx],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            f"Falha na conversão de DOCX para PDF. Código {resultado.returncode}: {resultado.stderr}"
        )

    nome_base = os.path.splitext(os.path.basename(caminho_docx))[0]
    pdf_gerado = os.path.join(diretorio_saida, f"{nome_base}.pdf")

    if not os.path.exists(pdf_gerado):
        raise FileNotFoundError(f"O PDF esperado não foi encontrado em: {pdf_gerado}")

    return pdf_gerado


def converter_pdf_para_imagens(
    caminho_pdf: str,
    diretorio_saida: Optional[str] = None,
    formato: str = "png",
    dpi: int = 200
) -> List[str]:
    """
    Converte as páginas de um PDF em arquivos de imagem individuais usando pdftoppm.
    
    Args:
        caminho_pdf: Caminho do arquivo PDF.
        diretorio_saida: Diretório de destino das imagens. Se None, usa pasta temporária.
        formato: 'png' ou 'jpeg'.
        dpi: Resolução das imagens geradas (padrão 200 DPI).
        
    Returns:
        Lista ordenada de caminhos para as imagens geradas.
    """
    if not os.path.exists(caminho_pdf):
        raise FileNotFoundError(f"Arquivo PDF não encontrado: {caminho_pdf}")

    if not shutil.which("pdftoppm"):
        raise RuntimeError("pdftoppm não encontrado. Instale com: sudo apt install poppler-utils")

    if diretorio_saida is None:
        diretorio_saida = tempfile.mkdtemp(prefix="pdf_imgs_")
    else:
        os.makedirs(diretorio_saida, exist_ok=True)

    flag_formato = "-png" if formato.lower() == "png" else "-jpeg"
    prefixo_saida = os.path.join(diretorio_saida, "pagina")

    cmd = ["pdftoppm", flag_formato, "-r", str(dpi), caminho_pdf, prefixo_saida]
    resultado = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)

    if resultado.returncode != 0:
        raise RuntimeError(f"Erro ao converter PDF em imagens: {resultado.stderr}")

    ext = ".png" if formato.lower() == "png" else ".jpg"
    imagens = sorted([
        os.path.join(diretorio_saida, f)
        for f in os.listdir(diretorio_saida)
        if f.startswith("pagina-") and f.endswith(ext)
    ])
    return imagens


def analisar_documento_com_gemini(
    file_path: str,
    mime_type: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-3-flash-preview",
) -> Optional[Dict[str, Any]]:
    """
    Analisa um documento (PDF, DOCX, PNG, JPG, JPEG) usando o modelo Gemini
    e extrai informações estruturadas de ofício/documento em formato dict/JSON.
    
    Caso o arquivo seja DOCX, converte automaticamente para PDF antes do envio
    e remove os arquivos temporários criados ao final.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        print("Aviso: GEMINI_API_KEY não configurada.")
        return None

    arquivo_para_upload = file_path
    temp_dir_criado = None

    # Tratamento específico de extensão para DOCX
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".docx":
        try:
            temp_dir_criado = tempfile.mkdtemp(prefix="gemini_docx_")
            arquivo_para_upload = converter_docx_para_pdf(file_path, diretorio_saida=temp_dir_criado)
            mime_type = "application/pdf"
        except Exception as e:
            print(f"Erro ao converter DOCX para PDF antes da análise: {e}")
            if temp_dir_criado and os.path.exists(temp_dir_criado):
                shutil.rmtree(temp_dir_criado, ignore_errors=True)
            return None

    # Mapeamento padrão de MIME Type caso não informado ou genérico
    if not mime_type or mime_type in ["application/octet-stream", "binary/octet-stream"]:
        upload_ext = os.path.splitext(arquivo_para_upload)[1].lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        mime_type = mime_map.get(upload_ext, "application/pdf")

    try:
        client = genai.Client(api_key=key)
        print(f"Enviando {arquivo_para_upload} para análise no Gemini (mime_type: {mime_type})...")
        
        uploaded_file = client.files.upload(file=arquivo_para_upload, config={"mime_type": mime_type})
        while uploaded_file.state == "PROCESSING":
            time.sleep(2)
            uploaded_file = client.files.get(name=uploaded_file.name)

        prompt = """
        Analise este documento (ofício) e extraia as seguintes informações em formato JSON puro:
        {
            "numero_oficio": "string",
            "data_documento": "string (data de criação mencionada no documento, formato DD/MM/AAAA)",
            "nome_unidade": "string",
            "assunto": "string",
            "resumo_pedido": "string"
        }
        Retorne apenas o JSON, sem markdown ou explicações.
        """
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, uploaded_file]
        )
        
        text_response = response.text.strip()
        if text_response.startswith("```json"):
            text_response = text_response.split("```json")[1].split("```")[0].strip()
        elif text_response.startswith("```"):
            text_response = text_response.split("```")[1].split("```")[0].strip()
            
        return json.loads(text_response)

    except Exception as e:
        print(f"Erro ao analisar com Gemini: {e}")
        logging.error(
            json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "model": model_name,
                    "request_count": 1,
                    "error": str(e),
                    "prompt_tokens": 0,
                    "candidate_tokens": 0,
                    "total_tokens": 0,
                }
            )
        )
        return None
    finally:
        # Limpeza automática de diretórios temporários criados para a conversão
        if temp_dir_criado and os.path.exists(temp_dir_criado):
            shutil.rmtree(temp_dir_criado, ignore_errors=True)
