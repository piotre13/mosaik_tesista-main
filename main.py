#scenario creation imports
#from Scenario.Prj_creation_archetypes import  PrjScenario
#simul imports
import mosaik
from mosaik.util import connect_randomly, connect_many_to_one
from plot import plot_execution_graph, plot_execution_graph_st
#from plot_results import plot_primary
import networkx as nx
import matplotlib.pyplot as plt
import sys
from building_model.initialize import Initialize 
import cea.config
import cea.inputlocator
import pickle
#from pyvis.network import Network

#***SCENARIO CREATION***

def create_scenario(path=None):
    if not path:
        #create a new scenario
        project = PrjScenario()
        project.load_project(path)
        return project
    else:
        pass
        #load a scenario from path











#SIMULATION********
sim_config = {
    'Building':{
            'python':'BuildingMosaik.Building_API:BuildingApi'
        },
    'PV':{
            'python':'PVsim.mosaik_pv_sim:PVSIM'
        },
    'CSV':{
            'python':'meteo.mk_csvsim:CSV'
        },
    'Grid': {
         'python':'Grid.grid_API:GridApi'
    },

    'DSO':{
        'python':'Dso.Dso_API:DsoApi'
    },

    'MAS':{
        'cmd': '%(python)s -m mas.mosaik -l debug %(addr)s',
        'env': {
            'PYTHONPATH': 'src/',
    }
    },


}

sys.path.insert(0, 'src/')

# Add PV data file
END = 5  * 60 * 60  #two days ---> 2 * 24 * 60 * 60
START = '2010-01-01 02:00:00'
GRID_FILE = 'cigre_mv_all' # import directly from pandpaower simbench module
METEO_PATH = 'meteo/meteo_mosaik_1h.csv' 
#GRID_FILE = 'test_pp'
#NB the grid must already have loads/gen/storages and transf created
Threshold_DSO = 0.05



def main():

    #initialize the CEA scenario
    #config = cea.config.Configuration()
    #locator = cea.inputlocator.InputLocator(scenario = config.scenario)
    #scenario_cea = Initialize(config, locator)
    #print(scenario_cea.__dict__)

    #step2 save the scenario as pickle object
    #with open ('building_model/scenario_obj.pickle', 'wb') as f:
    #    pickle.dump(scenario_cea, f, pickle.HIGHEST_PROTOCOL)

    #exit()

    """Compose the mosaik scenario and run the simulation."""
    # Set up the "world" instance.
    world = mosaik.World(sim_config, debug= True)

#SIMULATORS START init()

    dsosim = world.start('DSO', step_size = 60 * 60, TH = Threshold_DSO)

    #mas = world.start('MAS', start_date = START)

    gridsim = world.start('Grid', step_size = 60 * 60)  # mode = 'pf' or 'pf_timeseries'

    pvsim = world.start ('PV', step_size = 60 * 60)

    meteoSim = world.start('CSV', sim_start = START, datafile = METEO_PATH)
    #print(meteoSim.meta)
    #exit()
    #print(meteoSim.meta)
    #exit()
    buildingsim = world.start('Building',step_size = 60 * 60) 
#ENTITIES CREATION create()
    
    #creating mosaik entities
    grid = gridsim.Grid(gridfile=GRID_FILE)  # calls create() could be called for more than one grid
    grid_components = grid.children  # attribute children returns children of the grid entity
    dso = dsosim.Dso()
    csv = meteoSim.meteo()
    pvs = pvsim.PVsimulator.create(10)
    
    buildings = buildingsim.Building.create(10)


    #creating aiomas environment and agents use this or the mosaik version

    #mas = massim.MAS.create(1)
    #aggrs = mas.Aggregator.create(3)
    #builds = mas.Building.create(10)

#CONNECTIONS
#todo must connect weather meteo to buildings

    
   # world.connect(dso,grid,'proceed', weak = True )
   

   #NB if cretaing more buildings of PV than busess find another way to connect
    
    grid_bus = [e for e in grid_components if e.type in 'Bus']
    i = 0
    for building in buildings:
        world.connect(csv,building,'T_ext')
        world.connect(building,grid_bus[i],'load')
        i+=1

    j=0    
    for pv in pvs:
        world.connect(csv,pv,'ghi', 'T_ext') 
        world.connect(pv, grid_bus[j], 'sgen')
        j+=1

    world.connect(grid, dso, 'P_rt')

    #aggrs.setup_done()
    #drawing the entity graph

    #plt.figure(10,20)
    #plt.fig()
    #nx.draw_networkx(world.entity_graph, node_size=10, font_size= 5)
    #plt.draw()
    #plt.show()
    #ts = world.entity_graph.edges.__getattribute__('color')


    #net=Network()
    #net.from_nx(world.entity_graph)
    #net.show_buttons()
    #net.show('nx.html')
    #creating list of connection attrs
    #load_attr = ['p_mw','q_mvar', 'min_p_mw','max_p_mw','min_q_mvar','max_q_mvar','controllable', 'cost']
    #gen_attr = ['p_mw','q_mvar', 'min_p_mw','max_p_mw','min_q_mvar','max_q_mvar','controllable', 'cost']

    #creating the connections
    # #connecting loads
    # grid_loads = [e for e in grid_components if e.type in 'Load']
    # dummy_loads = [e for e in dummy_components if e.type in 'Load']
    # for i in range(len(grid_loads)):
    #     world.connect(dummy_loads[i],grid_loads[i],'p_mw','q_mvar', 'min_p_mw','max_p_mw','min_q_mvar','max_q_mvar','controllable', 'cost')
    # #for node in nodes:
    # #    world.connect(dummy, node,'p_mw','q_mvar', 'min_p_mw','max_p_mw','min_q_mvar','max_q_mvar','controllable', 'cost')
    # #connecting sgens
    # #todo generalise te connection if in the grid there are not sgen or others must be checked
    # grid_sgens = [e for e in grid_components if e.type in 'Sgen']
    # dummy_sgens = [e for e in dummy_components if e.type in 'Sgen']
    # for i in range(len(grid_sgens)):
    #     world.connect(dummy_sgens[i], grid_sgens[i], 'p_mw','q_mvar', 'min_p_mw','max_p_mw','min_q_mvar','max_q_mvar','controllable', 'cost')
    # #for sgen in sgens:
    # #    world.connect(dummy, sgen, 'p_mw', 'q_mvar', 'min_p_mw', 'max_p_mw', 'min_q_mvar', 'max_q_mvar', 'controllable',
    # #                  'cost')
    #     # TODO WHEN mas_api for the buildings is done could use a connect randomly to populate the nodes
    # world.connect(grid, dso, 'P_rt', 'results')
    # world.connect(dso,grid,'proceed', weak = True)

    #drawing the entity graph
    #nx.draw_networkx(world.entity_graph, node_size=50)
    #plt.draw()
    #plt.show()
    #plot_execution_graph_st(world)
    #start the simulation
    print('good until here ')
    world.run(until=END)

    #p_rt = dso.sim._inst.P_rt
    #p_sch = dso.sim._inst.P_sch
    #p_res = dso.sim._inst.P_res
    #print('lenghts: P_rt:%s  P_sch:%s  P_res:%s '%(len(p_rt),len(p_sch),len(p_res)))

    plot_execution_graph_st(world)
    plot_execution_graph(world)
    #plot_primary(p_rt, p_sch, p_res)

if __name__ == '__main__':
    main()