#!/bin/sh
#
# Block downloading of user defined http requests
#
# This script is intended to be used together 
# with the 'request_handler' uzbl-core handler
#
# $8 contains the URI of the current ressource
#
# Writing BLOCK to stdout will block loading the 
# specific ressource


# Block every ressource containing .png
#
if echo "$8" | grep '.png'; then
    echo BLOCK
fi

