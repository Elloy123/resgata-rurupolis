# Resgata Rurópolis

Site da ONG Resgata Rurópolis (Rurópolis-PA): animais para adoção, apadrinhamento mensal,
vaquinhas (doações via Mercado Pago), telefones úteis e página institucional.

Feito com Django 6.1 + Bootstrap 5. Conteúdo gerenciado pelo painel `/admin/`.

## Rodando localmente (Windows)

```powershell
.\rodar.ps1
```

O script cria o `venv` (se não existir), instala as dependências, cria o `.env`
(se não existir), aplica as migrações e inicia o servidor em http://127.0.0.1:8000.

Passo a passo manual:

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env        # e troque a SECRET_KEY
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py createsuperuser
.\venv\Scripts\python.exe manage.py runserver
```

## Testes

```powershell
.\venv\Scripts\python.exe manage.py test
```

O Mercado Pago é simulado nos testes; nenhuma cobrança real é feita.

## Mercado Pago

1. Pegue as credenciais em https://www.mercadopago.com.br/developers/panel
   (use as de **teste** durante o desenvolvimento).
2. Preencha `MERCADOPAGO_ACCESS_TOKEN` e `MERCADOPAGO_PUBLIC_KEY` no `.env`.

Sem o token, o site funciona normalmente, mas os formulários de doação e apadrinhamento
mostram um aviso de "temporariamente indisponível" (e a chave PIX, se cadastrada em
*Sobre a ONG*).

**Confirmação dos pagamentos.** O status de doações e apadrinhamentos é atualizado de duas formas,
sempre consultando a API do Mercado Pago (nunca confiando nos parâmetros recebidos):

- quando o doador volta do Mercado Pago para as páginas de obrigado / pendente / erro;
- pelos webhooks `/vaquinhas/webhook/mercadopago/` e `/apadrinhamento/webhook/mercadopago/`.

- pelo webhook único `/webhook/mercadopago/` (os antigos `/vaquinhas/webhook/...` e
  `/apadrinhamento/webhook/...` continuam funcionando).

### Passo a passo (teste)

1. Em https://www.mercadopago.com.br/developers/panel crie uma aplicação
   (pagamentos online, Checkout Pro, com assinaturas).
2. Em **Contas de teste**, crie um usuário **vendedor** e um **comprador**.
   Entre no painel com o vendedor de teste e copie as credenciais dele para o `.env`.
3. Reinicie o servidor e faça uma doação. Pague numa janela anônima, logado como o
   **comprador de teste**, com um cartão de teste (ex: Mastercard `5031 4332 1540 6351`,
   CVV `123`, validade `11/30`, CPF `12345678909`). O nome do titular define o resultado:
   `APRO` aprova, `OTHE` recusa, `CONT` deixa pendente.
4. **Apadrinhamento:** no formulário, use o **e-mail do comprador de teste**. A assinatura
   exige que o e-mail informado seja o da conta que vai pagar.
5. **Webhook:** em localhost o Mercado Pago não consegue avisar o site. Use `ngrok http 8000` e no `.env` coloque
   `SITE_URL=https://SEU-ENDERECO.ngrok-free.app`, o mesmo host em `ALLOWED_HOSTS` e a URL completa
   em `CSRF_TRUSTED_ORIGINS`. No painel → **Webhooks**, cadastre
   `https://SEU-ENDERECO.ngrok-free.app/webhook/mercadopago/` com os eventos **Pagamentos** e
   **Planos e assinaturas**, e use o botão de simular notificação.

Com `SITE_URL` público o site também envia `auto_return` (o doador volta sozinho ao site
após pagar) e o `notification_url` das doações.

### Passo a passo (produção)

1. No painel, ative as **credenciais de produção** (preenchendo os dados do negócio)
   e troque no `.env` do servidor para as credenciais `APP_USR-...`.
2. Cadastre o webhook de **produção** com `https://SEU-DOMINIO/webhook/mercadopago/`.
3. Faça uma doação real de valor baixo e confira o status em **Admin → Doações**.

Erros de integração aparecem em `logs/site.log`.

## Publicar no PythonAnywhere

Nos comandos abaixo, troque `USUARIO` pelo seu nome de usuário do PythonAnywhere.

### 1. Baixar o código (aba **Consoles → Bash**)

```bash
git clone https://github.com/Elloy123/resgata-rurupolis.git
cd resgata-rurupolis
ls /usr/bin/python3.1*          # veja as versões disponíveis (precisa ser 3.12 ou mais nova)
python3.13 -m venv venv         # use a versão mais nova da lista
source venv/bin/activate
pip install -r requirements.txt
```

Se o repositório for **privado**, o `git clone` pede usuário e senha. Use seu usuário do GitHub e,
como senha, um *token* criado em GitHub → Settings → Developer settings → Personal access tokens.

### 2. Criar o `.env` do servidor

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"   # copie a chave
nano .env
```

```
SECRET_KEY=<cole a chave gerada>
DEBUG=False
ALLOWED_HOSTS=USUARIO.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://USUARIO.pythonanywhere.com
SITE_URL=https://USUARIO.pythonanywhere.com
MERCADOPAGO_ACCESS_TOKEN=<seu token>
MERCADOPAGO_PUBLIC_KEY=<sua public key>
```

(Para salvar no nano: Ctrl+O, Enter, Ctrl+X.)

### 3. Banco de dados e arquivos estáticos

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Para levar os dados do computador (animais, vaquinhas, telefones, usuário admin), em vez do
`createsuperuser`, envie o `db.sqlite3` e a pasta `media/` pela aba **Files** para
`/home/USUARIO/resgata-rurupolis/` e rode `python manage.py migrate` de novo.

### 4. Criar o site (aba **Web**)

1. **Add a new web app** → **Manual configuration** → mesma versão do Python do passo 1.
2. **Virtualenv:** `/home/USUARIO/resgata-rurupolis/venv`
3. **WSGI configuration file:** apague o conteúdo e cole:

   ```python
   import os
   import sys

   path = '/home/USUARIO/resgata-rurupolis'
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ['DJANGO_SETTINGS_MODULE'] = 'resgata_rurupolis.settings'

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

4. **Static files:**

   | URL       | Directory                                     |
   |-----------|-----------------------------------------------|
   | `/static/` | `/home/USUARIO/resgata-rurupolis/staticfiles` |
   | `/media/`  | `/home/USUARIO/resgata-rurupolis/media`       |

5. Ative **Force HTTPS** e clique em **Reload**.

Se der erro, o motivo aparece no **Error log** (link na aba Web) e em `logs/site.log`.

### Atualizar o site depois de mudanças

```bash
cd ~/resgata-rurupolis
source venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Depois clique em **Reload** na aba Web.

**Conta gratuita:** o PythonAnywhere grátis só deixa o site acessar alguns sites externos.
Se as doações derem erro de conexão com o Mercado Pago (veja o Error log), será preciso uma
conta paga. Eventos e bazar funcionam normalmente, porque usam só o WhatsApp.

## Produção

No `.env` do servidor:

```
DEBUG=False
SECRET_KEY=<chave longa e aleatória>
ALLOWED_HOSTS=resgatarurupolis.org.br
CSRF_TRUSTED_ORIGINS=https://resgatarurupolis.org.br
SITE_URL=https://resgatarurupolis.org.br
```

Com `DEBUG=False` o site passa a exigir HTTPS (cookies seguros, HSTS, redirecionamento).
Rode `manage.py collectstatic` e configure o servidor web para servir `staticfiles/` e `media/`.
`manage.py check --deploy` lista o que ainda falta.

Erros do Mercado Pago e dos webhooks ficam em `logs/site.log`.
