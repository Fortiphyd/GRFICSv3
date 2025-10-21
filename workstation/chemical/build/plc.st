TYPE
  LOGLEVEL : (CRITICAL, WARNING, INFO, DEBUG) := INFO;
END_TYPE

FUNCTION_BLOCK LOGGER
  VAR_INPUT
    TRIG : BOOL;
    MSG : STRING;
    LEVEL : LOGLEVEL := INFO;
  END_VAR
  VAR
    TRIG0 : BOOL;
  END_VAR

  IF TRIG AND NOT TRIG0 THEN
  {{
   LogMessage(GetFbVar(LEVEL),(char*)GetFbVar(MSG, .body),GetFbVar(MSG, .len));
  }}
  END_IF;
  TRIG0:=TRIG;
END_FUNCTION_BLOCK


FUNCTION scale_to_real : REAL
  VAR_INPUT
    raw_input_value : UINT := 0;
  END_VAR
  VAR_OUTPUT
    scaled_real : REAL := 0.0;
  END_VAR
  VAR_INPUT
    real_max : REAL := 0.0;
    real_min : REAL := 0.0;
  END_VAR
  VAR
    raw_max : UINT := 65535;
    raw_min : UINT := 0;
    rate : REAL := 1.0;
    offset : REAL := 1.0;
  END_VAR

  rate := (real_max - real_min) / UINT_TO_REAL(raw_max - raw_min);
  offset := real_min - UINT_TO_REAL(raw_min)*rate;
  scaled_real := UINT_TO_REAL(raw_input_value)*rate + offset;
  scale_to_real := scaled_real;
END_FUNCTION

FUNCTION scale_to_uint : UINT
  VAR_INPUT
    real_in : REAL := 0.0;
  END_VAR
  VAR_OUTPUT
    uint_out : UINT := 0;
  END_VAR

  uint_out := REAL_TO_UINT((real_in / 100.0) * 65535.0);
  scale_to_uint := uint_out;
END_FUNCTION

FUNCTION control : UINT
  VAR
    current_value_real : REAL := 0.0;
    valve_pos_limited : REAL := 0.0;
    setpoint_real : REAL := 0.0;
    pos_update_real : REAL := 0.0;
    valve_pos_real : REAL := 0.0;
  END_VAR
  VAR_OUTPUT
    valve_pos : UINT := 0;
  END_VAR
  VAR_INPUT
    rmax : REAL := 0.0;
    rmin : REAL := 0.0;
    k : REAL := 0.0;
    current_value : UINT := 0;
    setpoint : UINT := 0;
    current_pos : UINT := 0;
  END_VAR

  current_value_real := scale_to_real(raw_input_value := current_value, real_max := rmax, real_min := rmin);

  setpoint_real := scale_to_real(raw_input_value := setpoint, real_max := rmax, real_min := rmin);

  pos_update_real := (setpoint_real - current_value_real) * k;

  valve_pos_real := scale_to_real(raw_input_value := current_pos, real_max := 100.0, real_min := 0.0);

  valve_pos_limited := LIMIT(0.0, valve_pos_real + pos_update_real, 100.0);


  control := scale_to_uint(real_in:= valve_pos_limited);
END_FUNCTION

FUNCTION pressure_override : UINT
  VAR_INPUT
    pressure_in : UINT := 0;
  END_VAR
  VAR
    override_sp_real : REAL := 2900.0;
    sp_update : REAL := 0.0;
  END_VAR
  VAR_INPUT
    current_sp : UINT := 0;
  END_VAR
  VAR
    product_sp_real : REAL := 0.0;
  END_VAR
  VAR_OUTPUT
    product_sp : UINT := 0;
  END_VAR
  VAR_INPUT
    override_sp : UINT := 0;
  END_VAR
  VAR
    curr_sp_real : REAL := 0.0;
    pressure_real : REAL := 0.0;
  END_VAR

  pressure_real := scale_to_real(raw_input_value := pressure_in, real_max := 3200.0, real_min := 0.0);

  sp_update := MAX(0.0, 1.0 * (override_sp_real - pressure_real));

  curr_sp_real := scale_to_real(raw_input_value := current_sp, real_max := 500.0, real_min := 0.0);

  product_sp_real := curr_sp_real + sp_update;

  product_sp := REAL_TO_UINT(65535.0 * (product_sp_real / 500.0));

  pressure_override := product_sp;
END_FUNCTION

PROGRAM main1
  VAR
    product_flow_setpoint AT %MW0 : UINT := 13107;
    a_setpoint AT %MW1 : UINT := 30801;
    pressure_sp AT %MW2 : UINT := 55295;
    override_sp AT %MW3 : UINT := 31675;
    level_sp AT %MW4 : UINT := 28835;
    f1_valve_pos AT %IW100 : UINT;
    f1_flow AT %IW101 : UINT;
    f2_valve_pos AT %IW102 : UINT;
    f2_flow AT %IW103 : UINT;
    purge_valve_pos AT %IW104 : UINT;
    purge_flow AT %IW105 : UINT;
    product_valve_pos AT %IW106 : UINT;
    product_flow AT %IW107 : UINT;
    pressure AT %IW108 : UINT;
    level AT %IW109 : UINT;
    a_in_purge AT %IW110 : UINT;
    b_in_purge AT %IW111 : UINT;
    c_in_purge AT %IW112 : UINT;
    f1_valve_sp AT %QW100 : UINT;
    f2_valve_sp AT %QW101 : UINT;
    purge_valve_sp AT %QW102 : UINT;
    product_valve_sp AT %QW103 : UINT;
  END_VAR
  VAR
    product_valve_safe : UINT := 0;
    purge_valve_safe : UINT := 65535;
    f1_valve_safe : UINT := 0;
    f2_valve_safe : UINT := 0;
  END_VAR
  VAR
    hmi_pressure AT %MW20 : INT;
    hmi_level AT %MW21 : INT;
    hmi_f1_valve_pos AT %MW22 : INT;
    hmi_f1_flow AT %MW23 : INT;
    hmi_f2_valve_pos AT %MW24 : INT;
    hmi_f2_flow AT %MW25 : INT;
    hmi_purge_valve AT %MW26 : INT;
    hmi_purge_flow AT %MW27 : INT;
    hmi_product_valve AT %MW28 : INT;
    hmi_product_flow AT %MW29 : INT;
  END_VAR
  VAR
    test_real : REAL;
  END_VAR
  VAR
    test_int AT %MW30 : UINT;
  END_VAR



  f1_valve_sp := control(
       current_value := product_flow,
       setpoint := product_flow_setpoint,
       current_pos := f1_valve_pos,
       k := 20.0,
       rmax := 500.0,
       rmin := 0.0);
       
  purge_valve_sp := control(
       current_value := pressure,
       setpoint := pressure_sp,
       current_pos := purge_valve_pos,
       k := -20.0,
       rmax := 3200.0,
       rmin := 0.0);
       
  f2_valve_sp := control(
       current_value := a_in_purge,
       setpoint := a_setpoint,
       current_pos := f2_valve_pos,
       k := 1.0,
       rmax := 100.0,
       rmin := 0.0);
       
  product_flow_setpoint := pressure_override(
       pressure_in := pressure,
       current_sp := product_flow_setpoint,
       override_sp := override_sp);
     
  product_valve_sp := control(
       current_value := level,
       setpoint := level_sp,
       current_pos := product_valve_pos,
       k := -10.0,
       rmax := 100.0,
       rmin := 0.0);  
       
  f1_valve_pos := LIMIT(0, f1_valve_pos, 65535);
  f1_flow := LIMIT(0, f1_flow, 65535);
  f2_valve_pos := LIMIT(0, f2_valve_pos, 65535);
  f2_flow := LIMIT(0, f2_flow, 65535);
  purge_valve_pos := LIMIT(0, purge_valve_pos, 65535);
  purge_flow := LIMIT(0, purge_flow, 65535);
  product_valve_pos := LIMIT(0, product_valve_pos, 65535);
  product_flow := LIMIT(0, product_flow, 65535);
  a_in_purge := LIMIT(0, a_in_purge, 65535);
  b_in_purge := LIMIT(0, b_in_purge, 65535);
  c_in_purge := LIMIT(0, c_in_purge, 65535);
  a_setpoint := LIMIT(0, a_setpoint, 65535);
  level := LIMIT(0, level, 65535);
  level_sp := LIMIT(0, level_sp, 65535);
  pressure_sp := LIMIT(0, pressure_sp, 65535);

  product_flow_setpoint := 30000;
END_PROGRAM

FUNCTION_BLOCK complex
  VAR
    IN : INT;
    N : BYTE;
    OUT : INT;
    ERR : BYTE;
    I : INT;
    a : INT;
  END_VAR

  IF N > 1 AND N < 12 THEN
      ERR:=0;
      (* IF IN < P[0].X THEN *)
      IF IN < a THEN
        ERR := 2;
        OUT := a;
      (* ELSIF IN > P[N-1].X THEN *)
      ELSIF IN > a THEN
        ERR := 2;
        OUT := a;
      ELSE
        FOR I:=1 TO a-1 DO
          (* IF P[I-1].X >= P[I].X THEN *)
          IF a >= a THEN
            ERR:=1;
            EXIT;
          END_IF;
          (* IF IN <= P[I].X THEN *)
          IF IN <= a THEN
            EXIT;
          END_IF;
        END_FOR;
        IF ERR = 0 THEN
          (* OUT := DINT_TO_INT(P[I].Y - (P[I].X-IN) * (P[I].Y-P[I-1].Y) / (P[I].X-P[I-1].X)); *)
          OUT := (a - (a - IN) * (a - a) / (a - a));
        ELSE
          OUT:=0;
        END_IF;
      END_IF;
    ELSE
      ERR := 4;
    END_IF;
END_FUNCTION_BLOCK


CONFIGURATION Config0

  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#20ms,PRIORITY := 0);
    PROGRAM instance0 WITH task0 : main1;
  END_RESOURCE
END_CONFIGURATION
