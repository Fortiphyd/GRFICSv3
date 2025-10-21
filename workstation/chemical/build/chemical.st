FUNCTION control : UINT
  VAR
    real_val : REAL := 0.0;
    valve_pos_limited : REAL := 0.0;
    sp_real : REAL := 0.0;
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
    current_val : UINT := 0;
    setpoint : UINT := 0;
    curr_pos : UINT := 0;
  END_VAR

  real_val := (UINT_TO_REAL(current_val) / 65535.0) * (rmax - rmin) + rmin;
  sp_real := (UINT_TO_REAL(setpoint) / 65535.0) * (rmax - rmin) + rmin;
  pos_update_real := (sp_real - real_val) * k;
  valve_pos_real := (UINT_TO_REAL(curr_pos) / 65535.0) * 100.0;
  valve_pos_limited := LIMIT(rmin, valve_pos_real - pos_update_real, rmax);
  control := Real_to_Uint((valve_pos_limited) / (100.0) * 65535.0);
END_FUNCTION

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
    rate : REAL := 0.0;
    offset : REAL := 0.0;
  END_VAR

  rate := (real_max - real_min) / UINT_TO_REAL(raw_max - raw_min);
  offset := real_min - UINT_TO_REAL(raw_min)*rate;
  scaled_real := UINT_TO_REAL(raw_input_value)*rate + offset;
END_FUNCTION

FUNCTION pressure_override : UINT
  VAR_INPUT
    pressure_in : UINT := 0;
  END_VAR
  VAR
    override_sp_real : REAL := 0.0;
    sp_update : REAL := 0.0;
  END_VAR
  VAR_INPUT
    curr_sp : UINT := 0;
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
  override_sp_real := scale_to_real(raw_input_value := override_sp, real_max := 100.0, real_min := 0.0);
  sp_update := MAX(0.0, 1.0 * (override_sp_real - pressure_real));
  curr_sp_real := scale_to_real(raw_input_value := curr_sp, real_max := 500.0, real_min := 0.0);
  product_sp_real := LIMIT(50.0, curr_sp_real + sp_update, 150.0);
  product_sp := REAL_TO_UINT(65535.0 * (product_sp_real / 500.0));
END_FUNCTION

PROGRAM main1
  VAR
    flow_set AT %MW0 : UINT := 13107;
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



  f1_valve_sp := control(
       current_val := product_flow,
       setpoint := flow_set,
       curr_pos := f1_valve_pos,
       k := 20.0,
       rmax := 500.0,
       rmin := 0.0);
       
  purge_valve_sp := control(
       current_val := pressure,
       setpoint := pressure_sp,
       curr_pos := purge_valve_pos,
       k := 20.0,
       rmax := 3200.0,
       rmin := 0.0);
       
  f2_valve_sp := control(
       current_val := a_in_purge,
       setpoint := a_setpoint,
       curr_pos := f2_valve_pos,
       k := 1.0,
       rmax := 100.0,
       rmin := 0.0);
       
  flow_set := pressure_override(
       pressure_in := pressure,
       curr_sp := flow_set,
       override_sp := override_sp);
     
  product_valve_sp := control(
       current_val := level,
       setpoint := level_sp,
       curr_pos := product_valve_pos,
       k := 10.0,
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
END_PROGRAM

FUNCTION scale_to_uint : UINT
  VAR_INPUT
    real_in : REAL := 0.0;
  END_VAR
  VAR_OUTPUT
    uint_out : UINT := 0;
  END_VAR

  uint_out := REAL_TO_UINT((real_in / 100.0) * 65535.0);
END_FUNCTION

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

(*DBG:char md5[] = "38c9dfb4cc33d6415fdfb6392351893e";*)
(*DBG:/**)
(*DBG: * This file is part of OpenPLC Runtime*)
(*DBG: **)
(*DBG: * Copyright (C) 2023 Autonomy, GP Orcullo*)
(*DBG: * Based on the work by GP Orcullo on Beremiz for uC*)
(*DBG: **)
(*DBG: * This program is free software; you can redistribute it and/or*)
(*DBG: * modify it under the terms of the GNU General Public License*)
(*DBG: * as published by the Free Software Foundation; either version 2*)
(*DBG: * of the License, or (at your option) any later version.*)
(*DBG: **)
(*DBG: * This program is distributed in the hope that it will be useful,*)
(*DBG: * but WITHOUT ANY WARRANTY; without even the implied warranty of*)
(*DBG: * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the*)
(*DBG: * GNU General Public License for more details.*)
(*DBG: **)
(*DBG: * You should have received a copy of the GNU General Public License*)
(*DBG: * along with this program; If not, see <http://www.gnu.org/licenses/>.*)
(*DBG: **)
(*DBG: */*)
(*DBG:*)
(*DBG:#include <stdbool.h>*)
(*DBG:*)
(*DBG:#include "iec_types_all.h"*)
(*DBG:#include "POUS.h"*)
(*DBG:*)
(*DBG:#define SAME_ENDIANNESS      0*)
(*DBG:#define REVERSE_ENDIANNESS   1*)
(*DBG:*)
(*DBG:uint8_t endianness;*)
(*DBG:*)
(*DBG:*)
(*DBG:extern MAIN1 RES0__INSTANCE0;*)
(*DBG:*)
(*DBG:static const struct {*)
(*DBG:    void *ptr;*)
(*DBG:    __IEC_types_enum type;*)
(*DBG:} debug_vars[] = {*)
(*DBG:    {&(RES0__INSTANCE0.FLOW_SET), UINT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.A_SETPOINT), UINT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PRESSURE_SP), UINT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.OVERRIDE_SP), UINT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.LEVEL_SP), UINT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.F1_VALVE_POS), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.F1_FLOW), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.F2_VALVE_POS), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.F2_FLOW), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PURGE_VALVE_POS), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PURGE_FLOW), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PRODUCT_VALVE_POS), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PRODUCT_FLOW), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PRESSURE), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.LEVEL), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.A_IN_PURGE), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.B_IN_PURGE), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.C_IN_PURGE), UINT_P_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.F1_VALVE_SP), UINT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.F2_VALVE_SP), UINT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PURGE_VALVE_SP), UINT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PRODUCT_VALVE_SP), UINT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PRODUCT_VALVE_SAFE), UINT_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PURGE_VALVE_SAFE), UINT_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.F1_VALVE_SAFE), UINT_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.F2_VALVE_SAFE), UINT_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.HMI_PRESSURE), INT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.HMI_LEVEL), INT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.HMI_F1_VALVE_POS), INT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.HMI_F1_FLOW), INT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.HMI_F2_VALVE_POS), INT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.HMI_F2_FLOW), INT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.HMI_PURGE_VALVE), INT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.HMI_PURGE_FLOW), INT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.HMI_PRODUCT_VALVE), INT_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.HMI_PRODUCT_FLOW), INT_O_ENUM},*)
(*DBG:};*)
(*DBG:*)
(*DBG:#define VAR_COUNT               36*)
(*DBG:*)
(*DBG:uint16_t get_var_count(void)*)
(*DBG:{*)
(*DBG:    return VAR_COUNT;*)
(*DBG:}*)
(*DBG:*)
(*DBG:size_t get_var_size(size_t idx)*)
(*DBG:{*)
(*DBG:    if (idx >= VAR_COUNT)*)
(*DBG:    {*)
(*DBG:        return 0;*)
(*DBG:    }*)
(*DBG:    switch (debug_vars[idx].type) {*)
(*DBG:    case INT_O_ENUM:*)
(*DBG:        return sizeof(INT);*)
(*DBG:    case UINT_ENUM:*)
(*DBG:    case UINT_O_ENUM:*)
(*DBG:    case UINT_P_ENUM:*)
(*DBG:        return sizeof(UINT);*)
(*DBG:    default:*)
(*DBG:        return 0;*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void *get_var_addr(size_t idx)*)
(*DBG:{*)
(*DBG:    void *ptr = debug_vars[idx].ptr;*)
(*DBG:*)
(*DBG:    switch (debug_vars[idx].type) {*)
(*DBG:    case INT_O_ENUM:*)
(*DBG:        return (void *)((((__IEC_INT_p *) ptr)->flags & __IEC_FORCE_FLAG) *)
(*DBG:                        ? &(((__IEC_INT_p *) ptr)->fvalue) *)
(*DBG:                        : ((__IEC_INT_p *) ptr)->value);*)
(*DBG:    case UINT_ENUM:*)
(*DBG:        return (void *)&((__IEC_UINT_t *) ptr)->value;*)
(*DBG:    case UINT_O_ENUM:*)
(*DBG:    case UINT_P_ENUM:*)
(*DBG:        return (void *)((((__IEC_UINT_p *) ptr)->flags & __IEC_FORCE_FLAG) *)
(*DBG:                        ? &(((__IEC_UINT_p *) ptr)->fvalue) *)
(*DBG:                        : ((__IEC_UINT_p *) ptr)->value);*)
(*DBG:    default:*)
(*DBG:        return 0;*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void force_var(size_t idx, bool forced, void *val)*)
(*DBG:{*)
(*DBG:    void *ptr = debug_vars[idx].ptr;*)
(*DBG:*)
(*DBG:    if (forced) {*)
(*DBG:        size_t var_size = get_var_size(idx);*)
(*DBG:        switch (debug_vars[idx].type) {*)
(*DBG:        case INT_O_ENUM: {*)
(*DBG:            memcpy((((__IEC_INT_p *) ptr)->value), val, var_size);*)
(*DBG:            //*(((__IEC_INT_p *) ptr)->value) = *((INT *) val);*)
(*DBG:            ((__IEC_INT_p *) ptr)->flags |= __IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:        case UINT_ENUM: {*)
(*DBG:            memcpy(&((__IEC_UINT_t *) ptr)->value, val, var_size);*)
(*DBG:            //((__IEC_UINT_t *) ptr)->value = *((UINT *) val);*)
(*DBG:            ((__IEC_UINT_t *) ptr)->flags |= __IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:        case UINT_O_ENUM: {*)
(*DBG:            memcpy((((__IEC_UINT_p *) ptr)->value), val, var_size);*)
(*DBG:            //*(((__IEC_UINT_p *) ptr)->value) = *((UINT *) val);*)
(*DBG:            ((__IEC_UINT_p *) ptr)->flags |= __IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:        case UINT_P_ENUM: {*)
(*DBG:            memcpy(&((__IEC_UINT_p *) ptr)->fvalue, val, var_size);*)
(*DBG:            //((__IEC_UINT_p *) ptr)->fvalue = *((UINT *) val);*)
(*DBG:            ((__IEC_UINT_p *) ptr)->flags |= __IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:        default:*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:    } else {*)
(*DBG:        switch (debug_vars[idx].type) {*)
(*DBG:        case INT_O_ENUM:*)
(*DBG:            ((__IEC_INT_p *) ptr)->flags &= ~__IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        case UINT_ENUM:*)
(*DBG:            ((__IEC_UINT_t *) ptr)->flags &= ~__IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        case UINT_O_ENUM:*)
(*DBG:        case UINT_P_ENUM:*)
(*DBG:            ((__IEC_UINT_p *) ptr)->flags &= ~__IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        default:*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void swap_bytes(void *ptr, size_t size) *)
(*DBG:{*)
(*DBG:    uint8_t *bytePtr = (uint8_t *)ptr;*)
(*DBG:    size_t i;*)
(*DBG:    for (i = 0; i < size / 2; ++i) *)
(*DBG:    {*)
(*DBG:        uint8_t temp = bytePtr[i];*)
(*DBG:        bytePtr[i] = bytePtr[size - 1 - i];*)
(*DBG:        bytePtr[size - 1 - i] = temp;*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void trace_reset(void)*)
(*DBG:{*)
(*DBG:    for (size_t i=0; i < VAR_COUNT; i++) *)
(*DBG:    {*)
(*DBG:        force_var(i, false, 0);*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void set_trace(size_t idx, bool forced, void *val)*)
(*DBG:{*)
(*DBG:    if (idx >= 0 && idx < VAR_COUNT) *)
(*DBG:    {*)
(*DBG:        if (endianness == REVERSE_ENDIANNESS)*)
(*DBG:        {*)
(*DBG:            // Aaaaarghhhh... Stupid AVR is Big Endian.*)
(*DBG:            swap_bytes(val, get_var_size(idx));*)
(*DBG:        }*)
(*DBG:*)
(*DBG:        force_var(idx, forced, val);*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void set_endianness(uint8_t value)*)
(*DBG:{*)
(*DBG:    if (value == SAME_ENDIANNESS || value == REVERSE_ENDIANNESS)*)
(*DBG:    {*)
(*DBG:        endianness = value;*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)