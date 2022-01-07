import mosaik_api
from .DsoModel import DsoModel
import numpy as np
from config import *

meta = {
    'type': 'time-based',  # or hybrid...
    'models': {
        'Dso': {
            'public': True,
            'params': ['TH'],
            'attrs': ['P_rt']
        },
    },
}


class DsoApi(mosaik_api.Simulator):

    def __init__(self):
        super().__init__(meta)
        self.step_size = None
        self._entities = {}
        self.res_cache = {}
        self.relations = []
        self.P_rt = []
        self.P_sch = []
        self.P_res = []
        self.sameTime = True
        self.DR_list_participants = []

    def init(self, sid, step_size, TH):
        self.step_size = step_size
        self.model = DsoModel(TH)
        return self.meta

    def create(self, num, modelname):

        if modelname != 'Dso':
            raise ValueError('Unknown model: "%s"' % modelname)
        # in case more than one dso must be created
        entities = []
        for i in range(num):
            eid = 'Dso_%d' % i
            entities.append({'eid': eid, 'type': modelname, 'rel': []})
        self._entities = entities
        return entities

    def step(self, time, inputs, max_advance):

        src_id = '%s.%s' % (self.mosaik.sim_id, self._entities[0]['eid'])
        if time == 0:
            rel = yield self.mosaik.get_related_entities(src_id)
            for dest in rel.keys():
                edge = (src_id, dest)
                if edge not in self.relations: self.relations.append(edge)

        self.time = time
        #self.proceed = False

        # if time % (SEC_IN_DAY) == 0:
        #     #TODO FORECAST
        #     self.model.power_forecast()
        #     self.P_sch.extend(self.model.P_sch24)

        # # reading inputs
        # if self.sameTime:
        #      # calculate the forecast
        #         #self.P_sch.extend(self.model.P_sch24) this is correct commented only when testing
        #     print('Dso receive P_rt value at time %s \n ' %self.time)
        #     for eid, attrs in inputs.items():
        #         for name, values in attrs.items():
        #             if name == 'P_rt':
        #                 p_rt = list(attrs[name].values())[0] # todo must be generalised in case of more than one grid
        #                 self.P_rt.append(p_rt)
        #                 #checking the threshold
        #                 self.proceed = self.model.check_threshold(p_rt)

        #                 #only for testing must be deleted***********
        #                 self.P_sch.append(self.model.P_fake[0])
        #                 self.model.P_fake.pop(0)
        #                 #****************

        # else:
        #     print('Dso received OPF results at time %s\n' %self.time)
        #     #todo avoid the cycle keeping it generalised
        #     #TODO prepare the results from grid in dict by buildings/aggregators to be spread back

        #     for eid, attrs in inputs.items():
        #         for name, values in attrs.items():
        #             if name=='results':
        #                 pre_results = list(values.values())[0]
        #                 #self.P_res.append(attrs[name]['Grid-0.0-grid'])

        #     self.DR_list_participants = [building[1] for building in self.relations if 'Building' in building[1]]
        #     self.results = self.model.prepare_res(src_id,pre_results,self.DR_list_participants, time,self.step_size)
        #     #results = {aid: {self.uids[aid][1]: dictionary}  # todo check well self.uid
        #     #          for aid, dictionary in builds_state.items()}
        #     #yield self.mosaik.set_data(results)

            #print('============TS END==============\n')

        return self.time + self.step_size

    # def get_data(self, outputs):
    #     data = {}
    #     if self.sameTime:  # se siamo al primo scambio passiamo proceed
    #         for eid, attrs in outputs.items():
    #             data[eid] = {}
    #             for attr in attrs:
    #                 if attr not in self.meta['models']['Dso']['attrs']: #todo this check as in all others API could be useless
    #                     raise ValueError('Unknown output attribute "%s"' % attr)
    #                 if attr == 'proceed':
    #                     data[eid][attr] = self.proceed
    #                 else:
    #                     data[eid][attr] = None
    #         self.sameTime = False
    #         return data
    #     else:
    #         self.sameTime = True
    #         for eid, attrs in outputs.items():
    #             data[eid]={}
    #             for attr in attrs:
    #                 if attr == 'aggr_msg':
    #                     data[eid][attr] = 'dict with all the info per aggr and components'
    #                 elif attr == 'proceed':
    #                     data[eid][attr] = False
    #                 elif attr == 'opf_results':
    #                     data[eid][attr] = self.results


    #             data['time'] = self.time + self.step_size
    #             #yield self.mosaik.set_data(results)

    #         return data


