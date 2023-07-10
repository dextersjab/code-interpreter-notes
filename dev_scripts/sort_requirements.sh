#!/bin/bash
# This script sorts the lines in a requirements.txt file in alphabetical order.

# Make sure a file name is supplied
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <file>"
    exit 1
fi

# Check if the file exists
if [ ! -f $1 ]; then
    echo "File $1 not found!"
    exit 1
fi

# Sort the file
sort $1 -o $1
