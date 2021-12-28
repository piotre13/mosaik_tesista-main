import cea.config
import cea.inputlocator
from initialize import Initialize
import pickle
from building_model import Mpc




#here must be a new scenario do it with only one building change cea.config
def initialize (config, locator, sc_path):
	scenario_cea = Initialize(config, locator)
	print(scenario_cea.__dict__)

	#step2 save the scenario as pickle object
	with open (sc_path, 'wb') as f:
		pickle.dump(scenario_cea, f, pickle.HIGHEST_PROTOCOL)


def test_simulation(config, locator, end, sc_path):
	model = Mpc(config, locator)
	bui_name = 'B1000'
	with open (sc_path,'rb') as f:
		scenario = pickle.load(f)
	print(scenario.__dict__.keys())

	tsd = scenario.tsd_log[bui_name]
	tsd_ref = scenario.tsd_ref_log[bui_name]
	bpr = scenario.bpr_log[bui_name]
	schedule = scenario.schedules_log[bui_name]

	t=0
	while t < end:
		tsd = model.calc_demand(bui_name, bpr, tsd, schedule, tsd_ref, t) 
		t+=1


	print(tsd['E_hs'][:20])







if __name__ == '__main__':
	config= cea.config.Configuration()
	locator = cea.inputlocator.InputLocator(scenario = config.scenario)
	sc_path = 'scenario_obj.pickle'
	
	# STEP1 initialize and save the scenario obj
	#initialize(config, locator, sc_path)

	#STEP2 SIMULATION
	test_simulation(config, locator, 20, sc_path )
	