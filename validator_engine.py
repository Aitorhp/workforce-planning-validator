"""Fachada de compatibilidad para la aplicacion existente.

La logica productiva vive en el paquete ``workforce_validator``. Este modulo
mantiene los imports publicos utilizados por app.py y por integraciones previas.
"""
from __future__ import annotations

from datetime import timedelta

from workforce_validator.config import SETTINGS, ValidatorSettings, load_settings
from workforce_validator.dataframes import result_dataframes
from workforce_validator.dates import (
    collect_data_dates,
    daterange,
    find_consecutive_st