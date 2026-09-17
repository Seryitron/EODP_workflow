# CROSS VALIDATE THE OUTPUTS
"""
Comparación EXACTA de los ficheros NetCDF generados por mi simulación (output_test)
frente a los ficheros de referencia del profesor (output).

Criterio: los valores deben ser idénticos bit a bit. Cualquier diferencia,
por pequeña que sea, se marca como fallo.

Uso:
    python compare_l1b.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from netCDF4 import Dataset

# -------------------------------------------------------------------------
# CONFIGURACIÓN
# -------------------------------------------------------------------------
base = r"C:/Users/TRSEHG/OneDrive - gmv.com/Documents/MiSE/Earth Observation/EODP materials/SHARED/EODP_TER_2021/EODP-TS-L1B"

dir_ref = os.path.join(base, "output")        # ficheros buenos (referencia)
dir_mine = os.path.join(base, "output_test_eq")  # mis ficheros

N_SHOW = 5   # cuántos puntos discrepantes mostrar cuando algo no coincide

# --- Paso final: efecto de la ecualización para VNIR-0 -------------------
BAND = "VNIR-0"

file_isrf = os.path.join(base, "input", f"ism_toa_isrf_{BAND}.nc")   # TOA tras el ISRF
file_eq = os.path.join(base, "output_test_eq", f"l1b_toa_{BAND}.nc")     # L1B con ecualización
file_noeq = os.path.join(base, "output_test_no_eq", f"l1b_toa_{BAND}.nc")  # L1B sin ecualización

ALT_LINE = 50        # línea ALT que se representa (la gráfica es TOA vs ACT)
SAVE_DIR = dir_mine  # dónde guardar el PNG; None para no guardarlo


# -------------------------------------------------------------------------
# FUNCIONES
# -------------------------------------------------------------------------
def read_nc(filepath):
    """Devuelve {nombre_variable: array} del fichero NetCDF, sin cambiar el dtype."""
    data = {}
    with Dataset(filepath, "r") as nc:
        for name, var in nc.variables.items():
            data[name] = np.array(var[:])
    return data


def compare_variable(name, mine, ref):
    """Compara una variable exigiendo igualdad exacta. Devuelve (pasa, texto)."""
    if mine.shape != ref.shape:
        return False, f"    [{name}] FALLO: dimensiones distintas {mine.shape} vs {ref.shape}"

    if mine.dtype != ref.dtype:
        return False, (f"    [{name}] FALLO: tipo de dato distinto "
                       f"{mine.dtype} vs {ref.dtype}")

    # equal_nan=True -> dos NaN en la misma posición se consideran iguales
    if np.array_equal(mine, ref, equal_nan=np.issubdtype(ref.dtype, np.floating)):
        return True, f"    [{name}] shape={ref.shape} dtype={ref.dtype} -> IDÉNTICO"

    # Hay diferencias: localizarlas
    idx = np.argwhere(mine != ref)
    n_diff = len(idx)
    pct = n_diff / ref.size * 100.0

    lines = [f"    [{name}] shape={ref.shape} -> NO COINCIDE: "
             f"{n_diff} de {ref.size} valores distintos ({pct:.4f} %)"]

    for pos in idx[:N_SHOW]:
        pos_t = tuple(pos)
        lines.append(f"        {pos_t}: mío = {mine[pos_t]!r} | ref = {ref[pos_t]!r}")
    if n_diff > N_SHOW:
        lines.append(f"        ... y {n_diff - N_SHOW} más")

    return False, "\n".join(lines)


def get_toa(filepath):
    """Lee la variable de radiancia TOA de un fichero NetCDF."""
    with Dataset(filepath, "r") as nc:
        name = "toa" if "toa" in nc.variables else list(nc.variables)[0]
        return np.array(nc.variables[name][:], dtype=np.float64)


def plot_equalization():
    """Reproduce la figura 'Effect of the Equalization' para la banda BAND."""
    print("\n" + "=" * 78)
    print(f"PASO FINAL: efecto de la ecualización para {BAND} (línea ALT {ALT_LINE})")
    print("=" * 78)

    for f in (file_isrf, file_eq, file_noeq):
        if not os.path.isfile(f):
            print(f"  FALTA el fichero: {f}")
            return

    toa_isrf = get_toa(file_isrf)
    toa_eq = get_toa(file_eq)
    toa_noeq = get_toa(file_noeq)

    for label, arr in (("ISRF", toa_isrf), ("con eq", toa_eq), ("sin eq", toa_noeq)):
        print(f"  {label:8s} shape={arr.shape}")

    # Se extrae la línea ALT pedida de cada array (si es 2D)
    def line(arr):
        return arr[ALT_LINE, :] if arr.ndim == 2 else arr

    y_isrf, y_eq, y_noeq = line(toa_isrf), line(toa_eq), line(toa_noeq)
    act = np.arange(y_eq.size)

    plt.figure(figsize=(11, 6))
    plt.plot(act, y_eq, "k-", linewidth=1.2, label="TOA L1B with eq")
    plt.plot(act, y_noeq, "r-", linewidth=1.0, label="TOA L1B no eq")
    plt.plot(act[:y_isrf.size], y_isrf, "b-", linewidth=1.2, label="TOA after the ISRF")

    plt.title(f"Effect of the Equalization for {BAND}")
    plt.xlabel("ACT pixel [-]")
    plt.ylabel("TOA [mW/m2/sr]")
    plt.legend(loc="upper left", fontsize=8)
    plt.grid(True, linestyle="-", linewidth=0.4, alpha=0.6)
    plt.tight_layout()

    if SAVE_DIR:
        out = os.path.join(SAVE_DIR, f"equalization_{BAND}.png")
        plt.savefig(out, dpi=150)
        print(f"  Figura guardada en: {out}")

    plt.show()


# -------------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# -------------------------------------------------------------------------
def main():
    files_mine = sorted(f for f in os.listdir(dir_mine) if f.endswith(".nc"))
    files_ref = set(f for f in os.listdir(dir_ref) if f.endswith(".nc"))

    common = [f for f in files_mine if f in files_ref]
    missing = [f for f in files_mine if f not in files_ref]

    print("=" * 78)
    print("COMPARACIÓN EXACTA  output_test  vs  output")
    print("=" * 78)
    print(f"Ficheros .nc en output_test : {len(files_mine)}")
    print(f"Ficheros .nc comparables    : {len(common)}")
    if missing:
        print(f"Sin equivalente en output   : {missing}")
    print("-" * 78)

    all_passed = True
    resumen = []

    for fname in common:
        print(f"\n{fname}")
        d_mine = read_nc(os.path.join(dir_mine, fname))
        d_ref = read_nc(os.path.join(dir_ref, fname))

        file_ok = True

        for varname in d_ref:
            if varname not in d_mine:
                print(f"    [{varname}] FALLO: variable ausente en mi fichero")
                file_ok = False
                continue

            passed, txt = compare_variable(varname, d_mine[varname], d_ref[varname])
            print(txt)
            file_ok &= passed

        extra = [v for v in d_mine if v not in d_ref]
        if extra:
            print(f"    AVISO: variables que sobran en mi fichero: {extra}")

        resumen.append((fname, file_ok))
        all_passed &= file_ok

    print("\n" + "=" * 78)
    print("RESUMEN")
    for fname, ok in resumen:
        print(f"  {'OK  ' if ok else 'FALLO'}  {fname}")
    print("-" * 78)
    print("RESULTADO GLOBAL:",
          "TODOS LOS FICHEROS SON IDÉNTICOS" if all_passed
          else "HAY FICHEROS QUE NO COINCIDEN")
    print("=" * 78)

    # Paso final: comprobación visual de la ecualización
    plot_equalization()


if __name__ == "__main__":
    main()