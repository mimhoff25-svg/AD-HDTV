#!/bin/bash
# Legacy wrapper for compatibility. Use install_adhdtv.sh instead.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Forward to the new installer
exec "$DIR/install_adhdtv.sh" "$@"
