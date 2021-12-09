import pandas as pd
from matplotlib import pyplot as plt
#from Standard_Profile import *
class TrajectorInfo:
    temp = 10
    no_cars = 2

class TrajectoryArrays:
    delta_t_driving = []
    delta_t_standing = []
    E_whacc = []
    E_whrec = []
    E_hvac = []
    E_auxtr = []
    under_catenary = []
    v_max = []
    position = []
    station_name = []

def read_excel():
    TrajectoryArrays.E_hvac = []
    TrajectoryArrays.E_auxtr = []
    def E_HVAC(n_cars, Temp, delta_t):
        return n_cars * (-1.2 * Temp + 21.2)*(delta_t/3600)

    df = pd.read_excel("RB26.xlsx")
    TrajectoryArrays.position = df["position [m]"].tolist()
    TrajectoryArrays.station_name = df["station_name []"].tolist()
    TrajectoryArrays.delta_t_standing = df["stop_time [s]"].tolist()
    TrajectoryArrays.delta_t_driving = df["drive_time [s]"].tolist()
    TrajectoryArrays.under_catenary = df["electrified []"].tolist()
    TrajectoryArrays.v_max = df["v_max [km/h]"].tolist()
    TrajectoryArrays.E_whacc = df["Ewheel_pos [kWh]"].tolist()
    TrajectoryArrays.E_whrec = df["Ewheel_neg [kWh]"].tolist()

    for i in range(0,len(TrajectoryArrays.under_catenary)):
        if not TrajectoryArrays.delta_t_standing[i]:
            TrajectoryArrays.E_hvac.append(E_HVAC(TrajectorInfo.no_cars, TrajectorInfo.temp, TrajectoryArrays.delta_t_driving[i]))
        else:
            TrajectoryArrays.E_hvac.append(E_HVAC(TrajectorInfo.no_cars, TrajectorInfo.temp, TrajectoryArrays.delta_t_standing[i]))
        TrajectoryArrays.E_auxtr.append(TrajectoryArrays.E_whacc[i] * 0.06)

class BSInput:
    eta_bat2acc = 0.975
    eta_bat2aux = 0.975
    eta_cat2acc = 0.975
    eta_cat2aux = 0.975
    #Fehlt in der Liste im Dokument
    eta_cat2wh = 0.975
    E_batmax = 500
    P_catmax = 1200
    starting_percentage = 0.6
class BSOutput:
    E_catmax = []
    E_catacc = []
    E_cataux = []
    E_battacc = []
    E_bataux = []
    E_batt_acc = []
    E_bat = []
    E_batrec = []
    E_chmax = []
    E_ch = []
    SoC = []
    E_catrec = []



def soc_calc(delta_t_standing,delta_t_driving,E_whacc,E_whrec,E_hvac,E_auxtr,under_catenary):
    for i in range(0,len(delta_t_driving)):

        if under_catenary[i]:
            #STEP A1 --> Standing und Driving miteinbezogen!
            BSOutput.E_catmax.append(((BSInput.P_catmax * delta_t_driving[i]) / 3600) + ((BSInput.P_catmax * delta_t_standing[i]) / 3600))
            temp_E_catmax_driving = (BSInput.P_catmax * delta_t_driving[i]) / 3600
            temp_E_catmax_standing = (BSInput.P_catmax * delta_t_standing[i]) / 3600
            #STEP A2
            BSOutput.E_catacc.append(min(E_whacc[i]/BSInput.eta_cat2acc,BSOutput.E_catmax[i]))
            #STEP A3 --> IF DRIVING
            if BSOutput.E_catacc[i] < temp_E_catmax_driving:
                BSOutput.E_cataux.append(min((E_auxtr[i]+E_hvac[i])/BSInput.eta_cat2aux,temp_E_catmax_driving-BSOutput.E_catacc[i]))
            else:
                BSOutput.E_cataux.append(0)
            temp_E_cataux_driving = BSOutput.E_cataux[i]
            #STEP A4 --> IF STANDING
            temp_E_cataux_standing = min((E_hvac[i]/BSInput.eta_cat2aux),temp_E_catmax_standing)
            BSOutput.E_cataux[i] = BSOutput.E_cataux[i] + temp_E_cataux_standing
            #STEP A5
            BSOutput.E_battacc.append((E_whacc[i]-BSInput.eta_cat2wh*BSOutput.E_catacc[i])*(1/BSInput.eta_bat2acc))

            if not temp_E_cataux_standing:
            #STEP A6 --> If driving --> Bedingung einfügen
                BSOutput.E_bataux.append((E_auxtr[i]+E_hvac[i]-BSInput.eta_cat2aux * temp_E_cataux_driving)*(1/BSInput.eta_bat2aux))
            else:
                BSOutput.E_bataux.append(0)
            if not temp_E_cataux_driving:
            #STEP A7 --> If standing --> Bedingung einfügen
                BSOutput.E_bataux[i] = BSOutput.E_bataux[i] + ((E_hvac[i]-BSInput.eta_cat2aux * temp_E_cataux_standing) * (1/BSInput.eta_bat2aux))
        else:
            BSOutput.E_catmax.append(0)
            BSOutput.E_catacc.append(0)
            BSOutput.E_cataux.append(0)
            #STEP A8
            BSOutput.E_battacc.append(E_whacc[i]*(1/BSInput.eta_bat2acc))
            #STEP A9
            BSOutput.E_bataux.append((E_auxtr[i]+E_hvac[1]) * (1/BSInput.eta_bat2aux))
        if i == 0:
            #A11
            BSOutput.E_batrec.append(0)
        else:
            # A12
            BSOutput.E_batrec.append(min(BSInput.E_batmax - BSOutput.E_bat[i - 1] - BSOutput.E_bataux[i] - BSOutput.E_battacc[i], E_whrec[i]))
        #A13
        BSOutput.E_chmax.append(max(min(BSOutput.E_catmax[i] - BSOutput.E_catacc[i] - BSOutput.E_cataux[i], BSOutput.E_catmax[i]), 0))

        if i == 0:
           #A10
           BSOutput.E_bat.append(BSInput.E_batmax*BSInput.starting_percentage)
        else:
           # A14
           BSOutput.E_bat.append(min(BSOutput.E_bat[i - 1] - BSOutput.E_bataux[i] - BSOutput.E_battacc[i] + BSOutput.E_batrec[i] + BSOutput.E_chmax[i], BSInput.E_batmax))
        if i == 0:
            BSOutput.E_ch.append(0)
        else:
            #A15 ACHTUNG WEGEN I-1 --> IF ODER TRY DEFINIEREN
            BSOutput.E_ch.append(min(max(BSOutput.E_bat[i]-BSOutput.E_bat[i-1],0),BSOutput.E_chmax[i]))
        #A16
        BSOutput.SoC.append(BSOutput.E_bat[i]/BSInput.E_batmax)
        #A17
        BSOutput.E_catrec.append(E_whrec[i]-BSOutput.E_batrec[i])


read_excel()
soc_calc(TrajectoryArrays.delta_t_standing,TrajectoryArrays.delta_t_driving,TrajectoryArrays.E_whacc,TrajectoryArrays.E_whrec,TrajectoryArrays.E_hvac,TrajectoryArrays.E_auxtr,TrajectoryArrays.under_catenary)


plt.plot(TrajectoryArrays.position,BSOutput.SoC,"r-")
plt.axvspan(81400, 83500, facecolor='b', alpha=0.2)
plt.axvspan(36600, 42900, facecolor='b', alpha=0.2)
plt.axvspan(124200,130400,facecolor="b",alpha=0.2)
plt.show()
print(sum(BSOutput.E_catmax))