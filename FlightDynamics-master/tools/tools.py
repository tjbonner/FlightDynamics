import numpy as np
import math

def Euler2Quaternion(phi,theta,psi):
    e0 = np.cos(psi/2)*np.cos(theta/2)*np.cos(phi/2) + np.sin(psi/2)*np.sin(theta/2)*np.sin(phi/2)
    e1 = np.cos(psi/2)*np.cos(theta/2)*np.sin(phi/2) - np.sin(psi/2)*np.sin(theta/2)*np.cos(phi/2)
    e2 = np.cos(psi/2)*np.sin(theta/2)*np.cos(phi/2) + np.sin(psi/2)*np.cos(theta/2)*np.sin(phi/2)
    e3 = np.sin(psi/2)*np.cos(theta/2)*np.cos(phi/2) - np.cos(psi/2)*np.sin(theta/2)*np.sin(phi/2)

    return np.array([e0,e1,e2,e3])

def Quaternion2Euler(e):
    e = e/np.linalg.norm(e) # do i need this?
    
    e0 = e[0]
    e1 = e[1]
    e2 = e[2]
    e3 = e[3]

    phi = np.arctan2(2*(e0*e1+e2*e3),(e0**2+e3**2-e1**2-e2**2)).item(0)
    theta = np.sin(2*(e0*e2-e1*e3)).item(0)
    psi = np.arctan2(2*(e0*e3+e1*e2),(e0**2+e1**2-e2**2-e3**2)).item(0)
    return phi, theta, psi

def Quaternion2Rotation(e):
    e0 = e.item(0)
    e1 = e.item(1)
    e2 = e.item(2)
    e3 = e.item(3)

    R = np.array([[e0**2+e1**2-e2**2-e3**2, 2*(e1*e2 - e0*e3)         , 2*(e1*e3 + e0*e2)      ],
                  [2*(e1*e2 + e0*e3)      , e0**2-e1**2+e2**2-e3**2   , 2*(e2*e3 - e0*e1)      ],
                  [2*(e1*e3 - e0*e2)      , 2*(e2*e3 + e0*e1)         , e0**2-e1**2-e2**2+e3**2]]) 

    return R