# Relatório de Desenvolvimento - API Agroenergia

Este repositório contém a entrega final da API de cálculo emergético. Durante o desenvolvimento, o projeto passou por diversas etapas de configuração, testes e refatoração de código para garantir o tratamento correto de regras de negócio e estabilidade do servidor.

## 1. Configuração de Ambiente e Desafios Iniciais
A etapa inicial apresentou desafios significativos de infraestrutura. Tive dificuldades com a instalação e configuração do ambiente virtual (`.venv`), além de conflitos com versões do Python que exigiram ajustes na escrita do código e nas bibliotecas para que o framework FastAPI e o Uvicorn rodassem adequadamente. A transição entre os testes executados diretamente no terminal via PowerShell (usando `Invoke-RestMethod`) e as validações visuais na interface web (Swagger UI) foi fundamental para isolar onde os erros estavam ocorrendo.

## 2. Passo 3: Validações e Tratamento de Erros (RFC 9457)
O motor matemático original não possuía travas na porta de entrada da API. 
* **Bloqueio de Campos Extras:** O DTO foi ajustado com a regra `extra = "forbid"`. Isso garantiu que erros de digitação intencionais nos testes (como enviar `energia_produto_jj` em vez de `_j`) fossem barrados imediatamente com um erro 422, impedindo que o motor processasse cálculos incompletos silenciosamente.
* **Handlers de Exceção:** Foi criado tratadores de erro para evitar que falhas de domínio (como divisões por zero ao enviar um inventário sem fluxos renováveis) gerassem o genérico "Erro 500". A API agora traduz essas falhas perfeitamente para o status 422, retornando um JSON estruturado com os cinco campos obrigatórios da RFC 9457 (`type`, `title`, `status`, `detail`, `instance`).

## 3. Passo 4: Resolução da "Rota-Armadilha"
Na rota `/v1/demo/travada`. O uso de uma função síncrona e bloqueante tradicional (`time.sleep()`) dentro de uma declaração assíncrona (`async def`) paralisava todo o *event loop* principal do servidor, impedindo que a aplicação respondesse a novas requisições (até mesmo a interface do Swagger ficava travada carregando).

Para resolver esse travamento, havia duas opções de implementação na arquitetura do FastAPI:

* **Opção 1 (A implementada no projeto): Remover a declaração `async`.** 
Ao alterar a rota de `async def` para uma função síncrona normal (`def`), o FastAPI reconhece que a tarefa é bloqueante e a envia automaticamente para um *thread pool* em segundo plano gerenciado pelo Starlette. Isso libera o *event loop* principal imediatamente, permitindo que o servidor continue atendendo outros usuários sem travar.

* **Opção 2 (A alternativa totalmente assíncrona): Substituir o bloqueio por `await asyncio.sleep()`.** 
Se a intenção fosse manter a rota como `async def`, seria obrigatório trocar a biblioteca síncrona `time` pela biblioteca assíncrona `asyncio`. Assim, ao chegar no comando `await`, a função "devolve" o controle para o *event loop* atender outras requisições enquanto a espera acontece no fundo.

Foi aplicado a primeira opção 1 para resolver o travamento. Após validar que a API voltou a responder normalmente, o arquivo inteiro de demonstração (`rotas_demo.py`) foi excluído do repositório para manter a higiene da base de código, cumprindo as diretrizes do projeto.

## 4. Passo 5: Testes Automatizados e Limites do Motor Matemático
A etapa final focou na automação dos testes em Pytest (`test_tarefas_aluno.py`), avaliando a precisão do núcleo matemático isolado da infraestrutura web.
* **Resolução de Importação:** Foi corrijido uma divergência de nomenclatura entre o arquivo local (`motor_energia.py`) e a importação esperada pelo Pytest (`motor.py`), o que inicialmente impedia a coleta dos testes.
* **Desafio da Precisão Extrema (InvalidOperation):** O motor crava a precisão decimal em 28 dígitos (`ctx.prec = 28`). Durante o teste de magnitudes divergentes, ao simular a divisão de valores extremos, o cálculo do índice ESI gerou um número astronômico (na casa de 1E36) que extrapolou a memória alocada ao tentar ser quantizado para 6 casas decimais. A solução foi balancear a diferença de grandezas nos fluxos de teste (usando `1E14` e `1E-15`), o que manteve a divergência de 29 casas necessária para provar a importância da ordem da soma, mas sem quebrar os limites de memória do Python na divisão final.
* **Resultado Final:** Todos os 20 testes da aplicação passaram com sucesso no terminal (`100% passed`), homologando tanto a infraestrutura web quanto as regras estritas de arredondamento e quantização do domínio.
