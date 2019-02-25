#!/bin/sh

executed=0
for filename in ./samples/*.lispy; do
  printf "\n\nExecuting: $filename...\n"
  ./execute $filename
  ((executed++))
done

printf "\n\nEXECUTED $executed FILES.\n\n"
