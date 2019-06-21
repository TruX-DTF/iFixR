#!/bin/bash -l

dir=$1

proj=Lang
for bug in $(seq 1 65)
do
	defects4j compile -w ${dir}${proj}_${bug}
done

proj=Math
for bug in $(seq 1 106)
do
        defects4j compile -w ${dir}${proj}_${bug}
done

