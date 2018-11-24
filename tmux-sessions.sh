#!/bin/bash

tmux -2 new-session -d -s truec -n 'controllers'

tmux send-keys "cd ~/workspace/projects/Truechain/forked/py-trueconsensus" C-m

tmux split-window -v
tmux split-window -v
tmux split-window -v

for i in {0..3}; do
    # 3 panes - 0/1/2 - in one window now
    tmux select-pane -t $i
    tmux send-keys "source venv/bin/activate" C-m
    tmux send-keys "#./minerva.py -i $i" C-m
done

# tmux -2 attach-session -t truec

# http://tmuxcheatsheet.com/

# Toggle between pane layouts
# Ctrl + b  Spacebar
# Switch to next pane
# Ctrl + b  o

# enter command mode
# Ctrl + b :

# :setw synchronize-panes

# enable mouse clicks
# ^b + :
# then
# setw -g mouse on
