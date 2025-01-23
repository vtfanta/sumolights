#!/usr/bin/env bash
for i in {1..1}
do
    # python run.py -sim my_test -n 1 -tsc maxpressure -mode test -gmin 5 
    # python run.py -sim single -n 1 -tsc websters -mode test -cmax 180 -cmin 40 -f 1800 -satflow 0.44 
    # python run.py -sim double -n 1 -tsc uniform -mode test -gmin 12 
    python run.py -sim single -n 1 -tsc sotl -mode test -mu 5 -omega 0 -theta 10
    # python run.py -sim double -n 8 -tsc dqn -load -nogui -mode test
    # python run.py -sim double -n 8 -tsc ddpg -load -nogui -mode test
done
