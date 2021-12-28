import asyncio
import logging
import multiprocessing
import sys
import time
import random

import aiomas
import arrow
import click

import mas.aggregator
import mas.util
import mas.building

logger = logging.getLogger('mas.mosaik')

@click.command()
@click.option('--log-level', '-l', default='info', show_default=True,
              type=click.Choice(
                  ['debug', 'info', 'warning', 'error', 'critical']),
              help='Log level for the MAS')
@click.argument('addr', metavar='HOST:PORT', callback=mas.util.validate_addr)



def main(addr, log_level):
    """Run the multi-agent system."""
    logging.basicConfig(level=getattr(logging, log_level.upper()))
    try:
        # Run the "run()" coroutine which starts the RPC server for mosaik:
        aiomas.run(until=run(addr, log_level))
    finally:
        # Make sure the event loop is closed so that everything is properly
        # cleaned up and we don't get nasty log messages at the end:
        asyncio.get_event_loop().close()




async def run(addr, log_level):
    """Start the RPC server serving the mosaik API until we receive a *stop*
    message from mosaik.
    """
    mosaik_api = MosaikAPI(log_level)
    try:
        # Create an RPC connection to mosaik.  It will handle all incoming
        # requests until we receive a *stop* message:
        logger.debug('Connecting to %s:%s ...' % addr)
        mosaik_con = await aiomas.rpc.open_connection(
            addr, rpc_service=mosaik_api, codec=aiomas.JSON)
        # Set the reverse-proxy that allows the "mosaik_api" to make calls back
        # to mosaik:
        mosaik_api.mosaik = mosaik_con.remote

        # If mosaik crashes and closes its connection, we also need to stop.
        # The RpcClient "mosaik_con" allows us to register a callback that gets
        # called when the connection is lost.  Our callback will trigger the
        # "mosaik_api.stopped" future:
        def on_connection_reset_cb(exc):
            if not mosaik_api.stopped.done():
                mosaik_api.stopped.set_result(True)

        mosaik_con.on_connection_reset(on_connection_reset_cb)

        # Wait until the future "mosaik_api.stopped" is triggered.  This will
        # happen if mosaik called "mosaik_api.stop()" or if the connection to
        # mosaik is lost and the callback defined above is run:
        logger.debug('Waiting for mosaik requests ...')
        await mosaik_api.stopped
    except KeyboardInterrupt:
        logger.info('Execution interrupted by user')
    finally:
        logger.debug('Closing socket and terminating ...')
        await mosaik_con.close()
        await mosaik_api.finalize()



class MosaikAPI:
    """Interface to mosaik.
    It implements and exposes the API calls :meth:`init()`, :meth:`create()`,
    :meth:`setup_done()`, :meth:`step()`, :meth:`get_data()` and
    :meth:`stop()`.
    The coroutine :meth:`finalize()` is executed by :func:`run()` just before
    we terminate to clean up everything.
    """
    router = aiomas.rpc.Service()

    # Host and port for the local container.  Sub-processes will use an
    # incremented port number.
    host = 'localhost'
    port = 5678

    def __init__(self, log_level):
        self.log_level = log_level
        # We have a step size of 15 minutes specified in seconds:
        self.step_size = 60 * 15  # seconds

        # The simulator meta data that we return in "init()":
        self.meta = {# todo add type
            'api_version': '3.0',
            'models': {
                'Building': {
                    'type':'hybrid',
                    'public': True,
                    'params': [],
                    'attrs': ['load','storage','sgen','waiting_DR','results','opf_results'], # the attrs of the grid children
                    #'trigger':['results']
                },
                'Aggregator':{
                    'public': True,
                    'params':[], #for initialization (when create)
                    'attrs':['aggr_msg'] # for communication are used for data exchange
                },
            },
        }

        # This future will be triggered when mosaik calls "stop()":
        self.stopped = asyncio.Future()

        # Set by "run()":
        self.mosaik = None  # Proxy object for mosaik

        # Set in "init()"
        self.sid = None  # Mosaik simulator ID
        self.container = None  # Root agent container
        self.start_date = None
        self.container_procs = []  # List of "(proc, container_proxy)" tuples

        # Updated in "setup_done()"
        self.bui_entities = []  # agent_id: agent_instance
        self.aggr_entities = [] # agent_id: agent_instance


        # Set/updated in "setup_done()"
        self.uids = {}  # agent_id: unit_id
        self.t_last_step = None  # Used to measure the real-time a step takes

    @aiomas.expose
    async def init(self, sid, time_resolution, *, start_date):
        """Create a local agent container and the mosaik agent and start the subcontainers."""
        #todo should allow multiple aggregatros creation
        self.sid = sid
        self.start_date = arrow.get(start_date).to('utc')

        # Root container for the MosaikAgent and Controller.  It will use the
        # ExternalClock which can be set by mosaik (see
        # "mas.util.get_container_kwargs()" for details):
        container_kwargs = mas.util.get_container_kwargs(start_date)
        self.container = await aiomas.Container.create(
            (self.host, self.port), as_coro=True, **container_kwargs)

        # Remote containers for WecsAgents
        self.container_procs = await self._start_containers(
            self.host, self.port + 1, start_date, self.log_level)

        # Start the MosaikAgent and Controller agent in the root container:
        self.ma = MosaikAgent(self.container, self.container_procs)


        return self.meta

    @aiomas.expose
    async def create(self, num, model, **model_conf):
        """Create *num* instances of *model* and return a list of entity dicts
        to mosaik."""

        assert model in self.meta['models']
        entities = []

        # Get the number of agents created so far and count from this number
        # when creating new entity IDs:
        n_buildings = len(self.ma.bui_agents)
        n_aggregators = len(self.ma.agg_agents)

        if model == 'Aggregator':

            for i in range(n_aggregators, n_aggregators + num):
                # Entity data
                eid = 'Aggregator_%s' % i
                entities.append({'eid': eid, 'type': model, 'rel':[]})
                self.aggr_entities.append(entities) # todo appendere solo l'entità

                # Get a remote/sub container for the agent and spawn it.  Rember,
                # "self.container_procs" is a list of tuples and the proxy to the
                # container's manager agent is at index [1]:
                container = self.container_procs[i % len(self.container_procs)][1]
                # We'll get a (proxy, addr) tuple, but only care for the proxy:

                self.ma.agg_agents[eid], addr = await container.spawn(
                    'mas.aggregator:AggregatorAgent.create', model_conf)
                self.ma.agg_addrs.append(addr)

        elif model == 'Building':
            for i in range(n_buildings, n_buildings + num):
                # Entity data
                eid = 'Building_%s' % i
                aggr_n = i % n_aggregators
                rel_aggr = 'Aggregator_%s'%aggr_n

                entities.append({'eid': eid, 'type': model,'rel':[rel_aggr] })
                #todo should return something better than the simple name

                # Get a remote/sub container for the agent and spawn it.  Remember,
                # "self.container_procs" is a list of tuples and the proxy to the
                # container's manager agent is at index [1]:
                container = self.container_procs[i % len(self.container_procs)][1]
                # We'll get a (proxy, addr) tuple, but only care for the proxy:
                self.ma.bui_agents[eid], _ = await container.spawn(
                    'mas.building:BuildingAgent.create',
                    self.ma.agg_addrs[aggr_n], model_conf, eid)

        else:
            raise ValueError ('Unknown type of agent for aiomas MAS')


        return entities

    @aiomas.expose
    async def setup_done(self):
        """Get the entities that our agents are connected to once the scenario
        setup is done."""
        full_ids = ['%s.%s' % (self.sid, aid) for aid in self.ma.agg_agents]
        full_ids.extend( ['%s.%s' % (self.sid, aid) for aid in self.ma.bui_agents])
        relations = await self.mosaik.get_related_entities(full_ids)
        for full_aid, units in relations.items():
            aid = full_aid.split('.')[-1]
            self.uids[aid]=[]
            for uid,_ in units.items():
                self.uids[aid].append(uid)

        # We need a reference (real-)time for measuring how long our step (see
        # "step()") takes in real-time.  If we have a step size of x minutes,
        # we want to make sure we don't spent more then x minutes of real-time
        # within "step()".
        self.t_last_step = time.monotonic()

    @aiomas.expose
    async def step(self, t, inputs):
        """Send the inputs of the controlled unites to our agents and get new
        set-points for these units from the agents.
        This method will run for at most "step_size" seconds, even if the
        agents need longer to do their calculations.  They will then continue
        to do stuff in the background, while this method returns and allows
        mosaik to continue the simulation.
        """
        # Update the time for the agents:
        await self.ma.update_containersClock(t)
        self.container.clock.set_time(t)
        #futs = [c.set_time(t) for _, c in self.container_procs]
        #await asyncio.gather(*futs)

        # at first time step get all the relations
        if t == 0:
            await self.setup_done()

        if t != 0:
            #actuation step is done at the beginning of a time step saving data of the previous one
            data = {}
            for eid, attrs in inputs.items():
                input_data = {}
                for attr, values in attrs.items():
                    assert len(values) == 1  # b/c we're only connected to 1 unit
                    _, value = values.popitem()
                    input_data[attr] = value
                    data[eid] = input_data
            await self.ma.update_buildings(data)


        # Check if we got new schedules and send them to mosaik.  Since we
        # could, in theory, wait longer then "step_size" seconds, we calculate
        # a timeout.  This timeout is "step_size - time_we_used_so_far" long:
        timeout = self.t_last_step + self.step_size - time.monotonic()
        try:
            await asyncio.wait_for(self.ma.buildings_calc(),
                                   timeout=timeout)


        except asyncio.TimeoutError as e:
            # Instead of raising an error here, we could as well let our agents
            # continue with their calculations in the background (because they
            # run in sub-processes) and just skip sending set-points in this
            # step.
            raise RuntimeError('Agent system did not finish its step within '
                               '%s seconds' % self.step_size) from e


        # # Get new reference time for the next "step()":
        # self.t_last_step = time.monotonic()
        #
        # #gathering values from buildings for the grid
        # builds_state = await self.ma.get_buildings_state() # TODO should return a dict with entity and then a dict with attrs to send
        #
        # # Make "set_data()" call back to mosaik to send the new states
        # # of each building pv nd storage directly connected to the grid
        # inputs = {aid: {self.uids[aid][1]: dictionary} #todo check well self.uid
        #           for aid, dictionary in builds_state.items()}
        # await self.mosaik.set_data(inputs)
        self.t_last_step = time.monotonic()

        return t + self.step_size

    @aiomas.expose
    def get_data(self,outputs):
        '''is used to communicate the Prt value to the connceted entities of the grid
        inputs: outputs | dict'''
        #todo match the dictionaries
        data={}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr not in self.meta['models']['Building']['attrs']:
                    raise ValueError('Unknown output attribute "%s"' % attr)
                if attr == 'waiting_DR':
                    data[eid][attr] = True
                elif attr != 'opf_results':
                    data[eid][attr] = self.ma.buildings_states[eid][attr]
        return data


    @aiomas.expose
    def stop(self):
        """Set a result for the :attr:`stopped` future causing :func:`run()` to
        finish and return."""
        self.stopped.set_result(True)

    async def finalize(self):
        """Stop all agents and sub-processes and wait for them to terminate.
        """
        # We collect a list of futures and wit for all of them at once:
        futs = []
        for proc, container_proxy in self.container_procs:
            # Send a "stop" message to the remote container and wait for the
            # corresponding subprocess to terminate:
            futs.append(container_proxy.stop())
            futs.append(proc.wait())

        # Wait for the futures to finish:
        await asyncio.gather(*futs)

        #await self.controller.stop()

        # Since the event loop is already running (we are currently in
        # a coroutine), we need to make "shutdown()" behave like a coroutine
        # as well:
        await self.container.shutdown(as_coro=True)

    async def _start_containers(self, host, start_port, start_date, log_level):
        """Start one container (process) on each CPU core."""
        addrs = []  # Container addresses
        procs = []  # Subprocess instances
        for i in range(multiprocessing.cpu_count()):
            # We define a network address for the new container, ...
            addr = (host, start_port + i)
            addrs.append('tcp://%s:%s/0' % addr)
            # ... and build the command for starting the subprocess.  We want
            # to use the same interpreter we currently use to run the
            # "mas.container" module.  We also pass some command line args:
            cmd = [
                sys.executable,
                '-m', 'mas.container',
                '--start-date=%s' % start_date,
                '--log-level=%s' % log_level,
                '%s:%s' % addr,
            ]
            # ... We finally create a task for starting the subprocess:
            procs.append(asyncio.create_subprocess_exec(*cmd))

        # Start all processes and connect to them.  Since it may take a while
        # until a process is listening on its socket, we use a timeout of 10s
        # in the "connect()" call.
        procs = await asyncio.gather(*procs)
        futs = [self.container.connect(a, timeout=10) for a in addrs]
        containers = await asyncio.gather(*futs)

        print(addrs)

        # Return a list of "(proc, container_proxy)" tuples:
        return [(p, c) for p, c in zip(procs, containers)]

class MosaikAgent(aiomas.Agent):
    """This agent is a gateway between the mosaik API and the WecsAgents.
    It forwards the current state of the simulated WECS to the agents and
    collects new set-points for the simulated WECS from the agents.
    CAN BE SEEN AS THE MODEL OF THE AIOMAS SIMULATOR THIS MANAGES ALL THE AIOMAS AGENTS
    """
    def __init__(self, container, external_containers):
        super().__init__(container)

        # Maps "agent_id: agent_proxy".  The mosaik API fills this dict when
        # it spawns new WecsAgents:
        self.bui_agents = {}
        self.agg_agents = {}
        self.agg_addrs = []
        self.container_procs = external_containers

        #data
        self.buildings_states = {}

    async def update_containersClock(self,t):
        futs = [c.set_time(t) for _, c in self.container_procs]
        await asyncio.gather(*futs)

    # async def building_calc_load(self, bui_aid):
    #     """make the calculations in alla the buildings."""
    #     futs = [self.bui_agents[aid].get_dummy_load() for aid in bui_aid]
    #     results = await asyncio.gather(*futs)

    # async def update_aggregators(self,  data):
    #     """Update the agents with new data from mosaik."""
    #     futs = [self.agents[aid].update_state(input_data)
    #             for aid, input_data in data.items()]
    #     await asyncio.gather(*futs)
    async def buildings_calc(self):
        """will be substituted by the aggregators and all exchange relative to buildings will remain inside AIOMAS
        return : buildings_state  : dict
                {bui_name: {'load':{},
                            'storage':{},
                            'sgen':{}
                            },
                }
                """
        #TODO this function
        futs = [val.calc_state() for key,val in self.bui_agents.items()]
        buildings_states = await asyncio.gather(*futs)
        self.buildings_states = {el[0]:el[1] for el in buildings_states }
        return self.buildings_states

    async def update_buildings(self,  data):
        """will be substituted by the aggregators and all exchange relative to buildings will remain inside AIOMAS"""
        #TODO this function
        futs = [self.bui_agents[aid].update_state(data)
                for aid, data in data.items()]
        await asyncio.gather(*futs)

    # async def get_buildings_state(self):
    #     """Collect new entities state info from the building agents and return
    #     them to the mosaik API.
    #     state info : """
    #     # "asyncio.gather()" returns only a list, but here, we need a mapping
    #     # "aid: P_max".  Thus, we first create a mapping "aid: future" and
    #     # once the futures completed, transform the dict to the one we need:
    #     futs = {aid: a.get_dummy_load() for aid, a in self.bui_agents.items()}
    #     await asyncio.gather(*(fut for fut in futs.values()))
    #     state = {aid: fut.result() for aid, fut in futs.items()}
    #
    #     return state


if __name__ == '__main__':
    main()