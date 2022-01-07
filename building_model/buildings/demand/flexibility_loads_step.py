# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import json
import sys
sys.path.append('building_model/')
from cea.constants import HOURS_IN_YEAR, HOURS_PRE_CONDITIONING, SECONDS_PER_HOUR

#import demand_writers
import buildings.demand.hourly_procedure_heating_cooling_system_load as hourly_procedure_heating_cooling_system_load
import buildings.demand.ventilation_air_flows_simple as ventilation_air_flows_simple
import buildings.demand.latent_loads as latent_loads
import buildings.demand.sensible_loads as sensible_loads
import buildings.demand.electrical_loads as electrical_loads
import buildings.demand.hotwater_loads as hotwater_loads
import buildings.demand.refrigeration_loads as refrigeration_loads
import buildings.demand.datacenter_loads as datacenter_loads
import buildings.demand.ventilation_air_flows_detailed as ventilation_air_flows_detailed
import buildings.demand.control_heating_cooling_systems as control_heating_cooling_systems
from buildings.demand.latent_loads import convert_rh_to_moisture_content
from cea.utilities import reporting
import buildings.demand.thermal_loads_step as thermal_loads_step



def calc_flexibility_loads_step(building_name, bpr, locator,use_dynamic_infiltration_calculation,  
								config, schedules,tsd, t,tsd_ref,T_s):
	#only working for heating season  with emission system supplied by electricity E_hs

	#print('time-step: %i ********'%t)
	tsd = electrical_loads.calc_Eal_Epro(tsd, schedules) #serve per riempire tsd['El'] e simili
	# CALCULATE SPACE CONDITIONING DEMANDS
	#lascio gli np.zeros perche tanto questo non ha impianti hvac
	# if np.isclose(bpr.rc_model['Af'], 0.0):  # if building does not have conditioned area
	# 	tsd['T_int'] = tsd['T_ext']
	# 	tsd['x_int'] = np.vectorize(convert_rh_to_moisture_content)(tsd['rh_ext'], tsd['T_int'])
	# 	tsd['E_cs'] = tsd['E_hs'] = np.zeros(HOURS_IN_YEAR)
	# 	tsd['Eaux_cs'] = tsd['Eaux_hs'] = tsd['Ehs_lat_aux'] = np.zeros(HOURS_IN_YEAR)
	# 	print(f"building {bpr.name} does not have an air-conditioned area")
	#else:

	
	tsd = latent_loads.calc_Qgain_lat(tsd, schedules, t)
	tsd = calc_set_points(bpr,tsd, building_name, config, locator,
						  schedules, t,T_s)
	#print(tsd['T_int'][t], '  >>> T_int_prev')
	tsd = thermal_loads_step.calc_Qhs_Qcs(bpr, tsd,
					   use_dynamic_infiltration_calculation,t)  # end-use demand latent and sensible + ventilation
	
	tsd = sensible_loads.calc_Qhs_Qcs_loss(bpr, tsd,t,tsd_ref)  # losses #maybe we should consider this 0
	tsd = sensible_loads.calc_Qhs_sys_Qcs_sys(tsd,t)  # system (incl. losses)

	tsd = sensible_loads.calc_temperatures_emission_systems(bpr, tsd,t,tsd_ref)  # calculate temperatures MAYBE NOT NEEDED

	tsd = electrical_loads.calc_Eve(tsd,t)  # calc auxiliary loads ventilation 

	tsd = electrical_loads.calc_Eaux_Qhs_Qcs(tsd, bpr,t)  # calc auxiliary loads heating and cooling
	
	tsd = thermal_loads_step.calc_Qcs_sys(bpr, tsd, t)  # final : including fuels and renewables # in this is impotante the scale of system
	tsd = thermal_loads_step.calc_Qhs_sys(bpr, tsd, t)  # final : including fuels and renewables
	#print(tsd['T_int'][t],  '  >>> T_int_fin')
	
	Qh_res = tsd['E_hs'][t]
	Qc_res = tsd['E_cs'][t]
	#print('time-step END: %i ********\n'%t) 
	#Q_res is the amount of power resulting with the specifi temp set point
	return Qh_res , tsd

	
	



def calc_set_points(bpr, tsd, building_name, config, locator,
							  schedules, t, T_s):
	#in this function we save in tsd both the setpoints values and the internal values for temperature and humidity
	#tsd = control_heating_cooling_systems.get_temperature_setpoints_incl_seasonality(tsd, bpr, schedules, t)
	if t == 0:
		tsd['T_int'][t] = 20
	else:
		tsd['T_int'][t] = tsd['T_int'][t-1]

	#T_hs_set = control_heating_cooling_systems.get_heating_system_set_point(t ,schedules.loc[t,'Ths_set_C'],bpr)
	#T_cs_set = control_heating_cooling_systems.get_cooling_system_set_point(t,schedules.loc[t,'Tcs_set_C'],bpr)
	#le possibilità di setpoint sono 3 una temperatura, un nan perchè OFF o un nan perchè boh

	if control_heating_cooling_systems.is_heating_season(t, bpr):
	
		tsd['ta_hs_set'][t] = float(T_s)
		
	#for now we only pass a heating set point and so for cooling season 
	#we use a nan as setpoint (meaning no cooling I think??)
	elif control_heating_cooling_systems.is_cooling_season(t, bpr):

		tsd['ta_hs_set'][t] = np.nan

	tsd['x_int'][t-1] = latent_loads.convert_rh_to_moisture_content(tsd['rh_ext'][t-1], tsd['T_ext'][t-1])

	return tsd
	














