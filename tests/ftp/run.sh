#!/bin/bash

python3 tester.py

if [[ $? -ne 0 ]]; then
  exit 1
fi