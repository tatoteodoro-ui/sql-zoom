# -*- coding: utf-8 -*-
def classFactory(iface):  # noqa: N802 - nome exigido pelo QGIS
    from .sql_zoom import SQLZoom
    return SQLZoom(iface)
