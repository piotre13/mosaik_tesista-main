import mosaik_api
from .GridModule import make_eid
from .GridModule import pandapower

meta = { #todo add storage and controllable generators
    #todo sgen should not have min and max
    'type': 'event-based',
    'models': {
        'Grid': {
            'public': True,
            'params': [
                'gridfile',  # Name of the file containing the grid topology.
                'sheetnames',  # Mapping of Excel sheet names, optional.
                'threshold'
            ],
            'attrs': ['P_rt','proceed', 'results'],
        },
        'Ext_grid': {
            'public': False,
            'params': [],
            'attrs': [
                'p_mw',  # load Active power [MW]
                'q_mvar',  # Reactive power [MVAr]
            ],

        },
        'Bus': {
            'public': False,
            'params': [],
            'attrs': [
                'p_mw',  # load Active power [MW]
                'q_mvar',  # Reactive power [MVAr]
                'vn_kv',  # Nominal bus voltage [KV]
                'vm_pu',  # Voltage magnitude [p.u]
                'va_degree',# Voltage angle [deg]
                'load',
                'storage',
                'sgen',
            ],
        },
        'Load': {
            'public': False,
            'params': [],
            'attrs': [
                'p_mw',  # load Active power [MW]
                'q_mvar',  # Reactive power [MVAr]
                'min_p_mw',
                'max_p_mw',
                'min_q_mvar',
                'max_q_mvar',
                'in_service',  # specifies if the load is in service.
                'controllable',  # States if load is controllable or not.
                'cost'
            ],
        },
        'Sgen': {
            'public': False,
            'params': [],
            'attrs': [
                'p_mw',  # load Active power [MW]
                'q_mvar',  # Reactive power [MVAr]
                'min_p_mw',
                'max_p_mw',
                'min_q_mvar',
                'max_q_mvar',
                'in_service',  # specifies if the load is in service.
                'controllable',  # States if load is controllable or not.
                'cost',
                'va_degree',  # Voltage angle [deg]
            ],
        },
        'Transformer': {
            'public': False,
            'params': [],
            'attrs': [
                'p_hv_mw',  # Active power at "from" side [MW]
                'q_hv_mvar',  # Reactive power at "from" side [MVAr]
                'p_lv_mw',  # Active power at "to" side [MW]
                'q_lv_mvar',  # Reactive power at "to" side [MVAr]
                'sn_mva',  # Rated apparent power [MVA]
                'max_loading_percent',  # Maximum Loading
                'vn_hv_kv',  # Nominal primary voltage [kV]
                'vn_lv_kv',  # Nominal secondary voltage [kV]
                'pl_mw',  # Active power loss [MW]
                'ql_mvar',  # reactive power consumption of the transformer [Mvar]
                # 'pfe_kw',       #  iron losses in kW [kW]
                # 'i0_percent',       #  iron losses in kW [kW]
                'loading_percent',  # load utilization relative to rated power [%
                'i_hv_ka',  # current at the high voltage side of the transformer [kA]
                'i_lv_ka',  # current at the low voltage side of the transformer [kA]
                'tap_max',  # maximum possible  tap turns
                'tap_min',  # minimum possible tap turns
                'tap_pos',  # Currently active tap turn
            ],
        },
        'Line': {
            'public': False,
            'params': [],
            'attrs': [
                'p_from_mw',  # Active power at "from" side [MW]
                'q_from_mvar',  # Reactive power at "from" side [MVAr]
                'p_to_mw',  # Active power at "to" side [MW]
                'q_to_mvar',  # Reactive power at "to" side [MVAr]
                'max_i_ka',  # Maximum current [KA]
                'length_km',  # Line length [km]
                'pl_mw',  # active power losses of the line [MW]
                'ql_mvar',  # reactive power consumption of the line [MVar]
                'i_from_ka',  # Current at from bus [kA]
                'i_to_ka',  # Current at to bus [kA]
                'loading_percent',  # line loading [%]
                'r_ohm_per_km',  # Resistance per unit length [Ω/km]
                'x_ohm_per_km',  # Reactance per unit length [Ω/km]
                'c_nf_per_km',  # Capactity per unit length [nF/km]
                'in_service',  # Boolean flag (True|False)
            ],
        },
    },
}

class GridApi(mosaik_api.Simulator):

    def __init__(self):

        super(GridApi, self).__init__(meta)
        # self.eid_prefix = 'Grid_' >>>>>>> use this when dealing with multiple model instantiation
        # self.eid = 'Grid'
        self.simulator = pandapower()  # instance of the model imported from GridSim.py
        self._entities = {}  # Maps EIDs to model instances/entities in case we want more grid entities DO NOT need now
        self._relations = []  # List of pair-wise related entities (IDs)
        self._dso_relations = [] # List of reltions that communicate with the whole grid thus with the dso (e.g. aggregators, market)
        self._ppcs = []  # The pandapower cases

    def init(self, sid, step_size, pos_loads=True):
        '''
		The initialization function only called once at the beginning used for initializing some info
		the info we want to initialize are the step size and the mode
		NB the mode serve solo per switchare tra time series and pf da togliere time series non si sa che è...
		'''
        # TODO when the grid and the scenario is instantiated must create all the pandapower loads
        # TODO: check if we need to change signs or we leave it
        self.proceed = False
        self.sameTime = True
        self.OPF_res = None
        self.step_size = step_size

        return self.meta

    def create(self, num, modelname, gridfile, sheetnames=None):
        #TODO for now is only possible to charge multiple grid with same topologyfile
        if modelname != 'Grid':
            raise ValueError('Unknown model: "%s"' % modelname)
        if not sheetnames:
            sheetnames = {}
        #the loop allow to create more grid with all their children (components)
        grids = []
        for i in range(num):
            grid_idx = len(self._ppcs)
            ppc, entities = self.simulator.load_case(gridfile, grid_idx) #loading the grid networks
            self._ppcs.append(ppc)

            children = []
            for eid, attrs in sorted(entities.items()):
                assert eid not in self._entities
                self._entities[eid] = attrs

                # We'll only add relations from line to nodes (and not from
                # nodes to lines) because this is sufficient for mosaik to
                # build the entity graph.
                relations = []
                if attrs['etype'] in ['Transformer', 'Line', 'Load', 'Sgen']:
                    relations = attrs['related']

                children.append({
                    'eid': eid,
                    'type': attrs['etype'],
                    'rel': relations,
                })

            grids.append({
                'eid': make_eid('grid', grid_idx),
                'type': 'Grid',
                'rel': [],
                'children': children,
            })
        print('====================')
        print('created grid entities')
        print('====================')

        return grids

    def step(self, time, inputs, max_advance):
        ''' this is the step function of the grid entity. receives data from the building/aggregators realted to
        bus related storage loads and sgens.
        it computes the calculations (PF,OPF)
        and trigger the same time loop with DSO for threshold checking
        the last thing it does is tor report opf results to dso which will trigger (async_request) the buildings new step

        '''

        self.time = time
        self.proceed = False

        #************* SAVING RELATIONS only once ******************
        if time == 0: # getting the related entities at the first time step
            rel = yield self.mosaik.get_related_entities() #when no entities as param return the whole entity relationships
            #saving relations among entities of the grid as a list tuples of connections
            for r in rel['edges']:
                relation = (r[0],r[1])
                self._relations.append(relation)
                if r[0].endswith('grid') or r[1].endswith('grid'):
                    self._dso_relations.append(relation)
        # ************************************************************
        # >>> STEP1 retrieving information from external simulators
        if self.sameTime: #separate information for the grid sub-component
            print('============TS START==============\n')
            print('Generating dummy data for the loads at time %s' % time)
            print('Grid start cycle at time %s \n'%self.time)
            self.simulator.reset_costs()
            for eid, attrs in inputs.items():
                if 'grid' not in eid :
                    idx = self._entities[eid]['idx'] # indice pp
                    etype = self._entities[eid]['etype'] #type of pp component
                    static = self._entities[eid]['static']

                    self.simulator.set_inputs(etype, idx, attrs, static) # static will be only used for transformers
            self.simulator.set_grid_price(2) # will be a values passed by the inputs from market the grid cost
         # >>> STEP2 performing PF in case to extract primary substation power value
            try:
                #TODO the try block is only for testing the simulation flow must be avoided
                self.simulator.powerflow()
            except:
                pass
            #scatta get_data per consegnare P_rt al DSO
            #self.P_rt = self.simulator.net.res_ext_grid.values[0][0]

            return

        else:
            #TODO CHECK THE GENERALISABILITY OF THIS
            self.proceed = list(inputs['0-grid']['proceed'].values())[0]
            if self.proceed:
                try:                 #TODO the try block is only for testing the simulation flow must be avoided

                    self.simulator.optimalpowerflow()
                except:
                    pass
                self.OPF_res = self.simulator.net.res_ext_grid['p_mw'][0] # maybe the whole configuration per bus nd loads
            else:  # if opf is not run use res of pf
                self.OPF_res = self.P_rt

            return

    def get_data(self, outputs):
        data = {}
        if self.sameTime: # se siamo al primo scambio passiamo P_rt
            for eid, attrs in outputs.items():
                data[eid] = {}
                for attr in attrs:
                    if attr not in ['P_rt', 'results']:
                        raise ValueError('Unknown output attribute "%s"' % attr)
                    if attr == 'P_rt':
                        data[eid][attr] = self.simulator.net.res_ext_grid.values[0][0]
                    else:
                        data[eid][attr] = None
            self.sameTime = False
            #if not working try to add 'time'
            return data

        else:
            for eid, attrs in outputs.items():
                data[eid] = {}
                for attr in attrs:
                    if attr not in ['P_rt', 'results']: #this check could be substitute with meta or cancelled
                        raise ValueError('Unknown output attribute "%s"' % attr)
                    if attr == 'results': #TODO should return the complete results in order to create messages for aggregators then
                        data[eid][attr] = self.simulator.opf_results()
            #data['time'] = self.time + self.step_size
            self.sameTime = True

            return data



def main():
    mosaik_api.start_simulation(GridApi(), 'The mosaik-Pandapower adapter')


if __name__ == '__main__':
    main()
