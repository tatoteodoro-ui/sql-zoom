# Histórico de versões

## 2.1 (novembro de 2026)

**Corrigido**
- O lote não era encontrado fora da intranet da prefeitura: o WFS agora usa o endereço público `https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs` e a camada `geoportal:lote_cidadao`, em SIRGAS 2000 / UTM 23S (EPSG:31983). Se falhar, tenta o endereço antigo da intranet (`geoportal:lote`).

## 2.0 (novembro de 2026)

Plugin reescrito.

**Novo**
- Busca só pelo SQ (`001.002`): quando o lote não é digitado, o mapa vai para a quadra.
- A janela mostra, enquanto se digita, se vai buscar quadra ou lote.
- Aceita SQL com ou sem dígito, com ou sem pontos e sem zeros à esquerda (`1.2.3` vira `001.002.0003`).
- Confere o dígito verificador com o campo `cd_digito_sql` e avisa quando for diferente.
- Condomínios: quando o SQL tem vários registros, mostra todos juntos.
- Lote não encontrado: aproxima da quadra e avisa.
- Enter já busca; as últimas 15 buscas ficam guardadas no campo.
- Mensagens na barra do QGIS, sem janelas de erro, e a feição encontrada pisca no mapa.

**Corrigido**
- A busca por SQL quebrava ao abrir o WFS, porque pedia a área de uma extensão que ainda estava vazia.

**Mudado**
- O WFS de lotes recebe um filtro só para o lote pedido, em vez de baixar a camada inteira. Usa a camada `Lotes` do projeto se houver; senão, abre o WFS do GeoSampa sozinho.
- A quadra é procurada direto pelo SQ na camada `Quadra Fiscal (shapefile)`, em vez de percorrer todas as quadras. Sem essa camada, é montada pelos lotes do WFS.
- Configuração reunida no início de `sql_zoom.py`.
- Removidos os arquivos que sobraram do gerador de plugins (testes, traduções, Makefile).

## 1.0

Versão inicial.
