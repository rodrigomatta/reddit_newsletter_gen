import os
import time
import json
import re
import requests
import pytz
import smtplib
import openai
import markdown
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env para o ambiente
load_dotenv()

class EnhancedRedditScraper:
    def __init__(self, subreddit: str):
        """
        Inicializa o scraper com capacidades aprimoradas para análise do subreddit.
        
        Args:
            subreddit: Nome do subreddit a ser analisado
        """
        self.subreddit = subreddit
        self.headers = {'User-Agent': 'Mozilla/5.0'}  # Cabeçalho para simular um navegador
        self.base_url = f"https://www.reddit.com/r/{subreddit}"  # URL base do subreddit

    def get_top_daily_posts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Obtém os posts mais populares do dia.
        
        Args:
            limit: Número de posts a serem retornados
            
        Returns:
            Lista de posts ordenada por popularidade
        """
        url = f"{self.base_url}/top.json?t=day&limit={limit}"  # URL para obter os posts mais populares do dia
        response = requests.get(url, headers=self.headers)  # Faz a requisição HTTP

        if response.status_code != 200:  # Verifica se a requisição foi bem-sucedida
            print(f"Erro ao acessar os posts: {response.status_code}")
            return []

        posts = response.json()['data']['children']  # Extrai os posts da resposta JSON
        processed_posts = []

        for post in posts:
            post_data = post['data']
            # Adiciona URL do post e qualquer link externo mencionado
            post_data['reddit_url'] = f"https://reddit.com{post_data['permalink']}"  # URL completa do post
            if 'url' in post_data and not post_data['url'].startswith('https://reddit.com'):
                post_data['external_url'] = post_data['url']  # URL externa mencionada no post
            else:
                post_data['external_url'] = None
            processed_posts.append(post_data)

        # Ordena os posts por score (popularidade)
        return sorted(processed_posts, key=lambda x: x['score'], reverse=True)

    def get_post_comments(self, post_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém os comentários mais relevantes de um post, incluindo links mencionados.
        
        Args:
            post_id: ID do post
            limit: Número máximo de comentários a retornar
            
        Returns:
            Lista dos comentários mais relevantes
        """
        url = f"{self.base_url}/comments/{post_id}.json"  # URL para obter os comentários do post
        response = requests.get(url, headers=self.headers)  # Faz a requisição HTTP

        if response.status_code != 200:  # Verifica se a requisição foi bem-sucedida
            print(f"Erro ao acessar os comentários do post {post_id}: {response.status_code}")
            return []

        try:
            comments_data = response.json()[1]['data']['children']  # Extrai os comentários da resposta JSON
            processed_comments = []

            for comment in comments_data:
                if 'data' in comment and 'body' in comment['data']:
                    comment_data = comment['data']
                    # Extrai URLs mencionadas no corpo do comentário
                    urls = re.findall(
                        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|'
                        r'(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                        comment_data['body']
                    )
                    comment_data['mentioned_urls'] = urls  # Adiciona as URLs encontradas ao comentário
                    processed_comments.append(comment_data)

            # Ordena os comentários por score e limita o número de comentários retornados
            return sorted(processed_comments, key=lambda x: x['score'], reverse=True)[:limit]

        except (IndexError, KeyError) as e:
            print(f"Erro ao processar comentários do post {post_id}: {e}")
            return []

    def collect_daily_content(self, post_limit: int = 20, comments_per_post: int = 5) -> Dict:
        """
        Coleta o conteúdo diário mais relevante do subreddit.
        
        Args:
            post_limit: Número de posts a coletar
            comments_per_post: Número de comentários por post
            
        Returns:
            Dicionário com o conteúdo coletado
        """
        posts = self.get_top_daily_posts(post_limit)  # Obtém os posts mais populares do dia
        collected_content = []

        for post in posts:
            post_content = {
                'title': post.get('title', ''),  # Título do post
                'author': f"u/{post.get('author', 'desconhecido')}",  # Autor do post
                'score': post.get('score', 0),  # Score (popularidade) do post
                'reddit_url': post.get('reddit_url', ''),  # URL do post no Reddit
                'external_url': post.get('external_url', ''),  # URL externa mencionada no post
                'text': post.get('selftext', ''),  # Texto do post
                'created_utc': datetime.fromtimestamp(
                    post.get('created_utc', 0),
                    tz=pytz.UTC
                ).strftime('%Y-%m-%d %H:%M:%S UTC'),  # Data de criação do post
                'comments': []  # Lista de comentários do post
            }

            comments = self.get_post_comments(post['id'], comments_per_post)  # Obtém os comentários do post
            for comment in comments:
                comment_data = {
                    'author': f"u/{comment.get('author', 'desconhecido')}",  # Autor do comentário
                    'text': comment.get('body', ''),  # Texto do comentário
                    'score': comment.get('score', 0),  # Score do comentário
                    'mentioned_urls': comment.get('mentioned_urls', []),  # URLs mencionadas no comentário
                    'created_utc': datetime.fromtimestamp(
                        comment.get('created_utc', 0),
                        tz=pytz.UTC
                    ).strftime('%Y-%m-%d %H:%M:%S UTC')  # Data de criação do comentário
                }
                post_content['comments'].append(comment_data)  # Adiciona o comentário ao post

            collected_content.append(post_content)  # Adiciona o post ao conteúdo coletado
            time.sleep(1)  # Respeita o limite de requisições para evitar bloqueios

        return {
            'subreddit': self.subreddit,  # Nome do subreddit
            'date': datetime.now(pytz.UTC).strftime('%Y-%m-%d'),  # Data de coleta
            'posts': collected_content  # Lista de posts coletados
        }

class NewsletterGenerator:
    def __init__(self, api_key: str):
        """
        Inicializa o gerador de newsletter.
        
        Args:
            api_key: Chave da API OpenAI/DeepSeek
        """
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")  # URL base da API
        )

    def generate_newsletter(self, content: Dict) -> str:
        """
        Gera a newsletter em português usando a API.
        
        Args:
            content: Dicionário com o conteúdo do Reddit
            
        Returns:
            Newsletter formatada em Markdown
        """
        prompt = self._prepare_prompt(content)  # Prepara o prompt para a API

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",  # Modelo da API
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um escritor profissional de newsletter para a comunidade de IA. "
                            "Escreva a newsletter em português do Brasil, mantendo termos técnicos em inglês quando apropriado. "
                            "Use formatação Markdown e inclua todos os links relevantes mencionados no conteúdo. "
                            "Mantenha um tom profissional mas acessível, explicando conceitos técnicos de forma clara."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,  # Controla a criatividade da resposta
            )
            newsletter_text = response.choices[0].message.content  # Extrai o texto da resposta
            return newsletter_text

        except Exception as e:
            print(f"Erro ao gerar newsletter: {e}")
            return ""

    def _prepare_prompt(self, content: Dict) -> str:
        """
        Prepara o prompt para a API com o conteúdo coletado.
        
        Args:
            content: Dicionário com o conteúdo do Reddit
            
        Returns:
            Prompt formatado
        """
        newsletter_title = os.getenv("NEWSLETTER_TITLE", "LocalLLaMA Community Newsletter")  # Título da newsletter

        prompt = (
            f"Crie uma newsletter profissional para r/{content['subreddit']} "
            f"baseada nas principais discussões de hoje ({content['date']}).\n\n"
            "Conteúdo para análise:\n"
        )

        for post in content['posts']:
            prompt += f"\nPost: {post['title']}\n"
            prompt += f"Autor: {post['author']}\n"
            prompt += f"Score: {post['score']}\n"
            prompt += f"Link do Reddit: {post['reddit_url']}\n"
            if post['external_url']:
                prompt += f"Link externo: {post['external_url']}\n"
            if post['text']:
                prompt += f"Conteúdo: {post['text']}\n"

            prompt += "\nComentários principais:\n"
            for comment in post['comments']:
                prompt += f"- {comment['author']}: {comment['text']}\n"
                prompt += f"  Score: {comment['score']}\n"
                if comment['mentioned_urls']:
                    prompt += (
                        f"  Links mencionados: {', '.join(comment['mentioned_urls'])}\n"
                    )

        # Adiciona instruções detalhadas para formatação
         prompt += f"""
Por favor, elabore a newsletter seguindo estas diretrizes:

1. **Título**: "{newsletter_title}"
2. **Data**: Incluir a data atual no formato "## [Data Atual]"
3. **Estrutura**: Organizar o conteúdo em 5 a 6 temas principais
4. **Para cada tema**:
   - Iniciar com um parágrafo introdutório envolvente
   - Incluir números específicos e detalhes técnicos relevantes
   - Referenciar usuários utilizando o formato "**u/username**"
   - Destacar termos-chave e estatísticas em **negrito**
   - Incluir links relevantes mencionados nos posts e comentários
5. **Seção Final**: Concluir com uma seção intitulada "Perspectivas Futuras"
6. **Formatação**: Utilizar Markdown para toda a formatação
7. **Foco**: Priorizar precisão técnica e insights práticos
8. **Idioma**: Escrever em português do Brasil, mantendo termos técnicos em inglês quando apropriado
9. **Emojis**: Iniciar cada tema com um emoji relevante para aumentar o engajamento
10. **Assinatura**: Finalizar com uma nota sobre a origem das informações
"""
        return prompt

def save_content_to_json(content: Dict, filename: str = "reddit_content.json") -> None:
    """
    Salva o conteúdo coletado do Reddit em um arquivo JSON.
    
    Args:
        content: Dicionário com o conteúdo do Reddit
        filename: Nome do arquivo JSON para salvar
    """
    try:
        # Verifica se o arquivo já existe e o remove
        if os.path.exists(filename):
            os.remove(filename)
            print(f"Arquivo {filename} existente foi removido.")

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)
        print(f"Conteúdo salvo com sucesso em {filename}")
    except Exception as e:
        print(f"Erro ao salvar o conteúdo em JSON: {e}")

def send_email(newsletter_text: str) -> bool:
    """
    Envia o texto gerado por e-mail utilizando as configurações do .env.
    Converte o Markdown para HTML antes de enviar.
    
    Args:
        newsletter_text: Conteúdo em Markdown para enviar no corpo do e-mail
        
    Returns:
        bool: True se o email foi enviado com sucesso, False caso contrário
    """
    smtp_server = os.getenv("SMTP_SERVER")  # Servidor SMTP
    smtp_port = int(os.getenv("SMTP_PORT", "587"))  # Porta SMTP
    smtp_username = os.getenv("SMTP_USERNAME")  # Usuário SMTP
    smtp_password = os.getenv("SMTP_PASSWORD")  # Senha SMTP
    email_from = os.getenv("EMAIL_FROM", smtp_username)  # Remetente do e-mail
    email_to = os.getenv("EMAIL_TO")  # Destinatário do e-mail
    newsletter_title = os.getenv("NEWSLETTER_TITLE", "LocalLLaMA Community Newsletter")  # Título da newsletter

    if not (smtp_server and smtp_port and smtp_username and smtp_password and email_to):
        print("Erro: Variáveis de ambiente SMTP não configuradas corretamente.")
        return False

    subject = newsletter_title  # Assunto do e-mail

    # Converte Markdown para HTML com extensões extras
    html_content = markdown.markdown(
        newsletter_text,
        extensions=[
            'markdown.extensions.extra',        # Tabelas, código destacado, etc
            'markdown.extensions.codehilite',   # Destaque de sintaxe
            'markdown.extensions.toc',          # Índice de conteúdo
            'markdown.extensions.sane_lists'    # Melhor tratamento de listas
        ]
    )

    # Adiciona CSS básico para melhorar a aparência
    html_template = f"""
    <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                }}
                a {{
                    color: #3498db;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                code {{
                    background-color: #f8f9fa;
                    padding: 2px 4px;
                    border-radius: 4px;
                    font-family: monospace;
                }}
                pre {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    overflow-x: auto;
                }}
                blockquote {{
                    border-left: 4px solid #3498db;
                    margin: 0;
                    padding-left: 20px;
                    color: #666;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
                ul, ol {{
                    padding-left: 20px;
                }}
                li {{
                    margin-bottom: 8px;
                }}
                strong {{
                    color: #2c3e50;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
    </html>
    """

    # Cria a mensagem com múltiplas partes (texto plano + HTML)
    msg = MIMEMultipart("alternative")
    msg['From'] = email_from
    msg['To'] = email_to
    msg['Subject'] = subject

    # Anexa tanto a versão em texto plano quanto a versão HTML
    text_part = MIMEText(newsletter_text, 'plain')
    html_part = MIMEText(html_template, 'html')
    
    msg.attach(text_part)  # Versão em texto plano como fallback
    msg.attach(html_part)  # Versão HTML como preferencial

    try:
        # Conecta ao servidor SMTP com timeout de 30 segundos
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.set_debuglevel(1)  # Habilita logs detalhados
        print(f"Conectado ao servidor SMTP: {smtp_server}:{smtp_port}")
        
        # Inicia TLS
        server.starttls()
        print("Conexão TLS estabelecida")
        
        # Login
        server.login(smtp_username, smtp_password)
        print(f"Login realizado com sucesso para: {smtp_username}")
        
        # Envia o email
        server.sendmail(email_from, email_to, msg.as_string())
        print(f"Email enviado para: {email_to}")
        
        # Fecha conexão
        server.quit()
        print("Conexão SMTP fechada")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("Erro de autenticação SMTP. Verifique seu usuário e senha.")
        return False
    except smtplib.SMTPServerDisconnected:
        print("Erro: Servidor SMTP desconectou. Verifique sua conexão e as configurações do servidor.")
        return False
    except smtplib.SMTPException as e:
        print(f"Erro SMTP: {str(e)}")
        return False
    except Exception as e:
        print(f"Erro inesperado ao enviar e-mail: {str(e)}")
        return False

def main():
    """
    Função principal que executa o processo completo de:
    - Coletar conteúdo do Reddit
    - Salvar o conteúdo em um arquivo JSON
    - Gerar a newsletter via API
    - Converter Markdown para HTML
    - Enviar por e-mail
    """
    # Carrega variáveis do .env
    subreddit = os.getenv("REDDIT_SUBREDDIT")  # Nome do subreddit
    openai_api_key = os.getenv("OPENAI_API_KEY")  # Chave da API OpenAI/DeepSeek

    if not subreddit or not openai_api_key:
        print("Erro: Variáveis de ambiente (REDDIT_SUBREDDIT ou OPENAI_API_KEY) não configuradas.")
        return

    try:
        # Inicializa as classes
        scraper = EnhancedRedditScraper(subreddit)  # Inicializa o scraper do Reddit
        newsletter_gen = NewsletterGenerator(openai_api_key)  # Inicializa o gerador de newsletter

        # Coleta conteúdo do Reddit
        print("Coletando conteúdo do Reddit...")
        content = scraper.collect_daily_content(
            post_limit=20,
            comments_per_post=5
        )

        # Salva o conteúdo em um arquivo JSON
        save_content_to_json(content, "reddit_content.json")

        # Gera a newsletter
        print("Gerando newsletter...")
        newsletter = newsletter_gen.generate_newsletter(content)

        if newsletter.strip():
            # Envia o email diretamente
            print("Enviando newsletter por e-mail...")
            if send_email(newsletter):
                print("Newsletter enviada com sucesso!")
            else:
                print("Falha no envio da newsletter. Verifique os logs acima para mais detalhes.")
        else:
            print("Erro: Não foi possível gerar a newsletter (texto vazio).")

    except Exception as e:
        print(f"Erro durante a execução: {e}")

if __name__ == "__main__":
    main()
