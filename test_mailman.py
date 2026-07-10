import pytest
from unittest.mock import MagicMock, patch
import mailman

# Mock para as variáveis de ambiente
@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("EMAIL_USER", "test@example.com")
    monkeypatch.setenv("EMAIL_PASS", "password")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key")

@pytest.fixture
def mailman_instance(mock_env):
    return mailman.Mailman()

def test_obter_id_original_email(mailman_instance):
    """Testa se o método extrai corretamente o ID e o e-mail do remetente."""
    # Simula um objeto de mensagem de e-mail
    mock_msg = MagicMock()
    mock_msg.get.return_value = "Nome Sobrenome <test@remetente.com>"
    
    email_id = b'123'
    
    # Executa o método
    res_id, res_email = mailman_instance.obter_id_original_email(mock_msg, email_id)
    
    # Validações
    assert res_id == '123'
    assert res_email == 'test@remetente.com'

def test_inserir_id_na_resposta(mailman_instance):
    """Testa se o método insere corretamente as novas chaves no dicionário."""
    email_data = {"subject": "Assunto"}
    email_id = "123"
    sender_email = "test@remetente.com"
    
    updated_data = mailman_instance.inserir_id_na_resposta(email_data, email_id, sender_email)
    
    assert updated_data["id"] == "123"
    assert updated_data["sender_email"] == "test@remetente.com"
    assert updated_data["subject"] == "Assunto"

@patch('imaplib.IMAP4_SSL')
def test_buscar_emails_nao_lidos_sucesso(mock_imap, mailman_instance):
    """Testa o fluxo de sucesso da busca de e-mails."""
    # Configuração dos mocks para simular o fluxo IMAP
    mock_mail = MagicMock()
    mock_imap.return_value = mock_mail
    
    # Simula busca de e-mails encontrando 1 e-mail
    mock_mail.search.return_value = ('OK', [b'10'])
    
    # Simula o conteúdo do e-mail
    mock_msg_data = b'Subject: Teste\r\nFrom: <test@remetente.com>\r\nDate: Wed, 10 Jun 2026 10:00:00 +0000\r\n\r\nCorpo do e-mail'
    mock_mail.fetch.return_value = ('OK', [(None, mock_msg_data)])
    
    # Executa a função
    results = mailman_instance.buscar_emails_nao_lidos()
    
    # Validações
    assert len(results) == 1
    assert results[0]['id'] == '10'
    assert results[0]['sender_email'] == 'test@remetente.com'
    assert results[0]['subject'] == 'Teste'
    
    mock_mail.login.assert_called_once()
    mock_mail.logout.assert_called_once()
