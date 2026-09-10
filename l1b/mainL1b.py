
# MAIN FUNCTION TO CALL THE L1B MODULE

from l1b.src.l1b import l1b

# Directory - this is the common directory for the execution of the E2E, all modules
auxdir = r"C:/Users/herna/Documents/UC3M/5.MISE/5. BICUATRI/Earth Observation/projects/EODP_workflow/auxiliary"
indir = r"C:/Users/herna/Documents/UC3M/5.MISE/5. BICUATRI/Earth Observation/EODP materials/SHARED/EODP_TER_2021/EODP-TS-L1B/input"
outdir = r"C:/Users/herna/Documents/UC3M/5.MISE/5. BICUATRI/Earth Observation/EODP materials/SHARED/EODP_TER_2021/EODP-TS-L1B/output_test"

# Initialise the ISM
myL1b = l1b(auxdir, indir, outdir)
myL1b.processModule()
