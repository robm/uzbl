#!/bin/sh
#
# Block downloading of user defined http requests
#
# This is script is intended たo be use together 
# with the 'request_handler' uzbl-core handler
#
# Writing BLOCK to stdout will block loading the 
# specific ressource


# Block every ressource  containing .png
#
if echo "$8" | grep '.png'; then
    echo BLOCK
fi

