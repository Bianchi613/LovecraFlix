# LovecraFlix

Servidor local de streaming de filmes, séries e documentários com autenticação, transcodificação automática e interface estilo Netflix.

---

## O que é isso?

O LovecraFlix **não é um serviço online** — ele roda na **sua própria máquina** e serve os vídeos que você já tem no seu disco. Pense nele como um Netflix pessoal para o seu acervo local.

### O que você precisa ter antes de instalar

1. **Uma pasta com seus filmes** organizada em subpastas por gênero, por exemplo:
   ```
   E:\Filmes\
   ├── Terror\
   │   ├── O Exorcista (1973)\
   │   │   ├── O Exorcista (1973).mkv
   │   │   └── O Exorcista (1973).jpg     ← poster (opcional)
   │   └── ...
   ├── Ficcao Cientifica\
   ├── Comedia\
   └── Series\
       └── Fringe\
           ├── Fringe.S01E01.mkv
           └── Fringe.S01E02.mkv
   ```

2. **Um banco de dados SQLite** (`acervo.db`) com os metadados dos seus filmes (títulos, sinopses, gêneros, caminhos dos arquivos). O LovecraFlix lê esse banco — ele não varre a pasta automaticamente.

> Se você não tem o banco ainda, o `setup.py` cria um banco **vazio** com o schema correto. Você precisará popular ele com seus filmes (manualmente ou com um script organizador separado).

---

## Instalação rápida

### 1. Pré-requisitos

- **Python 3.10+** → [python.org](https://python.org)
- **ffmpeg** → necessário para tocar H.265, AC3, AVI e outros formatos incompatíveis com o browser
  ```
  winget install Gyan.FFmpeg
  ```

### 2. Clone o repositório

```bash
git clone https://github.com/seu-usuario/LovecraftianFlix.git
cd LovecraftianFlix
```

### 3. Instale as dependências Python

```bash
pip install -r backend/requirements.txt
```

### 4. Execute o setup (primeira vez)

```bash
cd backend
python setup.py
```

O setup vai perguntar:
- **Pasta de filmes** — onde seus vídeos estão (ex: `E:\Filmes`)
- **Caminho do banco** — onde salvar o `acervo.db` (padrão: dentro da pasta de filmes)
- **Porta** — padrão `8000`
- **Usuário** — nome, email e senha para o login

### 5. Inicie o servidor

Clique duas vezes em **`iniciar.bat`** (Windows) ou:

```bash
cd backend
python app.py
```

Acesse **`http://localhost:8000`** no browser.

---

## Estrutura de arquivos

```
LovecraftianFlix/
├── backend/
│   ├── app.py              # Servidor FastAPI — toda a lógica de API e streaming
│   ├── setup.py            # Configuração inicial (execute uma vez)
│   ├── converter.py        # Conversão em lote de arquivos incompatíveis
│   ├── criar_usuario.py    # Adicionar/atualizar usuários via terminal
│   └── requirements.txt
├── frontend/
│   ├── home.html           # Landing page (pré-login)
│   ├── login.html          # Tela de login
│   ├── cadastro.html       # Tela de cadastro
│   ├── perfil.html         # Edição de perfil e avatar
│   ├── index.html          # Grade principal de filmes/séries
│   ├── player.html         # Player de vídeo
│   ├── filme.html          # Seleção de versão de um filme
│   ├── series.html         # Episódios de uma série
│   ├── documentario.html   # Episódios de uma coleção de documentários
│   ├── app.js              # Lógica da interface principal
│   └── style.css
├── config.json             # Criado pelo setup — caminhos e configurações
├── iniciar.bat             # Atalho Windows (detecta primeiro uso automaticamente)
└── README.md
```

---

## Funcionalidades

- **Home page** com grade de posters reais, carrossel em destaque e frases de Lovecraft
- **Autenticação** com login, cadastro e perfil com avatar customizável (18 avatares temáticos)
- **Filmes** agrupados por título — múltiplas versões (PT/EN) com página de seleção
- **Séries** agrupadas por pasta com episódios organizados por temporada e idioma
- **Documentários** agrupados em coleções (ex: BBC) com lista de episódios
- **Filtros** por tipo (Filmes / Séries / Documentários) e gênero incluindo 🐙 Horror Cósmico
- **Player** full-width com thumbnail do poster e legendas automáticas (.srt → WebVTT)
- **Transcodificação automática** — detecta codec via ffprobe e converte H.265, AC3, DTS etc. em tempo real

---

## Banco de dados

O `acervo.db` é um SQLite com duas tabelas:

### Tabela `filmes`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER | Identificador único |
| `titulo_pt` | TEXT | Título em português |
| `titulo_original` | TEXT | Título original |
| `ano` | INTEGER | Ano de lançamento |
| `genero` | TEXT | Gênero principal (ex: `Terror`, `Ficcao Cientifica`) |
| `subgenero` | TEXT | Subgênero (ex: `Horror Cosmico`) |
| `tipo` | TEXT | `filme`, `serie` ou `documentario` |
| `idioma` | TEXT | Idioma do áudio |
| `tem_legenda` | INTEGER | `1` se houver `.srt` junto ao arquivo |
| `arquivo_novo` | TEXT | Caminho absoluto para o arquivo de vídeo |
| `poster_local` | TEXT | Caminho absoluto para o `.jpg` do poster |
| `sinopse` | TEXT | Descrição do filme |
| `tmdb_url` | TEXT | Link para o TMDB |

### Tabela `usuarios` (criada automaticamente pelo setup)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER | Identificador único |
| `nome` | TEXT | Nome de exibição |
| `email` | TEXT | Email único (usado no login) |
| `senha_hash` | TEXT | Senha com bcrypt |
| `avatar` | TEXT | ID do avatar (ex: `octopus`) |

---

## Compatibilidade de vídeo

O player tenta reprodução direta e, se o codec for incompatível, transcodifica via ffmpeg automaticamente:

| Formato | Comportamento |
|---|---|
| MP4/MKV com H.264 + AAC | Direto — sem processamento extra |
| MKV com H.264 + AC3/DTS | Só áudio convertido → AAC |
| MP4/MKV com H.265/HEVC | Vídeo transcodificado → H.264 |
| AVI, MPEG-2, XviD | Tudo transcodificado via ffmpeg ultrafast |

> Sem ffmpeg instalado, apenas H.264 + AAC/MP3 funcionam.

---

## API resumida

| Endpoint | Descrição |
|---|---|
| `GET /api/filmes` | Lista filmes (filtros: `genero`, `busca`, `tipo`) |
| `GET /api/series` | Séries agrupadas por pasta |
| `GET /api/colecoes` | Coleções de documentários |
| `GET /api/generos` | Gêneros com contagem |
| `GET /video?path=` | Streaming direto com Range requests |
| `GET /transcode?path=` | Streaming via ffmpeg |
| `GET /poster?path=` | Serve imagem de poster |
| `GET /subtitle?path=` | Serve legenda SRT → WebVTT |
| `POST /auth/login` | Login → JWT |
| `PUT /api/perfil` | Atualiza nome e avatar |

---

## Gerenciar usuários

Para adicionar ou alterar a senha de um usuário:

```bash
cd backend
python criar_usuario.py
```
