# -*- coding: utf-8 -*-





import numpy as np
import pandas as pd
import datetime
from cea.constants import HOURS_IN_YEAR, SECONDS_PER_HOUR
import math

__author__ = "Gabriel Happle"
__copyright__ = "Copyright 2016, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Gabriel Happle"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "thomas@arch.ethz.ch"
__status__ = "Production"

#DONE
def has_heating_system(hvac_class_hs):
    """
    determines whether a building has a heating system installed or not

    :param str hvac_class_hs: Heating system class of the HVAC unit
    :return: True, if the building has a (supported) heating system or False
    :rtype: bool
    """

    supported = ['RADIATOR', 'FLOOR_HEATING', 'CENTRAL_AC']
    unsupported = ['NONE']
    if hvac_class_hs in supported:
        return True
    elif hvac_class_hs in unsupported:
        return False
    else:
        raise ValueError('Invalid value for class_cs: %s. CEA only supports the following systems %s' % (
            hvac_class_hs, supported.extend(unsupported)))

#DONE
def has_cooling_system(hvac_class_cs):
    """
    determines whether a building has a cooling system installed or not

    :param str hvac_class_cs: Cooling system class of the HVAC unit
    :return: True, if the building has a (supported) cooling system or False
    :rtype: bool
    """
    supported = ['CEILING_COOLING', 'FLOOR_COOLING', 'DECENTRALIZED_AC', 'CENTRAL_AC', 'HYBRID_AC']
    unsupported = ['NONE']
    if hvac_class_cs in supported:
        return True
    elif hvac_class_cs in unsupported:
        return False
    else:
        raise ValueError('Invalid value for class_cs: %s. CEA only supports the following systems %s' % (
            hvac_class_cs, supported.extend(unsupported)))

#DONE
def has_radiator_heating_system(bpr):
    """
    Checks if building has radiator heating system

    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :return: True or False
    :rtype: bool
    """

    supported1 = ['RADIATOR']
    supported2 = ['NONE', 'FLOOR_HEATING', 'CENTRAL_AC']
    if bpr.hvac['class_hs'] in supported1:
        return True
    elif bpr.hvac['class_hs'] in supported2:
        return False
    else:
        raise ValueError('Invalid value for class_hs: %s. CEA only supports the following systems  %s' %(bpr.hvac['class_hs'], supported1.extend(supported2)))

#DONE
def has_floor_heating_system(bpr):
    """
    Checks if building has floor heating system

    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :return: True or False
    :rtype: bool
    """

    supported1 = ['FLOOR_HEATING']
    supported2 = ['NONE', 'RADIATOR', 'CENTRAL_AC']
    if bpr.hvac['class_hs'] in supported1:
        return True
    elif bpr.hvac['class_hs'] in supported2:
        return False
    else:
        raise ValueError('Invalid value for class_hs: %s. CEA only supports the following systems  %s' %(bpr.hvac['class_hs'], supported1.extend(supported2)))

#DONE
def has_central_ac_heating_system(bpr):
    """
    Checks if building has central AC heating system

    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :return: True or False
    :rtype: bool
    """

    supported1 = ['CENTRAL_AC']
    supported2 = ['NONE', 'RADIATOR', 'FLOOR_HEATING']
    if bpr.hvac['class_hs'] in supported1:
        return True
    elif bpr.hvac['class_hs'] in supported2:
        return False
    else:
        raise ValueError('Invalid value for class_hs: %s. CEA only supports the following systems %s' %(bpr.hvac['class_hs'], supported1.extend(supported2)))

#DONE
def has_local_ac_cooling_system(bpr):
    """
    Checks if building has mini-split unit AC cooling system

    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :return: True or False
    :rtype: bool
    """

    supported1 = ['DECENTRALIZED_AC']
    supported2 = ['NONE', 'CEILING_COOLING', 'FLOOR_COOLING', 'CENTRAL_AC', 'HYBRID_AC']
    if bpr.hvac['class_cs'] in supported1:
        return True
    elif bpr.hvac['class_cs'] in supported2:
        return False
    else:
        raise ValueError('Invalid value for class_cs: %s. CEA only supports the following systems %s' %(bpr.hvac['class_cs'], supported1.extend(supported2)))


#DONE
def has_central_ac_cooling_system(bpr):
    """
    Checks if building has central AC cooling system

    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :return: True or False
    :rtype: bool
    """
    supported1 = ['CENTRAL_AC']
    supported2 = ['NONE', 'CEILING_COOLING', 'FLOOR_COOLING', 'DECENTRALIZED_AC', 'HYBRID_AC']
    if bpr.hvac['class_cs'] in supported1:
        return True
    elif bpr.hvac['class_cs'] in supported2:
        return False
    else:
        raise ValueError('Invalid value for class_cs: %s. CEA only supports the following systems %s' %(bpr.hvac['class_cs'], supported1.extend(supported2)))

#DONE
def has_3for2_cooling_system(bpr):
    """
    Checks if building has 3for2 cooling system

    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :return: True or False
    :rtype: bool
    """

    supported1 = ['HYBRID_AC']
    supported2 = ['NONE', 'CEILING_COOLING', 'FLOOR_COOLING', 'DECENTRALIZED_AC', 'CENTRAL_AC']
    if bpr.hvac['class_cs'] in supported1:
        return True
    elif bpr.hvac['class_cs'] in supported2:
        return False
    else:
        raise ValueError('Invalid value for class_cs: %s. CEA only supports the following systems %s' %(bpr.hvac['class_cs'], supported1.extend(supported2)))

#DONE
def has_ceiling_cooling_system(bpr):
    """
    Checks if building has ceiling cooling system

    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :return: True or False
    :rtype: bool
    """

    supported1 = ['CEILING_COOLING']
    supported2 = ['NONE', 'HYBRID_AC', 'FLOOR_COOLING', 'DECENTRALIZED_AC', 'CENTRAL_AC']
    if bpr.hvac['class_cs'] in supported1:
        return True
    elif bpr.hvac['class_cs'] in supported2:
        return False
    else:
        raise ValueError('Invalid value for class_cs: %s. CEA only supports the following systems %s' %(bpr.hvac['class_cs'], supported1.extend(supported2)))
#DONE
def has_floor_cooling_system(bpr):
    """
    Checks if building has ceiling cooling system

    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :return: True or False
    :rtype: bool
    """

    supported1 = ['FLOOR_COOLING']
    supported2 = ['NONE', 'HYBRID_AC', 'CEILING_COOLING', 'DECENTRALIZED_AC', 'CENTRAL_AC']
    if bpr.hvac['class_cs'] in supported1:
        return True
    elif bpr.hvac['class_cs'] in supported2:
        return False
    else:
        raise ValueError('Invalid value for class_cs: %s. CEA only supports the following systems %s' %(bpr.hvac['class_cs'], supported1.extend(supported2)))
#DONE
def cooling_system_is_active(bpr, tsd, t):
    """
    Checks whether the cooling system is active according to rules for a specific hour of the year
    i.e., is there a set point temperature

    :param tsd: a dictionary of time step data mapping variable names to ndarrays for each hour of the year.
    :type tsd: dict
    :param t: hour of the year, simulation time step [0...HOURS_IN_YEAR]
    :type t: int
    :return: True or False
    :rtype: bool
    """
    if t == 0:
        T_ref = 20.
    else:
        T_ref =  tsd['T_int'][t - 1]
    if not pd.isnull(tsd['ta_cs_set'][t]) and not T_ref <= np.max([bpr.hvac['Tc_sup_air_ahu_C'],
                                                                               bpr.hvac['Tc_sup_air_aru_C']]):
        # system has set point according to schedule of operation & internal temperature is not below the set point
        return True
    else:
        return False

#DONE
def heating_system_is_active(tsd, t):
    """
    Checks whether the heating system is active according to rules for a specific hour of the year
    i.e., is there a set point temperature

    :param tsd: a dictionary of time step data mapping variable names to ndarrays for each hour of the year.
    :type tsd: dict
    :param t: hour of the year, simulation time step [0...HOURS_IN_YEAR]
    :type t: int
    :return: True or False
    :rtype: bool
    """
    
    if not pd.isnull(tsd['ta_hs_set'][t]):
        # system has set point according to schedule of operation
      
        return True
    else:
     
        return False



#DONE >>>> added the possibility of change resolution  hourly >>> 15 min
def convert_date_to_hour(date):
    """
    converts date in 'DD|MM' format into hour of the year (first hour of the day)
    i.e. '01|01' results in 0

    :param date: date in 'DD|MM' format (from .xlsx database input)
    :type date: str
    :return: hour of the year (first hour of the day)
    :rtype: int
    """
    #SECONDS_PER_HOUR = 60 * 60
    #SECONDS_PER_15MIN = 60 * 15

    day, month = map(int, date.split('|'))
    delta = datetime.datetime(2017, month, day) - datetime.datetime(2017, 1, 1)
    
    return int(delta.total_seconds() / SECONDS_PER_HOUR)


#DONE >>>> limit to one year
def is_heating_season(t, bpr):
    """
    checks if time step is part of the heating season for the building

    :param t: hour of the year, simulation time step [0...HOURS_IN_YEAR]
    :type t: int
    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :return: True or False
    :rtype: bool
    """

    if bpr.hvac['has-heating-season']:
        #DONE

        #heating_start = convert_date_to_hour(bpr.hvac['heat_starts'])
        #heating_end = convert_date_to_hour(bpr.hvac['heat_ends']) + 23  # end at the last hour of the day


        #TO USE FOR 15 min
        heating_start = convert_date_to_hour(bpr.hvac['heat_start'])
        heating_end = convert_date_to_hour(bpr.hvac['heat_ends']) + (23*4)  # end at the last hour of the day

        
        #TODO
        # check if heating season is at the end of the year (north hemisphere) or in the middle of the year (south)
        if heating_start < heating_end and \
                heating_start <= t <= heating_end:
           
            # heating season time on south hemisphere
            return True

        elif heating_start > heating_end and \
                (heating_start <= t <= HOURS_IN_YEAR or 0 <= t <= heating_end):
         
            # heating season over the year end (north hemisphere)
            return True

        else:
            # not time of heating season
           
            return False

        

    elif not bpr.hvac['has-heating-season']:
        # no heating season
        return False

#DONE >>>> limit to one year
def is_cooling_season(t, bpr):
    """
    checks if time step is part of the cooling season for the building

    :param t: hour of the year, simulation time step [0...HOURS_IN_YEAR]
    :type t: int
    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :return: True or False
    :rtype: bool
        """

    if bpr.hvac['has-cooling-season']:

        #cooling_start = convert_date_to_hour(bpr.hvac['cool_starts'])
        #cooling_end = convert_date_to_hour(bpr.hvac['cool_ends']) + 23  # end at the last hour of the day
        
        #TO USE FOR 15 min
        cooling_start = convert_date_to_hour(bpr.hvac['cool_start'])
        cooling_end = convert_date_to_hour(bpr.hvac['cool_ends']) + (23*4)  # end at the last hour of the day


        # check if cooling season is at the end of the year (south hemisphere) or in the middle of the year (north)
        if cooling_start < cooling_end and \
                cooling_start <= t <= cooling_end:

            # cooling season time on north hemisphere
            return True

        elif cooling_start > cooling_end and \
                (cooling_start <= t <= HOURS_IN_YEAR or 0 <= t <= cooling_end):
            # cooling season around the year end (south hemisphere)
            return True

        else:
            # not time of cooling season
            return False

    elif not bpr.hvac['has-cooling-season']:
        # no cooling season
        return False

# temperature controllers

#DONE >>> limit one year
def get_temperature_setpoints_incl_seasonality(tsd, bpr, schedules,t):
    """

    :param tsd: a dictionary of time step data mapping variable names to ndarrays for each hour of the year.
    :type tsd: dict
    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :param weekday:
    :return: tsd with updated columns
    :rtype: dict
    """
    #TODO
    hour_in_the_year = t #the equivalent position in the iterations for the hour of timestep
    tsd['ta_hs_set'][t] = get_heating_system_set_point(hour_in_the_year ,schedules.loc[t,'Ths_set_C'],bpr)
    
    tsd['ta_cs_set'][t] = get_cooling_system_set_point(hour_in_the_year,schedules.loc[t,'Tcs_set_C'],bpr)

    
    return tsd

#DONE >>>> limit to one year
def get_heating_system_set_point(t, Ths_set_C, bpr):
    """

    :param people:
    :param t: hour of the year, simulation time step [0...HOURS_IN_YEAR]
    :type t: int
    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :param Ths_set_C:
    :return: heating system set point temperature [°C]
    :rtype: double
    """
    

    if is_heating_season(t, bpr):
        if Ths_set_C == 'OFF':
            return np.nan
        else:
            return Ths_set_C
    else:
        return np.nan  # huge so the system will be off

#DONE >>>> limit to one year
def get_cooling_system_set_point(t, Tcs_set_C, bpr):
    """

    :param people:
    :param t: hour of the year, simulation time step [0...HOURS_IN_YEAR]
    :type t: int
    :param bpr: BuildingPropertiesRow
    :type bpr: cea.demand.building_properties.BuildingPropertiesRow
    :param Tcs_set_C:
    :return: cooling system set point temperature [°C]
    :rtype: double
    """

    if is_cooling_season(t, bpr):
        if Tcs_set_C == 'OFF':
            return np.nan
        else:
            return Tcs_set_C
    else:
        return np.nan  # huge so the system will be off
