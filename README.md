# SSH Remote

Cliente SSH desktop, semelhante ao PuTTY, com gerenciador de sessões salvas
(usuário e senha pré-definidos por sessão) e terminal em abas.

## Recursos

- Gerenciador de sessões na coluna lateral (criar, editar, duplicar, excluir)
- Cada sessão guarda: nome, host, porta, usuário e senha (ou chave privada)
- Senhas/passphrases ficam criptografadas em disco (`~/.ssh_remote/`), nunca em texto puro
- Área central em abas: cada sessão conectada abre em uma nova aba, sem precisar de janelas separadas
- Suporte a autenticação por senha ou por chave privada (RSA/Ed25519/ECDSA/DSS)

## Instalação

```bash
cd ssh-remote
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python run.py
```

1. Clique em **Nova** (coluna esquerda) e preencha host, porta, usuário e senha (ou chave).
2. Selecione a sessão na lista e clique em **Conectar ▶** (ou dê duplo clique).
3. Uma nova aba abre no centro da janela, já conectada com as credenciais salvas.
4. Repita para abrir quantas sessões quiser — cada conexão vira uma aba própria.
   Use **Fechar aba** (ou Ctrl+W) para encerrar a aba atual.

## Onde ficam os dados

- `~/.ssh_remote/sessions.json` — lista de sessões (senhas armazenadas criptografadas)
- `~/.ssh_remote/secret.key` — chave de criptografia local (permissão 600)

Ambos os arquivos ficam restritos ao usuário dono (chmod 600/700). Se você
copiar `sessions.json` para outra máquina, também precisa copiar `secret.key`,
senão as senhas não poderão ser descriptografadas.

## Limitações conhecidas

- O terminal faz uma emulação simples (não é um VT100 completo): programas que
  usam muito controle de cursor/tela cheia (`top`, `vim`, `htop`) podem não
  renderizar perfeitamente. Comandos de linha (bash, ls, cat, git, etc.)
  funcionam bem.
