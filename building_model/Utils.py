import sys 
sys.path.append('building_model/')
import numpy as np
from config import *
import pandas as pd

def tsd_log_initilizer(building_names, building_properties, weather, locator):

		tsd_log = {}
		tsd_ref_log = {}
		schedules_ref = {}
		schedules = {}
		for name in building_names:
			
			bpr = building_properties[name]
			schedule, tsd = initialize_inputs(bpr, weather,locator)
			_schedule, _tsd = initialize_inputs(bpr, weather, locator)
			tsd_log[name] = tsd #a dict for all the parameters needed
			schedules[name] = schedule #a dataframe with 8760 rows
			tsd_ref_log[name] = _tsd
			schedules_ref[name] = _schedule

			#print (schedule)
			#print(schedule.columns)
			#print(schedule.people_pax)
			#exit()

		#self.visualize(tsd_log,self.building_properties)
		#exit()
		return schedules, tsd_log, tsd_ref_log, schedules_ref

def initialize_inputs(bpr, weather, locator):
		"""
		:param bpr: a collection of building properties for the building used for thermal loads calculation
		:type bpr: BuildingPropertiesRow
		:param weather_data: data from the .epw weather file. Each row represents an hour of the year. The columns are:
			``drybulb_C``, ``relhum_percent``, and ``windspd_ms``
		:type weather_data: pandas.DataFrame
		:param date_range: the pd.date_range of the calculation year
		:type date_range: pd.date_range
		:param locator: the input locator
		:type locator: cea.inpultlocator.InputLocator
		:returns: one dict of schedules, one dict of time step data
		:rtype: dict
		"""
		# TODO: documentation, this function is actually two functions

		# get the building name
		building_name = bpr.name

		# this is used in the NN please do not erase or change!!
		tsd = initialize_timestep_data(bpr, weather)

		# get occupancy file è serie oraria per 8760
		# baseline/outputs/data/occupancy
		occupancy_yearly_schedules = pd.read_csv(locator.get_schedule_model_file(building_name))

		tsd['people'] = occupancy_yearly_schedules['people_pax']
		tsd['ve_lps'] = occupancy_yearly_schedules['Ve_lps']
		tsd['Qs'] = occupancy_yearly_schedules['Qs_W']

		return occupancy_yearly_schedules, tsd

def initialize_timestep_data(bpr, weather_data):
	"""
	initializes the time step data with the weather data and the minimum set of variables needed for computation.

	:param bpr: a collection of building properties for the building used for thermal loads calculation
	:type bpr: BuildingPropertiesRow
	:param weather_data: data from the .epw weather file. Each row represents an hour of the year. The columns are:
		``drybulb_C``, ``relhum_percent``, and ``windspd_ms``
	:type weather_data: pandas.DataFrame

	:return: returns the `tsd` variable, a dictionary of time step data mapping variable names to ndarrays for each hour of the year.
	:rtype: dict
	"""

	# Initialize dict with weather variables
	tsd = {'T_ext': weather_data.drybulb_C.values[:3000],
		   'T_ext_wetbulb': weather_data.wetbulb_C.values[:3000],
		   'rh_ext': weather_data.relhum_percent.values[:3000],
		   'T_sky': weather_data.skytemp_C.values[:3000],
		   'u_wind': weather_data.windspd_ms[:3000]}

	# fill data with nan values

	nan_fields_electricity = ['Eaux', 'Eaux_hs', 'Eaux_cs', 'Eaux_ww', 'Eaux_fw', 'Ehs_lat_aux',
							  'Eve',
							  'GRID',
							  'GRID_a',
							  'GRID_l',
							  'GRID_v',
							  'GRID_ve',
							  'GRID_data',
							  'GRID_pro',
							  'GRID_aux',
							  'GRID_ww',
							  'GRID_hs',
							  'GRID_cs',
							  'GRID_cdata',
							  'GRID_cre',
							  'PV', 'Eal', 'Edata', 'Epro', 'E_sys',
							  'E_ww', 'E_hs','E_hs_prev', 'E_cs', 'E_cre', 'E_cdata']
	nan_fields = ['mcpww_sys', 'mcptw',
				  'mcpcre_sys',
				  'mcpcdata_sys',
				  'SOLAR_ww',
				  'SOLAR_hs',
				  'NG_hs',
				  'COAL_hs',
				  'OIL_hs',
				  'WOOD_hs',
				  'NG_ww',
				  'COAL_ww',
				  'OIL_ww',
				  'WOOD_ww',
				  'vfw_m3perh']

	TSD_KEYS_HEATING_LOADS = ['Qhs_sen_rc', 'Qhs_sen_shu', 'Qhs_sen_ahu', 'Qhs_lat_ahu', 'Qhs_sen_aru', 'Qhs_lat_aru',
						  'Qhs_sen_sys', 'Qhs_lat_sys', 'Qhs_em_ls', 'Qhs_dis_ls', 'Qhs_sys_shu', 'Qhs_sys_ahu',
						  'Qhs_sys_aru',
						  'DH_hs', 'Qhs', 'Qhs_sys', 'QH_sys',
						  'DH_ww', 'Qww_sys', 'Qww', 'Qhs', 'Qhpro_sys']
	TSD_KEYS_COOLING_LOADS = ['Qcs_sen_rc', 'Qcs_sen_scu', 'Qcs_sen_ahu', 'Qcs_lat_ahu', 'Qcs_sen_aru', 'Qcs_lat_aru',
							  'Qcs_sen_sys', 'Qcs_lat_sys', 'Qcs_em_ls', 'Qcs_dis_ls', 'Qcs_sys_scu', 'Qcs_sys_ahu',
							  'Qcs_sys_aru',
							  'DC_cs', 'Qcs', 'Qcs_sys', 'QC_sys',
							  'DC_cre', 'Qcre_sys', 'Qcre',
							  'DC_cdata', 'Qcdata_sys', 'Qcdata', 'Qcpro_sys']
	TSD_KEYS_HEATING_TEMP = ['ta_re_hs_ahu', 'ta_sup_hs_ahu', 'ta_re_hs_aru', 'ta_sup_hs_aru','ta_hs_set']
	TSD_KEYS_HEATING_FLOWS = ['ma_sup_hs_ahu', 'ma_sup_hs_aru']
	TSD_KEYS_COOLING_TEMP = ['ta_re_cs_ahu', 'ta_sup_cs_ahu', 'ta_re_cs_aru', 'ta_sup_cs_aru','ta_cs_set']
	TSD_KEYS_COOLING_FLOWS = ['ma_sup_cs_ahu', 'ma_sup_cs_aru']
	TSD_KEYS_COOLING_SUPPLY_FLOWS = ['mcpcs_sys_ahu', 'mcpcs_sys_aru', 'mcpcs_sys_scu', 'mcpcs_sys']
	TSD_KEYS_COOLING_SUPPLY_TEMP = ['Tcs_sys_re_ahu', 'Tcs_sys_re_aru', 'Tcs_sys_re_scu', 'Tcs_sys_sup_ahu',
									'Tcs_sys_sup_aru',
									'Tcs_sys_sup_scu', 'Tcs_sys_sup', 'Tcs_sys_re',
									'Tcdata_sys_re', 'Tcdata_sys_sup',
									'Tcre_sys_re', 'Tcre_sys_sup']
	TSD_KEYS_HEATING_SUPPLY_FLOWS = ['mcphs_sys_ahu', 'mcphs_sys_aru', 'mcphs_sys_shu', 'mcphs_sys']
	TSD_KEYS_HEATING_SUPPLY_TEMP = ['Ths_sys_re_ahu', 'Ths_sys_re_aru', 'Ths_sys_re_shu', 'Ths_sys_sup_ahu',
									'Ths_sys_sup_aru',
									'Ths_sys_sup_shu', 'Ths_sys_sup', 'Ths_sys_re',
									'Tww_sys_sup', 'Tww_sys_re']
	TSD_KEYS_RC_TEMP = ['T_int','T_int_prev', 'theta_m', 'theta_c', 'theta_o', 'theta_ve_mech']
	TSD_KEYS_MOISTURE = ['x_int', 'x_ve_inf', 'x_ve_mech', 'g_hu_ld', 'g_dhu_ld']
	TSD_KEYS_VENTILATION_FLOWS = ['m_ve_window', 'm_ve_mech', 'm_ve_rec', 'm_ve_inf', 'm_ve_required']
	TSD_KEYS_ENERGY_BALANCE_DASHBOARD = ['Q_gain_sen_light', 'Q_gain_sen_app', 'Q_gain_sen_peop', 'Q_gain_sen_data',
										 'Q_loss_sen_ref', 'Q_gain_sen_wall', 'Q_gain_sen_base', 'Q_gain_sen_roof',
										 'Q_gain_sen_wind', 'Q_gain_sen_vent', 'Q_gain_lat_peop', 'Q_gain_sen_pro']
	TSD_KEYS_SOLAR = ['I_sol', 'I_rad', 'I_sol_and_I_rad']
	TSD_KEYS_PEOPLE = ['people', 've', 'Qs', 'w_int']


	nan_fields.extend(TSD_KEYS_HEATING_LOADS)
	nan_fields.extend(TSD_KEYS_COOLING_LOADS)
	nan_fields.extend(TSD_KEYS_HEATING_TEMP)
	nan_fields.extend(TSD_KEYS_COOLING_TEMP)
	nan_fields.extend(TSD_KEYS_COOLING_FLOWS)
	nan_fields.extend(TSD_KEYS_HEATING_FLOWS)
	nan_fields.extend(TSD_KEYS_COOLING_SUPPLY_FLOWS)
	nan_fields.extend(TSD_KEYS_COOLING_SUPPLY_TEMP)
	nan_fields.extend(TSD_KEYS_HEATING_SUPPLY_FLOWS)
	nan_fields.extend(TSD_KEYS_HEATING_SUPPLY_TEMP)
	nan_fields.extend(TSD_KEYS_RC_TEMP)
	nan_fields.extend(TSD_KEYS_MOISTURE)
	nan_fields.extend(TSD_KEYS_ENERGY_BALANCE_DASHBOARD)
	nan_fields.extend(TSD_KEYS_SOLAR)
	nan_fields.extend(TSD_KEYS_VENTILATION_FLOWS)
	nan_fields.extend(nan_fields_electricity)
	nan_fields.extend(TSD_KEYS_PEOPLE)

	tsd.update(dict((x, np.zeros(HOURS_IN_YEAR) * np.nan) for x in nan_fields))

	# initialize system status log
	tsd['sys_status_ahu'] = np.chararray(HOURS_IN_YEAR, itemsize=20)
	tsd['sys_status_aru'] = np.chararray(HOURS_IN_YEAR, itemsize=20)
	tsd['sys_status_sen'] = np.chararray(HOURS_IN_YEAR, itemsize=20)
	tsd['sys_status_ahu'][:] = 'unknown'
	tsd['sys_status_aru'][:] = 'unknown'
	tsd['sys_status_sen'][:] = 'unknown'

	return tsd
