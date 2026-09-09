#ifndef TE_PROCESS_H
#define TE_PROCESS_H


#include <math.h>
#include <lapacke.h>
#include <time.h>
#include <sys/time.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <jsoncpp/json/json.h>



//TODO add sensor noise?

class TE {
        struct timeval last_update, current; 
        double time_scale;
        //parameters
        double sampling_delay;          //sampling delay in gas composition measurement [h]
        double ya1;                     //mol fraction A in feed 1
        double yb1;                     //mol fraction B in feed 1
        double yc1;
        double product_valve_max;       // max allowed posiition for product valve[%]
        double level_gain;              //gain for level controller
        double product_valve_nom;       //nominal steady state for product valve [%]
        double kpar;                      //pre-exponential k0 of eq 5
        double ncpar;                      //power on Pc in eq 5


        //state variables
        double molar_A;             //NA        kmol
        double molar_B;             //NB        kmol
        double molar_C;             //NC        kmol
        double molar_D;             //ND        kmol
        double f1_valve_pos;        //X1        percentage
        double f2_valve_pos;        //X2        percentage
        double purge_valve_pos;     //X3        percentage
        double product_valve_pos;   //X4        percentage
        bool   e_stop;

        //physical fault injection
        //slew rate faults: max valve travel [%/h]; 0 = no fault (instant, healthy)
        double f1_slew_rate;
        double f2_slew_rate;
        double purge_slew_rate;
        double product_slew_rate;
        //fouling faults: fraction of nominal Cv still achievable; 1.0 = no fault (healthy)
        double f1_cv_scale;
        double f2_cv_scale;
        double purge_cv_scale;
        double product_cv_scale;
        //stuck faults: actuator frozen at its current position, ignoring setpoint
        //and slew rate entirely; false = no fault (healthy)
        bool f1_stuck;
        bool f2_stuck;
        bool purge_stuck;
        bool product_stuck;
        //sensor freeze faults: when set, the corresponding measured_* value
        //below stops tracking its true output and holds its last value,
        //mirroring a real transmitter whose signal loop stops updating (e.g. a
        //plugged impulse line) while the process keeps moving. The true
        //outputs are never touched by these flags - only the measured_* copy.
        bool tank_pressure_freeze;
        bool tank_level_freeze;
        bool f1_flow_freeze;
        bool f2_flow_freeze;
        bool purge_flow_freeze;
        bool product_flow_freeze;
        bool analyzer_freeze;
        //measured (possibly faulted) sensor values - this is what Modbus
        //devices report; they have no fault logic of their own and simply
        //relay these values as-is
        double measured_pressure;
        double measured_liquid_level;
        double measured_f1_flow;
        double measured_f2_flow;
        double measured_purge_flow;
        double measured_product_flow;
        double measured_A_in_purge;
        double measured_B_in_purge;
        double measured_C_in_purge;

        //state var derivatives
        double dxdt_molar_A;             //NA        kmol
        double dxdt_molar_B;             //NB        kmol
        double dxdt_molar_C;             //NC        kmol
        double dxdt_molar_D;             //ND        kmol       
        
        //outputs
        double f1_flow;             //F1        kmol h-1
        double f2_flow;             //F2        kmol h-1
        double purge_flow;          //F3        kmol h-1
        double product_flow;        //F4        kmol h-1
        double pressure;            //P         kmol h-1
        double liquid_level;        //VL        percentage
        double A_in_purge;          //yA3       kmol h-1
        double B_in_purge;          //yB3       kmol h-1
        double C_in_purge;          //yC3       kmol h-1
        double ymeas[4];            //used for delayed sampling
        double ylast[4];            //used for delayed sampling
        double cost;                //C         kmol h-1
    public:
        void steady_state();
        TE();
        void update(Json::Value inputs);
        void print_outputs();
        Json::Value get_state_json() ;
        
};



#endif
