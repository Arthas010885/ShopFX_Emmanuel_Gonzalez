#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
respaldo_php.py
Proyecto ShopFX - TCHCL

Busca todos los archivos de código fuente .php de un proyecto, los renombra
agregando un prefijo y la fecha/hora, y los copia a una ubicación remota
segura (simulada con otro directorio del equipo).

Medidas de seguridad incluidas:
  - Verificación de integridad con hash SHA-256 (origen vs. copia).
  - Permisos restringidos en la carpeta de destino (solo el propietario).
  - Registro (log) de cada operación con fecha y hora.
  - Los archivos originales NO se modifican ni se eliminan.

Uso:
  python respaldo_php.py --origen ./proyecto_shopfx --destino ./servidor_remoto
"""

import argparse
import hashlib
import logging
import os
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path


def calcular_hash(ruta: Path) -> str:
    """Calcula el hash SHA-256 de un archivo para verificar su integridad."""
    sha256 = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(4096), b""):
            sha256.update(bloque)
    return sha256.hexdigest()


def preparar_destino(destino: Path) -> Path:
    """Crea la carpeta de respaldo con fecha y le asigna permisos restringidos."""
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    carpeta = destino / f"respaldo_{marca}"
    carpeta.mkdir(parents=True, exist_ok=True)
    try:
        # rwx solo para el propietario (700). En Windows se aplica parcialmente.
        os.chmod(destino, stat.S_IRWXU)
        os.chmod(carpeta, stat.S_IRWXU)
    except PermissionError:
        logging.warning("No se pudieron ajustar los permisos del destino.")
    return carpeta


def nuevo_nombre(archivo: Path, origen: Path, prefijo: str, marca: str) -> str:
    """
    Genera el nuevo nombre del archivo.
    Incluye la ruta relativa para evitar choques entre archivos con el mismo
    nombre en distintas carpetas.
    Ejemplo: modulos/pagos/procesar_pago.php
             -> shopfx_modulos-pagos-procesar_pago_20261006_153000.php
    """
    relativa = archivo.relative_to(origen).with_suffix("")
    base = "-".join(relativa.parts)
    return f"{prefijo}_{base}_{marca}.php"


def respaldar(origen: Path, destino: Path, prefijo: str) -> int:
    """Busca, renombra, copia y verifica los archivos .php. Devuelve los errores."""
    archivos = sorted(origen.rglob("*.php"))
    if not archivos:
        logging.warning("No se encontraron archivos .php en %s", origen)
        return 0

    carpeta = preparar_destino(destino)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    logging.info("Archivos .php encontrados: %d", len(archivos))
    logging.info("Destino seguro: %s", carpeta)

    copiados, errores = 0, 0
    for archivo in archivos:
        nombre = nuevo_nombre(archivo, origen, prefijo, marca)
        copia = carpeta / nombre
        try:
            shutil.copy2(archivo, copia)  # copia conservando fechas
            os.chmod(copia, stat.S_IRUSR | stat.S_IWUSR)  # permisos 600
            if calcular_hash(archivo) == calcular_hash(copia):
                logging.info("OK  %s -> %s", archivo.relative_to(origen), nombre)
                copiados += 1
            else:
                logging.error("ERROR de integridad en %s", archivo)
                errores += 1
        except OSError as error:
            logging.error("No se pudo copiar %s: %s", archivo, error)
            errores += 1

    logging.info("Resumen: %d copiados, %d errores", copiados, errores)
    return errores


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Renombra y copia archivos .php a una ubicación remota segura."
    )
    parser.add_argument("--origen", required=True, help="Carpeta del proyecto")
    parser.add_argument("--destino", required=True, help="Ubicación remota (simulada)")
    parser.add_argument("--prefijo", default="shopfx", help="Prefijo para los nombres")
    args = parser.parse_args()

    origen = Path(args.origen).resolve()
    destino = Path(args.destino).resolve()

    destino.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(destino / "registro_respaldos.log", encoding="utf-8"),
        ],
    )

    if not origen.is_dir():
        logging.error("La carpeta de origen no existe: %s", origen)
        sys.exit(1)

    logging.info("=== Inicio del respaldo de código fuente ShopFX ===")
    errores = respaldar(origen, destino, args.prefijo)
    logging.info("=== Fin del respaldo ===")
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()