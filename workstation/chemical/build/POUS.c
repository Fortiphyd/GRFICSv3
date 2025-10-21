void LOGGER_init__(LOGGER *data__, BOOL retain) {
  __INIT_VAR(data__->EN,__BOOL_LITERAL(TRUE),retain)
  __INIT_VAR(data__->ENO,__BOOL_LITERAL(TRUE),retain)
  __INIT_VAR(data__->TRIG,__BOOL_LITERAL(FALSE),retain)
  __INIT_VAR(data__->MSG,__STRING_LITERAL(0,""),retain)
  __INIT_VAR(data__->LEVEL,LOGLEVEL__INFO,retain)
  __INIT_VAR(data__->TRIG0,__BOOL_LITERAL(FALSE),retain)
}

// Code part
void LOGGER_body__(LOGGER *data__) {
  // Control execution
  if (!__GET_VAR(data__->EN)) {
    __SET_VAR(data__->,ENO,,__BOOL_LITERAL(FALSE));
    return;
  }
  else {
    __SET_VAR(data__->,ENO,,__BOOL_LITERAL(TRUE));
  }
  // Initialise TEMP variables

  if ((__GET_VAR(data__->TRIG,) && !(__GET_VAR(data__->TRIG0,)))) {
    #define GetFbVar(var,...) __GET_VAR(data__->var,__VA_ARGS__)
    #define SetFbVar(var,val,...) __SET_VAR(data__->,var,__VA_ARGS__,val)

   LogMessage(GetFbVar(LEVEL),(char*)GetFbVar(MSG, .body),GetFbVar(MSG, .len));
  
    #undef GetFbVar
    #undef SetFbVar
;
  };
  __SET_VAR(data__->,TRIG0,,__GET_VAR(data__->TRIG,));

  goto __end;

__end:
  return;
} // LOGGER_body__() 





// FUNCTION
REAL SCALE_TO_REAL(
  BOOL EN, 
  BOOL *__ENO, 
  UINT RAW_INPUT_VALUE, 
  REAL *__SCALED_REAL, 
  REAL REAL_MAX, 
  REAL REAL_MIN)
{
  BOOL ENO = __BOOL_LITERAL(TRUE);
  REAL SCALED_REAL = 0.0;
  UINT RAW_MAX = 65535;
  UINT RAW_MIN = 0;
  REAL RATE = 1.0;
  REAL OFFSET = 1.0;
  REAL SCALE_TO_REAL = 0;

  // Control execution
  if (!EN) {
    if (__ENO != NULL) {
      *__ENO = __BOOL_LITERAL(FALSE);
    }
    return SCALE_TO_REAL;
  }
  RATE = ((REAL_MAX - REAL_MIN) / UINT_TO_REAL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)(RAW_MAX - RAW_MIN)));
  OFFSET = (REAL_MIN - (UINT_TO_REAL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)RAW_MIN) * RATE));
  SCALED_REAL = ((UINT_TO_REAL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)RAW_INPUT_VALUE) * RATE) + OFFSET);
  SCALE_TO_REAL = SCALED_REAL;

  goto __end;

__end:
  if (__ENO != NULL) {
    *__ENO = ENO;
  }
  if (__SCALED_REAL != NULL) {
    *__SCALED_REAL = SCALED_REAL;
  }
  return SCALE_TO_REAL;
}


// FUNCTION
UINT SCALE_TO_UINT(
  BOOL EN, 
  BOOL *__ENO, 
  REAL REAL_IN, 
  UINT *__UINT_OUT)
{
  BOOL ENO = __BOOL_LITERAL(TRUE);
  UINT UINT_OUT = 0;
  UINT SCALE_TO_UINT = 0;

  // Control execution
  if (!EN) {
    if (__ENO != NULL) {
      *__ENO = __BOOL_LITERAL(FALSE);
    }
    return SCALE_TO_UINT;
  }
  UINT_OUT = REAL_TO_UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (REAL)((REAL_IN / 100.0) * 65535.0));
  SCALE_TO_UINT = UINT_OUT;

  goto __end;

__end:
  if (__ENO != NULL) {
    *__ENO = ENO;
  }
  if (__UINT_OUT != NULL) {
    *__UINT_OUT = UINT_OUT;
  }
  return SCALE_TO_UINT;
}


// FUNCTION
UINT CONTROL(
  BOOL EN, 
  BOOL *__ENO, 
  UINT *__VALVE_POS, 
  REAL RMAX, 
  REAL RMIN, 
  REAL K, 
  UINT CURRENT_VALUE, 
  UINT SETPOINT, 
  UINT CURRENT_POS)
{
  BOOL ENO = __BOOL_LITERAL(TRUE);
  REAL CURRENT_VALUE_REAL = 0.0;
  REAL VALVE_POS_LIMITED = 0.0;
  REAL SETPOINT_REAL = 0.0;
  REAL POS_UPDATE_REAL = 0.0;
  REAL VALVE_POS_REAL = 0.0;
  UINT VALVE_POS = 0;
  UINT CONTROL = 0;

  // Control execution
  if (!EN) {
    if (__ENO != NULL) {
      *__ENO = __BOOL_LITERAL(FALSE);
    }
    return CONTROL;
  }
  CURRENT_VALUE_REAL = SCALE_TO_REAL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)CURRENT_VALUE,
    NULL,
    (REAL)RMAX,
    (REAL)RMIN);
  SETPOINT_REAL = SCALE_TO_REAL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)SETPOINT,
    NULL,
    (REAL)RMAX,
    (REAL)RMIN);
  POS_UPDATE_REAL = ((SETPOINT_REAL - CURRENT_VALUE_REAL) * K);
  VALVE_POS_REAL = SCALE_TO_REAL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)CURRENT_POS,
    NULL,
    (REAL)100.0,
    (REAL)0.0);
  VALVE_POS_LIMITED = LIMIT__REAL__REAL__REAL__REAL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (REAL)0.0,
    (REAL)(VALVE_POS_REAL + POS_UPDATE_REAL),
    (REAL)100.0);
  CONTROL = SCALE_TO_UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (REAL)VALVE_POS_LIMITED,
    NULL);

  goto __end;

__end:
  if (__ENO != NULL) {
    *__ENO = ENO;
  }
  if (__VALVE_POS != NULL) {
    *__VALVE_POS = VALVE_POS;
  }
  return CONTROL;
}


// FUNCTION
UINT PRESSURE_OVERRIDE(
  BOOL EN, 
  BOOL *__ENO, 
  UINT PRESSURE_IN, 
  UINT CURRENT_SP, 
  UINT *__PRODUCT_SP, 
  UINT OVERRIDE_SP)
{
  BOOL ENO = __BOOL_LITERAL(TRUE);
  REAL OVERRIDE_SP_REAL = 2900.0;
  REAL SP_UPDATE = 0.0;
  REAL PRODUCT_SP_REAL = 0.0;
  UINT PRODUCT_SP = 0;
  REAL CURR_SP_REAL = 0.0;
  REAL PRESSURE_REAL = 0.0;
  UINT PRESSURE_OVERRIDE = 0;

  // Control execution
  if (!EN) {
    if (__ENO != NULL) {
      *__ENO = __BOOL_LITERAL(FALSE);
    }
    return PRESSURE_OVERRIDE;
  }
  PRESSURE_REAL = SCALE_TO_REAL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)PRESSURE_IN,
    NULL,
    (REAL)3200.0,
    (REAL)0.0);
  SP_UPDATE = MAX__REAL__REAL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)2,
    (REAL)0.0,
    (REAL)(1.0 * (OVERRIDE_SP_REAL - PRESSURE_REAL)));
  CURR_SP_REAL = SCALE_TO_REAL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)CURRENT_SP,
    NULL,
    (REAL)500.0,
    (REAL)0.0);
  PRODUCT_SP_REAL = (CURR_SP_REAL + SP_UPDATE);
  PRODUCT_SP = REAL_TO_UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (REAL)(65535.0 * (PRODUCT_SP_REAL / 500.0)));
  PRESSURE_OVERRIDE = PRODUCT_SP;

  goto __end;

__end:
  if (__ENO != NULL) {
    *__ENO = ENO;
  }
  if (__PRODUCT_SP != NULL) {
    *__PRODUCT_SP = PRODUCT_SP;
  }
  return PRESSURE_OVERRIDE;
}


void MAIN1_init__(MAIN1 *data__, BOOL retain) {
  __INIT_LOCATED(UINT,__MW0,data__->PRODUCT_FLOW_SETPOINT,retain)
  __INIT_LOCATED_VALUE(data__->PRODUCT_FLOW_SETPOINT,13107)
  __INIT_LOCATED(UINT,__MW1,data__->A_SETPOINT,retain)
  __INIT_LOCATED_VALUE(data__->A_SETPOINT,30801)
  __INIT_LOCATED(UINT,__MW2,data__->PRESSURE_SP,retain)
  __INIT_LOCATED_VALUE(data__->PRESSURE_SP,55295)
  __INIT_LOCATED(UINT,__MW3,data__->OVERRIDE_SP,retain)
  __INIT_LOCATED_VALUE(data__->OVERRIDE_SP,31675)
  __INIT_LOCATED(UINT,__MW4,data__->LEVEL_SP,retain)
  __INIT_LOCATED_VALUE(data__->LEVEL_SP,28835)
  __INIT_LOCATED(UINT,__IW100,data__->F1_VALVE_POS,retain)
  __INIT_LOCATED_VALUE(data__->F1_VALVE_POS,0)
  __INIT_LOCATED(UINT,__IW101,data__->F1_FLOW,retain)
  __INIT_LOCATED_VALUE(data__->F1_FLOW,0)
  __INIT_LOCATED(UINT,__IW102,data__->F2_VALVE_POS,retain)
  __INIT_LOCATED_VALUE(data__->F2_VALVE_POS,0)
  __INIT_LOCATED(UINT,__IW103,data__->F2_FLOW,retain)
  __INIT_LOCATED_VALUE(data__->F2_FLOW,0)
  __INIT_LOCATED(UINT,__IW104,data__->PURGE_VALVE_POS,retain)
  __INIT_LOCATED_VALUE(data__->PURGE_VALVE_POS,0)
  __INIT_LOCATED(UINT,__IW105,data__->PURGE_FLOW,retain)
  __INIT_LOCATED_VALUE(data__->PURGE_FLOW,0)
  __INIT_LOCATED(UINT,__IW106,data__->PRODUCT_VALVE_POS,retain)
  __INIT_LOCATED_VALUE(data__->PRODUCT_VALVE_POS,0)
  __INIT_LOCATED(UINT,__IW107,data__->PRODUCT_FLOW,retain)
  __INIT_LOCATED_VALUE(data__->PRODUCT_FLOW,0)
  __INIT_LOCATED(UINT,__IW108,data__->PRESSURE,retain)
  __INIT_LOCATED_VALUE(data__->PRESSURE,0)
  __INIT_LOCATED(UINT,__IW109,data__->LEVEL,retain)
  __INIT_LOCATED_VALUE(data__->LEVEL,0)
  __INIT_LOCATED(UINT,__IW110,data__->A_IN_PURGE,retain)
  __INIT_LOCATED_VALUE(data__->A_IN_PURGE,0)
  __INIT_LOCATED(UINT,__IW111,data__->B_IN_PURGE,retain)
  __INIT_LOCATED_VALUE(data__->B_IN_PURGE,0)
  __INIT_LOCATED(UINT,__IW112,data__->C_IN_PURGE,retain)
  __INIT_LOCATED_VALUE(data__->C_IN_PURGE,0)
  __INIT_LOCATED(UINT,__QW100,data__->F1_VALVE_SP,retain)
  __INIT_LOCATED_VALUE(data__->F1_VALVE_SP,0)
  __INIT_LOCATED(UINT,__QW101,data__->F2_VALVE_SP,retain)
  __INIT_LOCATED_VALUE(data__->F2_VALVE_SP,0)
  __INIT_LOCATED(UINT,__QW102,data__->PURGE_VALVE_SP,retain)
  __INIT_LOCATED_VALUE(data__->PURGE_VALVE_SP,0)
  __INIT_LOCATED(UINT,__QW103,data__->PRODUCT_VALVE_SP,retain)
  __INIT_LOCATED_VALUE(data__->PRODUCT_VALVE_SP,0)
  __INIT_VAR(data__->PRODUCT_VALVE_SAFE,0,retain)
  __INIT_VAR(data__->PURGE_VALVE_SAFE,65535,retain)
  __INIT_VAR(data__->F1_VALVE_SAFE,0,retain)
  __INIT_VAR(data__->F2_VALVE_SAFE,0,retain)
  __INIT_LOCATED(INT,__MW20,data__->HMI_PRESSURE,retain)
  __INIT_LOCATED_VALUE(data__->HMI_PRESSURE,0)
  __INIT_LOCATED(INT,__MW21,data__->HMI_LEVEL,retain)
  __INIT_LOCATED_VALUE(data__->HMI_LEVEL,0)
  __INIT_LOCATED(INT,__MW22,data__->HMI_F1_VALVE_POS,retain)
  __INIT_LOCATED_VALUE(data__->HMI_F1_VALVE_POS,0)
  __INIT_LOCATED(INT,__MW23,data__->HMI_F1_FLOW,retain)
  __INIT_LOCATED_VALUE(data__->HMI_F1_FLOW,0)
  __INIT_LOCATED(INT,__MW24,data__->HMI_F2_VALVE_POS,retain)
  __INIT_LOCATED_VALUE(data__->HMI_F2_VALVE_POS,0)
  __INIT_LOCATED(INT,__MW25,data__->HMI_F2_FLOW,retain)
  __INIT_LOCATED_VALUE(data__->HMI_F2_FLOW,0)
  __INIT_LOCATED(INT,__MW26,data__->HMI_PURGE_VALVE,retain)
  __INIT_LOCATED_VALUE(data__->HMI_PURGE_VALVE,0)
  __INIT_LOCATED(INT,__MW27,data__->HMI_PURGE_FLOW,retain)
  __INIT_LOCATED_VALUE(data__->HMI_PURGE_FLOW,0)
  __INIT_LOCATED(INT,__MW28,data__->HMI_PRODUCT_VALVE,retain)
  __INIT_LOCATED_VALUE(data__->HMI_PRODUCT_VALVE,0)
  __INIT_LOCATED(INT,__MW29,data__->HMI_PRODUCT_FLOW,retain)
  __INIT_LOCATED_VALUE(data__->HMI_PRODUCT_FLOW,0)
  __INIT_VAR(data__->TEST_REAL,0,retain)
  __INIT_LOCATED(UINT,__MW30,data__->TEST_INT,retain)
  __INIT_LOCATED_VALUE(data__->TEST_INT,0)
}

// Code part
void MAIN1_body__(MAIN1 *data__) {
  // Initialise TEMP variables

  __SET_LOCATED(data__->,F1_VALVE_SP,,CONTROL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    NULL,
    (REAL)500.0,
    (REAL)0.0,
    (REAL)20.0,
    (UINT)__GET_LOCATED(data__->PRODUCT_FLOW,),
    (UINT)__GET_LOCATED(data__->PRODUCT_FLOW_SETPOINT,),
    (UINT)__GET_LOCATED(data__->F1_VALVE_POS,)));
  __SET_LOCATED(data__->,PURGE_VALVE_SP,,CONTROL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    NULL,
    (REAL)3200.0,
    (REAL)0.0,
    (REAL)-20.0,
    (UINT)__GET_LOCATED(data__->PRESSURE,),
    (UINT)__GET_LOCATED(data__->PRESSURE_SP,),
    (UINT)__GET_LOCATED(data__->PURGE_VALVE_POS,)));
  __SET_LOCATED(data__->,F2_VALVE_SP,,CONTROL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    NULL,
    (REAL)100.0,
    (REAL)0.0,
    (REAL)1.0,
    (UINT)__GET_LOCATED(data__->A_IN_PURGE,),
    (UINT)__GET_LOCATED(data__->A_SETPOINT,),
    (UINT)__GET_LOCATED(data__->F2_VALVE_POS,)));
  __SET_LOCATED(data__->,PRODUCT_FLOW_SETPOINT,,PRESSURE_OVERRIDE(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)__GET_LOCATED(data__->PRESSURE,),
    (UINT)__GET_LOCATED(data__->PRODUCT_FLOW_SETPOINT,),
    NULL,
    (UINT)__GET_LOCATED(data__->OVERRIDE_SP,)));
  __SET_LOCATED(data__->,PRODUCT_VALVE_SP,,CONTROL(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    NULL,
    (REAL)100.0,
    (REAL)0.0,
    (REAL)-10.0,
    (UINT)__GET_LOCATED(data__->LEVEL,),
    (UINT)__GET_LOCATED(data__->LEVEL_SP,),
    (UINT)__GET_LOCATED(data__->PRODUCT_VALVE_POS,)));
  __SET_LOCATED(data__->,F1_VALVE_POS,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->F1_VALVE_POS,),
    (UINT)65535));
  __SET_LOCATED(data__->,F1_FLOW,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->F1_FLOW,),
    (UINT)65535));
  __SET_LOCATED(data__->,F2_VALVE_POS,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->F2_VALVE_POS,),
    (UINT)65535));
  __SET_LOCATED(data__->,F2_FLOW,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->F2_FLOW,),
    (UINT)65535));
  __SET_LOCATED(data__->,PURGE_VALVE_POS,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->PURGE_VALVE_POS,),
    (UINT)65535));
  __SET_LOCATED(data__->,PURGE_FLOW,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->PURGE_FLOW,),
    (UINT)65535));
  __SET_LOCATED(data__->,PRODUCT_VALVE_POS,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->PRODUCT_VALVE_POS,),
    (UINT)65535));
  __SET_LOCATED(data__->,PRODUCT_FLOW,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->PRODUCT_FLOW,),
    (UINT)65535));
  __SET_LOCATED(data__->,A_IN_PURGE,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->A_IN_PURGE,),
    (UINT)65535));
  __SET_LOCATED(data__->,B_IN_PURGE,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->B_IN_PURGE,),
    (UINT)65535));
  __SET_LOCATED(data__->,C_IN_PURGE,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->C_IN_PURGE,),
    (UINT)65535));
  __SET_LOCATED(data__->,A_SETPOINT,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->A_SETPOINT,),
    (UINT)65535));
  __SET_LOCATED(data__->,LEVEL,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->LEVEL,),
    (UINT)65535));
  __SET_LOCATED(data__->,LEVEL_SP,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->LEVEL_SP,),
    (UINT)65535));
  __SET_LOCATED(data__->,PRESSURE_SP,,LIMIT__UINT__UINT__UINT__UINT(
    (BOOL)__BOOL_LITERAL(TRUE),
    NULL,
    (UINT)0,
    (UINT)__GET_LOCATED(data__->PRESSURE_SP,),
    (UINT)65535));
  __SET_LOCATED(data__->,PRODUCT_FLOW_SETPOINT,,30000);

  goto __end;

__end:
  return;
} // MAIN1_body__() 





void COMPLEX_init__(COMPLEX *data__, BOOL retain) {
  __INIT_VAR(data__->EN,__BOOL_LITERAL(TRUE),retain)
  __INIT_VAR(data__->ENO,__BOOL_LITERAL(TRUE),retain)
  __INIT_VAR(data__->IN,0,retain)
  __INIT_VAR(data__->N,0,retain)
  __INIT_VAR(data__->OUT,0,retain)
  __INIT_VAR(data__->ERR,0,retain)
  __INIT_VAR(data__->I,0,retain)
  __INIT_VAR(data__->A,0,retain)
}

// Code part
void COMPLEX_body__(COMPLEX *data__) {
  // Control execution
  if (!__GET_VAR(data__->EN)) {
    __SET_VAR(data__->,ENO,,__BOOL_LITERAL(FALSE));
    return;
  }
  else {
    __SET_VAR(data__->,ENO,,__BOOL_LITERAL(TRUE));
  }
  // Initialise TEMP variables

  if (((__GET_VAR(data__->N,) > 1) && (__GET_VAR(data__->N,) < 12))) {
    __SET_VAR(data__->,ERR,,0);
    if ((__GET_VAR(data__->IN,) < __GET_VAR(data__->A,))) {
      __SET_VAR(data__->,ERR,,2);
      __SET_VAR(data__->,OUT,,__GET_VAR(data__->A,));
    } else if ((__GET_VAR(data__->IN,) > __GET_VAR(data__->A,))) {
      __SET_VAR(data__->,ERR,,2);
      __SET_VAR(data__->,OUT,,__GET_VAR(data__->A,));
    } else {
      /* FOR ... */
      __SET_VAR(data__->,I,,1);
      {
        int __do_increment = 0;
        while(1) {
          if(__do_increment){
            /* BY ... (of FOR loop) */
            __SET_VAR(data__->,I,,(__GET_VAR(data__->I,) + 1));
          } else __do_increment = 1;
          if(__GET_VAR(data__->I,) <= (__GET_VAR(data__->A,) - 1)          ){
            if ((__GET_VAR(data__->A,) >= __GET_VAR(data__->A,))) {
              __SET_VAR(data__->,ERR,,1);
              break;
            };
            if ((__GET_VAR(data__->IN,) <= __GET_VAR(data__->A,))) {
              break;
            };
          }else break;
        }
      } /* END_FOR */;
      if ((__GET_VAR(data__->ERR,) == 0)) {
        __SET_VAR(data__->,OUT,,(__GET_VAR(data__->A,) - (((__GET_VAR(data__->A,) - __GET_VAR(data__->IN,)) * (__GET_VAR(data__->A,) - __GET_VAR(data__->A,))) / (__GET_VAR(data__->A,) - __GET_VAR(data__->A,)))));
      } else {
        __SET_VAR(data__->,OUT,,0);
      };
    };
  } else {
    __SET_VAR(data__->,ERR,,4);
  };

  goto __end;

__end:
  return;
} // COMPLEX_body__() 





