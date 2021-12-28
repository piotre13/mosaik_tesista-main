# -*- coding: utf-8 -*-
"""
Electrical loads
"""




import numpy as np
import pandas as pd

from cea.constants import *
from cea.constants import HOURS_IN_YEAR, P_WATER_KGPERM3, SECONDS_PER_HOUR
import buildings.demand.control_heating_cooling_systems as control_heating_cooling_systems
import buildings.demand.constants as constants
from cea.utilities import physics

__author__ = "Jimeno A. Fonseca, Gabriel Happle"
__copyright__ = "Copyright 2016, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Jimeno A. Fonseca"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"

# import constants
H_F = constants.H_F
P_WATER = P_WATER_KGPERM3
P_FAN = constants.P_FAN
F_SR = constants.F_SR
DELTA_P_1 = constants.DELTA_P_1
EFFI = constants.EFFI
HOURS_OP = constants.HOURS_OP
GR = constants.GR


def calc_Eal_Epro(tsd, schedules):
    """
    Calculate final internal electrical loads (without auxiliary loads)

    :param tsd: Timestep data
    :type tsd: Dict[str, numpy.ndarray]

    :param bpr: building properties
    :type bpr: cea.demand.thermal_loads.BuildingPropertiesRow

    :param schedules: The list of schedules defined for the project - in the same order as `list_uses`
    :type schedules: List[numpy.ndarray]

    :returns: `tsd` with new keys: `['Eaf', 'Elf', 'Ealf']`
    :rtype: Dict[str, numpy.ndarray]
    """

    # calculate final electrical consumption due to appliances and lights in W
    tsd['Ea'] = schedules['Ea_W']
    tsd['El'] = schedules['El_W']
    tsd['Ev'] = schedules['Ev_W']
    tsd['Eal'] = schedules['El_W'] + schedules['Ea_W']
    tsd['Epro'] = schedules['Epro_W']

    return tsd

#DONE
def calc_E_sys(tsd, t):
    """
    Calculate the compound of end use electrical loads

    """
    tsd['E_sys'][t] =  tsd['Eve'][t] + tsd['Ea'][t] + tsd['El'][t] + tsd['Edata'][t] + tsd['Epro'][t] + tsd['Eaux'][t] + tsd['Ev'][t]  # assuming a small loss

    return tsd

#DONE
def calc_Ef(bpr, tsd, t):
    """
    Calculate the compound of final electricity loads
    with contain the end-use demand,

    """
    # GET SYSTEMS EFFICIENCIES
    energy_source = bpr.supply['source_el']
    scale_technology = bpr.supply['scale_el']
    total_el_demand = (tsd['Eve'][t] + tsd['Ea'][t] + tsd['El'][t] + tsd['Edata'][t] + tsd['Epro'][t] + tsd['Eaux'][t] +
                       tsd['Ev'][t] + tsd['E_ww'][t] + tsd['E_cs'][t] + tsd['E_hs'][t] + tsd['E_cdata'][t] + tsd['E_cre'][t])

    if scale_technology == "CITY":
        if energy_source == "GRID":
            tsd['GRID'][t] = total_el_demand
            tsd['GRID_a'][t] = tsd['Ea'][t]
            tsd['GRID_l'][t] = tsd['El'][t]
            tsd['GRID_v'][t] = tsd['Ev'][t]
            tsd['GRID_ve'][t] = tsd['Eve'][t]
            tsd['GRID_data'][t] = tsd['Edata'][t]
            tsd['GRID_pro'][t] = tsd['Epro'][t]
            tsd['GRID_aux'][t] = tsd['Eaux'][t]
            tsd['GRID_ww'][t] = tsd['E_ww'][t]
            tsd['GRID_cs'][t] = tsd['E_cs'][t]
            tsd['GRID_hs'][t] = tsd['E_hs'][t]
            tsd['GRID_cdata'][t] = tsd['E_cdata'][t]
            tsd['GRID_cre'][t] = tsd['E_cre'][t]
        else:
            raise Exception('check potential error in input database of LCA infrastructure / ELECTRICITY')
    elif scale_technology == "NONE":
        tsd['GRID'][t] = 0.
        tsd['GRID_a'][t] = 0.
        tsd['GRID_l'][t] = 0.
        tsd['GRID_v'][t] = 0.
        tsd['GRID_ve'][t] = 0.
        tsd['GRID_data'][t] = 0.
        tsd['GRID_pro'][t] = 0.
        tsd['GRID_aux'][t] = 0.
        tsd['GRID_ww'][t] = 0.
        tsd['GRID_cs'][t] = 0.
        tsd['GRID_hs'][t] = 0.
        tsd['GRID_cdata'][t] = 0.
        tsd['GRID_cre'][t] = 0.
    else:
        raise Exception('check potential error in input database of LCA infrastructure / ELECTRICITY')

    return tsd

#DONE
def calc_Eaux(tsd, t):
    """
    Calculate the compound of final electricity loads
    with contain the end-use demand,

    """
    tsd['Eaux'][t] = tsd['Eaux_fw'][t] + tsd['Eaux_ww'][t] + tsd['Eaux_cs'][t] + tsd['Eaux_hs'][t] + tsd['Ehs_lat_aux'][t]

    return tsd


def calc_Eaux_fw(tsd, bpr, schedules):

    tsd['vfw_m3perh'] = schedules['Vw_lph'] / 1000  # m3/h

    nf_ag = bpr.geometry['floors_ag']
    if nf_ag > 5:  # up to 5th floor no pumping needs
        # pressure losses
        effective_height = (bpr.geometry['height_ag'] - (5 * H_F))  # solo apartir de 5 pisos
        deltaP_kPa = DELTA_P_1 * effective_height
        b = 1  # assuming a good pumping system
        tsd['Eaux_fw'] = np.vectorize(calc_Eauxf_fw)(tsd['vfw_m3perh'], deltaP_kPa, b)
    else:
        tsd['Eaux_fw'] = np.zeros(HOURS_IN_YEAR)
    return tsd


def calc_Eaux_ww(tsd, bpr):
    Ll = bpr.geometry['Blength']
    Lw = bpr.geometry['Bwidth']
    Mww = tsd['mww_kgs']
    Qww = tsd['Qww']
    Year = bpr.age['YEAR']
    nf_ag = bpr.geometry['floors_ag']
    fforma = bpr.building_systems['fforma']

    # pressure losses
    deltaP_fittings_gen_kPa = 16  # equation F.4 -standard values
    l_w_dis_col = 2 * (max(Ll, Lw) + 2.5 + nf_ag * H_F) * fforma  # equation F.5
    deltaP_kPa = DELTA_P_1 * l_w_dis_col + deltaP_fittings_gen_kPa
    if Year >= 2000:
        b = 1
    else:
        b = 2

    tsd['Eaux_ww'] = np.vectorize(calc_Eauxf_ww)(Qww, deltaP_kPa, b, Mww)

    return tsd

#DONE
def calc_Eaux_Qhs_Qcs(tsd, bpr,t):
    """
    Auxiliary electric loads
    from Legacy
    Following EN 15316-3-2:2007 Annex F

    :param tsd: Time series data of building
    :type tsd: dict
    :param bpr: Building Properties Row object
    :type bpr: cea.demand.thermal_loads.BuildingPropertiesRow
    :return:
    """
    # TODO: documentation

    Ll = bpr.geometry['Blength']
    Lw = bpr.geometry['Bwidth']
    fforma = bpr.building_systems['fforma']
    Qcs_sys = tsd['Qcs_sys'][t]
    Qcs_sys_ref = tsd['Qcs_sys']

    Qhs_sys = tsd['Qhs_sys'][t]
    Qhs_sys_ref = tsd['Qhs_sys']
    
    Tcs_re_ahu = tsd['Tcs_sys_re_ahu'][t]
    Tcs_sup_ahu = tsd['Tcs_sys_sup_ahu'][t]
    Tcs_re_aru = tsd['Tcs_sys_re_aru'][t]
    Tcs_sup_aru = tsd['Tcs_sys_sup_aru'][t]
    Tcs_re_scu = tsd['Tcs_sys_re_scu'][t]
    Tcs_sup_scu = tsd['Tcs_sys_sup_scu'][t]
    Ths_re_ahu = tsd['Ths_sys_re_ahu'][t]
    Ths_sup_ahu = tsd['Ths_sys_sup_ahu'][t]
    Ths_re_aru = tsd['Ths_sys_re_aru'][t]
    Ths_sup_aru = tsd['Ths_sys_sup_aru'][t]
    Ths_re_shu = tsd['Ths_sys_re_shu'][t]
    Ths_sup_shu = tsd['Ths_sys_sup_shu'][t]

    Year = bpr.age['YEAR']
    nf_ag = bpr.geometry['floors_ag']

    # split up the final demands according to the fraction of energy
    #TODO
    if tsd['Qhs_sen_sys'][t]>0:
        frac_heat_ahu = tsd['Qhs_sen_ahu'][t] / tsd['Qhs_sen_sys'][t]
    else:
        frac_heat_ahu = 0

    Qhs_sys_ahu = Qhs_sys * frac_heat_ahu
    Qhs_sys_ahu_ref = Qhs_sys_ref * frac_heat_ahu
    
    #ORIGINAL MUST FIND A WAY
    #REMEMBER THAT NAN VALUES COULD OCCUR
    Qhs_sys_0_ahu = np.nanmax(Qhs_sys_ahu_ref) # BOHHHHHHH????
    

    if tsd['Qhs_sen_sys'][t]>0:
        frac_heat_aru = tsd['Qhs_sen_aru'][t] / tsd['Qhs_sen_sys'][t]
    else:
        frac_heat_aru = 0
    Qhs_sys_aru = Qhs_sys * frac_heat_aru
    
    #ORIGINAL MUST FIND A WAY
    #REMEMBER THAT NAN VALUES COULD OCCUR
    #Qhs_sys_0_aru = np.nanmax(Qhs_sys_aru) # BOHHHHHHH????
    if pd.isnull(Qhs_sys_aru):
        Qhs_sys_0_aru=0
    else:
        Qhs_sys_0_aru = Qhs_sys_aru

    if tsd['Qhs_sen_sys'][t]>0:
        frac_heat_shu = tsd['Qhs_sen_shu'][t] / tsd['Qhs_sen_sys'][t]
    else:
        frac_heat_shu = 0
    Qhs_sys_shu = Qhs_sys * frac_heat_shu
    
    #ORIGINAL MUST FIND A WAY
    #REMEMBER THAT NAN VALUES COULD OCCUR
    #Qhs_sys_0_shu = np.nanmax(Qhs_sys_shu) # BOHHHHHHH????
    if pd.isnull(Qhs_sys_shu):
        Qhs_sys_0_shu=0
    else:
        Qhs_sys_0_shu = Qhs_sys_shu

    if tsd['Qhs_sen_sys'][t]<0:
        frac_cool_ahu = tsd['Qcs_sen_ahu'][t] / tsd['Qcs_sen_sys'][t]
    else:
        frac_cool_ahu = 0
    Qcs_sys_ahu = Qcs_sys * frac_cool_ahu
    
    #ORIGINAL MUST FIND A WAY
    #REMEMBER THAT NAN VALUES COULD OCCUR
    #Qcs_sys_0_ahu = np.nanmin(Qcs_sys_ahu) # BOHHHHHHH????
    if pd.isnull(Qcs_sys_ahu):
        Qcs_sys_0_ahu=0
    else:
        Qcs_sys_0_ahu = Qcs_sys_ahu

    if tsd['Qhs_sen_sys'][t]<0:
        frac_cool_aru = tsd['Qcs_sen_aru'][t] / tsd['Qcs_sen_sys'][t]
    else:
        frac_cool_aru = 0
    Qcs_sys_aru = Qcs_sys * frac_cool_aru
    
    #ORIGINAL MUST FIND A WAY
    #REMEMBER THAT NAN VALUES COULD OCCUR
    #Qcs_sys_0_aru = np.nanmin(Qcs_sys_aru) # BOHHHHHHH????
    if pd.isnull(Qcs_sys_aru):
        Qcs_sys_0_aru=0
    else:
        Qcs_sys_0_aru = Qcs_sys_aru

    if tsd['Qhs_sen_sys'][t]<0:
        frac_cool_scu = tsd['Qcs_sen_scu'][t] / tsd['Qcs_sen_sys'][t]
    else:
        frac_cool_scu = 0
    Qcs_sys_scu = Qcs_sys * frac_cool_scu
    
    #ORIGINAL MUST FIND A WAY
    #REMEMBER THAT NAN VALUES COULD OCCUR
    #Qcs_sys_0_scu = np.nanmin(Qcs_sys_scu) # BOHHHHHHH????
    if pd.isnull(Qcs_sys_scu):
        Qcs_sys_0_scu=0
    else:
        Qcs_sys_0_scu=Qcs_sys_scu

    # pressure losses
    deltaP_fittings_gen_kPa = 16  # equation F.4 -standard values
    l_w_dis_col = 2 * (max(Ll, Lw) + 2.5 + nf_ag * H_F) * fforma  # equation F.5
    deltaP_kPa = DELTA_P_1 * l_w_dis_col + deltaP_fittings_gen_kPa

    if Year >= 2000:
        b = 1
    else:
        b = 2

    if control_heating_cooling_systems.has_heating_system(bpr.hvac["class_hs"]):

        # for all subsystems
        Eaux_hs_ahu = calc_Eauxf_hs_dis(Qhs_sys_ahu, Qhs_sys_0_ahu, deltaP_kPa, b, Ths_sup_ahu,
                                                      Ths_re_ahu)
        Eaux_hs_aru = calc_Eauxf_hs_dis(Qhs_sys_aru, Qhs_sys_0_aru, deltaP_kPa, b, Ths_sup_aru,
                                                      Ths_re_aru)
        Eaux_hs_shu = calc_Eauxf_hs_dis(Qhs_sys_shu, Qhs_sys_0_shu, deltaP_kPa, b, Ths_sup_shu,
                                                      Ths_re_shu)
        tsd['Eaux_hs'][t] = Eaux_hs_ahu + Eaux_hs_aru + Eaux_hs_shu  # sum up
    else:
        tsd['Eaux_hs'][t] = 0.

    if control_heating_cooling_systems.has_cooling_system(bpr.hvac["class_cs"]):

        # for all subsystems
        Eaux_cs_ahu = calc_Eauxf_cs_dis(Qcs_sys_ahu, Qcs_sys_0_ahu, deltaP_kPa, b, Tcs_sup_ahu,
                                                      Tcs_re_ahu)
        Eaux_cs_aru = calc_Eauxf_cs_dis(Qcs_sys_aru, Qcs_sys_0_aru, deltaP_kPa, b, Tcs_sup_aru,
                                                      Tcs_re_aru)
        Eaux_cs_scu = calc_Eauxf_cs_dis(Qcs_sys_scu, Qcs_sys_0_scu, deltaP_kPa, b, Tcs_sup_scu,
                                                      Tcs_re_scu)
        tsd['Eaux_cs'][t] = Eaux_cs_ahu + Eaux_cs_aru + Eaux_cs_scu  # sum up
    else:
        tsd['Eaux_cs'][t] = 0.

    return tsd
#DONE
def calc_Eauxf_hs_dis(Qhs_sys, Qhs_sys0, deltaP_kPa, b, ts, tr):
    # Following EN 15316-3-2:2007 Annex F

    # the power of the pump in Watts
    Cpump = 0.97
    if Qhs_sys > 0 and (ts - tr) != 0.0:
        m_kgs = (Qhs_sys / ((ts - tr) * HEAT_CAPACITY_OF_WATER_JPERKGK))
        Phydr_kW = deltaP_kPa * (m_kgs / P_WATER_KGPERM3)
        feff = (1.5 * b) / (0.015 * (Phydr_kW) ** 0.74 + 0.4)
        epmp_eff = feff * Cpump * 1 ** -0.94
        Eaux_hs = epmp_eff * Phydr_kW * 1000
    else:
        Eaux_hs = 0.0
    return Eaux_hs  # in #W

#DONE
def calc_Eauxf_cs_dis(Qcs_sys, Qcs_sys0, deltaP_kPa, b, ts, tr):
    # Following EN 15316-3-2:2007 Annex F

    # refrigerant R-22 1200 kg/m3
    # for Cooling system
    # the power of the pump in Watts
    Cpump = 0.97
    if Qcs_sys < 0 and (ts - tr) != 0:
        m_kgs = (Qcs_sys / ((ts - tr) * HEAT_CAPACITY_OF_WATER_JPERKGK))
        Phydr_kW = deltaP_kPa * (m_kgs / P_WATER_KGPERM3)
        feff = (1.5 * b) / (0.015 * (Phydr_kW) ** 0.74 + 0.4)
        epmp_eff = feff * Cpump * 1 ** -0.94
        Eaux_cs = epmp_eff * Phydr_kW * 1000
    else:
        Eaux_cs = 0.0
    return Eaux_cs  # in #W

#DONE
def calc_Eve(tsd,t):
    """
    calculation of electricity consumption of mechanical ventilation and AC fans
    
    :param tsd: Time series data of building
    :type tsd: dict
    :return: electrical energy for fans of mechanical ventilation in [Wh/h]
    :rtype: float
    """

    # TODO: DOCUMENTATION
    # FIXME: Why only energy demand for AC? Also other mechanical ventilation should have auxiliary energy demand
    # FIXME: What are the units

    # m_ve_mech is
    fan_power = P_FAN  # specific fan consumption in W/m3/h, #REMEMBER THIS MUST BE CHANGED TO WORK WITH 15

    # mechanical ventilation system air flow [m3/s] = outdoor air + recirculation air
    q_ve_mech = tsd['m_ve_mech'][t] / physics.calc_rho_air(tsd['theta_ve_mech'][t]) \
                + tsd['m_ve_rec'][t] / physics.calc_rho_air(tsd['T_int'][t])

    Eve = fan_power * q_ve_mech * SECONDS_PER_HOUR

    if pd.isnull(Eve):
        tsd['Eve'][t] =  0
    else:
        tsd['Eve'][t] = Eve

    return tsd

def calc_Eauxf_ww(Qww, deltaP_kPa, b, m_kgs):
    """
    #Following EN 15316-3-2:2007 Annex F
    :param Qww:
    :param Qwwf:
    :param Qwwf0:
    :param Imax:
    :param deltaP_kPa:
    :param b:
    :param m_kgs:
    :return:
    """
    # TODO: documentation

    # the power of the pump in Watts
    Cpump = 0.97
    if Qww > 0.0 and m_kgs != 0.0:
        Phydr_kW = deltaP_kPa * (m_kgs / P_WATER_KGPERM3)
        feff = (1.5 * b) / (0.015 * (Phydr_kW) ** 0.74 + 0.4)
        epmp_eff = feff * Cpump * 1 ** -0.94
        Eaux_ww = epmp_eff * Phydr_kW * 1000
    else:
        Eaux_ww = 0.0
    return Eaux_ww  # in #W


def calc_Eauxf_fw(Vfw_m3h, deltaP_kPa, b):
    """
    #Following EN 15316-3-2:2007 Annex F
    :param Vfw_m3h:
    :param nf:
    :return:
    """
    # TODO: documentation
    # the power of the pump in Watts
    Cpump = 0.97
    if Vfw_m3h > 0.0:
        Phydr_kW = deltaP_kPa * Vfw_m3h * 1 / 3600
        feff = (1.5 * b) / (0.015 * (Phydr_kW) ** 0.74 + 0.4)
        epmp_eff = feff * Cpump * 1 ** -0.94
        Eaux_fw = epmp_eff * Phydr_kW * 1000
    else:
        Eaux_fw = 0.0
    return Eaux_fw
