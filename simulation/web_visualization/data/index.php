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
    'suppressed_tags' => [],
];
// How long a real triggered fault suppresses the ambient scheduler for, and
// which tags it suppresses - see design doc's "quiet buffer". Two changes
// from the original fixed-60s/suppress-everything version, after live
// testing showed a full-silence window is itself a tell ("it's quiet, too
// quiet") once it's a large multiple of the configured event density:
//   - Scaled to the configured mean_interval_s instead of fixed, capped at
//     $quiet_buffer_max_seconds. A dense noise floor (short mean_interval_s)
//     gets a short buffer; a sparse one keeps the full default.
//   - Only the specific tag(s) the real trigger just touched are excluded
//     (see derive_affected_tags() below) - the scheduler keeps generating
//     ambient events on everything else during the window, so there's no
//     silence to notice, just no direct same-tag collision.
$quiet_buffer_max_seconds = 60;
$quiet_buffer_fraction = 0.5; // of mean_interval_s
$quiet_buffer_min_seconds = 5;

// How long to hold a *genuinely newly-activated* fault before actually
// forwarding it to the simulator, so its visible effect lands a beat after
// the quiet window has already started (otherwise it starts at exactly the
// same instant the window opens, as noticeable as the window itself - see
// the design doc). Deliberately not applied to every request touching a
// fault field - see detect_new_activation() below for why that matters.
$fault_activation_delay_seconds = 3;

// Maps a real-trigger field name to the tag name
// simulation/noise_floor/scheduler.py picks ambient events from, so the
// scheduler can avoid re-touching whatever the instructor just triggered.
// Fields with no ambient equivalent (e_stop, valve_sp/slew_rate/cv_scale -
// the scheduler doesn't generate sticky/fouled ambient events) map to
// nothing and are ignored.
//
// Checks the field's *value*, not just whether the key is present - the
// dashboard's existing faultInputsPayload() always POSTs every valve/sensor
// field on every change (the full current state, not a diff), so most of
// them are present but in their neutral/off value (stuck=0, fault_mode=0)
// on any given request. Treating mere presence as "just triggered" (the
// first version of this function did) flagged literally everything on
// every request - functionally identical to the old suppress-everything
// behavior this was meant to replace. Only a field whose value indicates
// an actually active fault counts.
function derive_affected_tags($inputs) {
    $tags = [];
    foreach ($inputs as $key => $value) {
        if (preg_match('/^(.+)_stuck$/', $key, $m) && $value) {
            $tags[] = $key; // scheduler's STUCK_TAGS are the literal field names
        } elseif (preg_match('/^(.+)_fault_mode$/', $key, $m) && (float)$value != 0.0) {
            $tags[] = $m[1]; // scheduler's SENSOR_TAGS are the bare sensor name
        }
    }
    return array_values(array_unique($tags));
}

// True if $inputs contains a field genuinely transitioning from
// inactive to active, compared against the simulator's *current* state
// (not the noise-floor state file - the simulator itself is the source of
// truth for "is this already active"). This is deliberately narrower than
// derive_affected_tags() above: the dashboard resends every fault field's
// current value on *every* interaction, including dragging a severity
// slider or stroke-time slider for a fault that's already toggled on - if
// those re-sends of an already-active value also counted as "just
// triggered," every slider drag would eat the activation delay below,
// which would feel laggy for no benefit (adjusting an active fault's
// intensity isn't a new event the quiet buffer needs to protect).
function detect_new_activation($inputs, $current_state) {
    foreach ($inputs as $key => $value) {
        if (preg_match('/^(.+)_stuck$/', $key)) {
            $old = !empty($current_state[$key]);
            if (!$old && $value) return true;
        } elseif (preg_match('/^(.+)_fault_mode$/', $key)) {
            $old = isset($current_state[$key]) ? (float)$current_state[$key] : 0.0;
            $new = (float)$value;
            if ($old != $new && $new != 0.0) return true;
        }
    }
    return false;
}

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
        // Read current state first, to tell a genuine new activation (e.g.
        // toggling a valve stuck) apart from re-sending an already-active
        // fault's current value (e.g. dragging its severity slider) - see
        // detect_new_activation()'s comment for why conflating the two
        // would be a problem.
        fwrite($fp, "{\"request\":\"read\"}\n");
        $current = json_decode(fgets($fp, 4096), true);
        $current_state = (is_array($current) && isset($current['state'])) ? $current['state'] : [];
        $is_new_activation = detect_new_activation($inputs, $current_state);

        // A real fault was just triggered through this same endpoint -
        // suppress the ambient scheduler from reusing the same tag(s) briefly
        // (see the quiet-buffer comments above). Set this *before* the delay
        // below, so the quiet window's countdown starts immediately rather
        // than only once the fault's effect actually lands.
        $nf_state = read_noise_floor_state($noise_floor_state_file, $noise_floor_default_state);
        $quiet_buffer_seconds = min(
            $quiet_buffer_max_seconds,
            max($quiet_buffer_min_seconds, (float)$nf_state['mean_interval_s'] * $quiet_buffer_fraction)
        );
        $nf_state['suppress_until'] = microtime(true) + $quiet_buffer_seconds;
        $nf_state['suppressed_tags'] = derive_affected_tags($inputs);
        write_noise_floor_state($noise_floor_state_file, $nf_state);

        if ($is_new_activation) {
            sleep($fault_activation_delay_seconds);
        }

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
