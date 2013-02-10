#!/bin/sh
sudo kill -9 8292 && sudo  env/bin/python server.py &> ~/server.log & disown
