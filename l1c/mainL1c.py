
# MAIN FUNCTION TO CALL THE L1C MODULE

from l1c.src.l1c import l1c

# Directory - this is the common directory for the execution of the E2E, all modules
auxdir = r'/Users/sergio_ini/Documents/UC3M/5.MISE/5. BICUATRI/Earth Observation/projects/EODP_workflow/auxiliary'
# GM dir + L1B dir
indir = '/Users/sergio_ini/Documents/UC3M/5.MISE/5. BICUATRI/Earth Observation/EODP materials/SHARED/EODP_TER_2021/EODP-TS-L1C/input/gm_alt100_act_150,/Users/sergio_ini/Documents/UC3M/5.MISE/5. BICUATRI/Earth Observation/EODP materials/SHARED/EODP_TER_2021/EODP-TS-L1C/input/l1b_output'
outdir = '/Users/sergio_ini/Documents/UC3M/5.MISE/5. BICUATRI/Earth Observation/EODP materials/SHARED/EODP_TER_2021/EODP-TS-L1C/output_test'

# Initialise the ISM
myL1c = l1c(auxdir, indir, outdir)
myL1c.processModule()
