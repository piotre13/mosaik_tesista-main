

#INITIALIZATION and HIERARCHY CREATION
#ZONE_PATH = 'baseline_GIS/zone_uso.shp'
#NET_PATH = '../scenario_1000_1h/mpc.mat'

#MAX_B_per_B = 22  #maximun number of Building per Bus
#MAX_B_per_A = 5	#maximum number of bus per aggregator




#DSO - OPF
#THRESHOLD = 0.05
#FORC_NOISE = 0.10 #percentage of noise +- to add at real power to obtain forcast
#PF = 0.9 #power factor


#simulation
SEC_IN_TS = 3600 #seconds in time-step  3600 (1h), 900 (15min)
SEC_IN_DAY = 86400
DAY_IN_YEAR = 365
HOURS_IN_YEAR = 3000
HOST = 'localhost' #main host
PORT = 5780 #main port (main container)
NUM_TS = 292  # end number of time-steps simulating 73h


#buildings
#TOLERANCE = 1.0
#SCENARIO = 'GA' # could be 'TO 'or 'ST' or 'GA'  # TO =1, ST = 2 GA =3
#HORIZON = 1/2


#for not saturating all cores
N_cores_OFF = 5
