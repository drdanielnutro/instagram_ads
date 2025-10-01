"""
Web Fetch Tool for Google ADK
Ferramenta customizada para fazer fetch real de páginas web e extrair conteúdo.
"""

import logging
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse
import trafilatura
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)


def web_fetch_tool(url: str, tool_context: Optional[Any] = None) -> Dict[str, Any]:
    """
    Faz o fetch de uma página web e extrai seu conteúdo HTML e texto.

    Esta ferramenta realiza uma requisição HTTP para a URL fornecida,
    extrai o HTML completo e usa Trafilatura para extrair o texto principal,
    removendo elementos desnecessários como menus, anúncios e rodapés.

    Args:
        url: A URL da página web para fazer fetch
        tool_context: Contexto da ferramenta injetado pelo ADK (opcional)

    Returns:
        Dict contendo:
        - text_content: Texto principal extraído via Trafilatura
        - title: Título da página
        - meta_description: Meta descrição
        - status: 'success' ou 'error'
        - error_message: Mensagem de erro se houver
        - metadata: Metadados adicionais extraídos do HTML
    """

    # Validar URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {
                "status": "error",
                "error_message": f"URL inválida: {url}",
                "text_content": "",
                "metadata": {}
            }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Erro ao parsear URL: {str(e)}",
            "text_content": "",
            "metadata": {}
        }

    # Configurar sessão com retry strategy
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Headers para evitar bloqueios
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        logger.info(f"Fazendo fetch da URL: {url}")

        # Fazer requisição
        response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()

        # Obter HTML
        html_content = response.text

        # Extrair texto principal com Trafilatura
        extracted = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=True,
            include_links=True,
            output_format='json',
            target_language='pt'
        )

        # Parse do resultado do Trafilatura
        import json
        if extracted:
            try:
                extracted_data = json.loads(extracted)
                text_content = extracted_data.get('text', '')
            except:
                text_content = extracted if isinstance(extracted, str) else ''
        else:
            # Fallback para BeautifulSoup se Trafilatura falhar
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remover scripts e styles
            for script in soup(["script", "style"]):
                script.decompose()

            text_content = soup.get_text(separator='\n', strip=True)

        # Extrair metadados com BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Título
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Meta description
        meta_description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            meta_description = meta_desc.get('content', '')

        # Extrair outros metadados úteis
        metadata = {
            'title': title,
            'meta_description': meta_description,
            'url': response.url,  # URL final após redirects
            'status_code': response.status_code,
            'content_length': len(html_content),
            'text_length': len(text_content)
        }

        # Extrair Open Graph tags se disponíveis
        og_tags = {}
        for tag in soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')}):
            property_name = tag.get('property', '').replace('og:', '')
            og_tags[property_name] = tag.get('content', '')

        if og_tags:
            metadata['open_graph'] = og_tags

        # Extrair headings principais
        h1_tags = soup.find_all('h1')
        if h1_tags:
            metadata['h1_headings'] = [h.get_text(strip=True) for h in h1_tags[:3]]

        # Salvar no estado se tool_context disponível
        if tool_context and hasattr(tool_context, 'state'):
            tool_context.state['last_fetched_url'] = url
            tool_context.state['last_fetch_status'] = 'success'
            logger.info(f"Conteúdo salvo no estado para URL: {url}")

        return {
            "status": "success",
            "text_content": text_content,
            "title": title,
            "meta_description": meta_description,
            "metadata": metadata,
            "error_message": None
        }

    except requests.exceptions.Timeout:
        error_msg = f"Timeout ao acessar {url}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error_message": error_msg,
            "text_content": "",
            "metadata": {}
        }

    except requests.exceptions.RequestException as e:
        error_msg = f"Erro na requisição: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error_message": error_msg,
            "text_content": "",
            "metadata": {}
        }

    except Exception as e:
        error_msg = f"Erro inesperado: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error_message": error_msg,
            "text_content": "",
            "metadata": {}
        }
    finally:
        session.close()