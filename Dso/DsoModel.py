import numpy as np


class DsoModel(object):

    def __init__(self, TH):
        self.P_sch24 = None
        self.P_fake = []
        self.report = dict()
        self.TH = TH
        pass

    def power_forecast(self):
        ''' This function furnish the scheduling for next 24 hours
        here should act a forecasting model of the reading of some written data'''
        #self.P_sch24 = list(np.zeros(24 * 4))
        self.P_sch24 = list(np.random.uniform(0, 3, 24*4))

    def check_threshold(self, P_rt):
        #for testing purpose********* cancelled when load forecasting is present
        self.P_sch24[0] = P_rt - (P_rt * 0.1)
        self.P_fake.append(self.P_sch24[0])
        #*****************
        delta = abs(self.P_sch24[0] - P_rt)
        if delta < abs(self.TH * self.P_sch24[0]):
            print('Threshold compliant!')
            self.P_sch24.pop(0)
            return False
        else:
            print('threshold exceeded')
            self.P_sch24.pop(0)
            return True

    def prepare_res(self,src_id,values,participant_list, time, step):
        results = {}
        results[src_id] = {}
        for building in participant_list:
            results[src_id][building] = {'opf_results':
                                                {'load':None,
                                                'sgen':None,
                                                'storage':None}}
            for el,id in values['name2index'].items():
                if building in el:
                    type = el.split('_')[-1]
                    key = 'res_'+ type
                    results[src_id][building]['opf_results']= {type:{'p_mw':values[key].loc[id,'p_mw'],
                                                    'q_mvar':values[key].loc[id,'q_mvar']}}
                    results[src_id][building]['time'] = time+step
        return results




