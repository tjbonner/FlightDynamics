"""
Class to determine wind velocity at any given moment,
calculates a steady wind speed and uses a stochastic
process to represent wind gusts. (Follows section 4.4 in uav book)
"""
import sys
sys.path.append('..')
from tools.transfer_function import transfer_function
import numpy as np

class wind_simulation:
    def __init__(self, Ts):
        # steady state wind defined in the inertial frame

        Va = 20.
        Lu = 200.
        Lv = Lu
        Lw = 50.
        sigma_u = 2.12
        sigma_v = sigma_u
        sigma_w = 1.4

        a1 = sigma_u*np.sqrt(2.0*Va/(np.pi*Lu))
        a2 = sigma_v*np.sqrt(3.0*Va/(np.pi*Lv))
        a3 = (Va/(np.sqrt(3.0)*Lv))*a2
        a4 = sigma_w*np.sqrt(3.0*Va/(np.pi*Lw))
        a5 = (Va/(np.sqrt(3.0)*Lw))*a4

        b1 = Va/Lu
        b2 = Va/Lv
        b3 = Va/Lw

        self._steady_state = [[1],[-0.5],[0.1]]

        self.u_w = transfer_function(num=np.array([[a1]]),
                                     den=np.array([[1, b1]]),
                                     Ts=Ts)
        self.v_w = transfer_function(num=np.array([[a2, a3]]),
                                     den=np.array([[1, 2*b2, b2**2.0]]),
                                     Ts=Ts)
        self.w_w = transfer_function(num=np.array([[a4, a5]]),
                                     den=np.array([[1, 2*b3, b3**2.0]]),
                                     Ts=Ts)
        self._Ts = Ts

    def update(self):
        # returns a six vector.
        #   The first three elements are the steady state wind in the inertial frame
        #   The second three elements are the gust in the body frame
        gust = np.array([[self.u_w.update(np.random.randn())],
                         [self.v_w.update(np.random.randn())],
                         [self.w_w.update(np.random.randn())]])
        # gust = np.array([[0.],[0.],[0.]])
        
        return np.concatenate(( self._steady_state, gust )).flatten()

