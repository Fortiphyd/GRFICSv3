#!/bin/bash

python feed1.py &
python feed2.py &
python purge.py &
python product.py &
python tank.py &
python analyzer.py &

wait
