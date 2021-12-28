import aiomas
import random
from mas.UDP_trigger import Client


class BuildingAgent(aiomas.Agent):
    """A WecsAgent is the “brain” of a simulated or real WECS.
    This class should not be instantiated directly but only via the
    :meth:`create()` factory function: ``wecs = WECS.create(...)``.  That
    function performs some async. tasks (like registering the agent with the
    Controller agent) which cannot be done in ``__init__()``.
    """
    def __init__(self, container, aggregator, model_conf,name):
        super().__init__(container)
        self.aggregator = aggregator
        self.model_conf = model_conf
        self.name = name

        #communicatioon Villas
        if name == 'Building_0':
            #host = '130.192.177.15' # TODO should be assigned at the creation in order to use different ports per buildings
            local_host = '192.168.177.114'
            local_port = 12000
            remote_host = '130.192.177.15'
            remote_port = 12004
            self.Client = Client(local_host, local_port, remote_host, remote_port)

        #STATE PARAMETERS
        self.load_state = None
        self.pv_state = None
        self.storage_state = None
        self.appliances_state = None

    @classmethod
    async def create(cls, container, aggregator_address, model_conf,name):
        """Return a new :class:`WecsAgent` instance.
        *container* is the container that the agent lives in.
        *controller_address* is the address of the Controller agent that the
        agent will register with.
        *model_conf* is a dictionary containing values for *P_rated*,
        *v_rated*, *v_min*, *v_max* (see the WECs model for details).
        """
        # We use a factory function here because __init__ cannot be a coroutine
        # and creating init *tasks* init __init__ on whose results other
        # coroutines depend is bad style, so we better to all that stuff
        # before we create the instance and then have a fully initialized
        # instance.
        #
        # Classmethods don't receive an instance "self" but the class object as
        # an argument, hence the argument name "cls".
        #TODO GIVE A SPECIFIC NAME THAT SHOULD BE THA SAME OF THE ON EIN MOSAIK
        aggregator = await container.connect(aggregator_address)
        building = cls(container, aggregator, model_conf,name)
        await aggregator.register(building.addr)
        return building

    @aiomas.expose
    def calc_state(self):
        ''' this function is run all the calculation in the buildings'''
        data = {'load':None,
                'storage':None,
                'sgen':None
                }
        #reporting comulative values only one element
        data['load'] = self.get_dummy_load()
        data['storage'] = None
        data['sgen'] = None

        #echo loop test
        if self.name == 'Building_0':
            self.Client.trigger(data['load']['p_mw'])


        return (self.name,data)

    def get_dummy_load(self):
        data = {}
        data['p_mw'] = random.uniform(0.8, 0.9)
        data['q_mvar'] = 0.01
        data['min_p_mw'] = 0.5
        data['max_p_mw'] = 1.0
        data['min_q_mvar'] = - 100.0
        data['max_q_mvar'] = 100.0
        data['controllable'] = True
        data['cost'] = 0.01
        return data

    @aiomas.expose
    def update_state(self,data):
        ''' this function is the actuation process it takes the data of the DR scheme results
        and set them inside the buildings'''
        pass

    #TODO SHOULD ADD A STOP FUNCTION FOR CLOSING SOCKETS

    # @aiomas.expose
    # def calculations (self):
    #     """perform the building calculations:
    #     - load demand
    #     - generation
    #     - flexibility
    #     for one step"""
    #     data = {}
    #     return data
    #
    # @aiomas.expose
    # def actuation(self, inputs):
    #     """perform actuation of the commanded inputs"""
    #     data = {}
    #     return data
    #
    #
    # @aiomas.expose
    # def get_state(self):
    #     state = {}
    #     state['load'] = self.load_state
    #     state['sgen'] = self.pv_state
    #     state['storage'] = self.storage_state
    #
    #     #test for echo loop
    #     #self.Client.trigger(state)
    #     return state
    #
    # @aiomas.expose

    #
    # async def set_state (self, state):
    #     pass
    #
    #
    #
    # @aiomas.expose
    # def get_dummy_sgen(self):
    #     data = {}
    #     data['p_mw'] = random.uniform(0.001, 0.003)
    #     data['q_mvar'] = 0.003
    #     data['min_p_mw'] = data['p_mw']
    #     data['max_p_mw'] = data['p_mw']
    #     data['min_q_mvar'] = -100000
    #     data['max_q_mvar'] = 100000
    #     data['controllable'] = True
    #     data['cost'] = -0.02
    #     self.pv_state = data
    #     return data