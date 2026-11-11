# SQL Zoom

Complemento (plugin) do QGIS que aproxima o mapa de um **lote**, pelo SQL, ou de uma **quadra**, só pelo SQ.

- Versão atual: **2.0** (veja o [histórico de versões](CHANGELOG.md))
- QGIS mínimo: 3.16
- Pasta do código: [`sql_zoom/`](sql_zoom/)
- Pacote pronto para instalar: [`sql_zoom_2.1.zip`](sql_zoom_2.1.zip)

## Instalação

1. No QGIS, abra **Complementos > Gerenciar e instalar complementos > Instalar a partir do ZIP**.
2. Escolha o arquivo `sql_zoom_2.1.zip` e clique em **Instalar complemento**.
3. Se a versão 1.0 já estava instalada, ela é substituída. Reinicie o QGIS ou recarregue o complemento.

Outra forma é copiar a pasta `sql_zoom` para a pasta de complementos do seu perfil, substituindo a antiga:

```
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\sql_zoom
```

## Como usar

Clique no ícone **Encontrar SQL / SQ** na barra de ferramentas (ou em **Complementos > SQL Zoom**), digite o código e tecle **Enter**.

| O que digitar | Para onde vai |
|---|---|
| `001.002.0003-4` | Lote, conferindo o dígito verificador |
| `001.002.0003` | Lote, sem conferir dígito |
| `001.002` | Quadra (só o SQ, sem o lote) |
| `00100200034`, `0010020003`, `001002` | O mesmo que acima, sem pontos |
| `1.2.3` | Aceita sem zeros à esquerda: vira `001.002.0003` |

Enquanto você digita, a janela mostra se vai buscar uma quadra ou um lote. As últimas 15 buscas ficam guardadas na lista do campo.

O resultado aparece na barra de mensagens do QGIS, e a feição encontrada pisca no mapa.

## De onde vêm os dados

**Quadra (SQ):** a busca é feita na camada `Quadra Fiscal (shapefile)` do projeto, no campo `SQ`, que pode estar como `001.002` ou `001002`. Se essa camada não estiver no projeto, a quadra é montada juntando os lotes daquela quadra no WFS.

**Lote (SQL):** se houver no projeto uma camada chamada `Lotes`, ela é usada. Senão, o plugin abre sozinho o WFS público do GeoSampa (`https://…/geoportal/wfs`, camada `geoportal:lote_cidadao`, que funciona fora da intranet; se falhar, tenta o antigo `geoportal:lote` da intranet), sem adicioná-lo ao painel Camadas. Em qualquer caso, o filtro vai para o servidor e só o lote pedido é baixado, nunca a camada inteira.

A camada de lotes precisa dos campos `cd_setor_fiscal`, `cd_quadra_fiscal` e `cd_lote`. O campo `cd_digito_sql`, se existir, é usado para conferir o dígito.

O plugin não altera as camadas do projeto: as consultas são feitas em cópias.

## Situações especiais

- **Lote não encontrado:** o mapa vai para a quadra e a barra avisa.
- **Dígito diferente:** o mapa vai para o lote, e a barra mostra qual é o dígito que está na camada.
- **Condomínio:** quando o SQL tem vários registros, todos são mostrados juntos.
- **Filtro não aplicado no servidor:** se o WFS devolver mais de 50 feições para um lote (ou 3000 para uma quadra), a busca é interrompida para não baixar a camada inteira.

## Configuração

Os nomes das camadas, o campo do SQ, o endereço do WFS, os limites e as margens do zoom ficam no início de [`sql_zoom/sql_zoom.py`](sql_zoom/sql_zoom.py), no bloco `CONFIGURAÇÃO`:

| Constante | Valor padrão | Para que serve |
|---|---|---|
| `CAMADA_QUADRAS` | `Quadra Fiscal (shapefile)` | Nome da camada de quadras no painel Camadas |
| `CAMPO_SQ` | `SQ` | Campo com o SQ na camada de quadras |
| `CAMADA_LOTES` | `Lotes` | Nome da camada de lotes, se estiver no projeto |
| `WFS_FONTES` | `https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs` + `geoportal:lote_cidadao`; depois `http://…` + `geoportal:lote` | Endereços e tipos de feição do WFS, tentados em ordem quando não há camada de lotes |
| `WFS_SRS` | `EPSG:31983` | Sistema de coordenadas pedido ao WFS |
| `LIMITE_LOTE` / `LIMITE_QUADRA` | `50` / `3000` | Máximo de feições aceitas por busca |
| `MARGEM_LOTE` / `MARGEM_QUADRA` | `0.6` / `0.15` | Folga em volta da feição ao aproximar |

Depois de mudar algum valor, gere o ZIP de novo (veja abaixo) ou edite direto a pasta instalada e recarregue o complemento.

## Problemas comuns

| Mensagem | O que fazer |
|---|---|
| `Formato não reconhecido` | Confira o código: SQ tem 3 + 3 dígitos; SQL tem 3 + 3 + 4, e o dígito é opcional. |
| `Não foi possível abrir o WFS de lotes` | Verifique a rede da Prefeitura ou adicione a camada `Lotes` ao projeto. |
| `A camada ... não tem o campo ...` | A camada com aquele nome não tem a estrutura esperada. Ajuste o nome ou o campo na configuração. |
| `A consulta devolveu mais de N feições` | O servidor ignorou o filtro. Tente de novo; se continuar, use uma camada `Lotes` local. |

## Organização do código

| Arquivo | Conteúdo |
|---|---|
| `__init__.py` | Ponto de entrada exigido pelo QGIS |
| `sql_zoom.py` | Configuração, botão, busca nas camadas, WFS e zoom |
| `dialogo.py` | Janela de busca, confirmação ao digitar e histórico |
| `entrada.py` | Leitura do texto digitado (Python puro, sem QGIS) |
| `metadata.txt` | Nome, versão e histórico exibidos no gerenciador de complementos |
| `LEIA-ME.txt` | Resumo de uso que vai junto no ZIP |

## Testes

A leitura do que é digitado (`entrada.py`) não depende do QGIS e tem testes em [`testes/test_entrada.py`](testes/test_entrada.py). Para rodar, na raiz do repositório:

```
python testes/test_entrada.py
```

A busca nas camadas e no WFS só pode ser testada dentro do QGIS.

## Gerar o ZIP para instalar

O ZIP precisa ter a pasta `sql_zoom` na raiz. Na raiz do repositório:

```
python -c "import shutil; shutil.make_archive('sql_zoom_2.0', 'zip', '.', 'sql_zoom')"
```

Ao lançar uma versão nova, atualize `version` e `changelog` em `sql_zoom/metadata.txt` e o [CHANGELOG.md](CHANGELOG.md).
