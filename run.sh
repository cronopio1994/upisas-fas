#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/UPISAS
python3 experiment-runner/experiment-runner/ UPISAS/experiment_runner_configs/DINGNET_baseline.py
