"""
mav_dynamics
    - this file implements the dynamic equations of motion for MAV
    - use unit quaternion for the attitude state
    
"""
import sys
sys.path.append('..')
import numpy as np
import math

# load message types
from message_types.msg_state import msg_state

import parameters.aerosonde_parameters as MAV
# from tools.tools import Quaternion2Rotation, Quaternion2Euler
from tools.tools import Quaternion2Rotation, Quaternion2Euler

class mav_dynamics:
    def __init__(self, Ts):
        self._ts_simulation = Ts
        # set initial states based on parameter file
        # _state is the 13x1 internal state of the aircraft that is being propagated:
        # _state = [pn, pe, pd, u, v, w, e0, e1, e2, e3, p, q, r]
        # We will also need a variety of other elements that are functions of the _state and the wind.
        # self.true_state is a 19x1 vector that is estimated and used by the autopilot to control the aircraft:
        # true_state = [pn, pe, h, Va, alpha, beta, phi, theta, chi, p, q, r, Vg, wn, we, psi, gyro_bx, gyro_by, gyro_bz]
        self._state = np.array([[MAV.pn0],  # (0)
                               [MAV.pe0],   # (1)
                               [MAV.pd0],   # (2)
                               [MAV.u0],    # (3)
                               [MAV.v0],    # (4)
                               [MAV.w0],    # (5)
                               [MAV.e0],    # (6)
                               [MAV.e1],    # (7)
                               [MAV.e2],    # (8)
                               [MAV.e3],    # (9)
                               [MAV.p0],    # (10)
                               [MAV.q0],    # (11)
                               [MAV.r0]])   # (12)
        # store wind data for fast recall since it is used at various points in simulation
        self._wind = np.array([[0.],
                               [0.],
                               [0.]])  # wind in NED frame in meters/sec
        self._update_velocity_data()
        # store forces to avoid recalculation in the sensors function
        self._forces = np.array([[0.],
                                 [0.],
                                 [0.]])
        self._Va = MAV.u0
        self._alpha = 0
        self._beta = 0
        # initialize true_state message
        self.msg_true_state = msg_state()

    ###################################
    # public functions
    def update_state(self, delta, wind):
        '''
            Integrate the differential equations defining dynamics, update sensors
            delta = (delta_a, delta_e, delta_r, delta_t) are the control inputs
            wind is the wind vector in inertial coordinates
            Ts is the time step between function calls.
        '''
        # get forces and moments acting on rigid bod
        forces_moments = self._forces_moments(delta)

        # Integrate ODE using Runge-Kutta RK4 algorithm
        time_step = self._ts_simulation
        k1 = self._derivatives(self._state, forces_moments)
        k2 = self._derivatives(self._state + time_step/2.*k1, forces_moments)
        k3 = self._derivatives(self._state + time_step/2.*k2, forces_moments)
        k4 = self._derivatives(self._state + time_step*k3, forces_moments)
        self._state += time_step/6.0 * (k1 + 2*k2 + 2*k3 + k4)

        # normalize the quaternion
        e0 = self._state.item(6)
        e1 = self._state.item(7)
        e2 = self._state.item(8)
        e3 = self._state.item(9)
        normE = np.sqrt(e0**2+e1**2+e2**2+e3**2)
        self._state[6][0] = self._state.item(6)/normE
        self._state[7][0] = self._state.item(7)/normE
        self._state[8][0] = self._state.item(8)/normE
        self._state[9][0] = self._state.item(9)/normE

        # update the airspeed, angle of attack, and side slip angles using new state
        self._update_velocity_data(wind)

        # update the message class for the true state
        self._update_msg_true_state()

    ###################################
    # private functions
    def _derivatives(self, state, forces_moments):
        """
        for the dynamics xdot = f(x, u), returns f(x, u)
        """
        # extract the states
        pn = state.item(0)
        pe = state.item(1)
        pd = state.item(2)
        u = state.item(3)
        v = state.item(4)
        w = state.item(5)
        e0 = state.item(6)
        e1 = state.item(7)
        e2 = state.item(8)
        e3 = state.item(9)
        p = state.item(10)
        q = state.item(11)
        r = state.item(12)
        #   extract forces/moments
        fx = forces_moments.item(0)
        fy = forces_moments.item(1)
        fz = forces_moments.item(2)
        l = forces_moments.item(3)
        m = forces_moments.item(4)
        n = forces_moments.item(5)

        # position kinematics
        pn_dot = u*(e1**2 + e0**2 - e2**2 - e3**2) + v*(2*(e1*e2 - e3*e0))               + w*(2*(e1*e3 + e2*e0))
        pe_dot = u*(2*(e1*e2 + e3*e0))             + v*(e2**2 + e0**2 - e1**2 - e3**2)   + w*(2*(e2*e3 - e1*e0))
        pd_dot = u*(2*(e1*e3 - e2*e0))             + v*(2*(e2*e3 + e1*e0))               + w*(e3**2 + e0**2 - e1**2 - e2**2)

        # position dynamics
        u_dot = (r*v - q*w) + fx/MAV.mass
        v_dot = (p*w - r*u) + fy/MAV.mass
        w_dot = (q*u - p*v) + fz/MAV.mass

        # rotational kinematics
        e0_dot = (1/2)  *  (0         - e1*p      - e2*q      - e3*r    )
        e1_dot = (1/2)  *  (e0*p      + 0         + e2*r      - e3*q    )
        e2_dot = (1/2)  *  (e0*q      - e1*r      + 0         + e3*p    )
        e3_dot = (1/2)  *  (e0*r      + e1*q      - e2*p      + 0       )

        # rotatonal dynamics
        p_dot = MAV.gamma1*p*q - MAV.gamma2*q*r + MAV.gamma3*l + MAV.gamma4*n
        q_dot = MAV.gamma5*p*r - MAV.gamma6*(p**2-r**2) + m/MAV.Jy
        r_dot = MAV.gamma7*p*q - MAV.gamma1*q*r + MAV.gamma4*l + MAV.gamma8*n

        # collect the derivative of the states
        x_dot = np.array([[pn_dot, pe_dot, pd_dot, u_dot, v_dot, w_dot,
                           e0_dot, e1_dot, e2_dot, e3_dot, p_dot, q_dot, r_dot]]).T
        return x_dot

    def _update_velocity_data(self, wind=np.zeros((6,1))):
        # Pull the wind data
        steady_state = wind[0:3]
        gust = wind[3:6]

        # Pull MAV angles and rotate
        e = self._state[6:10]
        R = Quaternion2Rotation(e)

        # Rotate steady to body and add gusts
        steady_state_NED = R.T @ steady_state + gust

        # Calculate airspeed components
        u,v,w = self._state[3:6]

        # Get relative u,v,w componentns in NED
        u_r = u - steady_state_NED[0]
        v_r = v - steady_state_NED[1]
        w_r = w - steady_state_NED[2]

        # compute airspeed
        self._Va = np.sqrt(u_r**2 + v_r**2 + w_r**2).item(0)
        # compute angle of attack
        self._alpha = np.arctan(w_r/u_r).item(0)
        # compute sideslip angle
        self._beta = np.sin(v_r/self._Va).item(0)

    def _forces_moments(self, delta):
        """
        return the forces on the UAV based on the state, wind, and control surfaces
        :param delta: np.matrix(delta_e, delta_t, delta_a, delta_r)
        :return: Forces and Moments on the UAV np.matrix(Fx, Fy, Fz, Ml, Mn, Mm)
        """
        # delta_a = delta.item(0)
        # delta_e = delta.item(1)
        # delta_r = delta.item(2)
        # delta_t = delta.item(3)

        delta_e = delta.item(0)
        delta_t = delta.item(1)
        delta_a = delta.item(2)
        delta_r = delta.item(3)

        Va = self._Va
        alpha = self._alpha
        beta = self._beta

        p, q, r = self._state[10:13]
        p = p.item(0)
        q = q.item(0)
        r = r.item(0)

        C_L = MAV.C_L_0 + MAV.C_L_alpha*alpha
        C_D = MAV.C_D_0 + MAV.C_D_alpha*alpha

        C_X_alpha = lambda a : -C_D*np.cos(a) + C_L*np.sin(a)
        C_X_q_alpha = lambda a : -MAV.C_D_q*np.cos(a) + MAV.C_L_q*np.sin(a)
        C_X_delta_e_alpha = lambda a : -MAV.C_D_delta_e*np.cos(a) + MAV.C_L_delta_e*np.sin(a)
        C_Z_alpha = lambda a : -C_D*np.sin(a) - C_L*np.cos(a)
        C_Z_q_alpha = lambda a : -MAV.C_D_q*np.sin(a) - MAV.C_L_q*np.cos(a)
        C_Z_delta_e_alpha = lambda a : -MAV.C_D_delta_e*np.sin(a) - MAV.C_L_delta_e*np.cos(a)

        # get Euler angles from quaternion
        phi, theta, psi = Quaternion2Euler(self._state[6:10])

        # Compute thrust and torque due to propeller
        # Map delta_t throttle command (0 to 1) into motor input voltage
        V_in = MAV.V_max * delta_t

        # Quadratic formula to solve for motor speed
        a = MAV.C_Q0 * MAV.rho * MAV.D_prop**5 / ((2*np.pi)**2)
        b = (MAV.C_Q1 * MAV.rho * MAV.D_prop**4 / (2*np.pi)) * self._Va + MAV.KQ**2/MAV.R_motor
        c = MAV.C_Q2 * MAV.rho * MAV.D_prop**3 * self._Va**2 - (MAV.KQ/MAV.R_motor)*V_in + MAV.KQ*MAV.i0

        # Consider only positive root
        Omega_op = (-b + np.sqrt(b**2 - 4*a*c)) / (2.0*a)

        # Compute advance ratio
        J_op = 2*np.pi*self._Va / (Omega_op*MAV.D_prop)

        # Compute non-dimensionalized coefficients of thrust and torque
        C_T = MAV.C_T2*J_op**2 + MAV.C_T1*J_op + MAV.C_T0
        C_Q = MAV.C_Q2*J_op**2 + MAV.C_Q1*J_op + MAV.C_Q0

        # Add thrust and torque to propeller
        n = Omega_op / (2*np.pi)
        T_p = MAV.rho * n**2. * MAV.D_prop**4. * C_T
        Q_p = -MAV.rho * n**2. * MAV.D_prop**5. * C_Q

        A = np.array([[-MAV.mass * MAV.gravity * np.sin(theta)],
                      [MAV.mass * MAV.gravity * np.cos(theta) * np.sin(phi)],
                      [MAV.mass * MAV.gravity * np.cos(theta) * np.cos(phi)]])

        B = np.array([[T_p],
                        [0],
                        [0]])

        coef = (1/2) * MAV.rho * self._Va**2 * MAV.S_wing

        C = np.array([[C_X_alpha(alpha) + C_X_q_alpha(alpha)*(MAV.c/(2*Va))*q],
                        [MAV.C_Y_0 + MAV.C_Y_beta*beta + MAV.C_Y_p*(MAV.b/(2*Va))*p + MAV.C_Y_r*(MAV.b/(2*Va))*r],
                        [C_Z_alpha(alpha) + C_Z_q_alpha(alpha)*(MAV.c/(2*Va))*q]])

        D = np.array([[C_X_delta_e_alpha(alpha)*delta_e],
                        [MAV.C_Y_delta_a*delta_a + MAV.C_Y_delta_r*delta_r],
                        [C_Z_delta_e_alpha(alpha)*delta_e]])

        (fx, fy, fz) = A + B + coef*C + coef*D

        self._forces[0] = fx
        self._forces[1] = fy
        self._forces[2] = fz

        E = np.array([[MAV.b*( MAV.C_ell_0 + MAV.C_ell_beta*beta + MAV.C_ell_p*(MAV.b/(2*Va))*p + MAV.C_ell_r*(MAV.b/(2*Va))*r )],
                        [MAV.c*( MAV.C_m_0 + MAV.C_m_alpha*alpha + MAV.C_m_q*(MAV.c/(2*Va))*q )],
                        [MAV.b*( MAV.C_n_0 + MAV.C_n_beta*beta + MAV.C_n_p*(MAV.b/(2*Va))*p + MAV.C_n_r*(MAV.b/(2*Va))*r )]])

        F = np.array([[MAV.b*( MAV.C_ell_delta_a*delta_a + MAV.C_ell_delta_r*delta_r )],
                        [MAV.c*( MAV.C_m_delta_e*delta_e )],
                        [MAV.b*( MAV.C_n_delta_a*delta_a + MAV.C_n_delta_r*delta_r )]])

        G = np.array([[Q_p],
                        [0],
                        [0]])


        (Mx, My, Mz) = coef*E + coef*F + G

        return np.array([[fx, fy, fz, Mx, My, Mz]]).T

    def _update_msg_true_state(self):
        # update the class structure for the true state:
        #   [pn, pe, h, Va, alpha, beta, phi, theta, chi, p, q, r, Vg, wn, we, psi, gyro_bx, gyro_by, gyro_bz]
        phi, theta, psi = Quaternion2Euler(self._state[6:10])
        self.msg_true_state.pn = self._state.item(0)
        self.msg_true_state.pe = self._state.item(1)
        self.msg_true_state.h = -self._state.item(2)
        self.msg_true_state.Va = self._Va
        self.msg_true_state.alpha = self._alpha
        self.msg_true_state.beta = self._beta
        self.msg_true_state.phi = phi
        self.msg_true_state.theta = theta
        self.msg_true_state.psi = psi
        self.msg_true_state.Vg = np.sqrt(self._state[3].item()**2 + self._state[4].item()**2 + self._state[5].item()**2)
        # self.msg_true_state.gamma = 10
        # self.msg_true_state.chi = 10
        self.msg_true_state.p = self._state.item(10)
        self.msg_true_state.q = self._state.item(11)
        self.msg_true_state.r = self._state.item(12)
        self.msg_true_state.wn = self._wind.item(0)
        self.msg_true_state.we = self._wind.item(1)
        self.msg_true_state.wd = self._wind.item(2)
