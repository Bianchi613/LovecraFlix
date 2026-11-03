# Segurança do LovecraFlix

**Atualizado em 2026-11-03.** Alterações do [PR #1](https://github.com/Bianchi613/LovecraFlix/pull/1), mescladas na `main`. Revisão estática; a aplicação não foi executada ou submetida a um teste de invasão neste atendimento.

## O que mudou

| Área | Mudança |
| --- | --- |
| Assinatura de sessão | Removida a string fixa usada como `JWT_SECRET`. O segredo vem de `LOVECRAFLIX_JWT_SECRET`, `jwt_secret` em configuração local ou é gerado automaticamente e guardado em `.lovecraflix_jwt_secret`. |
| Validade | Novos JWTs incluem campo de expiração (`exp`), com prazo de sete dias. |
| Acesso a arquivos | `/poster`, `/subtitle`, `/video`, `/transcode` e `/api/open-vlc` passam pelo verificador `safe_media_path`, limitado a `filmes_dir` e às extensões esperadas. |
| Leitura de vídeo | Cabeçalhos `Range` inválidos ou fora dos limites retornam HTTP 416, em vez de provocar falhas inesperadas. |
| Entrada SQL | Filtro de gênero em recomendações passa a usar parâmetros SQL. |
| Arquivos locais | `.gitignore` impede novos commits acidentais de `config.json`, bancos locais e segredo gerado. |

## Configuração após a atualização

O `config.json` deve apontar corretamente para a pasta do acervo. O servidor **não deve ter acesso irrestrito a outras pastas**, nem receber uma pasta raiz genérica como `C:/` ou `/`. Exemplo com dados fictícios:

```json
{
  "db_path": "D:/Midia/_organizer/acervo.db",
  "filmes_dir": "D:/Midia/Filmes",
  "host": "127.0.0.1",
  "port": 8000
}
```

Se `filmes_dir` não estiver configurado, o código usa a pasta `Filmes` dentro do repositório como limite. Arquivos do catálogo apontando para fora dessa pasta resultarão em HTTP 404 até que a configuração seja corrigida.

Para ambientes persistentes, defina `LOVECRAFLIX_JWT_SECRET` com uma string aleatória de pelo menos 32 caracteres, **fora do código e do repositório**, ou preserve o arquivo local `.lovecraflix_jwt_secret` gerado na primeira inicialização. O arquivo não deve ser compartilhado. Se houver múltiplas instâncias, elas precisam usar o **mesmo segredo seguro**, caso contrário os tokens serão incompatíveis.

**Efeito esperado:** tokens emitidos com a chave fixa antiga deixam de ser aceitos e usuários precisam fazer login novamente. Trocar o segredo intencionalmente revoga as sessões existentes.

## Testes recomendados

```bash
python -m py_compile backend/app.py
```

Faça também testes manuais em uma cópia do acervo:

1. Reinicie o servidor duas vezes e confirme que um login continua válido enquanto o segredo persistir.
2. Faça novo cadastro/login, valide `/auth/me` e confirme a expiração de tokens.
3. Tente buscar um arquivo existente **fora** de `filmes_dir` por `/video?path=`: deve retornar 404.
4. Teste pôsteres, legendas, streaming e transcodificação de arquivos válidos dentro da pasta.
5. Confirme `Range` válido (206), inválido (416), e arquivo inexistente (404).
6. Verifique o lançamento do VLC apenas após autenticação e para um arquivo de mídia permitido.
7. Confira recomendações e avaliações usando o banco existente.

## Limitações importantes

**Não considere o LovecraFlix pronto para ser exposto à internet.** A restrição de pasta impede leitura arbitrária de arquivos, mas as rotas de mídia e várias rotas de metadados **ainda não exigem autenticação**; o programa foi desenhado para uso local. Além disso, algumas respostas de API podem expor caminhos internos do acervo e devem ser revistas antes de publicar o serviço.

Também são desejáveis limitação de tentativas de login, política de sessão e permissões, HTTPS quando houver acesso remoto e testes automatizados para a API de streaming. O `.gitignore` não remove conteúdos que já estejam no histórico do Git.

## Histórico e reversão

Veja o [PR de segurança #1](https://github.com/Bianchi613/LovecraFlix/pull/1). Alterações de configuração, de chave JWT e de pastas de mídia devem ser validadas antes de reverter ou implantar o serviço.