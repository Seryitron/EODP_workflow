# CROSS VALIDATE THE OUTPUTS
"""
EODP-TS-L1B test.

Runs the L1B twice, with and without equalization, compares the equalized outputs with the
reference outputs (max relative difference < 1e-3 %) and plots the effect of the equalization
for the 4 bands. The console output is also written to xval_l1b.txt.

Run from the repo root (or from PyCharm):
    python l1b/test/lib1_test.py
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from netCDF4 import Dataset

# -------------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------------
# repo root (EODP_workflow), taken from the location of this script
PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJ)

# test folder
base = os.path.normpath(os.path.join(PROJ, "..", "..", "EODP materials", "SHARED",
                                     "EODP_TER_2021", "EODP-TS-L1B"))
auxdir = os.path.join(PROJ, "auxiliary")

dir_in = os.path.join(base, "input")                  # reference ISM output (input of the L1B)
dir_ref = os.path.join(base, "output")                # reference L1B outputs
dir_mine = os.path.join(base, "output_test_eq")       # my outputs with eq
dir_noeq = os.path.join(base, "output_test_no_eq")    # my outputs without eq
dir_fig = os.path.join(base, "figures_test")          # figures for the report
file_report = os.path.join(base, "xval_l1b.txt")      # copy of the console output

RUN_L1B = True   # False to only compare and plot the files that already exist
TOL = 1e-3       # [%]
N_SHOW = 5       # number of differing values to print

# equalization plot
BANDS = ["VNIR-0", "VNIR-1", "VNIR-2", "VNIR-3"]
ALT_LINE = 50          # ALT line to plot (TOA vs ACT)
ACT_RANGE = (10, 140)  # ACT pixels used for the metrics (skips the MTF borders and the bad pixel)
DN_SAT = 2 ** 12 - 1   # ADC saturation (12 bits)


# -------------------------------------------------------------------------
# FUNCTIONS
# -------------------------------------------------------------------------
class Tee:
    """Prints to the screen and to a file at the same time."""
    def __init__(self, path):
        self.file = open(path, "w")
        self.stdout = sys.stdout

    def write(self, text):
        self.stdout.write(text)
        self.file.write(text)

    def flush(self):
        self.stdout.flush()
        self.file.flush()


def run_l1b(outdir, do_equalization):
    """Runs the L1B with or without equalization (without touching l1bConfig.py)."""
    from l1b.src.l1b import l1b
    os.makedirs(outdir, exist_ok=True)
    log = os.path.join(outdir, "L1B.log")
    if os.path.isfile(log):
        os.remove(log)   # the logger appends, so start with a clean log
    myL1b = l1b(auxdir, dir_in, outdir)
    myL1b.l1bConfig.do_equalization = do_equalization
    myL1b.processModule()


def read_nc(filepath):
    """Returns {variable: array} of a NetCDF file, keeping the dtype."""
    data = {}
    with Dataset(filepath, "r") as nc:
        for name, var in nc.variables.items():
            data[name] = np.array(var[:])
    return data


def compare_variable(name, mine, ref):
    """Compares one variable. Returns (passed, text)."""
    if mine.shape != ref.shape:
        return False, f"    [{name}] FAIL: different shape {mine.shape} vs {ref.shape}"

    if mine.dtype != ref.dtype:
        return False, (f"    [{name}] FAIL: different dtype "
                       f"{mine.dtype} vs {ref.dtype}")

    # equal_nan: two NaNs in the same position count as equal
    if np.array_equal(mine, ref, equal_nan=np.issubdtype(ref.dtype, np.floating)):
        return True, f"    [{name}] shape={ref.shape} dtype={ref.dtype} -> IDENTICAL (max relative difference = 0 %)"

    # not identical: relative difference (where ref = 0 the absolute difference has to be 0)
    m, r = mine.astype(np.float64), ref.astype(np.float64)
    diff = np.abs(m - r)
    nz = r != 0
    rel = np.zeros_like(r)
    rel[nz] = diff[nz] / np.abs(r[nz]) * 100.0
    bad = (rel > TOL) | (~nz & (diff > 0))
    n_bad = int(bad.sum())
    passed = n_bad == 0

    lines = [f"    [{name}] shape={ref.shape} -> max absolute difference = {diff.max():.3g}, "
             f"max relative difference = {rel.max():.3g} % "
             f"-> {'OK (< %g %%)' % TOL if passed else 'FAIL: %d values > %g %%' % (n_bad, TOL)}"]

    for pos in np.argwhere(bad)[:N_SHOW]:
        pos_t = tuple(pos)
        lines.append(f"        {pos_t}: mine = {mine[pos_t]!r} | ref = {ref[pos_t]!r}")
    if n_bad > N_SHOW:
        lines.append(f"        ... and {n_bad - N_SHOW} more")

    return passed, "\n".join(lines)


def get_toa(filepath):
    """Reads the TOA of a NetCDF file."""
    with Dataset(filepath, "r") as nc:
        name = "toa" if "toa" in nc.variables else list(nc.variables)[0]
        return np.array(nc.variables[name][:], dtype=np.float64)


def plot_equalization():
    """Effect of the equalization for the 4 bands: plot and metrics."""
    print("\n" + "=" * 78)
    print(f"EFFECT OF THE EQUALIZATION (ALT line {ALT_LINE})")
    print("=" * 78)
    os.makedirs(dir_fig, exist_ok=True)
    a0, a1 = ACT_RANGE
    print(f"RMS of the relative difference with the truth (TOA after the ISRF), "
          f"ACT {a0}-{a1 - 1}, non-saturated pixels")
    print(f"{'band':8s} {'saturated':>10s} {'1st sat. ACT':>12s} {'4095*gain':>10s} "
          f"{'RMS no eq':>11s} {'RMS eq':>11s}")

    from config.l1bConfig import l1bConfig
    gain = l1bConfig().gain

    for i, band in enumerate(BANDS):
        file_isrf = os.path.join(dir_in, f"ism_toa_isrf_{band}.nc")    # TOA after the ISRF
        file_dn = os.path.join(dir_in, f"ism_toa_{band}.nc")           # ISM TOA in DN
        file_eq = os.path.join(dir_mine, f"l1b_toa_{band}.nc")         # L1B with eq
        file_noeq = os.path.join(dir_noeq, f"l1b_toa_{band}.nc")       # L1B without eq

        missing = [f for f in (file_isrf, file_dn, file_eq, file_noeq) if not os.path.isfile(f)]
        if missing:
            print(f"  MISSING files: {missing}")
            return

        toa_isrf, toa_dn = get_toa(file_isrf), get_toa(file_dn)
        toa_eq, toa_noeq = get_toa(file_eq), get_toa(file_noeq)

        # metrics on the selected ALT line
        y_isrf, y_eq, y_noeq = toa_isrf[ALT_LINE, :], toa_eq[ALT_LINE, :], toa_noeq[ALT_LINE, :]
        sat = toa_dn >= DN_SAT
        sel = ~sat[ALT_LINE, :]
        sel[:a0] = False
        sel[a1:] = False
        rms = lambda y: np.sqrt(np.mean(((y[sel] - y_isrf[sel]) / y_isrf[sel]) ** 2)) * 100
        first = np.argmax(sat[ALT_LINE, :]) if sat[ALT_LINE, :].any() else None
        print(f"{band:8s} {sat.mean() * 100:9.1f}% {str(first if first is not None else '-'):>12s} "
              f"{DN_SAT * gain[i]:10.1f} {rms(y_noeq):10.2f}% {rms(y_eq):10.2f}%")

        # figure
        act = np.arange(y_eq.size)
        plt.figure(figsize=(11, 6))
        plt.plot(act, y_isrf, "b-", linewidth=1.8, label="TOA after the ISRF (truth)")
        plt.plot(act, y_noeq, "r-", linewidth=1.0, label="TOA L1B no eq")
        plt.plot(act, y_eq, "k-", linewidth=1.2, label="TOA L1B with eq")
        plt.title(f"Effect of the Equalization for {band} (ALT {ALT_LINE})")
        plt.xlabel("ACT pixel [-]")
        plt.ylabel("TOA [mW/m2/sr]")
        plt.legend(loc="upper left", fontsize=9)
        plt.grid(True, linestyle="-", linewidth=0.4, alpha=0.6)
        plt.tight_layout()
        out = os.path.join(dir_fig, f"l1b_equalization_{band}.png")
        plt.savefig(out, dpi=150)
        plt.close()
        print(f"  Figure saved: {os.path.relpath(out, base)}")


# -------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------
def main():
    if RUN_L1B:
        run_l1b(dir_mine, do_equalization=True)
        run_l1b(dir_noeq, do_equalization=False)
        plt.close("all")

    sys.stdout = Tee(file_report)   # from here on, the output also goes to xval_l1b.txt

    files_mine = sorted(f for f in os.listdir(dir_mine) if f.endswith(".nc"))
    files_ref = set(f for f in os.listdir(dir_ref) if f.endswith(".nc"))

    common = [f for f in files_mine if f in files_ref]
    missing = [f for f in files_mine if f not in files_ref]

    print("=" * 78)
    print("EODP-TS-L1B - CROSS-VALIDATION  output_test_eq  vs  output (reference)")
    print(f"Criterion: max relative difference < {TOL} %")
    print("=" * 78)
    print(f".nc files in output_test_eq : {len(files_mine)}")
    print(f".nc files compared           : {len(common)}")
    if missing:
        print(f"Without reference            : {missing}")
    print("-" * 78)

    all_passed = True
    summary = []

    for fname in common:
        print(f"\n{fname}")
        d_mine = read_nc(os.path.join(dir_mine, fname))
        d_ref = read_nc(os.path.join(dir_ref, fname))

        file_ok = True

        for varname in d_ref:
            if varname not in d_mine:
                print(f"    [{varname}] FAIL: variable missing in my file")
                file_ok = False
                continue

            passed, txt = compare_variable(varname, d_mine[varname], d_ref[varname])
            print(txt)
            file_ok &= passed

        extra = [v for v in d_mine if v not in d_ref]
        if extra:
            print(f"    WARNING: extra variables in my file: {extra}")

        summary.append((fname, file_ok))
        all_passed &= file_ok

    print("\n" + "=" * 78)
    print("SUMMARY")
    for fname, ok in summary:
        print(f"  {'OK  ' if ok else 'FAIL'}  {fname}")
    print("-" * 78)
    print("GLOBAL RESULT:",
          "ALL FILES MEET THE CRITERION (PASS)" if all_passed
          else "SOME FILES DO NOT MEET THE CRITERION (FAIL)")
    print("=" * 78)

    # equalization plot
    plot_equalization()

    sys.stdout.file.close()
    sys.stdout = sys.stdout.stdout


if __name__ == "__main__":
    main()
