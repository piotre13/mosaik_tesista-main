#scenario creation imports
from Scenario.Prj_creation_archetypes import  PrjScenario
#simul imports
import mosaik
from mosaik.util import connect_randomly, connect_many_to_one
from plot import plot_execution_graph, plot_execution_graph_st
from plot_results import plot_primary
import networkx as nx
import matplotlib.pyplot as plt
import sys
from pyvis.network import Network

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
    'DUMMY':{
            'python':'Dummy_loads.dummy_API:DummyApi'
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
END = 1  * 60 * 60  #two days ---> 2 * 24 * 60 * 60
START = '2014-01-01 01:00:00'
GRID_FILE = 'cigre_mv_all' # import directly from pandpaower simbench module
#GRID_FILE = 'test_pp'
#NB the grid must already have loads/gen/storages and transf created
Threshold_DSO = 0.05



def main():
    """Compose the mosaik scenario and run the simulation."""
    # Set up the "world" instance.
    world = mosaik.World(sim_config, debug= True)

#SIMULATORS START init()

    dsosim = world.start('DSO', step_size=15 * 60, TH=Threshold_DSO)

    mas = world.start('MAS', start_date=START)

    gridsim = world.start('Grid', step_size=15 * 60)  # mode = 'pf' or 'pf_timeseries'


#ENTITIES CREATION create()
    #TODO USE RELATION IN ENTITIES FOR CONNECTIONS

    grid = gridsim.Grid(gridfile=GRID_FILE)  # calls create() could be called for more than one grid
    grid_components = grid.children  # attribute children returns children of the grid entity
    dso = dsosim.Dso()

    #mas = massim.MAS.create(1)
    aggrs = mas.Aggregator.create(3)
    builds = mas.Building.create(10)

#CONNECTIONS
    world.connect(grid, dso, 'P_rt', 'results')
    world.connect(dso,grid,'proceed', weak = True )
    i = 0
    #todo should connect buildings to bus not to loads
    grid_loads = [e for e in grid_components if e.type in 'Load']
    grid_bus = [e for e in grid_components if e.type in 'Bus']
    for building in builds:
        #world.connect(building,grid_loads[i],'p_mw','q_mvar', 'min_p_mw','max_p_mw','min_q_mvar','max_q_mvar','controllable', 'cost')
        world.connect(building,grid_bus[i],'load','storage','sgen')

        #world.connect(building,dso,'waiting_DR','results', async_requests=True, initial_data={'result':None})
        #world.connect(building,dso,'waiting_DR','opf_results', async_requests=True, initial_data={'opf_results':None})
        world.connect(dso,building, 'opf_results', time_shifted=True, initial_data={'opf_results':None})
        i+=1

    #world.connect(grid, dso, 'P_rt', 'results')
    #world.connect(dso, grid, 'proceed', weak=True,initial_data={'proceed':False})

    #connect_many_to_one(world,aggrs,dso,'aggr_msg')


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
    world.run(until=END)

    #p_rt = dso.sim._inst.P_rt
    #p_sch = dso.sim._inst.P_sch
    #p_res = dso.sim._inst.P_res
    #print('lenghts: P_rt:%s  P_sch:%s  P_res:%s '%(len(p_rt),len(p_sch),len(p_res)))

    plot_execution_graph_st(world)
    #plot_primary(p_rt, p_sch, p_res)

if __name__ == '__main__':
    main()