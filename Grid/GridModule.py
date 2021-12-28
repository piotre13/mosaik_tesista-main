import pandapower as pp
#import pandapower.network as ppn
import pandas as pd
import json
import math
import os.path
from pandapower.timeseries import DFData
from pandapower.timeseries import OutputWriter
from pandapower.control import ConstControl
from pandapower.timeseries.run_time_series import run_timeseries, run_time_step, init_time_series
import pandapower.networks as ppn

#import simbench as sb
import numpy as np
import math


#CLASS MODEL IN PANDAPOWER FOR GRID ACTIONS AND ANALYSIS

class pandapower(object):
    #TODO add storages
    #todo review Modelling for OPF and review well the creation and assignation of load gen etc...

    def __init__(self):
        self.entity_map={}
        self.Sch_24 = None
        self.name2index = {}



    def load_case(self,path,grid_idx):
        """
        Loads a pandapower network, the network should be ready in a separate json or excel file or as stated above
        TODO: pypower converter and network building with only parameter as input
        """
        #TO DO aggiungere il load da matlab con ,a conversione in pandapower net
        loaders = {
          '.json': 1,
          '.xlsx': 2,
          '': 3
          }
        try:
           ext = os.path.splitext(path)[-1]
           loader = loaders[ext]
        except KeyError:
            raise ValueError("Don't know how to open '%s'" % path)

        if loader == 1:
            self.net = pp.from_json(path)
        elif loader == 2:
            self.net = pp.from_excel(path)
        else:
            if path == 'cigre_hv':
                self.net = ppn.create_cigre_network_hv()
            elif path == 'cigre_mv_all':
                self.net = ppn.create_cigre_network_mv(with_der='all')
            elif path == 'cigre_mv_pv_wind':
                self.net = ppn.create_cigre_network_mv(with_der='pv_wind')
            elif path == 'cigre_lv':
                self.net = ppn.create_cigre_network_lv()
            elif path == 'test_pp':
                self.net =  ppn.simple_four_bus_system()
        self.bus_id = self.net.bus.name.to_dict()

        #create virtual loads and gens on each bus ready to be plugged in WHYYYYY?
        #for i in self.bus_id:
        # if self.net.ext_grid.bus[0] != i:
         #   pp.create_load(self.net, i, p_mw=0, name=('ext_load_%s' % i))
          #  pp.create_sgen(self.net, i, p_mw=0, name=('ext_gen_%s' % i))

        #create elements indices, to create entities
        self.load_id = self.net.load.name.to_dict()
        self.sgen_id = self.net.sgen.name.to_dict()
        self.line_id = self.net.line.name.to_dict()
        self.trafo_id = self.net.trafo.name.to_dict()
        self.switch_id = self.net.switch.name.to_dict()
        #todo add storage

        #load the entity map
        self._get_slack(grid_idx)
        self._get_buses(grid_idx)
        self._get_lines(grid_idx)
        self._get_trafos(grid_idx)
        self._get_loads(grid_idx)
        self._get_sgen(grid_idx)
        # todo add storage + create the _get_storage function

        entity_map = self.entity_map
        ppc = self.net #pandapower case

        return  ppc, entity_map



    def _get_slack(self, grid_idx):
        """Create entity of the slack bus"""

        self.slack_bus_idx = self.net.ext_grid.bus[0]
        bid = self.bus_id[self.slack_bus_idx]
        eid = make_eid(bid, grid_idx)

        self.entity_map[eid] = {
                'etype': 'Ext_grid',
                'idx': self.slack_bus_idx,
                'static': {'vm_pu': self.net.ext_grid['vm_pu'],
                           'va_degree': self.net.ext_grid['va_degree']
                }
        }
        slack = (0, self.slack_bus_idx)

        return slack



    def _get_buses(self,grid_idx):
        """Create entities of the buses"""
        buses = []

        for idx in self.bus_id:
         if self.slack_bus_idx != idx:
            element = self.net.bus.iloc[idx]
            bid = element['name']
            eid = make_eid(bid, grid_idx)
            buses.append((idx, element['vn_kv']))
            #etype = bid
            self.entity_map[eid] = {
                'etype': 'Bus',
                'idx': idx,
                'static': {
                    'vn_kv':  element['vn_kv']
                },
            }
         else:
             pass

        return buses



    def _get_loads(self, grid_idx):
        """Create load entities"""
        loads = []

        for idx in self.load_id:
                element = self.net.load.iloc[idx]
                eid = make_eid(element['name'], grid_idx)
                bid = make_eid(self.bus_id[element['bus']], grid_idx)

                element_data = element.to_dict()
                element_data_static = {key:element_data[key] for key in element_data}
                #keys_to_del = ['name', 'const_z_percent', 'const_i_percent', 'min_q_mvar', 'min_p_mw', 'max_q_mvar'
                #   , 'max_p_mw']
                #element_data_static = {key: element_data[key] for key in element_data if key not in keys_to_del}

                # time series calculation
                # if 'profile' in element_data_static:
                #     if type (element_data_static ['profile']) != float:
                #        profile_name = element_data_static['profile']
                #
                #        datasource = pd.DataFrame()
                #        datasource[profile_name+'_pload'] = self.net.profiles['load'][profile_name+'_pload']*element['p_mw']
                #        datasource[profile_name +'_qload'] = self.net.profiles['load'][profile_name+'_qload']* element['q_mvar']
                #
                #        ds = DFData(datasource)
                #
                #        ConstControl(self.net, element='load', variable='p_mw', element_index=idx,
                #                  data_source=ds, profile_name=profile_name+'_pload')
                #
                #        ConstControl(self.net, element='load', variable='q_mvar', element_index=idx,
                #                  data_source=ds, profile_name=profile_name+'_qload')
                #     else:
                #         pass
                # else:
                #     pass

                self.entity_map[eid] = {'etype': 'Load', 'idx': idx, 'static': element_data_static
                    , 'related': [bid]}

                loads.append((bid, element['p_mw'], element['q_mvar'], element['scaling']
                              , element['in_service']))

        return loads



    def _get_sgen(self, grid_idx):
        """Create static generator entities"""
        sgens = []

        for idx in self.sgen_id:
             element = self.net.sgen.iloc[idx]
             eid = make_eid(element['name'], grid_idx)
             bid = make_eid(self.bus_id[element['bus']], grid_idx)


             element_data = element.to_dict()
             element_data_static = {key: element_data[key] for key in element_data}

             #keys_to_del = ['name', 'min_q_mvar', 'min_p_mw', 'max_q_mvar', 'max_p_mw']
             #element_data_static = {key: element_data[key] for key in element_data if key not in keys_to_del}


             # time series calculation
             # if 'profile' in element_data_static:
             #     if type(element_data_static['profile']) != float:
             #         profile_name = element_data_static['profile']
             #
             #         datasource = pd.DataFrame()
             #         datasource[profile_name ] = self.net.profiles['renewables'][profile_name ] * element['p_mw']
             #
             #         ds = DFData(datasource)
             #
             #         ConstControl(self.net, element='sgen', variable='p_mw', element_index=idx
             #                      , data_source=ds, profile_name=profile_name )
             #     else:
             #       pass
             # else:
             #     pass


             self.entity_map[eid] = {'etype': 'Sgen', 'idx': idx, 'static': element_data_static
                 , 'related': [bid]}


             sgens.append((bid, element['p_mw'], element['q_mvar'], element['scaling']
                           , element['in_service']))

        return sgens



    def _get_lines(self, grid_idx):
        """create branches entities"""
        lines = []

        for idx in self.line_id:
            element = self.net.line.iloc[idx]
            eid = make_eid(element['name'], grid_idx)
            fbus = make_eid(self.bus_id[element['from_bus']], grid_idx)
            tbus = make_eid(self.bus_id[element['to_bus']], grid_idx)


            f_idx = self.entity_map[fbus]['idx']
            t_idx = self.entity_map[tbus]['idx']


            element_data= element.to_dict()
            keys_to_del = ['name', 'from_bus', 'to_bus']
            element_data_static = {key: element_data[key] for key in element_data if key not in keys_to_del }
            #del element_data_static

            self.entity_map[eid] = {'etype': 'Line', 'idx': idx, 'static': element_data_static
                , 'related': [fbus, tbus]}

            lines.append((f_idx, t_idx, element['length_km'], element['r_ohm_per_km'], element['x_ohm_per_km'],
                         element['c_nf_per_km'], element['max_i_ka'], element['in_service']))

        return lines



    def _get_trafos(self, grid_idx):
        """Create tranformer entities"""
        trafos = []

        for idx in self.trafo_id:
            element = self.net.trafo.iloc[idx]
            eid = make_eid(element['name'], grid_idx)
            hv_bus = make_eid(self.bus_id[element['hv_bus']], grid_idx)
            lv_bus = make_eid(self.bus_id[element['lv_bus']], grid_idx)


            hv_idx = self.entity_map[hv_bus]['idx']
            lv_idx = self.entity_map[lv_bus]['idx']

            element_data = element.to_dict()
            keys_to_del = ['name', 'hv_bus', 'lv_bus']
            element_data_static = {key: element_data[key] for key in element_data if key not in keys_to_del}
            # del element_data_static

            self.entity_map[eid] = {'etype': 'Transformer', 'idx': idx, 'static': element_data_static
                , 'related': [hv_bus, lv_bus]}

        trafos.append((hv_idx, lv_idx, element['sn_mva'], element['vn_hv_kv'], element['vn_lv_kv']
                       , element['vk_percent'], element['vkr_percent'], element['pfe_kw'], element['i0_percent']
                       , element['shift_degree'], element['tap_side'], element['tap_pos'], element['tap_neutral']
                       , element['tap_min'], element['tap_max'], element['in_service']))

        return trafos

    def set_grid_price(self, price):

        pp.create_poly_cost(self.net, 0, 'ext_grid',cp1_eur_per_mw=price) # NB the index is 0 cause only one ext_grid is considered


    def set_inputs(self, etype, idx, data, static):
        """setting the input from other simulators: the inputs could be :
            - aggregated : regarding a specific BUS
            - indivdual : regarding a specific grid component"""
        #TODO COMPLETE THE MODELLING WITH ALL POSSIBLE COMPONENTS
        if etype == 'Bus':
            self.set_loads(data['load'], idx)
            self.set_storages(data['storage'],idx)
            self.set_sgens(data['sgen'],idx)

        else: # single components
            #todo in case passing single elements mosaik entities
            pass

    def set_loads(self, load, bus_idx):
        '''used to create or fill data of load element is calle by set_inputs'''
        if list(load.values())[0] : #if no data just skip

            name = list(load.keys())[0]+'_load'

            if name not in self.net.load['name']: #check if already present if not create it
                self.create_element(bus_idx, name ,'load', load[list(load.keys())[0]])


            else: #if load already present only edit info
                idx = pp.get_element_index(self.net,'load',name, exact_match=True) # should be only one load
                for key,value in load[list(load.keys())[0]].items():
                    self.net.load.at[idx,key]=value

        else:
            pass



    def set_storages (self, storage, bus_idx):
        '''used to create or fill data of storage element is calle by set_inputs'''
        x= storage.values()
        if list(storage.values())[0]:  # if no data just skip

            name = list(storage.keys())[0] + '_storage'

            if name not in self.net.storage['name']:  # check if already present if not create it
                self.create_element(bus_idx, name, 'storage', storage[list(storage.keys())[0]])

            else:  # if load already present only edit info
                idx = pp.get_element_index(self.net, 'storage', name, exact_match=True)  # should be only one load
                for key, value in storage[list(storage.keys())[0]].items():
                    self.net.storage.at[idx, key] = value

        else:
            pass

    def set_sgens(self, sgen, bus_idx):
        '''used to create or fill data of sgen element is calle by set_inputs'''
        if list(sgen.values())[0]:  # if no data just skip

            name = list(sgen.keys())[0] + '_sgen'

            if name not in self.net.sgen['name']:  # check if already present if not create it
                self.create_element(bus_idx, name, 'sgen', sgen[list(sgen.keys())[0]])

            else:  # if load already present only edit info
                idx = pp.get_element_index(self.net, 'sgen', name, exact_match=True)  # should be only one load
                for key, value in sgen[list(sgen.keys())[0]].items():
                    self.net.sgen.at[idx, key] = value

        else:
            pass


    def create_element(self, bus, name, type, data):
        '''this function is used when the grid element is not found so its created from scratch with all the data information
        including the cost'''

        #data= data[name]
        if type == 'load':
            id = pp.create_load(self.net, bus, p_mw=data['p_mw'],q_mvar=data['q_mvar'], max_p_mw=data['max_p_mw'],min_p_mw=data['min_p_mw'],
                           max_q_mvar=data['max_q_mvar'],min_q_mvar=data['min_q_mvar'], controllable=data['controllable'], name = name)
            pp.create_poly_cost(self.net, id, 'load', cp1_eur_per_mw=data['cost'])
            self.name2index [name] = id

        elif type == 'sgen':
            id = pp.create_sgen(self.net, bus, p_mw=data['p_mw'],q_mvar=data['q_mvar'], max_p_mw=data['max_p_mw'],min_p_mw=data['min_p_mw'],
                           max_q_mvar=data['max_q_mvar'],min_q_mvar=data['min_q_mvar'], controllable=data['controllable'], name = name)
            pp.create_poly_cost(self.net, id, 'sgen', cp1_eur_per_mw=data['cost'])
            self.name2index[name] = id

        elif type == 'storage':
            #TODO add paramets when using storages
            id = pp.create_storage(self.net, bus, p_mw=data['p_mw'], q_mvar=data['q_mvar'], max_p_mw=data['max_p_mw'],min_p_mw=data['min_p_mw'],
                                max_q_mvar=data['max_q_mvar'], min_q_mvar=data['min_q_mvar'],
                                controllable=data['controllable'], name=name)
            pp.create_poly_cost(self.net, id, 'storage', cp1_eur_per_mw=data['cost'])
            self.name2index[name] = id

        else :
            raise  ValueError('Not known grid element!\n')


    def reset_costs(self):
        self.net.poly_cost = self.net.poly_cost.drop(self.net.poly_cost.index[0:])

    def powerflow(self):
        """Conduct power flow"""
        print('running a power flow')
        pp.runpp(self.net)
        print(' power flow ended')

    def optimalpowerflow(self):
        print('running an Optimal power flow')
        #pp.opf_task(self.net)
        pp.runopp(self.net, verbose = False)
        print( 'Optimal power flow ended')

    def opf_results(self):
        results = {}
        results['res_load'] = self.net.res_load
        results['res_sgen'] = self.net.res_sgen
        results['res_storage'] = self.net.res_storage
        results['res_ext_grid'] = self.net.res_ext_grid
        results['name2index'] = self.name2index
        return results

    def get_cache_entries(self):
        """cache the results of the power flow to be communicated to other simulators"""

        cache = {}
        case = self.net

        for eid, attrs in self.entity_map.items():
            etype = attrs['etype']
            idx = attrs['idx']
            data = {}

            if not case.res_bus.empty:

                if etype == 'Bus':
                    bus = case.res_bus.iloc[idx]
                    data['p_mw'] = bus['p_mw']
                    data['q_mvar'] = bus['q_mvar']
                    data['vm_pu'] = bus['vm_pu']
                    data['va_degree'] = bus['va_degree']

                elif etype == 'Load':
                    load = case.res_load.iloc[idx]
                    data['p_mw'] = load['p_mw']
                    data['q_mvar'] = load['q_mvar']


                elif etype == 'Sgen':
                    sgen = case.res_sgen.iloc[idx]
                    data['p_mw'] = sgen['p_mw']
                    data['q_mvar'] = sgen['q_mvar']


                elif etype == 'Transformer':
                    trafo = case.res_trafo.iloc[idx]
                    data['va_lv_degree'] = trafo['va_lv_degree']
                    data['loading_percent'] = trafo['loading_percent']

                elif etype == 'Line':
                    line = case.res_line.iloc[idx]
                    data['i_ka'] = line['i_ka']
                    data['loading_percent'] = line ['loading_percent']

                else:
                    slack = case.res_ext_grid
                    data['p_mw'] = slack['p_mw']
                    data['q_mvar'] = slack['q_mvar']

            else:
                # Failed to converge.
                if etype in 'Bus':
                    data['p_mw'] = float('nan')
                    data['q_mvar'] = float('nan')
                    data['vm_pu'] = float('nan')
                    data['va_degree'] = float('nan')
                elif etype in 'Line':
                    data['i_ka'] = float('nan')
                    data['p_from_mw'] = float('nan')
                    data['q_from_mvar'] = float('nan')
                    data['p_to_mw'] = float('nan')
                    data['q_to_mvar'] = float('nan')
                elif etype in 'Transformer':
                    data['va_lv_degree'] = float('nan')
                    data['loading_percent'] = float('nan')


            cache[eid] = data
        return cache

def make_eid(name, grid_idx):
    return '%s-%s' % (grid_idx, name)



def create_output_writer(net, time_steps, output_dir):
    """Pandapower output to save results"""
    ow = OutputWriter(net, time_steps, output_path=output_dir, output_file_type=".xls")
    # these variables are saved to the harddisk after / during the time series loop
    ow.log_variable('res_load', 'p_mw')
    ow.log_variable('res_load', 'q_mvar')
    ow.log_variable('res_bus', 'vm_pu')
    ow.log_variable('res_bus', 'q_mvar')
    ow.log_variable('res_bus', 'va_degree')
    ow.log_variable('res_bus', 'p_mw')
    ow.log_variable('res_line', 'loading_percent')
    ow.log_variable('res_line', 'i_ka')
    ow.log_variable('res_trafo', 'va_lv_degree')
    ow.log_variable('res_trafo', 'loading_percent')
    ow.log_variable('res_sgen', 'p_mw')
    ow.log_variable('res_sgen', 'q_mvar')

    return ow




