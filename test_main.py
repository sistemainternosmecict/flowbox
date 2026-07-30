import pytest
from unittest.mock import MagicMock, patch
import main

# Mock para as variáveis de ambiente
@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("VITE_SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("VITE_SUPABASE_SERVICE_KEY", "test_key")
    monkeypatch.setenv("MAILIDS_URL", "https://mailids.supabase.co")
    monkeypatch.setenv("MAILIDS_KEY", "mailids_key")

# Mock das dependências externas que o Flowbox instancia no __init__
@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    monkeypatch.setattr("main.Sheetman", MagicMock())
    monkeypatch.setattr("main.Mailman", MagicMock())

@patch("main.create_client")
def test_flowbox_initialization(mock_create_client, mock_env):
    """Testa se o Flowbox inicializa corretamente os clientes Supabase."""
    # Configura o mock do cliente
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    # Instancia o Flowbox (isso chama o __init__ que chama criar_cliente_supabase e processar_emails)
    # Precisamos mockar os métodos que o __init__ chama para evitar execução de efeitos colaterais
    with patch.object(main.Flowbox, 'criar_cliente_supabase'), \
         patch.object(main.Flowbox, 'processar_emails'), \
         patch.object(main.Flowbox, 'carregar_dados_planilha'), \
         patch.object(main.Flowbox, 'buscar_mudancas', return_value=[]), \
         patch.object(main.Flowbox, 'atualiza_banco'):
        
        fb = main.Flowbox()
        
    assert fb.supabase_url == "https://test.supabase.co"
    assert fb.mailids_url == "https://mailids.supabase.co"

@patch("main.create_client")
def test_registra_mail_id_sucesso(mock_create_client, mock_env):
    """Testa se o método registra_mail_id insere dados corretamente no Supabase."""
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    # Mock dos métodos chamados no __init__
    with patch.object(main.Flowbox, 'criar_cliente_supabase'), \
         patch.object(main.Flowbox, 'processar_emails'), \
         patch.object(main.Flowbox, 'carregar_dados_planilha'), \
         patch.object(main.Flowbox, 'buscar_mudancas', return_value=[]), \
         patch.object(main.Flowbox, 'atualiza_banco'):
        
        fb = main.Flowbox()
        fb.mailids_client = mock_client
    
    # Dados de teste
    test_data = {
        "mail_id": "123",
        "numero_oficio": "1/2026",
        "email_unidade": "test@unidade.com",
        "unidade": "Unidade X",
        "assunto": "Assunto Teste",
        "url_anexo_drive": ""
    }
    
    # Executa o método
    fb.registra_mail_id(**test_data)
    
    # Verifica se o insert foi chamado na tabela correta
    mock_client.table.assert_called_with("mail_ids")
    mock_client.table("mail_ids").insert.assert_called_once_with(test_data)
    mock_client.table("mail_ids").insert(test_data).execute.assert_called_once()
