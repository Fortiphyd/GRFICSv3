<?php
$address = '127.0.0.1';
$port = 55555;

// Noise-floor scheduler state - see simulation/noise_floor/scheduler.py and
// docs/cyber-vs-physical-fault-injection-design.md §5. Shared JSON file: this
// script writes config, the scheduler polls it. Defaults to OFF/quiet -
// nothing here ever turns it on by itself.
$noise_floor_state_file = '/app/noise_floor/state.json';
$noise_floor_default_state = [
    'enabled' => false,
    'seed' => 0,
    'mean_interval_s' => 30.0,
    'suppress_until' => 0.0,
];
// How long a real triggered fault (any field below) suppresses the ambient
// scheduler for, so the seed can't occasionally land an ambient blip right
// on top of the real event by chance (see design doc's "quiet buffer").
$quiet_buffer_seconds = 60;

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

// noise_floor_* fields are handled separately below - they configure the
// scheduler (simulation/noise_floor/scheduler.py), not the TE_process
// itself, so they're written to $noise_floor_state_file instead of being
// forwarded over the simulator socket.
$noise_floor_fields = [
    'noise_floor_enabled'         => 'bool',
    'noise_floor_seed'            => 'int',
    'noise_floor_mean_interval_s' => 'float',
];

function read_noise_floor_state($path, $default) {
    $state = $default;
    if (file_exists($path)) {
        $decoded = json_decode(file_get_contents($path), true);
        if (is_array($decoded)) {
            $state = array_merge($default, $decoded);
        }
    }
    return $state;
}

function write_noise_floor_state($path, $state) {
    @mkdir(dirname($path), 0775, true);
    file_put_contents($path, json_encode($state));
}

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
        // A real fault was just triggered through this same endpoint -
        // suppress the ambient scheduler briefly so it can't coincidentally
        // overlap the real event (see $quiet_buffer_seconds above).
        $nf_state = read_noise_floor_state($noise_floor_state_file, $noise_floor_default_state);
        $nf_state['suppress_until'] = microtime(true) + $quiet_buffer_seconds;
        write_noise_floor_state($noise_floor_state_file, $nf_state);

        $request = json_encode(['request' => 'write', 'data' => ['inputs' => $inputs]]);
        fwrite($fp, $request);
        echo fgets($fp, 1500);
    }

    if (is_array($cmd)) {
        $nf_updates = [];
        foreach ($noise_floor_fields as $key => $type) {
            if (array_key_exists($key, $cmd)) {
                $value = $cmd[$key];
                if ($type === 'bool') $value = (bool)$value;
                if ($type === 'int') $value = (int)$value;
                if ($type === 'float') $value = max(1.0, (float)$value);
                $nf_updates[substr($key, strlen('noise_floor_'))] = $value;
            }
        }
        if (!empty($nf_updates)) {
            $nf_state = read_noise_floor_state($noise_floor_state_file, $noise_floor_default_state);
            $nf_state = array_merge($nf_state, $nf_updates);
            write_noise_floor_state($noise_floor_state_file, $nf_state);
            if (empty($inputs)) {
                echo json_encode(['noise_floor' => $nf_state]);
            }
        }
    }
} else {
    fwrite($fp, '{"request":"read"}\n');
    $response = fgets($fp, 1500);
    $decoded = json_decode($response, true);
    if (is_array($decoded)) {
        $decoded['noise_floor'] = read_noise_floor_state($noise_floor_state_file, $noise_floor_default_state);
        echo json_encode($decoded);
    } else {
        echo $response;
    }
}

?>
