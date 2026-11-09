# -*- coding: utf-8 -*-
"""Janela de busca: um campo só para SQL ou SQ, com as últimas buscas e a confirmação do que
foi entendido (quadra ou lote) enquanto se digita."""
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QLabel, QSizePolicy, QVBoxLayout)

from .entrada import descrever, interpretar

CHAVE_HISTORICO = "sql_zoom/historico"
MAX_HISTORICO = 15
DICA = "SQL (001.002.0003 ou 001.002.0003-4) ou só o SQ (001.002) para ir à quadra"


class DialogoBusca(QDialog):
    buscar = pyqtSignal(object)   # entrada.Busca

    def __init__(self, parent, settings):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Encontrar SQL / SQ")
        self.setMinimumWidth(460)

        rotulo = QLabel("Digite o SQL do lote ou só o SQ da quadra:")
        self.campo = QComboBox()
        self.campo.setEditable(True)
        self.campo.setInsertPolicy(QComboBox.NoInsert)
        self.campo.lineEdit().setPlaceholderText("001.002.0003-4  ou  001.002")
        self.campo.lineEdit().setClearButtonEnabled(True)
        self.campo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.campo.editTextChanged.connect(self._ao_digitar)

        self.situacao = QLabel(DICA)
        self.situacao.setWordWrap(True)

        self.botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.botoes.button(QDialogButtonBox.Ok).setText("Ir")
        self.botoes.accepted.connect(self._confirmar)
        self.botoes.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(rotulo)
        lay.addWidget(self.campo)
        lay.addWidget(self.situacao)
        lay.addWidget(self.botoes)

    # ------------------------------------------------------------ uso pelo plugin
    def preparar(self):
        self.campo.blockSignals(True)
        self.campo.clear()
        self.campo.addItems(self._historico())
        self.campo.setEditText("")
        self.campo.blockSignals(False)
        self._ao_digitar("")
        self.campo.setFocus()

    def mostrar_erro(self, texto):
        self.situacao.setText(texto)
        self.situacao.setStyleSheet("color: #b3261e;")
        self.campo.setFocus()
        self.campo.lineEdit().selectAll()

    def concluido(self):
        self._guardar(self.campo.currentText().strip())
        self.accept()

    # ------------------------------------------------------------ interno
    def _ao_digitar(self, texto):
        b = interpretar(texto)
        ok = self.botoes.button(QDialogButtonBox.Ok)
        ok.setEnabled(b is not None)
        self.situacao.setStyleSheet("")
        if not texto.strip():
            self.situacao.setText(DICA)
        elif b is None:
            self.situacao.setText("Formato não reconhecido. Use 001.002.0003, 001.002.0003-4 ou 001.002.")
            self.situacao.setStyleSheet("color: #b3261e;")
        else:
            self.situacao.setText("Vai buscar: %s" % descrever(b))

    def _confirmar(self):
        b = interpretar(self.campo.currentText())
        if b is None:
            self.mostrar_erro("Formato não reconhecido. Use 001.002.0003, 001.002.0003-4 ou 001.002.")
            return
        self.situacao.setText("Buscando %s..." % descrever(b))
        self.situacao.repaint()
        self.buscar.emit(b)   # o plugin chama concluido() ou mostrar_erro()

    def keyPressEvent(self, e):  # noqa: N802 - Enter no campo também busca
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.botoes.button(QDialogButtonBox.Ok).isEnabled():
                self._confirmar()
            e.accept()
            return
        super().keyPressEvent(e)

    def _historico(self):
        v = self.settings.value(CHAVE_HISTORICO, [])
        if isinstance(v, str):
            v = [v] if v else []
        return [str(x) for x in (v or [])]

    def _guardar(self, texto):
        if not texto:
            return
        h = [x for x in self._historico() if x != texto]
        self.settings.setValue(CHAVE_HISTORICO, ([texto] + h)[:MAX_HISTORICO])
