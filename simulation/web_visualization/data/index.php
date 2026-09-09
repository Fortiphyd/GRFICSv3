<?php
$address = '127.0.0.1';
$port = 55555;

// boolean fault/control fields the simulation will accept
$boolean_fields = [
    'e_stop',
    'f1_stuck', 'f2_stuck', 'purge_stuck', 'product_stuck',
];

// numeric fault/setpoint fields the simulation will accept, and their valid ranges
$numeric_fields = [
    'f1_valve_sp'      => [0.0, 100.0],
    'f2_valve_sp'      => [0.0, 100.0],
    'purge_valve_sp'   => [0.0, 100.0],
    'product_valve_sp' => [0.0, 100.0],
    'f1_slew_rate'      => [0.0, null],
    'f2_slew_rate'      => [0.0, null],
    'purge_slew_rate'   => [0.0, null],
    'product_slew_rate' => [0.0, null],
    'f1_cv_scale'      => [0.0, 1.0],
    'f2_cv_scale'      => [0.0, 1.0],
    'purge_cv_scale'   => [0.0, 1.0],
    'product_cv_scale' => [0.0, 1.0],
    // sensor fault mode: 0=none, 1=frozen, 2=drift, 3=noise, 4=dropout
    'tank_pressure_fault_mode'   => [0.0, 4.0],
    'tank_pressure_fault_severity' => [0.0, 1000000.0],
    'tank_level_fault_mode'      => [0.0, 4.0],
    'tank_level_fault_severity'  => [0.0, 1000000.0],
    'f1_flow_fault_mode'         => [0.0, 4.0],
    'f1_flow_fault_severity'     => [0.0, 1000000.0],
    'f2_flow_fault_mode'         => [0.0, 4.0],
    'f2_flow_fault_severity'     => [0.0, 1000000.0],
    'purge_flow_fault_mode'      => [0.0, 4.0],
    'purge_flow_fault_severity'  => [0.0, 1000000.0],
    'product_flow_fault_mode'    => [0.0, 4.0],
    'product_flow_fault_severity' => [0.0, 1000000.0],
    'analyzer_fault_mode'        => [0.0, 4.0],
    'analyzer_fault_severity'    => [0.0, 1000000.0],
];

$httpMethod = $_SERVER['REQUEST_METHOD'];
$fp = pfsockopen($address, $port, $errno, $errstr);
echo $errstr;

if ($httpMethod === 'POST') {
    $cmd = json_decode(file_get_contents('php://input'), true);
    $inputs = [];

    if (is_array($cmd)) {
        foreach ($boolean_fields as $key) {
            if (array_key_exists($key, $cmd)) {
                $inputs[$key] = $cmd[$key] ? 1 : 0;
            }
        }
        foreach ($numeric_fields as $key => $range) {
            if (array_key_exists($key, $cmd) && is_numeric($cmd[$key])) {
                $value = (float)$cmd[$key];
                if ($range[0] !== null) $value = max($value, $range[0]);
                if ($range[1] !== null) $value = min($value, $range[1]);
                $inputs[$key] = $value;
            }
        }
    }

    if (!empty($inputs)) {
        $request = json_encode(['request' => 'write', 'data' => ['inputs' => $inputs]]);
        fwrite($fp, $request);
        echo fgets($fp, 1500);
    }
} else {
    fwrite($fp, '{"request":"read"}\n');
    echo fgets($fp, 1500);
}

?>
