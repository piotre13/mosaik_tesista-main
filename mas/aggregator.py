import asyncio

import aiomas


class AggregatorAgent(aiomas.Agent):
    """The Controller agent knows all WecsAgents of its wind farm.
    It regularly (every *check_interval* seconds) collects the current power
    output of all WECS from the WecsAgents and checks if the total power output
    exceeds *max_windpark_feedin*.  If so, it sets power limits to the WECS.
    It also requires the *start_date* of the simulation to calculate the
    initial check time.
    """
    def __init__(self, container, model_conf ):
        super().__init__(container)
        self.model_conf = model_conf

        self.buildings = []  # List of WecsAgent proxies registered with us.


    @classmethod
    async def create(cls, container, model_conf):
        # TODO GIVE A SPECIFIC NAME THAT SHOULD BE THA SAME OF THE ON EIN MOSAIK
        aggregator = cls(container, model_conf)
        return aggregator

    @aiomas.expose
    def register(self, building_proxy):
        """Called by WecsAgents to register themselves with this controller."""
        # We don't want duplicate registrations:
        #assert building_proxy not in self.buildings
        if building_proxy not in self.buildings:
        #aggregator = await container.connect(aggregator_address)
            self.buildings.append(building_proxy)

    @aiomas.expose
    async  def update_state(self, data):
        pass

