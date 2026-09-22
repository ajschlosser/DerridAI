#!/bin/bash
pid=$(ss -ltnp | grep ":${1:-5199}" | grep -o "pid=[0-9]*" | cut -d= -f2); [ -n "$pid" ] && kill $pid
exit 0
