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
        self.subreddit = subreddit
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.base_url = f"https://www.reddit.com/r/{subreddit}"

    def get_top_daily_posts(self, limit: int = 20) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/top.json?t=day&limit={limit}"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"Erro ao acessar os posts: {response.status_code}")
            return []

        posts = response.json()['data']['children']
        processed_posts = []
        for post in posts:
            post_data = post['data']
            post_data['reddit_url'] = f"https://reddit.com{post_data['permalink']}"
            if 'url' in post_data and not post_data['url'].startswith('https://reddit.com'):
                post_data['external_url'] = post_data['url']
            else:
                post_data['external_url'] = None
            processed_posts.append(post_data)
        return sorted(processed_posts, key=lambda x: x['score'], reverse=True)

    def get_post_comments(self, post_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/comments/{post_id}.json"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"Erro ao acessar os comentários do post {post_id}: {response.status_code}")
            return []

        try:
            comments_data = response.json()[1]['data']['children']
            processed_comments = []
            for comment in comments_data:
                if 'data' in comment and 'body' in comment['data']:
                    comment_data = comment['data']
                    urls = re.findall(
                        r'http[s]?://(?:[a-zA-Z0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                        comment_data['body']
                    )
                    comment_data['mentioned_urls'] = urls
                    processed_comments.append(comment_data)
            return sorted(processed_comments, key=lambda x: x['score'], reverse=True)[:limit]
        except (IndexError, KeyError) as e:
            print(f"Erro ao processar comentários do post {post_id}: {e}")
            return []

    def collect_daily_content(self, post_limit: int = 20, comments_per_post: int = 5) -> Dict:
        posts = self.get_top_daily_posts(post_limit)
        collected_content = []
        for post in posts:
            post_content = {
                'title': post.get('title', ''),
                'author': f"u/{post.get('author', 'desconhecido')}",
                'score': post.get('score', 0),
                'reddit_url': post.get('reddit_url', ''),
                'external_url': post.get('external_url', ''),
                'text': post.get('selftext', ''),
                'created_utc': datetime.fromtimestamp(
                    post.get('created_utc', 0),
                    tz=pytz.UTC
                ).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'comments': []
            }
            comments = self.get_post_comments(post['id'], comments_per_post)
            for comment in comments:
                comment_data = {
                    'author': f"u/{comment.get('author', 'desconhecido')}",
                    'text': comment.get('body', ''),
                    'score': comment.get('score', 0),
                    'mentioned_urls': comment.get('mentioned_urls', []),
                    'created_utc': datetime.fromtimestamp(
                        comment.get('created_utc', 0),
                        tz=pytz.UTC
                    ).strftime('%Y-%m-%d %H:%M:%S UTC')
                }
                post_content['comments'].append(comment_data)
            collected_content.append(post_content)
            time.sleep(1)
        return {
            'subreddit': self.subreddit,
            'date': datetime.now(pytz.UTC).strftime('%Y-%m-%d'),
            'posts': collected_content
        }

class NewsletterGenerator:
    def __init__(self, primary_api_key: str):
        self.primary_api_key = primary_api_key
        self.primary_base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        self.primary_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.backup_api_key = os.getenv("OPENAI_BACKUP_API_KEY")
        self.backup_base_url = os.getenv("OPENAI_BACKUP_BASE_URL", "https://api.openai.com/v1")
        self.backup_model = os.getenv("OPENAI_BACKUP_MODEL", "gpt-4")
        self.primary_client = None
        self.backup_client = None

    def _initialize_primary_client(self):
        return openai.OpenAI(
            api_key=self.primary_api_key,
            base_url=self.primary_base_url
        )

    def _initialize_backup_client(self):
        return openai.OpenAI(
            api_key=self.backup_api_key,
            base_url=self.backup_base_url
        )

    def _check_deepseek_availability(self) -> bool:
        try:
            if not self.primary_client:
                self.primary_client = self._initialize_primary_client()
            self.primary_client.chat.completions.create(
                model=self.primary_model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            print(f"DeepSeek API indisponível: {e}")
            return False

    def generate_newsletter(self, content: Dict) -> str:
        prompt = self._prepare_prompt(content)
        if self._check_deepseek_availability():
            try:
                newsletter_text = self._generate_with_deepseek(prompt)
                return newsletter_text
            except Exception as e:
                print(f"Erro ao gerar com DeepSeek: {e}")
        if self.backup_api_key:
            try:
                newsletter_text = self._generate_with_openai(prompt)
                return newsletter_text
            except Exception as e:
                print(f"Erro ao gerar com OpenAI: {e}")
                raise Exception("Todos os provedores LLM falharam")
        else:
            raise Exception("API de backup não configurada e DeepSeek indisponível")

    def _generate_with_deepseek(self, prompt: str) -> str:
        if not self.primary_client:
            self.primary_client = self._initialize_primary_client()
        response = self.primary_client.chat.completions.create(
            model=self.primary_model,
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
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _generate_with_openai(self, prompt: str) -> str:
        if not self.backup_client:
            self.backup_client = self._initialize_backup_client()
        response = self.backup_client.chat.completions.create(
            model=self.backup_model,
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
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _prepare_prompt(self, content: Dict) -> str:
        newsletter_title = os.getenv("NEWSLETTER_TITLE", "LocalLLaMA Community Newsletter")
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
                    prompt += f"  Links mencionados: {', '.join(comment['mentioned_urls'])}\n"
        prompt += f"""
Por favor, elabore a newsletter seguindo estas diretrizes:

1. **Título**: "{newsletter_title}"
2. **Data**: Incluir a data atual no formato "## [Data Atual]"
3. **Estrutura**: Organizar o conteúdo em 6 a 7 temas principais
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
    try:
        if os.path.exists(filename):
            os.remove(filename)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erro ao salvar o conteúdo em JSON: {e}")

def send_email(newsletter_text: str) -> bool:
    newsletter_text = newsletter_text.replace("```markdown", "").replace("```", "")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_from = os.getenv("EMAIL_FROM", smtp_username)
    email_to_string = os.getenv("EMAIL_TO")
    newsletter_title = os.getenv("NEWSLETTER_TITLE", "LocalLLaMA Community Newsletter")

    if not (smtp_server and smtp_port and smtp_username and smtp_password and email_to_string):
        print("Erro: Variáveis de ambiente SMTP não configuradas corretamente.")
        return False

    email_to_list = [email.strip() for email in email_to_string.split(',')]
    if not email_to_list:
        print("Erro: Nenhum endereço de email destinatário configurado.")
        return False

    subject = newsletter_title
    html_content = markdown.markdown(
        newsletter_text,
        extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.sane_lists'
        ]
    )

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

    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.starttls()
        server.login(smtp_username, smtp_password)
        successful_sends = 0
        for email_to in email_to_list:
            try:
                msg = MIMEMultipart("alternative")
                msg['From'] = email_from
                msg['To'] = email_to
                msg['Subject'] = subject
                html_part = MIMEText(html_template, 'html')
                msg.attach(html_part)
                server.sendmail(email_from, email_to, msg.as_string())
                successful_sends += 1
            except Exception as e:
                print(f"Erro ao enviar email para {email_to}: {str(e)}")
                continue
        server.quit()
        return successful_sends == len(email_to_list)
    except Exception as e:
        print(f"Erro ao enviar e-mail: {str(e)}")
        return False

def main():
    subreddit = os.getenv("REDDIT_SUBREDDIT")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not subreddit or not openai_api_key:
        print("Erro: Variáveis de ambiente (REDDIT_SUBREDDIT ou OPENAI_API_KEY) não configuradas.")
        return

    try:
        scraper = EnhancedRedditScraper(subreddit)
        newsletter_gen = NewsletterGenerator(openai_api_key)
        content = scraper.collect_daily_content(post_limit=20, comments_per_post=5)
        save_content_to_json(content, "reddit_content.json")
        newsletter = newsletter_gen.generate_newsletter(content)
        if newsletter.strip():
            if send_email(newsletter):
                print("Newsletter enviada com sucesso!")
            else:
                print("Falha no envio da newsletter.")
        else:
            print("Erro: Newsletter vazia.")
    except Exception as e:
        print(f"Erro durante a execução: {e}")

if __name__ == "__main__":
    main()
