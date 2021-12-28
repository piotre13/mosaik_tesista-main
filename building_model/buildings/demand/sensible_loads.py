# -*- coding: utf-8 -*-
"""
Sensible space heating and space cooling loads
EN-13970
"""



import numpy as np
import pandas as pd
import buildings.demand.control_heating_cooling_systems as control_heating_cooling_systems
import buildings.demand.constants as constants
from cea.constants import HOURS_IN_YEAR, BOLTZMANN, KELVIN_OFFSET

__author__ = "Jimeno A. Fonseca"
__copyright__ = "Copyright 2016, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Jimeno A. Fonseca", "Shanshan Hsieh", "Daren Thomas", "Martin Mosteiro", "Gabriel Happle"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"

B_F = constants.B_F
D = constants.D
C_A = constants.C_A
RSE = constants.RSE


# capacity of emission/control system
HOURS_IN_YEAR=3000

def calc_Qhs_Qcs_sys_max(Af, prop_HVAC):
    # TODO: Documentation
    # Refactored from CalcThermalLoads

    IC_max = -prop_HVAC['Qcsmax_Wm2'] * Af
    IH_max = prop_HVAC['Qhsmax_Wm2'] * Af
    return IC_max, IH_max


# solar and heat gains

#DONE
def calc_Qgain_sen(t, tsd, bpr):
    # TODO
    # internal loads
    tsd['I_sol_and_I_rad'][t], tsd['I_rad'][t], tsd['I_sol'][t] = calc_I_sol(t, bpr, tsd)
    
    return tsd

#DONE
def calc_I_sol(t, bpr, tsd):
    """
    This function calculates the net solar radiation (incident - reflected - re-irradiated) according to ISO 13790
    see Eq. (23) in 11.3.1

    :param t: hour of the year
    :param bpr: building properties object
    :param tsd: time series dataframe
    :return:
        I_sol_net: vector of net solar radiation to the building
        I_rad: vector solar radiation re-irradiated to the sky.
        I_sol_gross : vector of incident radiation to the building.
    """

    # calc irradiation to the sky
    I_rad = calc_I_rad(t, tsd, bpr)  # according to section 11.3.2 in ISO 13790 I_rad is a positive term

    # get incident radiation
    I_sol_gross = bpr.solar.I_sol[t]

    I_sol_net = I_sol_gross - I_rad  # Eq. (43) in 11.3.1, I_rad gets subtracted here

    return I_sol_net, I_rad, I_sol_gross  # vector in W

#DONE
def calc_I_rad(t, tsd, bpr):
    """
    This function calculates the solar radiation re-irradiated from a building to the sky according to ISO 13790
    See Eq. (46) in 11.3.5

    :param t: hour of the year
    :param tsd: time series dataframe
    :param bpr:  building properties object
    :return:
        I_rad: vector solar radiation re-irradiated to the sky.
    """

    temp_s_prev = tsd['theta_c'][t - 1]
    if np.isnan(tsd['theta_c'][t - 1]):
        temp_s_prev = tsd['T_ext'][t - 1]

    # theta_ss is the is the arithmetic average of the surface temperature and the sky temperature, in °C.
    theta_ss = 0.5 * (tsd['T_sky'][t] + temp_s_prev)  # [see 11.4.6 in ISO 13790]

    # delta_theta_er is the average difference between outdoor air temperature and sky temperature
    delta_theta_er = tsd['T_ext'][t] - tsd['T_sky'][t]  # [see 11.3.5 in ISO 13790]

    Fform_wall, Fform_win, Fform_roof = 0.5, 0.5, 1  # 50% re-irradiated by vertical surfaces and 100% by horizontal
    I_rad_win = RSE * bpr.rc_model['U_win'] * calc_hr(bpr.architecture.e_win, theta_ss) * bpr.rc_model[
        'Awin_ag'] * delta_theta_er
    I_rad_roof = RSE * bpr.rc_model['U_roof'] * calc_hr(bpr.architecture.e_roof, theta_ss) * bpr.rc_model[
        'Aroof'] * delta_theta_er
    I_rad_wall = RSE * bpr.rc_model['U_wall'] * calc_hr(bpr.architecture.e_wall, theta_ss) * bpr.rc_model[
        'Awall_ag'] * delta_theta_er
    I_rad = Fform_wall * I_rad_wall + Fform_win * I_rad_win + Fform_roof * I_rad_roof

    return I_rad

#DONE
def calc_hr(emissivity, theta_ss):
    """
    This function calculates the external radiative heat transfer coefficient according to ISO 13790
    see Eq. (51) in section 11.4.6

    :param emissivity: emissivity of the considered surface
    :param theta_ss: delta of temperature between building surface and the sky.
    :return:
        hr:

    """
    return 4.0 * emissivity * BOLTZMANN * (theta_ss + KELVIN_OFFSET) ** 3.0


#ONLY INITIALIZING REFERENCES
def calc_Qhs_sys_Qcs_sys_ref(tsd_ref):
    # Calc requirements of generation systems (both cooling and heating do not have a storage):
    tsd_ref['Qhs'] = tsd_ref['Qhs_sen_sys']
    tsd_ref['Qhs_sys'] = tsd_ref['Qhs'] + tsd_ref['Qhs_em_ls'] + tsd_ref['Qhs_dis_ls']  # no latent is considered because it is already added a

    # electricity from the adiabatic system. --> TODO
    tsd_ref['Qcs'] = tsd_ref['Qcs_sen_sys'] + tsd_ref['Qcs_lat_sys']
    tsd_ref['Qcs_sys'] = tsd_ref['Qcs'] + tsd_ref['Qcs_em_ls'] + tsd_ref['Qcs_dis_ls']

    # split  Qhs_sys into different heating units (disaggregation of losses)
    frac_ahu = [ahu / sys if sys > 0 else 0 for ahu, sys in zip(tsd_ref['Qhs_sen_ahu'], tsd_ref['Qhs_sen_sys'])]
    tsd_ref['Qhs_sys_ahu'] = tsd_ref['Qhs_sen_ahu'] + (tsd_ref['Qhs_em_ls'] + tsd_ref['Qhs_dis_ls']) * frac_ahu

    frac_aru = [aru / sys if sys > 0 else 0 for aru, sys in zip(tsd_ref['Qhs_sen_aru'], tsd_ref['Qhs_sen_sys'])]
    tsd_ref['Qhs_sys_aru'] = tsd_ref['Qhs_sen_aru'] + (tsd_ref['Qhs_em_ls'] + tsd_ref['Qhs_dis_ls']) * frac_aru

    frac_shu = [shu / sys if sys > 0 else 0 for shu, sys in zip(tsd_ref['Qhs_sen_shu'], tsd_ref['Qhs_sen_sys'])]
    tsd_ref['Qhs_sys_shu'] = tsd_ref['Qhs_sen_shu'] + (tsd_ref['Qhs_em_ls'] + tsd_ref['Qhs_dis_ls']) * frac_shu

    # split Qcs_sys into different cooling units (disaggregation of losses)
    frac_ahu = [ahu / sys if sys < 0 else 0 for ahu, sys in zip(tsd_ref['Qcs_sen_ahu'], tsd_ref['Qcs_sen_sys'])]
    tsd_ref['Qcs_sys_ahu'] = tsd_ref['Qcs_sen_ahu'] + tsd_ref['Qcs_lat_ahu'] + (tsd_ref['Qcs_em_ls'] + tsd_ref['Qcs_dis_ls']) * frac_ahu

    frac_aru = [aru / sys if sys < 0 else 0 for aru, sys in zip(tsd_ref['Qcs_sen_aru'], tsd_ref['Qcs_sen_sys'])]
    tsd_ref['Qcs_sys_aru'] = tsd_ref['Qcs_sen_aru'] + tsd_ref['Qcs_lat_aru'] + (tsd_ref['Qcs_em_ls'] + tsd_ref['Qcs_dis_ls']) * frac_aru

    frac_scu = [scu / sys if sys < 0 else 0 for scu, sys in zip(tsd_ref['Qcs_sen_scu'], tsd_ref['Qcs_sen_sys'])]
    tsd_ref['Qcs_sys_scu'] = tsd_ref['Qcs_sen_scu'] + (tsd_ref['Qcs_em_ls'] + tsd_ref['Qcs_dis_ls']) * frac_scu

    return tsd_ref


#DONE
def calc_Qhs_sys_Qcs_sys(tsd,t):


    # Calc requirements of generation systems (both cooling and heating do not have a storage):
    tsd['Qhs'][t] = tsd['Qhs_sen_sys'][t]
    tsd['Qhs_sys'][t] = tsd['Qhs'][t] + tsd['Qhs_em_ls'][t] + tsd['Qhs_dis_ls'][t]  # no latent is considered because it is already added a

    # electricity from the adiabatic system. --> TODO
    tsd['Qcs'][t] = tsd['Qcs_sen_sys'][t] + tsd['Qcs_lat_sys'][t]
    tsd['Qcs_sys'][t] = tsd['Qcs'][t] + tsd['Qcs_em_ls'][t] + tsd['Qcs_dis_ls'][t]

    #HEATING****************
    # split  Qhs_sys into different heating units (disaggregation of losses)
    if tsd['Qhs_sen_sys'][t] > 0:
        frac_ahu = tsd['Qhs_sen_ahu'][t] / tsd['Qhs_sen_sys'][t]
    else:
        frac_ahu = 0
    tsd['Qhs_sys_ahu'][t] = tsd['Qhs_sen_ahu'][t] + (tsd['Qhs_em_ls'][t] + tsd['Qhs_dis_ls'][t]) * frac_ahu

    if tsd['Qhs_sen_sys'][t] > 0:
        frac_aru = tsd['Qhs_sen_aru'][t] / tsd['Qhs_sen_sys'][t]
    else:
        frac_aru = 0
    tsd['Qhs_sys_aru'][t] = tsd['Qhs_sen_aru'][t] + (tsd['Qhs_em_ls'][t] + tsd['Qhs_dis_ls'][t]) * frac_aru

    if tsd['Qhs_sen_sys'][t] > 0:
        frac_shu = tsd['Qhs_sen_shu'][t] / tsd['Qhs_sen_sys'][t]
    else:
        frac_shu = 0 
    tsd['Qhs_sys_shu'][t] = tsd['Qhs_sen_shu'][t] + (tsd['Qhs_em_ls'][t] + tsd['Qhs_dis_ls'][t]) * frac_shu
    
    #COOLING****************
    # split Qcs_sys into different cooling units (disaggregation of losses)
    if tsd['Qcs_sen_sys'][t] < 0:
        frac_ahu = tsd['Qcs_sen_ahu'][t] / tsd['Qcs_sen_sys'][t]
    else:
        frac_ahu = 0 
    tsd['Qcs_sys_ahu'][t] = tsd['Qcs_sen_ahu'][t] + tsd['Qcs_lat_ahu'][t] + (tsd['Qcs_em_ls'][t] + tsd['Qcs_dis_ls'][t]) * frac_ahu

    if tsd['Qcs_sen_sys'][t] < 0:
        frac_aru = tsd['Qcs_sen_aru'][t] / tsd['Qcs_sen_sys'][t]
    else:
        frac_aru = 0 
    tsd['Qcs_sys_aru'][t] = tsd['Qcs_sen_aru'][t] + tsd['Qcs_lat_aru'][t] + (tsd['Qcs_em_ls'][t] + tsd['Qcs_dis_ls'][t]) * frac_aru

    if tsd['Qcs_sen_sys'][t] < 0:
        frac_scu = tsd['Qcs_sen_scu'][t] / tsd['Qcs_sen_sys'][t]
    else:
        frac_scu = 0
    tsd['Qcs_sys_scu'][t] = tsd['Qcs_sen_scu'][t] + (tsd['Qcs_em_ls'][t] + tsd['Qcs_dis_ls'][t]) * frac_scu

    return tsd


#DONE BUT MUST FIX REFERENCE VALUES
# temperature of emission/control system
def calc_temperatures_emission_systems(bpr, tsd, t,tsd_ref):
    """
    Calculate temperature of emission systems.
    Using radiator function also for cooling ('radiators.calc_radiator')
    Modified from legacy

    Gabriel Happle, Feb. 2018

    :param bpr: Building Properties
    :type bpr: BuildingPropertiesRow
    :param tsd: Time series data of building
    :type tsd: dict
    :return: modifies tsd
    :rtype: None
    """

    from buildings.demand.technologies import radiators, heating_coils, tabs

    #
    # TEMPERATURES HEATING SYSTEMS
    #
    if not control_heating_cooling_systems.has_heating_system(bpr.hvac["class_hs"]):
        # if no heating system

        tsd['Ths_sys_sup_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Ths_sys_re_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcphs_sys_ahu'][t] = 0.
        tsd['Ths_sys_sup_aru'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Ths_sys_re_aru'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcphs_sys_aru'][t] = 0.
        tsd['Ths_sys_sup_shu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Ths_sys_re_shu'][t] = np.nan # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcphs_sys_shu'][t] = 0.

    #RADIATOR**************************************************************************
    elif control_heating_cooling_systems.has_radiator_heating_system(bpr):
        # if radiator heating system
        #TODO
        Ta_heating_0 = np.nanmax(tsd_ref['ta_hs_set'])
        Qhs_sys_0 = np.nanmax(tsd_ref['Qhs_sys'])  # in W  Nominal end-use space heating demand
        #Ta_heating_0 = 20. #testing value
        #Qhs_sys_0 = 3000 #testing values
        tsd['Ths_sys_sup_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Ths_sys_re_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcphs_sys_ahu'][t] = 0
        tsd['Ths_sys_sup_aru'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Ths_sys_re_aru'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcphs_sys_aru'][t] = 0

        Ths_sup, Ths_re, mcphs = radiators.calc_radiator(tsd['Qhs_sys'][t], tsd['T_int'][t], Qhs_sys_0, Ta_heating_0,
                                                                       bpr.building_systems['Ths_sup_shu_0'],
                                                                       bpr.building_systems['Ths_re_shu_0'])

        tsd['Ths_sys_sup_shu'][t] = Ths_sup
        tsd['Ths_sys_re_shu'][t] = Ths_re
        tsd['mcphs_sys_shu'][t] = mcphs
    #***********************************************************************************

    elif control_heating_cooling_systems.has_central_ac_heating_system(bpr):

        # ahu
        # consider losses according to loads of systems
        if tsd['Qhs_sen_sys'][t] > 0:
            frac_ahu = tsd['Qhs_sen_ahu'][t] / tsd['Qhs_sen_sys'][t]
        else:
            frac_ahu = 0.
        qhs_sys_ahu = tsd['Qhs_sen_ahu'][t] + (tsd['Qhs_em_ls'][t] + tsd['Qhs_dis_ls'][t]) * frac_ahu
       
        #Qhs_sys_ahu_0 = qhs_sys_ahu #testing purpose
        #ma_sup_0 = tsd['ma_sup_hs_ahu'][t]#testing purpose
        #Ta_sup_0 = tsd['ta_sup_hs_ahu'][t]#testing purpose
        #Ta_re_0 = tsd['ta_re_hs_ahu'][t]#testing purpose

        qhs_sys_ahu_ref = tsd_ref['Qhs_sen_ahu'] + (tsd_ref['Qhs_em_ls'] + tsd_ref['Qhs_dis_ls']) * frac_ahu
        #Qhs_sys_ahu_0 = np.nanmax(qhs_sys_ahu_ref)  # in W #MUST FIND A REF VALUES 
        index = np.where(qhs_sys_ahu_ref == Qhs_sys_ahu_0)
        ma_sup_0 = tsd_ref['ma_sup_hs_ahu'][index[0][0]]
        Ta_sup_0 = tsd_ref['ta_sup_hs_ahu'][index[0][0]] + KELVIN_OFFSET
        Ta_re_0 = tsd_ref['ta_re_hs_ahu'][index[0][0]] + KELVIN_OFFSET
        
        Ths_sup, Ths_re, mcphs = heating_coils.calc_heating_coil(qhs_sys_ahu, Qhs_sys_ahu_0, tsd['ta_sup_hs_ahu'][t],
                                                                               tsd['ta_re_hs_ahu'][t],
                                                                               bpr.building_systems['Ths_sup_ahu_0'],
                                                                               bpr.building_systems['Ths_re_ahu_0'],
                                                                               tsd['ma_sup_hs_ahu'][t], ma_sup_0,
                                                                               Ta_sup_0, Ta_re_0)
        tsd['Ths_sys_sup_ahu'][t] = Ths_sup  # in C
        tsd['Ths_sys_re_ahu'][t] = Ths_re  # in C
        tsd['mcphs_sys_ahu'][t] = mcphs

        # ARU
        # consider losses according to loads of systems
        if tsd['Qhs_sen_sys'][t] > 0:
            frac_aru = tsd['Qhs_sen_aru'][t] / tsd['Qhs_sen_sys'][t]
        else:
            frac_aru = 0
        
        qhs_sys_aru = tsd['Qhs_sen_aru'][t] + (tsd['Qhs_em_ls'][t] + tsd['Qhs_dis_ls'][t]) * frac_aru
        qhs_sys_aru_ref = tsd_ref['Qhs_sen_aru'] + (tsd_ref['Qhs_em_ls'] + tsd_ref['Qhs_dis_ls']) * frac_aru


        # Qhs_sys_aru_0 = qhs_sys_aru # for testing purpose
        # ma_sup_0 = tsd['ma_sup_hs_aru'][t] # for testing purpose
        # Ta_sup_0 = tsd['ta_sup_hs_aru'][t] # for testing purpose
        # Ta_re_0 = tsd['ta_re_hs_aru'][t] # for testing purpose
       
        Qhs_sys_aru_0 = np.nanmax(qhs_sys_aru_ref)  # in W
        index = np.where(qhs_sys_aru_ref == Qhs_sys_aru_0)
        ma_sup_0 = tsd_ref['ma_sup_hs_aru'][index[0][0]]
        Ta_sup_0 = tsd_ref['ta_sup_hs_aru'][index[0][0]] + KELVIN_OFFSET
        Ta_re_0 = tsd_ref['ta_re_hs_aru'][index[0][0]] + KELVIN_OFFSET
       
        Ths_sup, Ths_re, mcphs = heating_coils.calc_heating_coil(qhs_sys_aru, Qhs_sys_aru_0,
                                                                               tsd['ta_sup_hs_aru'][t],
                                                                               tsd['ta_re_hs_aru'][t],
                                                                               bpr.building_systems['Ths_sup_aru_0'],
                                                                               bpr.building_systems['Ths_re_aru_0'],
                                                                               tsd['ma_sup_hs_aru'][t], ma_sup_0,
                                                                               Ta_sup_0, Ta_re_0)
        tsd['Ths_sys_sup_aru'][t] = Ths_sup  # in C
        tsd['Ths_sys_re_aru'][t] = Ths_re  # in C
        tsd['mcphs_sys_aru'][t] = mcphs

        # SHU
        tsd['Ths_sup_shu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Ths_sys_re_shu'][t] =  np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcphs_sys_shu'][t] = 0.

    elif control_heating_cooling_systems.has_floor_heating_system(bpr):
        
       
        Ta_heating_0 = np.nanmax(tsd_ref['ta_hs_set'])
        Qhs_sys_0 = np.nanmax(tsd_ref['Qhs_sys'])  # in W
   
        #Ta_heating_0 = tsd['ta_hs_set'][t]#for testing purpose
        #Qhs_sys_0 = tsd['Qhs_sys'][t]#for testing puprose

        tsd['Ths_sys_sup_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Ths_sys_re_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcphs_sys_ahu'][t] = 0.
        tsd['Ths_sys_sup_aru'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Ths_sys_re_aru'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcphs_sys_aru'][t] = 0.

        Ths_sup, Ths_re, mcphs = radiators.calc_radiator(tsd['Qhs_sys'][t], tsd['T_int'][t], Qhs_sys_0, Ta_heating_0,
                                                                       bpr.building_systems['Ths_sup_shu_0'][t],
                                                                       bpr.building_systems['Ths_re_shu_0'][t])
        tsd['Ths_sys_sup_shu'][t] = Ths_sup
        tsd['Ths_sys_re_shu'][t] = Ths_re
        tsd['mcphs_sys_shu'][t] = mcphs

    else:
        raise Exception('Heating system not defined in function: "calc_temperatures_emission_systems"')


    #
    # TEMPERATURES COOLING SYSTEMS
    #
    if not control_heating_cooling_systems.has_cooling_system(bpr.hvac["class_cs"]):
        # if no cooling system

        tsd['Tcs_sys_sup_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Tcs_sys_re_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcpcs_sys_ahu'][t] = 0.
        tsd['Tcs_sys_sup_aru'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Tcs_sys_re_aru'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcpcs_sys_aru'][t] = 0.
        tsd['Tcs_sys_sup_scu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Tcs_sys_re_scu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcpcs_sys_scu'][t] = 0.

    elif control_heating_cooling_systems.has_central_ac_cooling_system(bpr):

        # AHU
        # consider losses according to loads of systems
        if tsd['Qcs_sen_sys'][t] < 0:
            frac_ahu = tsd['Qcs_sen_ahu'][t] / tsd['Qcs_sen_sys'][t]
        else:
            frac_ahu = 0
        qcs_sys_ahu = tsd['Qcs_sen_ahu'][t] + tsd['Qcs_lat_ahu'][t] + (tsd['Qcs_em_ls'][t] + tsd['Qcs_dis_ls'][t]) * frac_ahu
        qcs_sys_ahu_ref = tsd_ref['Qcs_sen_ahu'][t] + tsd_ref['Qcs_lat_ahu'][t] + (tsd_ref['Qcs_em_ls'][t] + tsd_ref['Qcs_dis_ls'][t]) * frac_ahu

      
        Qcs_sys_ahu_0 = np.nanmin(qcs_sys_ahu_ref)  # in W
        index = np.where(qcs_sys_ahu_ref == Qcs_sys_ahu_0)
        ma_sup_0 = tsd_ref['ma_sup_cs_ahu'][index[0][0]]
        Ta_sup_0 = tsd_ref['ta_sup_cs_ahu'][index[0][0]] + KELVIN_OFFSET
        Ta_re_0 = tsd_ref['ta_re_cs_ahu'][index[0][0]] + KELVIN_OFFSET
      
        # Qcs_sys_ahu_0 = qcs_sys_ahu # testing purpose
        # ma_sup_0 = tsd['ma_sup_cs_ahu'][t] # testing purpose
        # Ta_sup_0 = tsd['ta_sup_cs_ahu'][t] # testing purpose
        # Ta_re_0 = tsd['ta_re_cs_ahu'][t] # testing purpose

        Tcs_sup, Tcs_re, mcpcs = heating_coils.calc_cooling_coil(qcs_sys_ahu, Qcs_sys_ahu_0, tsd['ta_sup_cs_ahu'][t],
                                                                               tsd['ta_re_cs_ahu'][t],
                                                                               bpr.building_systems['Tcs_sup_ahu_0'],
                                                                               bpr.building_systems['Tcs_re_ahu_0'],
                                                                               tsd['ma_sup_cs_ahu'][t], ma_sup_0,
                                                                               Ta_sup_0, Ta_re_0)
        tsd['Tcs_sys_sup_ahu'][t] = Tcs_sup  # in C
        tsd['Tcs_sys_re_ahu'][t] = Tcs_re  # in C
        tsd['mcpcs_sys_ahu'][t] = mcpcs

        # ARU
        # consider losses according to loads of systems
        if tsd['Qcs_sen_sys'][t] < 0:
            frac_aru = tsd['Qcs_sen_aru'][t] / tsd['Qcs_sen_sys'][t]
        else:
            frac_aru = 0
        qcs_sys_aru = tsd['Qcs_sen_aru'][t] + tsd['Qcs_lat_aru'][t] + (tsd['Qcs_em_ls'][t] + tsd['Qcs_dis_ls'][t]) * frac_aru
        qcs_sys_aru_ref = tsd_ref['Qcs_sen_aru'] + tsd_ref['Qcs_lat_aru'] + (tsd_ref['Qcs_em_ls'] + tsd_ref['Qcs_dis_ls']) * frac_aru
        
        if pd.isnull(qcs_sys_aru):
            qcs_sys_aru = 0
        
        Qcs_sys_aru_0 = np.nanmin(qcs_sys_aru_ref)  # in W
        index = np.where(qcs_sys_aru_ref == Qcs_sys_aru_0)
        ma_sup_0 = tsd_ref['ma_sup_cs_aru'][index[0][0]]
        Ta_sup_0 = tsd_ref['ta_sup_cs_aru'][index[0][0]] + KELVIN_OFFSET
        Ta_re_0 = tsd_ref['ta_re_cs_aru'][index[0][0]] + KELVIN_OFFSET
        
        # Qcs_sys_aru_0 = qcs_sys_aru #testing purpose
        # ma_sup_0 = tsd['ma_sup_cs_aru'][t] #testing purpose
        # Ta_sup_0 = tsd['ta_sup_cs_aru'][t] #testing purpose
        # Ta_re_0 = tsd['ta_re_cs_aru'][t] #testing purpose

        Tcs_sup, Tcs_re, mcpcs = heating_coils.calc_cooling_coil(qcs_sys_aru, Qcs_sys_aru_0, tsd['ta_sup_cs_aru'][t],
                                                                               tsd['ta_re_cs_aru'][t],
                                                                               bpr.building_systems['Tcs_sup_aru_0'],
                                                                               bpr.building_systems['Tcs_re_aru_0'],
                                                                               tsd['ma_sup_cs_aru'][t], ma_sup_0,
                                                                               Ta_sup_0, Ta_re_0)
        tsd['Tcs_sys_sup_aru'][t] = Tcs_sup  # in C
        tsd['Tcs_sys_re_aru'][t] = Tcs_re  # in C
        tsd['mcpcs_sys_aru'][t] = mcpcs

        # SCU
        tsd['Tcs_sys_sup_scu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Tcs_sys_re_scu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcpcs_sys_scu'][t] = 0.

    elif control_heating_cooling_systems.has_local_ac_cooling_system(bpr):

        # AHU
        tsd['Tcs_sys_sup_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Tcs_sys_re_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcpcs_sys_ahu'][t] = 0.

        # ARU
        # consider losses according to loads of systems
        qcs_sys_aru = tsd['Qcs_sen_aru'][t] + tsd['Qcs_lat_aru'][t] + (tsd['Qcs_em_ls'][t] + tsd['Qcs_dis_ls'][t])
        qcs_sys_aru_ref = tsd_ref['Qcs_sen_aru'] + tsd_ref['Qcs_lat_aru'] + (tsd_ref['Qcs_em_ls'] + tsd_ref['Qcs_dis_ls'])
        
        if pd.isnull(qcs_sys_aru):
            qcs_sys_aru = 0
   
        
       
        qcs_sys_aru_ref = np.nan_to_num(qcs_sys_aru_ref) #ORIGINAL fill the nan values
        # Calc nominal temperatures of systems
        Qcs_sys_aru_0 = np.nanmin(qcs_sys_aru_ref)  # in W
        index = np.where(qcs_sys_aru_ref == Qcs_sys_aru_0)
        ma_sup_0 = tsd_ref['ma_sup_cs_aru'][index[0][0]]
        Ta_sup_0 = tsd_ref['ta_sup_cs_aru'][index[0][0]] + KELVIN_OFFSET
        Ta_re_0 = tsd_ref['ta_re_cs_aru'][index[0][0]] + KELVIN_OFFSET
        

        Tcs_sup, Tcs_re, mcpcs = heating_coils.calc_cooling_coil(qcs_sys_aru, Qcs_sys_aru_0,
                                                                               tsd['ta_sup_cs_aru'][t],
                                                                               tsd['ta_re_cs_aru'][t],
                                                                               bpr.building_systems['Tcs_sup_aru_0'],
                                                                               bpr.building_systems['Tcs_re_aru_0'],
                                                                               tsd['ma_sup_cs_aru'], ma_sup_0,
                                                                               Ta_sup_0, Ta_re_0)
        tsd['Tcs_sys_sup_aru'][t] = Tcs_sup  # in C
        tsd['Tcs_sys_re_aru'][t] = Tcs_re  # in C
        tsd['mcpcs_sys_aru'][t] = mcpcs

        # SCU
        tsd['Tcs_sys_sup_scu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Tcs_sys_re_scu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcpcs_sys_scu'][t] = 0.

    elif control_heating_cooling_systems.has_3for2_cooling_system(bpr):

        # AHU
        # consider losses according to loads of systems
        if tsd['Qcs_sen_sys'][t] < 0:
            frac_ahu = tsd['Qcs_sen_ahu'][t] / tsd['Qcs_sen_sys'][t]
        else:
            frac_ahu = 0
        qcs_sys_ahu = tsd['Qcs_sen_ahu'][t] + tsd['Qcs_lat_ahu'][t] + (tsd['Qcs_em_ls'][t] + tsd['Qcs_dis_ls'][t]) * frac_ahu
        qcs_sys_ahu_ref = tsd_ref['Qcs_sen_ahu'] + tsd_ref['Qcs_lat_ahu'] + (tsd_ref['Qcs_em_ls'] + tsd_ref['Qcs_dis_ls']) * frac_ahu
        
        if pd.isnull(qcs_sys_ahu):
            qcs_sys_ahu = 0

        
        
        qcs_sys_ahu_ref = np.nan_to_num(qcs_sys_ahu_ref)
        Qcs_sys_ahu_0 = np.nanmin(qcs_sys_ahu_ref)  # in W
        index = np.where(qcs_sys_ahu_ref == Qcs_sys_ahu_0)
        ma_sup_0 = tsd_ref['ma_sup_cs_ahu'][index[0][0]]
        Ta_sup_0 = tsd_ref['ta_sup_cs_ahu'][index[0][0]] + KELVIN_OFFSET
        Ta_re_0 = tsd_ref['ta_re_cs_ahu'][index[0][0]] + KELVIN_OFFSET
        
        # Qcs_sys_ahu_0 = qcs_sys_ahu #testing purpose
        # ma_sup_0 = tsd['ma_sup_cs_ahu'][t] #testing purpose
        # Ta_sup_0 = tsd['ta_sup_cs_ahu'][t] #testing purpose
        # Ta_re_0 = tsd['ta_re_cs_ahu'][t] #testing purpose

        Tcs_sup, Tcs_re, mcpcs = heating_coils.calc_cooling_coil(qcs_sys_ahu, Qcs_sys_ahu_0,
                                                                               tsd['ta_sup_cs_ahu'][t],
                                                                               tsd['ta_re_cs_ahu'][t],
                                                                               bpr.building_systems['Tcs_sup_ahu_0'],
                                                                               bpr.building_systems['Tcs_re_ahu_0'],
                                                                               tsd['ma_sup_cs_ahu'][t], ma_sup_0,
                                                                               Ta_sup_0, Ta_re_0)
        tsd['Tcs_sys_sup_ahu'][t] = Tcs_sup  # in C
        tsd['Tcs_sys_re_ahu'][t] = Tcs_re  # in C
        tsd['mcpcs_sys_ahu'][t] = mcpcs


        # ARU
        # consider losses according to loads of systems
        if tsd['Qcs_sen_sys'][t] < 0:
            frac_aru = tsd['Qcs_sen_aru'][t] / tsd['Qcs_sen_sys'][t]
        else:
            frac_aru = 0

        qcs_sys_aru = tsd['Qcs_sen_aru'][t] + tsd['Qcs_lat_aru'][t] + (tsd['Qcs_em_ls'][t] + tsd['Qcs_dis_ls'][t]) * frac_aru
        qcs_sys_aru_ref = tsd_ref['Qcs_sen_aru'] + tsd_ref['Qcs_lat_aru'] + (tsd_ref['Qcs_em_ls'] + tsd_ref['Qcs_dis_ls']) * frac_aru
        
        if pd.isnull(qcs_sys_aru):
            qcs_sys_aru = 0

      
        qcs_sys_aru_ref = np.nan_to_num(qcs_sys_aru_ref)
        # Calc nominal temperatures of systems
        Qcs_sys_aru_0 = np.nanmin(qcs_sys_aru_ref)  # in W
        index = np.where(qcs_sys_aru_ref == Qcs_sys_aru_0)
        ma_sup_0 = tsd_ref['ma_sup_cs_aru'][index[0][0]]
        Ta_sup_0 = tsd_ref['ta_sup_cs_aru'][index[0][0]] + KELVIN_OFFSET
        Ta_re_0 = tsd_ref['ta_re_cs_aru'][index[0][0]] + KELVIN_OFFSET
       
        # Qcs_sys_aru_0 = qcs_sys_aru# testing purpose
        # ma_sup_0 = tsd['ma_sup_cs_aru'][t]# testing purpose
        # Ta_sup_0 = tsd['ta_sup_cs_aru'][t] # testing purpose
        # Ta_re_0 = tsd['ta_re_cs_aru'][t]# testing purpose

        Tcs_sup, Tcs_re, mcpcs = heating_coils.calc_cooling_coil(qcs_sys_aru, Qcs_sys_aru_0,
                                                                               tsd['ta_sup_cs_aru'][t],
                                                                               tsd['ta_re_cs_aru'][t],
                                                                               bpr.building_systems['Tcs_sup_aru_0'],
                                                                               bpr.building_systems['Tcs_re_aru_0'],
                                                                               tsd['ma_sup_cs_aru'][t], ma_sup_0,
                                                                               Ta_sup_0, Ta_re_0)
        tsd['Tcs_sys_sup_aru'][t] = Tcs_sup  # in C
        tsd['Tcs_sys_re_aru'][t] = Tcs_re  # in C
        tsd['mcpcs_sys_aru'][t] = mcpcs

        # SCU
        # consider losses according to loads of systems
        if tsd['Qcs_sen_sys'][t] < 0:
            frac_scu =  tsd['Qcs_sen_scu'][t] / tsd['Qcs_sen_sys'][t]
        else:
            frac_scu = 0


        qcs_sys_scu = tsd['Qcs_sen_scu'][t] + (tsd['Qcs_em_ls'][t] + tsd['Qcs_dis_ls'][t]) * frac_scu
        qcs_sys_scu_ref = tsd_ref['Qcs_sen_scu'] + (tsd_ref['Qcs_em_ls'] + tsd_ref['Qcs_dis_ls']) * frac_scu
        if pd.isnull(qcs_sys_scu):
            qcs_sys_scu = 0

      
        qcs_sys_scu_ref = np.nan_to_num(qcs_sys_scu_ref)
        Qcs_sys_scu_0 = np.nanmin(qcs_sys_scu_ref)  # in W
        Ta_cooling_0 = np.nanmin(tsd_ref['ta_cs_set'])
       
        # Qcs_sys_scu_0 = qcs_sys_scu
        # Ta_cooling_0 = tsd['ta_cs_set'][t]

        Tcs_sup, Tcs_re, mcpcs = radiators.calc_radiator(qcs_sys_scu, tsd['T_int'][t], Qcs_sys_scu_0, Ta_cooling_0,
                                                                       bpr.building_systems['Tcs_sup_scu_0'],
                                                                       bpr.building_systems['Tcs_re_scu_0'])
        tsd['Tcs_sys_sup_scu'][t] = Tcs_sup  # in C
        tsd['Tcs_sys_re_scu'][t] = Tcs_re  # in C
        tsd['mcpcs_sys_scu'][t] = mcpcs

    #**************############****TODO*****#########************************

    elif control_heating_cooling_systems.has_ceiling_cooling_system(bpr) or \
            control_heating_cooling_systems.has_floor_cooling_system(bpr):

        # SCU
        # consider losses according to loads of systems
        qcs_sys_scu = tsd['Qcs_sen_scu'][t] + (tsd['Qcs_em_ls'][t] + tsd['Qcs_dis_ls'][t])
        qcs_sys_scu_ref = tsd_ref['Qcs_sen_scu'] + (tsd_ref['Qcs_em_ls'] + tsd_ref['Qcs_dis_ls'])
        if pd.isnull(qcs_sys_scu):
            qcs_sys_scu = 0
        
        
        qcs_sys_scu_ref = np.nan_to_num(qcs_sys_scu_ref)
        Qcs_sys_scu_0 = np.nanmin(qcs_sys_scu_ref)  # in W
        Ta_cooling_0 = np.nanmin(tsd_ref['ta_cs_set'])
       
        # qcs_sys_scu = qcs_sys_scu#testing purpose
        # Qcs_sys_scu_0 = qcs_sys_scu#testing purpose
        # Ta_cooling_0 = tsd['ta_cs_set'][t]#testing purpose
        # use radiator for ceiling cooling calculation
        Tcs_sup, Tcs_re, mcpcs = radiators.calc_radiator(qcs_sys_scu, tsd['T_int'][t], Qcs_sys_scu_0, Ta_cooling_0,
                                                                       bpr.building_systems['Tcs_sup_scu_0'],
                                                                       bpr.building_systems['Tcs_re_scu_0'])

        tsd['Tcs_sys_sup_scu'][t] = Tcs_sup  # in C
        tsd['Tcs_sys_re_scu'][t] = Tcs_re  # in C
        tsd['mcpcs_sys_scu'][t] = mcpcs

        # AHU
        tsd['Tcs_sys_sup_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Tcs_sys_re_ahu'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcpcs_sys_ahu'][t] = 0.

        # ARU
        tsd['Tcs_sys_sup_aru'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['Tcs_sys_re_aru'][t] = np.nan  # in C  #FIXME: I don't like that non-existing temperatures are 0
        tsd['mcpcs_sys_aru'][t] = 0.

    else:
        raise Exception('Cooling system not defined in function: "calc_temperatures_emission_systems"')

    return tsd

#ONLY INITIALIZING REFERENCES
def calc_Qhs_Qcs_loss_ref (bpr,tsd_ref):
    Y = bpr.building_systems['Y'][0]
    Lv = bpr.building_systems['Lv']

    tsh_ahu = bpr.building_systems['Ths_sup_ahu_0']
    trh_ahu = bpr.building_systems['Ths_re_ahu_0']
    tsh_aru = bpr.building_systems['Ths_sup_aru_0']
    trh_aru = bpr.building_systems['Ths_re_aru_0']
    tsh_shu = bpr.building_systems['Ths_sup_shu_0']
    trh_shu = bpr.building_systems['Ths_re_shu_0']

    tsc_ahu = bpr.building_systems['Tcs_sup_ahu_0']
    trc_ahu = bpr.building_systems['Tcs_re_ahu_0']
    tsc_aru = bpr.building_systems['Tcs_sup_aru_0']
    trc_aru = bpr.building_systems['Tcs_re_aru_0']
    tsc_scu = bpr.building_systems['Tcs_sup_scu_0']
    trc_scu = bpr.building_systems['Tcs_re_scu_0']

    tair = tsd_ref['T_int']
    text = tsd_ref['T_ext']

    print(len(tair),'tair')
    print(len(text),'text')
    # Calculate tamb in basement according to EN
    tamb = tair - B_F * (tair - text)

    if np.any(tsd_ref['Qhs_sen_ahu'] > 0):
        frac_ahu = [ahu / sys if sys > 0 else 0 for ahu, sys in zip(tsd_ref['Qhs_sen_ahu'], tsd_ref['Qhs_sen_sys'])]
        qhs_sen_ahu_incl_em_ls = tsd_ref['Qhs_sen_ahu'] + tsd_ref['Qhs_em_ls'] * frac_ahu
        qhs_sen_ahu_incl_em_ls = np.nan_to_num(qhs_sen_ahu_incl_em_ls)
        Qhs_d_ls_ahu = ((tsh_ahu + trh_ahu) / 2 - tamb) * (
        qhs_sen_ahu_incl_em_ls / np.nanmax(qhs_sen_ahu_incl_em_ls)) * (Lv * Y)

    else:
        Qhs_d_ls_ahu = np.zeros(HOURS_IN_YEAR)

    if np.any(tsd_ref['Qhs_sen_aru'] > 0):
        frac_aru = [aru / sys if sys > 0 else 0 for aru, sys in zip(tsd_ref['Qhs_sen_aru'], tsd_ref['Qhs_sen_sys'])]
        qhs_sen_aru_incl_em_ls = tsd_ref['Qhs_sen_aru'] + tsd_ref['Qhs_em_ls'] * frac_aru
        qhs_sen_aru_incl_em_ls = np.nan_to_num(qhs_sen_aru_incl_em_ls)
        Qhs_d_ls_aru = ((tsh_aru + trh_aru) / 2 - tamb) * (
        qhs_sen_aru_incl_em_ls / np.nanmax(qhs_sen_aru_incl_em_ls)) * (
                           Lv * Y)
    else:
        Qhs_d_ls_aru = np.zeros(HOURS_IN_YEAR)

    if np.any(tsd_ref['Qhs_sen_shu'] > 0):
        frac_shu = [shu / sys if sys > 0 else 0 for shu, sys in zip(tsd_ref['Qhs_sen_shu'], tsd_ref['Qhs_sen_sys'])]
        qhs_sen_shu_incl_em_ls = tsd_ref['Qhs_sen_shu'] + tsd_ref['Qhs_em_ls'] * frac_shu
        qhs_sen_shu_incl_em_ls = np.nan_to_num(qhs_sen_shu_incl_em_ls)
        qhs_d_ls_shu = ((tsh_shu + trh_shu) / 2 - tamb) * (
        qhs_sen_shu_incl_em_ls / np.nanmax(qhs_sen_shu_incl_em_ls)) * (
                           Lv * Y)
    else:
        qhs_d_ls_shu = np.zeros(HOURS_IN_YEAR)

    if np.any(tsd_ref['Qcs_sen_ahu'] < 0):
        frac_ahu = [ahu / sys if sys < 0 else 0 for ahu, sys in zip(tsd_ref['Qcs_sen_ahu'], tsd_ref['Qcs_sen_sys'])]
        qcs_sen_ahu_incl_em_ls = tsd_ref['Qcs_sen_ahu'] + tsd_ref['Qcs_lat_ahu'] + tsd_ref['Qcs_em_ls'] * frac_ahu
        qcs_sen_ahu_incl_em_ls = np.nan_to_num(qcs_sen_ahu_incl_em_ls)
        qcs_d_ls_ahu = ((tsc_ahu + trc_ahu) / 2 - tamb) * (qcs_sen_ahu_incl_em_ls / np.nanmin(qcs_sen_ahu_incl_em_ls))\
                       * (Lv * Y)
    else:
        qcs_d_ls_ahu = np.zeros(HOURS_IN_YEAR)

    if np.any(tsd_ref['Qcs_sen_aru'] < 0):
        frac_aru = [aru / sys if sys < 0 else 0 for aru, sys in zip(tsd_ref['Qcs_sen_aru'], tsd_ref['Qcs_sen_sys'])]
        qcs_sen_aru_incl_em_ls = tsd_ref['Qcs_sen_aru'] + tsd_ref['Qcs_lat_aru'] + tsd_ref['Qcs_em_ls'] * frac_aru
        qcs_sen_aru_incl_em_ls = np.nan_to_num(qcs_sen_aru_incl_em_ls)
        qcs_d_ls_aru = ((tsc_aru + trc_aru) / 2 - tamb) * (qcs_sen_aru_incl_em_ls / np.nanmin(qcs_sen_aru_incl_em_ls))\
                        * (Lv * Y)
    else:
        qcs_d_ls_aru = np.zeros(HOURS_IN_YEAR)

    if np.any(tsd_ref['Qcs_sen_scu'] < 0):
        frac_scu = [scu / sys if sys < 0 else 0 for scu, sys in zip(tsd_ref['Qcs_sen_scu'], tsd_ref['Qcs_sen_sys'])]
        qcs_sen_scu_incl_em_ls = tsd_ref['Qcs_sen_scu'] + tsd_ref['Qcs_em_ls'] * frac_scu
        qcs_sen_scu_incl_em_ls = np.nan_to_num(qcs_sen_scu_incl_em_ls)
        Qcs_d_ls_scu = ((tsc_scu + trc_scu) / 2 - tamb) * (qcs_sen_scu_incl_em_ls / np.nanmin(qcs_sen_scu_incl_em_ls)) * (
        Lv * Y)
    else:
        Qcs_d_ls_scu = np.zeros(HOURS_IN_YEAR)

    tsd_ref['Qhs_dis_ls'] = Qhs_d_ls_ahu + Qhs_d_ls_aru + qhs_d_ls_shu
    tsd_ref['Qcs_dis_ls'] = qcs_d_ls_ahu + qcs_d_ls_aru + Qcs_d_ls_scu

    return tsd_ref




# space heating/cooling losses
#DONE
def calc_Qhs_Qcs_loss(bpr, tsd,t,tsd_ref):
    """
    Calculate distribution losses of emission systems.

    Modified from legacy:
        calculates distribution losses based on ISO 15316

    Gabriel Happle, Feb. 2018

    :param bpr: Building Properties
    :type bpr: BuildingPropertiesRow
    :param tsd: Time series data of building
    :type tsd: dict
    :return: modifies tsd
    :rtype: None
    """

    # look up properties
    Y = bpr.building_systems['Y'][0]
    Lv = bpr.building_systems['Lv']

    tsh_ahu = bpr.building_systems['Ths_sup_ahu_0']
    trh_ahu = bpr.building_systems['Ths_re_ahu_0']
    tsh_aru = bpr.building_systems['Ths_sup_aru_0']
    trh_aru = bpr.building_systems['Ths_re_aru_0']
    tsh_shu = bpr.building_systems['Ths_sup_shu_0']
    trh_shu = bpr.building_systems['Ths_re_shu_0']

    tsc_ahu = bpr.building_systems['Tcs_sup_ahu_0']
    trc_ahu = bpr.building_systems['Tcs_re_ahu_0']
    tsc_aru = bpr.building_systems['Tcs_sup_aru_0']
    trc_aru = bpr.building_systems['Tcs_re_aru_0']
    tsc_scu = bpr.building_systems['Tcs_sup_scu_0']
    trc_scu = bpr.building_systems['Tcs_re_scu_0']

    

    tair = tsd['T_int'][t]
    text = tsd['T_ext'][t]


    # Calculate tamb in basement according to EN
    tamb = tair - B_F * (tair - text)

    if tsd['Qhs_sen_ahu'][t] > 0:
        if tsd['Qhs_sen_sys'][t]>0:
            frac_ahu = tsd['Qhs_sen_ahu'][t]/tsd['Qhs_sen_sys'][t]
        else:
            frac_ahu = 0
        #frac_ahu = [ahu / sys if sys > 0 else 0 for ahu, sys in zip(tsd['Qhs_sen_ahu'], tsd['Qhs_sen_sys'])] ##CANCEL
        qhs_sen_ahu_incl_em_ls = tsd['Qhs_sen_ahu'][t] + tsd['Qhs_em_ls'][t] * frac_ahu
        qhs_sen_ahu_incl_em_ls_ref = tsd_ref['Qhs_sen_ahu'] + tsd_ref['Qhs_em_ls'] * frac_ahu

        if pd.isnull(qhs_sen_ahu_incl_em_ls):
            qhs_sen_ahu_incl_em_ls = 0
        
        Qhs_d_ls_ahu = ((tsh_ahu + trh_ahu) / 2 - tamb) * (
        qhs_sen_ahu_incl_em_ls / np.nanmax(qhs_sen_ahu_incl_em_ls_ref)) * (Lv * Y) #ORIGINAL

    else:
        Qhs_d_ls_ahu = 0

    

    #**********************************************************************
    if tsd['Qhs_sen_aru'][t] > 0:
        if tsd['Qhs_sen_sys'][t]>0:
            frac_aru = tsd['Qhs_sen_aru'][t] / tsd['Qhs_sen_sys'][t]
        else:
            frac_aru = 0
       
        qhs_sen_aru_incl_em_ls = tsd['Qhs_sen_aru'][t] + tsd['Qhs_em_ls'][t] * frac_aru
        qhs_sen_aru_incl_em_ls_ref = tsd_ref['Qhs_sen_aru'] + tsd_ref['Qhs_em_ls'] * frac_aru
        
        if pd.isull(qhs_sen_aru_incl_em_ls):
            qhs_sen_aru_incl_em_ls = 0
            
        Qhs_d_ls_aru = ((tsh_aru + trh_aru) / 2 - tamb) * (
        qhs_sen_aru_incl_em_ls / np.nanmax(qhs_sen_aru_incl_em_ls_ref)) * (
                           Lv * Y)
    else:
        Qhs_d_ls_aru = 0

    #**********************************************************************

    if tsd['Qhs_sen_shu'][t] > 0:
        if tsd['Qhs_sen_sys'][t] > 0:
            frac_shu = tsd['Qhs_sen_shu'][t] / tsd['Qhs_sen_sys'][t]
        else:
            frac_shu = 0
       
        qhs_sen_shu_incl_em_ls = tsd['Qhs_sen_shu'][t] + tsd['Qhs_em_ls'][t] * frac_shu
        qhs_sen_shu_incl_em_ls_ref = tsd_ref['Qhs_sen_shu'] + tsd_ref['Qhs_em_ls'] * frac_shu

        if pd.isnull(qhs_sen_shu_incl_em_ls):
            qhs_sen_shu_incl_em_ls = 0
    
        qhs_d_ls_shu = ((tsh_shu + trh_shu) / 2 - tamb) * (
        qhs_sen_shu_incl_em_ls / np.nanmax(qhs_sen_shu_incl_em_ls_ref)) * (
                           Lv * Y)
    else:
        qhs_d_ls_shu = 0


    #**********************************************************************


    if tsd['Qcs_sen_ahu'][t] < 0:
        if tsd['Qcs_sen_sys'][t] < 0:
            frac_ahu = tsd['Qcs_sen_ahu'][t] / tsd['Qcs_sen_sys'][t]
        else:
            frac_ahu = 0
       
        qcs_sen_ahu_incl_em_ls = tsd['Qcs_sen_ahu'][t] + tsd['Qcs_lat_ahu'][t] + tsd['Qcs_em_ls'][t] * frac_ahu
        qcs_sen_ahu_incl_em_ls_ref = tsd_ref['Qcs_sen_ahu'] + tsd_ref['Qcs_lat_ahu'] + tsd_ref['Qcs_em_ls'] * frac_ahu
        
        if pd.isnull(qcs_sen_ahu_incl_em_ls):
            qcs_sen_ahu_incl_em_ls = 0
       
        qcs_d_ls_ahu = ((tsc_ahu + trc_ahu) / 2 - tamb) * (qcs_sen_ahu_incl_em_ls / np.nanmin(qcs_sen_ahu_incl_em_ls_ref))\
                       * (Lv * Y) #here it uses the min
    else:
        qcs_d_ls_ahu = 0

    #**********************************************************************

    if tsd['Qcs_sen_aru'][t] < 0:
        if tsd['Qcs_sen_sys'][t] < 0:
            frac_aru = tsd['Qcs_sen_aru'][t] / tsd['Qcs_sen_sys'][t]
        else:
            frac_aru = 0

        qcs_sen_aru_incl_em_ls = tsd['Qcs_sen_aru'][t] + tsd['Qcs_lat_aru'][t] + tsd['Qcs_em_ls'][t] * frac_aru
        qcs_sen_aru_incl_em_ls_ref = tsd_ref['Qcs_sen_aru'] + tsd_ref['Qcs_lat_aru'] + tsd_ref['Qcs_em_ls'] * frac_aru

        if pd.isnull(qcs_sen_aru_incl_em_ls) :
            qcs_sen_aru_incl_em_ls = 0
           
        qcs_d_ls_aru = ((tsc_aru + trc_aru) / 2 - tamb) * (qcs_sen_aru_incl_em_ls / np.nanmin(qcs_sen_aru_incl_em_ls_ref))\
                        * (Lv * Y)
    else:
        qcs_d_ls_aru = 0


    #**********************************************************************

    if tsd['Qcs_sen_scu'][t] < 0:
        if tsd['Qcs_sen_sys'][t] < 0:
            frac_scu = tsd['Qcs_sen_scu'][t] / tsd['Qcs_sen_sys'][t]
        else:
            frac_scu = 0
        
        qcs_sen_scu_incl_em_ls = tsd['Qcs_sen_scu'][t] + tsd['Qcs_em_ls'][t] * frac_scu
        qcs_sen_scu_incl_em_ls_ref = tsd_ref['Qcs_sen_scu'] + tsd_ref['Qcs_em_ls'] * frac_scu

        if pd.isnull(qcs_sen_scu_incl_em_ls):
            qcs_sen_scu_incl_em_ls = 0
            
     
        Qcs_d_ls_scu = ((tsc_scu + trc_scu) / 2 - tamb) * (qcs_sen_scu_incl_em_ls / np.nanmin(qcs_sen_scu_incl_em_ls_ref)) * (
        Lv * Y)
    else:
        Qcs_d_ls_scu = 0

    

    tsd['Qhs_dis_ls'][t] = Qhs_d_ls_ahu + Qhs_d_ls_aru + qhs_d_ls_shu
    tsd['Qcs_dis_ls'][t] = qcs_d_ls_ahu + qcs_d_ls_aru + Qcs_d_ls_scu

    return tsd
