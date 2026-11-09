# -*- coding: utf-8 -*-
"""SQL Zoom: aproxima o mapa de um lote (pelo SQL) ou de uma quadra (só pelo SQ).

Como funciona
  * Quadra (SQ, ex. 001.002): procura na camada local de quadras fiscais e aproxima dela.
    Se essa camada não estiver no projeto, pede ao WFS só os lotes daquela quadra.
  * Lote (SQL, ex. 001.002.0003 ou 001.002.0003-4): pede ao WFS de lotes SÓ aquele lote
    (o filtro vai para o servidor; a camada inteira nunca é baixada). Se o lote não existir,
    aproxima da quadra e avisa.

Nada é alterado nas camadas do projeto: as consultas usam cópias.
"""
import os

from qgis.core import (Qgis, QgsCoordinateTransform, QgsDataSourceUri, QgsFeatureRequest, QgsGeometry,
                       QgsProject, QgsRectangle, QgsVectorLayer)
from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QApplication

from .dialogo import DialogoBusca
from .entrada import descrever, mesmo_numero, sq_texto

# ============================== CONFIGURAÇÃO ==============================
# Camada local de quadras fiscais (nome no painel Camadas) e o campo com o SQ (xxx.xxx).
CAMADA_QUADRAS = "Quadra Fiscal (shapefile)"
CAMPO_SQ = "SQ"

# Camada de lotes: se houver no projeto uma camada com este nome, ela é usada (numa cópia);
# senão, o plugin abre o WFS abaixo sozinho, sem adicioná-lo ao projeto.
CAMADA_LOTES = "Lotes"
WFS_URL = "http://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs"
WFS_TIPO = "geoportal:lote"

# Limites de segurança: se o servidor devolver mais feições que isto, o filtro não foi aplicado
# lá e a consulta é abortada (para não baixar a camada inteira).
LIMITE_LOTE = 50
LIMITE_QUADRA = 3000

# Folga em volta da feição ao aproximar (fração do tamanho).
MARGEM_LOTE = 0.6
MARGEM_QUADRA = 0.15
# ==========================================================================

MENU = "&SQL Zoom"
TITULO = "SQL Zoom"


class ErroBusca(RuntimeError):
    pass


class SQLZoom:
    def __init__(self, iface):
        self.iface = iface
        self.pasta = os.path.dirname(__file__)
        self.acao = None
        self.dlg = None
        self._wfs = None   # camada WFS aberta pelo plugin (reaproveitada entre buscas)

    # ------------------------------------------------------------ QGIS
    def initGui(self):  # noqa: N802 - nome exigido pelo QGIS
        self.acao = QAction(QIcon(os.path.join(self.pasta, "icon.png")), "Encontrar SQL / SQ",
                            self.iface.mainWindow())
        self.acao.setStatusTip("Aproxima o mapa de um lote (SQL) ou de uma quadra (SQ)")
        self.acao.triggered.connect(self.abrir)
        self.iface.addToolBarIcon(self.acao)
        self.iface.addPluginToMenu(MENU, self.acao)

    def unload(self):
        if self.acao:
            self.iface.removePluginMenu(MENU, self.acao)
            self.iface.removeToolBarIcon(self.acao)
        if self.dlg:
            self.dlg.close()
            self.dlg.deleteLater()
        self._wfs = None

    def abrir(self):
        if self.dlg is None:
            self.dlg = DialogoBusca(self.iface.mainWindow(), QSettings())
            self.dlg.buscar.connect(self._buscar)
        self.dlg.preparar()
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()

    # ------------------------------------------------------------ busca
    def _buscar(self, busca):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if busca.lote is None:
                ok = self._ir_para_quadra(busca)
            else:
                ok = self._ir_para_lote(busca)
        except ErroBusca as e:
            ok = False
            self.dlg.mostrar_erro(str(e))
        except Exception as e:  # noqa: BLE001 - qualquer erro vira mensagem, sem travar o QGIS
            ok = False
            self.dlg.mostrar_erro("Erro inesperado: %s" % e)
        finally:
            QApplication.restoreOverrideCursor()
        if ok:
            self.dlg.concluido()

    def _ir_para_quadra(self, busca):
        geom, crs = self._geometria_quadra(busca)
        if geom is not None:
            self._aproximar(geom, crs, MARGEM_QUADRA)
            self._aviso("%s encontrada." % descrever(busca), Qgis.Success)
            return True
        # Sem camada local de quadras: monta a quadra a partir dos lotes do WFS.
        lotes, crs = self._consultar_lotes(busca, LIMITE_QUADRA)
        if not lotes:
            raise ErroBusca("%s não encontrada." % descrever(busca))
        self._aproximar(_unir([f.geometry() for f in lotes]), crs, MARGEM_QUADRA)
        if QgsProject.instance().mapLayersByName(CAMADA_QUADRAS):
            motivo = "não está na camada '%s'" % CAMADA_QUADRAS
        else:
            motivo = "a camada '%s' não está no projeto" % CAMADA_QUADRAS
        self._aviso("%s encontrada pelos lotes do WFS (%s)." % (descrever(busca), motivo), Qgis.Info)
        return True

    def _ir_para_lote(self, busca):
        lotes, crs = self._consultar_lotes(busca, LIMITE_LOTE)
        if not lotes:
            geom, crs_q = self._geometria_quadra(busca)
            if geom is None:
                raise ErroBusca("%s não encontrado, nem a quadra %s." % (descrever(busca), sq_texto(busca)))
            self._aproximar(geom, crs_q, MARGEM_QUADRA)
            self._aviso("%s não encontrado na camada de lotes. Mostrando a quadra %s."
                        % (descrever(busca), sq_texto(busca)), Qgis.Warning)
            return True

        avisos = []
        if busca.digito is not None and lotes[0].fields().indexOf("cd_digito_sql") >= 0:
            digitos = {str(f["cd_digito_sql"]) for f in lotes if f["cd_digito_sql"] not in (None, "")}
            if digitos and not any(mesmo_numero(d, busca.digito) for d in digitos):
                avisos.append("o dígito na camada é %s, não %s" % (", ".join(sorted(digitos)), busca.digito))
        if len(lotes) > 1:
            avisos.append("%d registros (condomínio): mostrando todos" % len(lotes))

        self._aproximar(_unir([f.geometry() for f in lotes]), crs, MARGEM_LOTE)
        if avisos:
            self._aviso("%s encontrado — %s." % (descrever(busca), "; ".join(avisos)), Qgis.Warning)
        else:
            self._aviso("%s encontrado." % descrever(busca), Qgis.Success)
        return True

    # ------------------------------------------------------------ camadas
    def _geometria_quadra(self, busca):
        """Geometria da quadra na camada local, ou (None, None) se a camada não estiver no projeto."""
        camadas = QgsProject.instance().mapLayersByName(CAMADA_QUADRAS)
        if not camadas:
            return None, None
        camada = camadas[0]
        if not camada.isValid():
            raise ErroBusca("A camada '%s' não é válida." % CAMADA_QUADRAS)
        if camada.fields().indexOf(CAMPO_SQ) < 0:
            raise ErroBusca("A camada '%s' não tem o campo %s." % (CAMADA_QUADRAS, CAMPO_SQ))
        self._deixar_visivel(camada)
        sq = sq_texto(busca)
        expr = "\"%s\" IN ('%s', '%s')" % (CAMPO_SQ, sq, sq.replace(".", ""))
        geoms = [f.geometry() for f in camada.getFeatures(QgsFeatureRequest().setFilterExpression(expr))]
        if not geoms:
            return None, None
        return _unir(geoms), camada.crs()

    def _camada_lotes(self):
        """Cópia da camada de lotes do projeto ou o WFS aberto pelo próprio plugin."""
        camadas = QgsProject.instance().mapLayersByName(CAMADA_LOTES)
        if camadas and camadas[0].isValid():
            return camadas[0].clone()
        if self._wfs is None or not self._wfs.isValid():
            uri = QgsDataSourceUri()
            uri.setParam("url", WFS_URL)
            uri.setParam("typename", WFS_TIPO)
            uri.setParam("version", "auto")
            uri.setParam("pagingEnabled", "true")
            camada = QgsVectorLayer(uri.uri(False), "Lotes (SQL Zoom)", "WFS")
            if not camada.isValid():
                raise ErroBusca("Não foi possível abrir o WFS de lotes (%s). Verifique a rede ou adicione "
                                "a camada '%s' ao projeto." % (WFS_URL, CAMADA_LOTES))
            self._wfs = camada
        return self._wfs.clone()

    def _consultar_lotes(self, busca, limite):
        """Pede ao servidor só os lotes da busca (um lote ou a quadra inteira)."""
        camada = self._camada_lotes()
        campos = camada.fields()
        for c in ("cd_setor_fiscal", "cd_quadra_fiscal") + (("cd_lote",) if busca.lote else ()):
            if campos.indexOf(c) < 0:
                raise ErroBusca("A camada de lotes não tem o campo %s." % c)
        filtro = "\"cd_setor_fiscal\" = '%s' AND \"cd_quadra_fiscal\" = '%s'" % (busca.setor, busca.quadra)
        if busca.lote:
            filtro += " AND \"cd_lote\" = '%s'" % busca.lote

        prov = camada.dataProvider()
        if hasattr(prov, "clearErrors"):
            prov.clearErrors()
        req = QgsFeatureRequest()
        if not camada.setSubsetString(filtro):   # filtro aplicado no servidor
            req.setFilterExpression(filtro)
        req.setLimit(limite + 1)
        feicoes = [f for f in camada.getFeatures(req) if f.hasGeometry()]

        if not feicoes and hasattr(prov, "hasErrors") and prov.hasErrors():
            raise ErroBusca("O servidor de lotes respondeu com erro: %s" % prov.errors()[0][:300])
        if len(feicoes) > limite:
            raise ErroBusca("A consulta devolveu mais de %d feições: o filtro não foi aplicado no servidor. "
                            "Busca interrompida para não baixar a camada inteira." % limite)
        # Confere os códigos (o servidor pode devolver '083' ou 83).
        feicoes = [f for f in feicoes
                   if mesmo_numero(f["cd_setor_fiscal"], busca.setor)
                   and mesmo_numero(f["cd_quadra_fiscal"], busca.quadra)
                   and (not busca.lote or mesmo_numero(f["cd_lote"], busca.lote))]
        return feicoes, camada.crs()

    def _deixar_visivel(self, camada):
        no = QgsProject.instance().layerTreeRoot().findLayer(camada.id())
        if no is not None and not no.isVisible():
            no.setItemVisibilityCheckedParentRecursive(True)

    # ------------------------------------------------------------ mapa
    def _aproximar(self, geom, crs, margem):
        canvas = self.iface.mapCanvas()
        destino = canvas.mapSettings().destinationCrs()
        geom = QgsGeometry(geom)
        if crs is not None and crs.isValid() and crs != destino:
            geom.transform(QgsCoordinateTransform(crs, destino, QgsProject.instance()))
        caixa = geom.boundingBox()
        if caixa.width() == 0 and caixa.height() == 0:
            canvas.setCenter(caixa.center())
            canvas.zoomScale(500)
        else:
            dx = caixa.width() * margem / 2
            dy = caixa.height() * margem / 2
            canvas.setExtent(QgsRectangle(caixa.xMinimum() - dx, caixa.yMinimum() - dy,
                                          caixa.xMaximum() + dx, caixa.yMaximum() + dy))
        canvas.refresh()
        try:
            canvas.flashGeometries([geom], destino)
        except Exception:  # noqa: BLE001 - versões antigas do QGIS não piscam
            pass

    def _aviso(self, texto, nivel):
        self.iface.messageBar().pushMessage(TITULO, texto, level=nivel, duration=6)


def _unir(geoms):
    if len(geoms) == 1:
        return QgsGeometry(geoms[0])
    return QgsGeometry.collectGeometry(geoms)
