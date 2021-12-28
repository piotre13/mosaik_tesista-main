# -*- coding: utf-8 -*-
"""
Demand model of thermal loads
"""




import numpy as np
import pandas as pd
import json

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

def calc_thermal_loads_ref( building_name, date_range, locator, bpr, config, schedules, 
                            tsd_ref, t, use_dynamic_infiltration_calculation):
    tsd_ref = electrical_loads.calc_Eal_Epro(tsd_ref, schedules) #serve per riempire tsd['El'] e simili
    # CALCULATE SPACE CONDITIONING DEMANDS
    #lascio gli np.zeros perche tanto questo non ha impianti hvac
    
        
    tsd_ref = latent_loads.calc_Qgain_lat(tsd_ref, schedules, t) #<<<<<<
    tsd_ref = calc_set_points(bpr, date_range, tsd_ref, building_name, config, locator,
                            schedules, t)  # calculate the setpoints for every hour
    tsd_ref = calc_Qhs_Qcs(bpr, tsd_ref,
                        use_dynamic_infiltration_calculation,t)  # end-use demand latent and sensible + ventilation

    return tsd_ref


def calc_thermal_loads_step(building_name, bpr, weather_data, date_range, locator,
                       use_dynamic_infiltration_calculation, resolution_outputs, loads_output, massflows_output,
                       temperatures_output, config, debug,schedules,tsd, t,tsd_ref):
    """
    Calculate thermal loads of a single building with mechanical or natural ventilation.
    Calculation procedure follows the methodology of ISO 13790

    The structure of ``usage_schedules`` is:

    .. code-block:: python
        :emphasize-lines: 2,4

        {
            'list_uses': ['ADMIN', 'GYM', ...],
            'schedules': [ ([...], [...], [...], [...]), (), (), () ]
        }

    * each element of the 'list_uses' entry represents a building occupancy type.
    * each element of the 'schedules' entry represents the schedules for a building occupancy type.
    * the schedules for a building occupancy type are a 4-tuple (occupancy, electricity, domestic hot water,
      probability of use), with each element of the 4-tuple being a list of hourly values (HOURS_IN_YEAR values).


    Side effect include a number of files in two folders:

    * ``scenario/outputs/data/demand``

      * ``${Name}.csv`` for each building

    * temporary folder (as returned by ``tempfile.gettempdir()``)

      * ``${Name}T.csv`` for each building

    daren-thomas: as far as I can tell, these are the only side-effects.

    :param building_name: name of building
    :type building_name: str

    :param bpr: a collection of building properties for the building used for thermal loads calculation
    :type bpr: BuildingPropertiesRow

    :param weather_data: data from the .epw weather file. Each row represents an hour of the year. The columns are:
        ``drybulb_C``, ``relhum_percent``, and ``windspd_ms``
    :type weather_data: pandas.DataFrame

    :param locator:
    :param use_dynamic_infiltration_calculation:

    :returns: This function does not return anything
    :rtype: NoneType

"""
    #schedules, tsd = initialize_inputs(bpr, weather_data, locator)
    #schedules: pandas Dataframe
    #tsd : dict
    
    #consumpiotn due to light and appliances is scheduled for all the year
    tsd = electrical_loads.calc_Eal_Epro(tsd, schedules) #serve per riempire tsd['El'] e simili


   
    # CALCULATE SPACE CONDITIONING DEMANDS
    #lascio gli np.zeros perche tanto questo non ha impianti hvac
    if np.isclose(bpr.rc_model['Af'], 0.0):  # if building does not have conditioned area
        tsd['T_int'] = tsd['T_ext']
        tsd['x_int'] = np.vectorize(convert_rh_to_moisture_content)(tsd['rh_ext'], tsd['T_int'])
        tsd['E_cs'] = tsd['E_hs'] = np.zeros(HOURS_IN_YEAR)
        tsd['Eaux_cs'] = tsd['Eaux_hs'] = tsd['Ehs_lat_aux'] = np.zeros(HOURS_IN_YEAR)
        print(f"building {bpr.name} does not have an air-conditioned area")



    else:
        
        tsd = latent_loads.calc_Qgain_lat(tsd, schedules, t) #<<<<<<
        #DONE **************************
        tsd = calc_set_points(bpr, date_range, tsd, building_name, config, locator,
                              schedules, t)  # calculate the setpoints for every hour
        tsd = calc_Qhs_Qcs(bpr, tsd,
                           use_dynamic_infiltration_calculation,t)  # end-use demand latent and sensible + ventilation
        
        
        
        
        tsd = sensible_loads.calc_Qhs_Qcs_loss(bpr, tsd,t,tsd_ref)  # losses #maybe we should consider this 0
        tsd = sensible_loads.calc_Qhs_sys_Qcs_sys(tsd,t)  # system (incl. losses)

        tsd = sensible_loads.calc_temperatures_emission_systems(bpr, tsd,t,tsd_ref)  # calculate temperatures MAYBE NOT NEEDED

        tsd = electrical_loads.calc_Eve(tsd,t)  # calc auxiliary loads ventilation 

        tsd = electrical_loads.calc_Eaux_Qhs_Qcs(tsd, bpr,t)  # calc auxiliary loads heating and cooling
        
        tsd = calc_Qcs_sys(bpr, tsd, t)  # final : including fuels and renewables # in this is impotante the scale of system
        tsd = calc_Qhs_sys(bpr, tsd, t)  # final : including fuels and renewables

        # Positive loads
        tsd['Qcs_lat_sys'][t] = abs(tsd['Qcs_lat_sys'][t])
        tsd['DC_cs'][t] = abs(tsd['DC_cs'][t])
        tsd['Qcs_sys'][t] = abs(tsd['Qcs_sys'][t])
        tsd['Qcre_sys'][t] = abs(tsd['Qcre_sys'][t])  # inverting sign of cooling loads for reporting and graphs
        tsd['Qcdata_sys'][t] = abs(tsd['Qcdata_sys'][t])  # inverting sign of cooling loads for reporting and graphs


    # CALCULATE SUM OF HEATING AND COOLING LOADS
    tsd = calc_QH_sys_QC_sys(tsd, t)  # aggregated cooling and heating loads #DONE

    # CALCULATE ELECTRICITY LOADS PART 2/2 AUXILIARY LOADS + ENERGY GENERATION
    #DONE
    tsd = electrical_loads.calc_Eaux(tsd, t)  # auxiliary totals
    tsd = electrical_loads.calc_E_sys(tsd, t)  # system (incl. losses)
    tsd = electrical_loads.calc_Ef(bpr, tsd, t)  # final (incl. self. generated)

    # WRITE SOLAR RESULTS
    #write_results(bpr, building_name, date_range, loads_output, locator, massflows_output,
    #              resolution_outputs, temperatures_output, tsd, debug)

    #print (tsd)
    return tsd

#DONE
def calc_QH_sys_QC_sys(tsd, t):
    tsd['QH_sys'][t] = tsd['Qww_sys'][t] + tsd['Qhs_sys'][t] + tsd['Qhpro_sys'][t]
    tsd['QC_sys'][t] = tsd['Qcs_sys'][t] + tsd['Qcdata_sys'][t] + tsd['Qcre_sys'][t] + tsd['Qcpro_sys'][t]

    return tsd


def write_results(bpr, building_name, date, loads_output, locator, massflows_output,
                  resolution_outputs, temperatures_output, tsd, debug):
    if resolution_outputs == 'hourly':
        writer = demand_writers.HourlyDemandWriter(loads_output, massflows_output, temperatures_output)
    elif resolution_outputs == 'monthly':
        writer = demand_writers.MonthlyDemandWriter(loads_output, massflows_output, temperatures_output)
    else:
        raise Exception('error')

    if debug:
        print('Creating instant plotly visualizations of demand variable time series.')
        print('Behavior can be changed in cea.utilities.reporting code.')
        print('Writing detailed demand results of {} to .xls file.'.format(building_name))
        reporting.quick_visualization_tsd(tsd, locator.get_demand_results_folder(), building_name)
        reporting.full_report_to_xls(tsd, locator.get_demand_results_folder(), building_name)
    else:
        writer.results_to_csv(tsd, bpr, locator, date, building_name)

#DONE
def calc_Qcs_sys(bpr, tsd, t):
    # GET SYSTEMS EFFICIENCIES
    energy_source = bpr.supply['source_cs']
    scale_technology = bpr.supply['scale_cs']
    efficiency_average_year = bpr.supply['eff_cs']
    if scale_technology == "BUILDING":
        if energy_source == "GRID":
            # sum
            tsd['E_cs'][t] = abs(tsd['Qcs_sys'][t]) / efficiency_average_year
            tsd['DC_cs'][t] = 0.
        elif energy_source == "NONE":
            tsd['E_cs'][t] = 0.
            tsd['DC_cs'][t] = 0.
        else:
            raise Exception('check potential error in input database of LCA infrastructure / COOLING')
    elif scale_technology == "DISTRICT":
        if energy_source == "GRID":
            tsd['DC_cs'][t] = tsd['Qcs_sys'][t] / efficiency_average_year
            tsd['E_cs'][t] = 0.
        elif energy_source == "NONE":
            tsd['DC_cs'][t] = 0.
            tsd['E_cs'][t] = 0.
        else:
            raise Exception('check potential error in input database of ALL IN ONE SYSTEMS / COOLING')
    elif scale_technology == "NONE":
        tsd['DC_cs'][t] = 0.
        tsd['E_cs'][t] = 0.
    else:
        raise Exception('check potential error in input database of LCA infrastructure / COOLING')
    return tsd

#DONE
def calc_Qhs_sys(bpr, tsd, t):
    """
    it calculates final loads
    """

    # GET SYSTEMS EFFICIENCIES
    # GET SYSTEMS EFFICIENCIES
    energy_source = bpr.supply['source_hs']
    scale_technology = bpr.supply['scale_hs']
    efficiency_average_year = bpr.supply['eff_hs']

    if scale_technology == "BUILDING":
        if energy_source == "GRID":
            tsd['E_hs'][t] = tsd['Qhs_sys'][t] / efficiency_average_year
            tsd['DH_hs'][t] = 0.
            tsd['NG_hs'][t] = 0.
            tsd['COAL_hs'][t] = 0.
            tsd['OIL_hs'][t] = 0.
            tsd['WOOD_hs'][t] = 0.
        elif energy_source == "NATURALGAS":
            tsd['NG_hs'][t] = tsd['Qhs_sys'][t] / efficiency_average_year
            tsd['COAL_hs'][t] = 0.
            tsd['OIL_hs'][t] = 0.
            tsd['WOOD_hs'][t] = 0.
            tsd['DH_hs'][t] = 0.
            tsd['E_hs'][t] = 0.
        elif energy_source == "OIL":
            tsd['NG_hs'][t] = 0.
            tsd['COAL_hs'][t] = 0.
            tsd['OIL_hs'][t] = tsd['Qhs_sys'][t] / efficiency_average_year
            tsd['WOOD_hs'][t] = 0.
            tsd['DH_hs'][t] = 0.
            tsd['E_hs'][t] = 0.
        elif energy_source == "COAL":
            tsd['NG_hs'][t] = 0.
            tsd['COAL_hs'][t] = tsd['Qhs_sys'][t] / efficiency_average_year
            tsd['OIL_hs'][t] = 0.
            tsd['WOOD_hs'][t] = 0.
            tsd['DH_hs'][t] = 0.
            tsd['E_hs'][t] = 0.
            tsd['SOLAR_hs'][t] = 0.
        elif energy_source == "WOOD":
            tsd['NG_hs'][t] = 0.
            tsd['COAL_hs'][t] = 0.
            tsd['OIL_hs'][t] = 0.
            tsd['WOOD_hs'][t] = tsd['Qhs_sys'][t] / efficiency_average_year
            tsd['DH_hs'][t] = 0.
            tsd['E_hs'][t] = 0.
        elif energy_source == "NONE":
            tsd['NG_hs'][t] = 0.
            tsd['COAL_hs'][t] = 0.
            tsd['OIL_hs'][t] = 0.
            tsd['WOOD_hs'][t] = 0.
            tsd['DH_hs'][t] = 0.
            tsd['E_hs'][t] = 0.
        else:
            raise Exception('check potential error in input database of LCA infrastructure / HEATING')
    #probably district scale will not be used!!!
    elif scale_technology == "DISTRICT":
        tsd['NG_hs'][t] = 0.
        tsd['COAL_hs'][t] = 0.
        tsd['OIL_hs'][t] = 0.
        tsd['WOOD_hs'][t] = 0.
        tsd['DH_hs'][t] = tsd['Qhs_sys'][t] / efficiency_average_year
        tsd['E_hs'][t] = 0.
    elif scale_technology == "NONE":
        tsd['NG_hs'][t] = 0.
        tsd['COAL_hs'][t] = 0.
        tsd['OIL_hs'][t] = 0.
        tsd['WOOD_hs'][t] = 0.
        tsd['DH_hs'][t] = 0.
        tsd['E_hs'][t] = 0.
    else:
        raise Exception('check potential error in input database of LCA infrastructure / HEATING')
    return tsd

#DONE
def calc_set_points(bpr, date, tsd, building_name, config, locator, schedules, t):
    # get internal comfort properties
    tsd = control_heating_cooling_systems.get_temperature_setpoints_incl_seasonality(tsd, bpr, schedules, t)
    
    #t_prev = next(get_hours(bpr)) - 1 #ORIGINAL
    if t == 0:
        tsd['T_int'][t] = 20
    else:
        tsd['T_int'][t] = tsd['T_int'][t-1] #inizialmente t int = a t int all'istante precedente
    
    #tsd['T_int'][t_prev] = tsd['T_ext'][t_prev] #ORIGINAL
    
    #tsd['x_int'][t_prev] = latent_loads.convert_rh_to_moisture_content(tsd['rh_ext'][t_prev], tsd['T_ext'][t_prev])
    tsd['x_int'][t-1] = latent_loads.convert_rh_to_moisture_content(tsd['rh_ext'][t-1], tsd['T_ext'][t-1])
    #DONE
    return tsd

#DONE
def calc_Qhs_Qcs(bpr, tsd, use_dynamic_infiltration_calculation,t):
    # get ventilation flows
    
    ventilation_air_flows_simple.calc_m_ve_required(tsd,t) # NEED TO UNDERSTAND HOW OCCUPANCY SCHEDULE ARE CONSTRUCTED
    ventilation_air_flows_simple.calc_m_ve_leakage_simple(bpr, tsd,t)
    
    # end-use demand calculation
    #for t in get_hours(bpr): #ORIGINAL

    # heat flows in [W]
    tsd = sensible_loads.calc_Qgain_sen(t, tsd, bpr)
    
     
    if use_dynamic_infiltration_calculation:
        # OVERWRITE STATIC INFILTRATION WITH DYNAMIC INFILTRATION RATE
        dict_props_nat_vent = ventilation_air_flows_detailed.get_properties_natural_ventilation(bpr)
        qm_sum_in, qm_sum_out = ventilation_air_flows_detailed.calc_air_flows(
            tsd['T_int'][t - 1], tsd['u_wind'][t], tsd['T_ext'][t], dict_props_nat_vent)
        # INFILTRATION IS FORCED NOT TO REACH ZERO IN ORDER TO AVOID THE RC MODEL TO FAIL
        tsd['m_ve_inf'][t] = max(qm_sum_in / SECONDS_PER_HOUR, 1 / SECONDS_PER_HOUR)
   
    # ventilation air flows [kg/s]
    ventilation_air_flows_simple.calc_air_mass_flow_mechanical_ventilation(bpr, tsd, t)
    ventilation_air_flows_simple.calc_air_mass_flow_window_ventilation(bpr, tsd, t)
    # ventilation air temperature and humidity
    ventilation_air_flows_simple.calc_theta_ve_mech(bpr, tsd, t)
    
    latent_loads.calc_moisture_content_airflows(tsd, t)
    
    #DONE
    #TO DO
    # heating / cooling demand of building
    tsd= hourly_procedure_heating_cooling_system_load.calc_heating_cooling_loads(bpr, tsd, t)
    #print(bpr.name, 'T_int: ', tsd['T_int'][t])
      
    return tsd



def update_timestep_data_no_conditioned_area(tsd):
    """
    Update time step data with zeros for buildings without conditioned area

    Author: Gabriel Happle
    Date: 01/2017

    :param tsd: time series data dict
    :return: update tsd
    """

    zero_fields = ['Qhs_lat_sys',
                   'Qhs_sen_sys',
                   'Qcs_lat_sys',
                   'Qcs_sen_sys',
                   'Qhs_sen',
                   'Qcs_sen',
                   'x_int',
                   'Qhs_em_ls',
                   'Qcs_em_ls',
                   'Qhpro_sys',
                   'Qcpro_sys',
                   'ma_sup_hs',
                   'ma_sup_cs',
                   'Ta_sup_hs',
                   'Ta_re_hs',
                   'Ta_sup_cs',
                   'Ta_re_cs',
                   'NG_hs',
                   'COAL_hs',
                   'OIL_hs',
                   'WOOD_hs',
                   'NG_ww',
                   'COAL_ww',
                   'OIL_ww',
                   'WOOD_ww',
                   'vfw_m3perh',
                   'DH_hs',
                   'Qhs_sys', 'Qhs',
                   'DH_ww',
                   'Qww_sys',
                   'Qww',
                   'DC_cs',
                   'DC_cs_lat',
                   'Qcs_sys',
                   'Qcs',
                   'DC_cdata',
                   'Qcdata_sys',
                   'Qcdata',
                   'DC_cre',
                   'Qcre_sys',
                   'Qcre',
                   'Eaux',
                   'Ehs_lat_aux',
                   'Eaux_hs',
                   'Eaux_cs',
                   'Eaux_ve',
                   'Eaux_ww',
                   'Eaux_fw',
                   'E_sys',
                   'GRID',
                   'E_ww',
                   'E_hs',
                   'E_cs',
                   'E_cre',
                   'E_cdata',
                   'E_pro',
                   'Epro',
                   'Edata',
                   'Ea',
                   'El',
                   'Eal',
                   'Ev',
                   'Eve',
                   'mcphs_sys',
                   'mcpcs_sys',
                   'mcptw'
                   'mcpww_sys',
                   'mcpcdata_sys',
                   'mcpcre_sys',
                   'Tcdata_sys_re', 'Tcdata_sys_sup',
                   'Tcre_sys_re', 'Tcre_sys_sup',
                   'Tww_sys_sup', 'Tww_sys_re',
                   'Ths_sys_sup', 'Ths_sys_re',
                   'Tcs_sys_sup', 'Tcs_sys_re',
                   'DH_ww', 'Qww_sys', 'Qww',
                   'mcptw', 'I_sol', 'I_rad',
                   'Qgain_light', 'Qgain_app', 'Qgain_pers', 'Qgain_data', 'Qgain_wall', 'Qgain_base', 'Qgain_roof',
                   'Qgain_wind', 'Qgain_vent'
                                 'Q_cool_ref', 'q_cs_lat_peop']

    tsd.update(dict((x, np.zeros(HOURS_IN_YEAR)) for x in zero_fields))

    tsd['T_int'] = tsd['T_ext'].copy()

    return tsd


#NOT USED MUST BE CHANGED
def get_hours(bpr):
    """


    :param bpr: BuildingPropertiesRow
    :type bpr:
    :return:
    """

    if bpr.hvac['has-heating-season']:
        # if has heating season start simulating at [before] start of heating season
        ###function convert_date_to_hour if 15 min must be changed
        hour_start_simulation = control_heating_cooling_systems.convert_date_to_hour(bpr.hvac['heat_starts'])
    elif not bpr.hvac['has-heating-season'] and bpr.hvac['has-cooling-season']:
        # if has no heating season but cooling season start at [before] start of cooling season
        ###function convert_date_to_hour if 15 min must be changed
        hour_start_simulation = control_heating_cooling_systems.convert_date_to_hour(bpr.hvac['cool_starts'])
    elif not bpr.hvac['has-heating-season'] and not bpr.hvac['has-cooling-season']:
        # no heating or cooling
        hour_start_simulation = 0

    # TODO: HOURS_PRE_CONDITIONING could be part of config in the future
    #hours_simulation_total = HOURS_IN_YEAR + HOURS_PRE_CONDITIONING #ORIGINAL
    #hour_start_simulation = hour_start_simulation - HOURS_PRE_CONDITIONING #ORIGINAL
    hours_simulation_total = HOURS_IN_YEAR #not original avoid preconditioning


    #t = hour_start_simulation #ORIGINAL
    #for i in range(hours_simulation_total): #ORIGINAL
    #   yield (t + i) % HOURS_IN_YEAR #ORIGINAL
    #need to return
    return (hour_start_simulation + t) % HOURS_IN_YEAR



