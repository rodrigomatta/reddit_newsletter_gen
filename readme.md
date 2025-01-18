# Reddit Newsletter Generator

Este projeto é uma ferramenta automatizada que coleta as discussões mais relevantes de um subreddit específico e gera uma newsletter profissional em português. A ferramenta utiliza web scraping para coletar dados do Reddit, processa o conteúdo usando IA através da API da DeepSeek, e distribui a newsletter formatada via email.

## Características Principais

O projeto oferece uma solução completa para monitoramento e distribuição de conteúdo do Reddit, incluindo:

- Coleta automatizada dos posts mais populares do dia em um subreddit específico
- Extração de comentários relevantes e links mencionados
- Geração de conteúdo em português usando IA
- Formatação profissional com suporte a Markdown
- Conversão automática para HTML para emails mais atrativos
- Sistema de distribuição via email com suporte a HTML e texto plano

## Requisitos do Sistema

Para executar este projeto, você precisará ter:

- Python 3.10 ou superior
- Pip (gerenciador de pacotes Python)
- Acesso à internet
- Conta de email com suporte SMTP (gmail neste caso)
- Chave de API da DeepSeek ou OpenAI

## Dependências

O projeto utiliza as seguintes bibliotecas Python:

```
requests
pytz
python-dotenv
openai
markdown
```

## Instrução de configuração do Google para Envio de Emails (em caso de uso do Gmail)

Para utilizar uma conta Google para o envio de emails, é necessário configurar a autenticação de dois fatores e gerar uma senha de aplicativo. Este processo aumenta a segurança da sua conta e permite que o aplicativo envie emails de forma segura. Siga estas etapas:

1. Ative a Verificação em Duas Etapas na sua conta Google:
   - Acesse sua Conta Google
   - Vá para a seção de Segurança
   - Procure por "Verificação em duas etapas"
   - Siga o processo de ativação

2. Crie uma Senha de Aplicativo:
   - Após ativar a verificação em duas etapas, volte à seção de Segurança
   - Procure por "Senhas de app" ou "Senhas de aplicativo"
   - Selecione "Email" como o aplicativo
   - Escolha seu dispositivo
   - O Google irá gerar uma senha de 16 caracteres
   - Use esta senha no arquivo .env para SMTP_PASSWORD

3. Configure o SMTP no arquivo .env:
   ```env
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=seu_email@gmail.com
   SMTP_PASSWORD=sua_senha_de_aplicativo_gerada
   ```

Para mais informações sobre chaves de segurança Google, visite: https://www.google.com/intl/pt-BR/account/about/passkeys/

## Configuração do Projeto

1. Clone o repositório e instale as dependências:

```bash
git clone https://github.com/rodrigomatta/reddit_newsletter_gen
cd reddit_newsletter_gen
pip install -r requirements.txt
```

2. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# Configurações do Reddit
REDDIT_SUBREDDIT=nome_do_subreddit

# Configurações da API
OPENAI_API_KEY=sua_chave_api
OPENAI_BASE_URL=https://api.deepseek.com

# Configurações de Email
SMTP_SERVER=seu_servidor_smtp
SMTP_PORT=587
SMTP_USERNAME=seu_email
SMTP_PASSWORD=sua_senha
EMAIL_FROM=email_remetente
EMAIL_TO=email_destinatario
NEWSLETTER_TITLE=Título da Newsletter
```

## Estrutura do Projeto

O projeto é composto por três classes principais e funções auxiliares:

### EnhancedRedditScraper

Responsável pela coleta de dados do Reddit, oferecendo funcionalidades como:

- Coleta dos posts mais populares do dia
- Extração de comentários relevantes
- Identificação de links externos
- Processamento de metadados dos posts

### NewsletterGenerator

Gerencia a geração do conteúdo da newsletter utilizando IA, incluindo:

- Formatação profissional do conteúdo
- Geração de texto em português
- Estruturação do conteúdo em seções temáticas
- Inclusão de emojis e formatação Markdown

### Funções Auxiliares

- `save_content_to_json`: Armazena os dados coletados em formato JSON
- `send_email`: Gerencia o envio de emails com suporte a HTML e texto plano
- `main`: Coordena o fluxo completo de execução

## Uso

Para executar o projeto, simplesmente rode o script principal:

```bash
python main.py
```

O script irá:

1. Coletar os posts mais populares do subreddit configurado
2. Salvar os dados em um arquivo JSON
3. Gerar uma newsletter formatada
4. Enviar a newsletter por email

## Personalização

### Modificando o Prompt da IA

O prompt da IA pode ser personalizado editando o método `_prepare_prompt` na classe `NewsletterGenerator`. O prompt atual inclui instruções para:

- Estruturação do conteúdo em 6-8 temas principais
- Inclusão de emojis relevantes
- Formatação específica para cada seção
- Uso apropriado de termos técnicos em inglês

### Ajustando a Coleta de Dados

Os parâmetros de coleta podem ser modificados na chamada do método `collect_daily_content`:

```python
content = scraper.collect_daily_content(
    post_limit=20,    # Número de posts a coletar
    comments_per_post=5    # Número de comentários por post
)
```

## Tratamento de Erros

O projeto inclui tratamento abrangente de erros para:

- Falhas na conexão com o Reddit
- Erros na API da DeepSeek
- Problemas no envio de email
- Falhas na leitura/escrita de arquivos

## Contribuindo

Contribuições são bem-vindas! Por favor, siga estas etapas:

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo LICENSE para detalhes.

## Suporte

Para suporte, por favor abra uma issue no repositório do projeto.
