# -*- coding: utf-8 -*-



import sys
sys.path.append('building_model/')
import buildings.demand.control_heating_cooling_systems as control_heating_cooling_systems
from buildings.demand.constants import TEMPERATURE_ZONE_CONTROL_NIGHT_FLUSHING, DELTA_T_NIGHT_FLUSHING 
from cea.constants import HOURS_IN_DAY, NIGHT_START, NIGHT_STOP
__author__ = "Gabriel Happle"
__copyright__ = "Copyright 2016, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Gabriel Happle"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "thomas@arch.ethz.ch"
__status__ = "Production"


#
#  CHECK SYSTEM STATUS
#
#DONE
def is_mechanical_ventilation_active(bpr, tsd, t):

	# TODO: check for ventilation schedule
	if has_mechanical_ventilation(bpr) \
			and tsd['m_ve_required'][t] > 0:

		# mechanical ventilation is active if there is a ventilation demand
		return True

	elif has_mechanical_ventilation(bpr) \
			and is_night_flushing_active(bpr, tsd, t):

		# mechanical ventilation for night flushing
		return True

	else:
		return False

#DONE
def is_window_ventilation_active(bpr, tsd, t):

	if has_window_ventilation(bpr) \
			and not is_mechanical_ventilation_active(bpr, tsd, t):

		# window ventilation in case of non-active mechanical ventilation
		return True

	else:
		return False

#DONE
def is_mechanical_ventilation_heat_recovery_active(bpr, tsd, t):
	"""
	Control of activity of heat exchanger of mechanical ventilation system
	
	Author: Gabriel Happle
	Date: APR 2017
	
	:param bpr: Building Properties
	:type bpr: BuildingPropertiesRow
	:param tsd: Time series data of building
	:type tsd: dict
	:param t: time step / hour of the year
	:type t: int
	:return: Heat exchanger ON/OFF status
	:rtype: bool
	"""
	if t == 0:
		T_ref = 20
	else:
		T_ref = tsd['T_int'][t-1]

	if is_mechanical_ventilation_active(bpr, tsd, t)\
			and has_mechanical_ventilation_heat_recovery(bpr)\
			and control_heating_cooling_systems.is_heating_season(t, bpr):
		if is_night_flushing_active(bpr, tsd, t) or is_economizer_active(bpr, tsd, t):
			return False
		else:
			return True

	elif is_mechanical_ventilation_active(bpr, tsd, t)\
			and has_mechanical_ventilation_heat_recovery(bpr)\
			and control_heating_cooling_systems.is_cooling_season(t, bpr)\
			and T_ref < tsd['T_ext'][t]:

		return True

	elif is_mechanical_ventilation_active(bpr, tsd, t) \
			and control_heating_cooling_systems.is_cooling_season(t, bpr) \
			and T_ref >= tsd['T_ext'][t]:

		# heat recovery is deactivated in the cooling case,
		# if outdoor air conditions are colder than indoor (free cooling)

		return False

	else:
		return False

#DONE
def is_night_flushing_active(bpr, tsd, t):

	# night flushing is available for window ventilation (manual) and mechanical ventilation (automatic)
	# night flushing is active during the night if the outdoor conditions are favourable
	if t == 0:
		T_ref = 20
	else:
		T_ref = tsd['T_int'][t-1]

	if has_night_flushing(bpr) \
			and is_night_time(t) \
			and T_ref > TEMPERATURE_ZONE_CONTROL_NIGHT_FLUSHING \
			and T_ref > tsd['T_ext'][t] + DELTA_T_NIGHT_FLUSHING \
			and tsd['rh_ext'][t] < bpr.comfort['RH_max_pc']:

		return True

	else:
		return False

#DONE
def is_economizer_active(bpr, tsd, t):
	"""
	Control of activity of economizer of mechanical ventilation system
	Economizer of mechanical ventilation is controlled via zone set point temperatures, indoor air temperature and
	outdoor air temperature.
	Economizer is active if the indoor air temperature exceeds the set point and the outdoor temperatures are lower
	than the set point.
	Economizer increases mechanical ventilation flow rate to the maximum.
	
	Author: Gabriel Happle
	Date: APR 2017
	
	:param bpr: Building Properties
	:type bpr: BuildingPropertiesRow
	:param tsd: Time series data of building
	:type tsd: dict
	:param t: time step / hour of the year
	:type t: int
	:return: Economizer ON/OFF status
	:rtype: bool
	"""
	if t == 0:
		T_ref = 20
	else:
		T_ref = tsd['T_int'][t-1]

	if has_mechanical_ventilation_economizer(bpr) \
			and T_ref > bpr.comfort['Tcs_set_C'] >= tsd['T_ext'][t]:

		return True

	else:
		return False




#
# CHECK SYSTEM CONFIGURATION
#
#DONE
def has_mechanical_ventilation(bpr):

	if bpr.hvac['MECH_VENT']:
		return True
	elif not bpr.hvac['MECH_VENT']:
		return False
	else:
		raise ValueError(bpr.hvac['MECH_VENT'])

#DONE
def has_window_ventilation(bpr):

	if bpr.hvac['WIN_VENT']:
		return True
	elif not bpr.hvac['WIN_VENT']:
		return False
	else:
		raise ValueError(bpr.hvac['WIN_VENT'])

#DONE
def has_mechanical_ventilation_heat_recovery(bpr):

	if bpr.hvac['HEAT_REC']:
		return True
	elif not bpr.hvac['HEAT_REC']:
		return False
	else:
		raise ValueError(bpr.hvac['HEAT_REC'])

#DONE
def has_night_flushing(bpr):

	if bpr.hvac['NIGHT_FLSH']:
		return True
	elif not bpr.hvac['NIGHT_FLSH']:
		return False
	else:
		raise ValueError(bpr.hvac['NIGHT_FLSH'])

#DONE
def has_mechanical_ventilation_economizer(bpr):

	if bpr.hvac['ECONOMIZER']:
		return True
	elif not bpr.hvac['ECONOMIZER']:
		return False
	else:
		raise ValueError(bpr.hvac['ECONOMIZER'])

#DONE
def is_night_time(t):
	"""
	Check if a certain hour of year is during night or not

	:param t:
	:return:
	"""
	return not is_day_time(t)

#DONE
def is_day_time(t):
	"""
	Check if a certain hour of the year is during the daytime or not

	:param t:
	:return:
	"""
	start_night = NIGHT_START  # 21:00 # TODO: make dynamic (e.g. as function of location/country)
	stop_night = NIGHT_STOP  # 07:00 # TODO: make dynamic (e.g. as function of location/country)
	hour_of_day = t % HOURS_IN_DAY
	return stop_night < hour_of_day < start_night
