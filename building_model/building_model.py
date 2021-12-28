#basic and utilities CEA imports
import cea.config
import cea.inputlocator
from cea.utilities import epwreader
from cea.utilities.date import get_date_range_hours_from_year
from cea.constants import HOURS_IN_YEAR, SECONDS_PER_HOUR
from cea.utilities.reporting import full_report_to_xls
from cea.utilities.dbf import dataframe_to_dbf, dbf_to_dataframe


#from demand imports
from buildings.demand.building_properties import BuildingProperties
import buildings.demand.thermal_loads_step as thermal_loads_step
import buildings.demand.sensible_loads as sensible_loads
import buildings.demand.flexibility_loads_step as flexibility_loads_step
import buildings.demand.rc_model_SIA as rc_model_SIA
from buildings.demand.latent_loads import convert_rh_to_moisture_content

#imports for testing
# import sys
# sys.path.append('../')
# sys.path.append('../initialization/')
# from demand.building_properties import BuildingProperties
# import demand.thermal_loads_step as thermal_loads_step
# import demand.sensible_loads as sensible_loads
# import demand.flexibility_loads_step as flexibility_loads_step
# import demand.rc_model_SIA as rc_model_SIA
# from demand.latent_loads import convert_rh_to_moisture_content

#simulation imports
from config import *

#flexibility imports
from geneticalgorithm import geneticalgorithm as ga

#basic imports
import pandas as pd
import numpy as np
import pickle
import copy
import random


class Mpc ():

	#@profile
	def __init__(self, config, locator):
		self.config = config
		self.locator = locator

		weather_path = self.locator.get_weather_file()
		self.weather_data = epwreader.epw_reader(weather_path)[['year', 'drybulb_C', 'wetbulb_C',
														   'relhum_percent', 'windspd_ms', 'skytemp_C']]
		year = self.weather_data['year'][0]
		self.date_range = get_date_range_hours_from_year(year)
		
	#@profile
	def calc_reference_annual(self,tsd_ref, b_name, bpr, schedule_ref):
		
		if np.isclose(bpr.rc_model['Af'], 0.0):  # if building does not have conditioned area
			tsd_ref['T_int'] = tsd_ref['T_ext']
			tsd_ref['x_int'] = np.vectorize(convert_rh_to_moisture_content)(tsd_ref['rh_ext'], tsd_ref['T_int'])
			tsd_ref['E_cs'] = tsd_ref['E_hs'] = np.zeros(HOURS_IN_YEAR)
			tsd_ref['Eaux_cs'] = tsd_ref['Eaux_hs'] = tsd_ref['Ehs_lat_aux'] = np.zeros(HOURS_IN_YEAR)
			print(f"building {bpr.name} does not have an air-conditioned area")
			return 'not_conditioned'

		else:

			use_dynamic_infiltration = self.config.demand.use_dynamic_infiltration_calculation

			for i in range(3000):
				tsd_ref = thermal_loads_step.calc_thermal_loads_ref (b_name, self.date_range, self.locator, bpr, self.config, schedule_ref, 
								tsd_ref, i, use_dynamic_infiltration)

			#ricreo le funzioni originali e le chiamo senza timestep
			tsd_ref = sensible_loads.calc_Qhs_Qcs_loss_ref (bpr,tsd_ref)
			tsd_ref = sensible_loads.calc_Qhs_sys_Qcs_sys_ref(tsd_ref)

			#save tsd ref 
			with open('buildings/tsd_ref_values/'+str(b_name)+'.pickle', 'wb') as file:
				pickle.dump(tsd_ref, file, protocol=pickle.HIGHEST_PROTOCOL)
		

			return tsd_ref

	#@profile
	def calc_demand(self, b_name, bpr, tsd, schedule, tsd_ref, t):
		
		if np.isclose(bpr.rc_model['Af'], 0.0):  # if building does not have conditioned area
			tsd['T_int'] = tsd['T_ext']
			tsd['x_int'] = np.vectorize(convert_rh_to_moisture_content)(tsd['rh_ext'], tsd['T_int'])
			tsd['E_cs'] = tsd['E_hs'] = np.zeros(HOURS_IN_YEAR)
			tsd['Eaux_cs'] = tsd['Eaux_hs'] = tsd['Ehs_lat_aux'] = np.zeros(HOURS_IN_YEAR)
			print(f"building {bpr.name} does not have an air-conditioned area")

		else:
			use_dynamic_infiltration = self.config.demand.use_dynamic_infiltration_calculation
			resolution_output = self.config.demand.resolution_output #str: resolution ex 'hourly'
			loads_output = self.config.demand.loads_output #list of keys for the load outputs
			massflows_output = self.config.demand.massflows_output #list of keys for the massflow outputs
			temperatures_output = self.config.demand.temperatures_output #list of keys for the temperatures outputs
			debug = self.config.debug #boolean BOH forse non serve
			#print(b_name,'>>>REAL T_int at beging of timestep',tsd['T_int'][t-1])
			tsd = thermal_loads_step.calc_thermal_loads_step(b_name, bpr, self.weather_data, self.date_range, self.locator,
						   use_dynamic_infiltration, resolution_output, loads_output, massflows_output,
							temperatures_output, self.config, debug, schedule, tsd, t, tsd_ref)
			

		return tsd



	

	def Mw_2_w (self, power):
		return power * 1e6







if __name__ == '__main__':

	
	config = cea.config.Configuration()
	locator = cea.inputlocator.InputLocator(scenario = config.scenario)


	#*********************************
	#outside this script
	#before all making changes in the databases
	#switching all heating into radiators with heatpump, no cooling, no ventilation, no hotwater
	# supply_path = '/Users/pietrorandomazzarino/Desktop/TESI/CODE/CEA/CityEnergyAnalyst/cea/examples/reference-case-open/baseline/inputs/building-properties/supply_systems.dbf'
	# hvac_path = '/Users/pietrorandomazzarino/Desktop/TESI/CODE/CEA/CityEnergyAnalyst/cea/examples/reference-case-open/baseline/inputs/building-properties/air_conditioning.dbf'
	# supp_df = dbf_to_dataframe(supply_path)
	# hvac_df = dbf_to_dataframe(hvac_path)
	
	# #making the changes
	# supp_df.loc[:,'type_cs'] = 'SUPPLY_COOLING_AS0'
	# supp_df.loc[:,'type_dhw'] = 'SUPPLY_HOTWATER_AS0'
	# supp_df.loc[:,'type_hs'] = 'SUPPLY_HEATING_AS6'

	# hvac_df.loc[:,'type_cs'] = 'HVAC_COOLING_AS0'
	# hvac_df.loc[:,'type_dhw'] = 'HVAC_HOTWATER_AS0'
	# hvac_df.loc[:,'type_hs'] = 'HVAC_HEATING_AS2'
	# hvac_df.loc[:,'type_vent'] = 'HVAC_VENTILATION_AS0'


	# dataframe_to_dbf(supp_df,supply_path)
	# dataframe_to_dbf(hvac_df,hvac_path)

	


	#building_names = config.demand.buildings #list of building names
	#building_properties = BuildingProperties(locator,building_names) #object with properties for all buildings
	#weather_path = locator.get_weather_file()
	#weather_data = epwreader.epw_reader(weather_path)[['year', 'drybulb_C', 'wetbulb_C',
	#													   'relhum_percent', 'windspd_ms', 'skytemp_C']] 
	#for building in building_names:
	
	#schedules, tsd_log, tsd_log_ref, schedules_ref = tsd_log_initilizer(building_names,building_properties, weather_data, locator)
	#***********************************

	#ACTUAL MAIN FOR FINAL MODULE
	with open ('/Users/pietrorandomazzarino/Desktop/TESI/CODE/SG_simulator/scenario_obj.pickle','rb') as f:
		scenario = pickle.load(f)
	print(scenario.__dict__.keys())

	bpr = scenario.bpr_log['B1000']
	tsd = scenario.tsd_log['B1000']
	tsd_ref = scenario.tsd_ref_log['B1000']
	schedule = scenario.schedules_log['B1000']
	schedule_ref =scenario.schedules_ref_log['B1000']
	mpc = Mpc(config, locator)
	##running test calc_demand will be incapsulated in simualtio while loop
	
	##STEP1 calc_reference_annual
	#tsd_ref = mpc.calc_reference_annual(tsd_ref, 'B1000', bpr, schedule_ref)
	##reading the ref values file to run separately
	
	
	##STEP2 calculating actual demand 
	#with open('reference_values/B1000.pickle', 'rb') as file:
	#	tsd_ref = pickle.load(file)

	#testing demand function
	#for t in range(8760):
	for building in scenario.building_names:
		for i in range (96):
			tsd = mpc.calc_demand(building,bpr, tsd, schedule, tsd_ref, i)
	#full_report_to_xls(tsd, 'testing_checks/', 'B1000')
	
	#testing flexibility function
		print(building)
		mpc.calc_flex(building, bpr, tsd, schedule, tsd_ref, 94)
		print('done!!')
	#testing actuation control function
	#P_ref = 72960.73/3600 #in KW
	#adjustment = (P_ref/100)*10 #in KW
	#mpc.controller('B1000', adjustment, P_ref, tsd, bpr, 0)









