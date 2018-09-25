#!/bin/bash
#if [ $(which flent) ]; then
#    echo "flent:Installed"
#else
#    echo "flent:Not installed"
#fi
if [ $(which tcpdump) ]; then
    echo "tcpdump:Installed"
else
    echo "tcpdump:Not installed"
fi
if [ $(which iperf) ]; then
    echo "iperf:Installed"
else
    echo "iperf:Not installed"
fi
#if [ $(which nuttcp) ]; then
#    echo "nuttcp:Installed"
#else
#    echo "nuttcp:Not installed"
#fi
#if [ $(which curl) ]; then
#    echo "curl:Installed"
#else
#    echo "curl:Not installed"
#fi
#if [ $(which netperf) ]; then
#    echo "netperf:Installed"
#else
#    echo "netperf:Not installed"
#fi