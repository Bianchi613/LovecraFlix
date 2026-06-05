# LovecraFlix

Servidor local de streaming de filmes, séries e documentários com autenticação, transcodificação automática e interface estilo Netflix.

---

## O que é isso?

O LovecraFlix **não é um serviço online** — ele roda na **sua própria máquina** e serve os vídeos que você já tem no seu disco. Pense nele como um Netflix pessoal para o seu acervo local.

### O que você precisa ter antes de instalar

1. **Uma pasta com seus filmes** organizada em subpastas por gênero:
   ```
   E:\Filmes\
   ├── Terror\
   │   ├── O Exorcista (1973)\
   │   │   ├── O Exorcista (1973).mkv
   │   │   └── O Exorcista (1973).jpg     ← poster (opcional)
   │   └── ...
   ├── Ficcao Cientifica\
   ├── Series\
   │   └── Fringe\
   │       ├── Fringe.S01E01.mkv
   │       └── Fringe.S01E02.mkv
   └── Documentario\
   ```

2. **Um banco de dados SQLite** (`acervo.db`) com os metadados dos seus filmes. O `setup.py` cria um banco vazio com o schema correto — você precisará populá-lo com seus filmes.

> Filmes com múltiplas versões do mesmo idioma podem ter `[1]`, `[2]` no nome do arquivo — serão exibidos como versões alternativas. Para filmes divididos em partes fisicamente, use o campo `parte` no banco (veja abaixo).

---

## Instalação rápida

### 1. Pré-requisitos

- **Python 3.10+** → [python.org](https://python.org)
- **ffmpeg** → necessário para transcodificação automática e troca de faixa de áudio
  ```
  winget install Gyan.FFmpeg
  ```

### 2. Clone o repositório

```bash
git clone https://github.com/Bianchi613/LovecraFlix.git
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

O setup pergunta onde estão seus filmes, onde salvar o banco, a porta e cria seu usuário.

### 5. Inicie o servidor

Clique duas vezes em **`iniciar.bat`** ou:

```bash
cd backend
python app.py
```

Acesse **`http://localhost:8000`**.

---

## Funcionalidades

- **Home page** com grade de posters reais, carrossel em destaque e frases de Lovecraft rotativas
- **Autenticação** com login, cadastro e perfil com 18 avatares temáticos
- **Filmes** agrupados por título — múltiplas versões (PT/EN) com página de seleção
- **Filmes com partes** — marcação explícita no banco via campo `parte`, com auto-play entre partes
- **Troca de faixa de áudio** — filmes "Dual (PT + original)" têm botão PT/EN no player
- **Séries** agrupadas por pasta, episódios por temporada, navegação por idioma
- **Documentários** agrupados em coleções (ex: BBC) com lista de episódios
- **Filtros** por tipo e gênero incluindo 🐙 Horror Cósmico
- **Player** full-width com thumbnail do poster, legendas automáticas (.srt → WebVTT)
- **Auto-play** de próximo episódio com contagem regressiva de 10s
- **Recomendações** ao terminar conteúdo, personalizadas pelo histórico de avaliações
- **Avaliação por estrelas** (1–5) por filme, com média geral exibida
- **Transcodificação automática** via ffmpeg — H.265, AC3, DTS, AVI e outros

---

## Estrutura de arquivos

```
LovecraftianFlix/
├── backend/
│   ├── app.py              # Servidor FastAPI
│   ├── setup.py            # Configuração inicial (execute uma vez)
│   ├── converter.py        # Conversão em lote de arquivos incompatíveis
│   ├── criar_usuario.py    # Adicionar/atualizar usuários via terminal
│   └── requirements.txt
├── frontend/
│   ├── home.html           # Landing page
│   ├── login.html / cadastro.html / perfil.html
│   ├── index.html          # Grade principal
│   ├── player.html         # Player de vídeo
│   ├── filme.html          # Seleção de versão/parte
│   ├── series.html         # Episódios de série
│   ├── documentario.html   # Episódios de documentário
│   ├── app.js
│   └── style.css
├── config.json             # Criado pelo setup (caminhos e porta)
├── config.example.json     # Modelo de configuração
├── iniciar.bat             # Atalho Windows
└── README.md
```

---

## Banco de dados

### Tabela `filmes`

| Campo | Tipo | Descrição |
|---|---|---|
| `titulo_pt` | TEXT | Título em português |
| `titulo_original` | TEXT | Título original |
| `ano` | INTEGER | Ano |
| `genero` | TEXT | Gênero (ex: `Terror`, `Ficcao Cientifica`) |
| `subgenero` | TEXT | Subgênero (ex: `Horror Cosmico`) |
| `tipo` | TEXT | `filme`, `serie` ou `documentario` |
| `idioma` | TEXT | Idioma do áudio (ex: `Dual (PT + original)`) |
| `parte` | INTEGER | Parte do filme — `NULL` para filmes normais, `1`, `2`... para filmes divididos |
| `tem_legenda` | INTEGER | `1` se houver `.srt` junto |
| `arquivo_novo` | TEXT | Caminho absoluto para o vídeo |
| `poster_local` | TEXT | Caminho absoluto para o `.jpg` |
| `sinopse` | TEXT | Sinopse |
| `tmdb_url` | TEXT | Link TMDB |

### Tabela `usuarios`

| Campo | Tipo | Descrição |
|---|---|---|
| `nome` | TEXT | Nome de exibição |
| `email` | TEXT | Email (usado no login) |
| `senha_hash` | TEXT | Senha com bcrypt |
| `avatar` | TEXT | ID do avatar (ex: `octopus`) |

### Tabela `avaliacoes`

| Campo | Tipo | Descrição |
|---|---|---|
| `usuario_id` | INTEGER | FK para usuarios |
| `filme_id` | INTEGER | FK para filmes |
| `nota` | INTEGER | Nota de 1 a 5 |

---

## Compatibilidade de vídeo

| Formato | Comportamento |
|---|---|
| MP4/MKV com H.264 + AAC | Direto |
| MKV com H.264 + AC3/DTS | Só áudio convertido → AAC |
| MP4/MKV com H.265/HEVC | Vídeo transcodificado → H.264 |
| AVI, MPEG-2, XviD | Tudo transcodificado |
| Dual audio | Botão PT/EN no player para trocar faixa |

> Sem ffmpeg instalado, apenas H.264 + AAC/MP3 funcionam.

---

## API resumida

| Endpoint | Descrição |
|---|---|
| `GET /api/filmes` | Lista filmes (filtros: `genero`, `busca`, `tipo`) |
| `GET /api/filmes/versoes` | Versões/partes de um filme por título |
| `GET /api/series` | Séries agrupadas por pasta |
| `GET /api/colecoes` | Coleções de documentários |
| `GET /api/generos` | Gêneros com contagem |
| `GET /api/recomendacoes` | Sugestões personalizadas por avaliações |
| `GET /video?path=` | Streaming direto com Range |
| `GET /transcode?path=&audio_track=` | Streaming via ffmpeg (faixa de áudio opcional) |
| `POST /api/avaliar` | Salva avaliação (1–5 estrelas) |
| `PUT /api/filmes/{id}/parte` | Marca um arquivo como parte N de um filme |
| `POST /auth/login` | Login → JWT |

---

## Gerenciar usuários

```bash
cd backend
python criar_usuario.py
```
