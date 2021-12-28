
import Utils
import sys
import random
from itertools import islice
import os
import cea.config 
import cea.inputlocator as inputlocator
from cea.utilities import epwreader
from building_properties import BuildingProperties
import pandapower as pp
from building_model import Mpc as MPC





#TODO 
	# - INITIALIZATION OF THE NET  X done
	# - CREATION OF THE HIERARCHY FILE X done
	# - RUN SOLAR RADIATION DAYSIM
	# - RUN DEMAND SCHEDULING

class Initialize(object):
	def __init__(self, config, locator):
		self.config = config
		self.locator = locator
		self.weather_data = self.weather()
		self.bpr_log = self.bpr()
		self.building_names = ['B1000'] # extremely hard coded must avoided...
		self.schedules_log, self.tsd_log, self.tsd_ref_log, self.schedules_ref_log = self.tsd()	

		self.tsd_ref()
		
		print('Scenario initialized: READY to create the Simulation Agents!\n')
	
	

	def weather(self):
		weather_path = self.locator.get_weather_file()
		weather_data = epwreader.epw_reader(weather_path)[['year', 'drybulb_C', 'wetbulb_C',
														   'relhum_percent', 'windspd_ms', 'skytemp_C']]
		print('1) Weather file retrieved!\n')
		
		return weather_data

	def bpr(self):
		#pass None building names it will automatically retrieve them
		building_properties = BuildingProperties(self.locator) #object with properties for all buildings
		print('2) Buildings properties retrieved!\n')
		return building_properties
	
	def tsd(self):
		schedules, tsd_log, tsd_log_ref, schedules_ref = Utils.tsd_log_initilizer(self.building_names,self.bpr_log, 
																			self.weather_data, self.locator)
		
		print('3) TSD dicts created!\n')
		return schedules, tsd_log, tsd_log_ref, schedules_ref
	
	def tsd_ref (self):
		mpc = MPC(self.config, self.locator)
		print('============================')
		for name in self.building_names:
			print('compiling tsd_ref for building: %s'%name)
			bpr = self.bpr_log[name]
			print(bpr.rc_model)
			tsd_ref = self.tsd_ref_log[name]
			schedule_ref = self.schedules_ref_log[name]

			tsd_ref = mpc.calc_reference_annual(tsd_ref, name, bpr, schedule_ref) #could be problem with the file path when saving pickle
			
			if tsd_ref == 'not_conditioned':
				self.not_conditioned_buildings.append(name)

			self.tsd_ref_log[name] = tsd_ref #saving in the object
		print('============================\n')
		
		print('4) TSD ANNUAL REFERENCE done! \n')
	




	

		










if __name__ == '__main__':

	#global params to be set
	path_zone = '/Users/pietrorandomazzarino/Desktop/TESI/CODE/SG_simulator/scenario_1000/baseline/inputs/building-geometry/work_in_progr5.shp'
	#***** before running change cea.config path scenario in the desired location ******
	Scenario_Obj = main(path_zone)# this in case of first usage
	#Scenario_Obj = main() # this when scenario folder is already done

	print(Scenario_Obj.__dict__.keys())


	
