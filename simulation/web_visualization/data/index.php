<?php
$address = '127.0.0.1';
$port = 55555;
$e_stop_true = '{"request":"write","data":{"inputs":{"e_stop":1}}}';
$e_stop_false = '{"request":"write","data":{"inputs":{"e_stop":0}}}';

$httpMethod = $_SERVER['REQUEST_METHOD'];
$fp = pfsockopen($address, $port, $errno, $errstr);
echo $errstr;


if ($httpMethod === 'POST') {
    $cmd = json_decode(file_get_contents('php://input'),true);
    if (array_key_exists('e_stop',$cmd)) {
        if ($cmd['e_stop'] == 0) {
            fwrite($fp, $e_stop_false);
        } else {
            fwrite($fp, $e_stop_true);
        }
    }
} else {
    fwrite($fp, '{"request":"read"}\n');
    echo fgets($fp, 1500);
}

?>
