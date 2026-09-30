#!/bin/bash
if [ ! -f .env ]; then
    echo "ERROR: .env not found. Copy .env.example to .env and configure it."
    exit 1
fi

source .env

OPENHOP_WAS_RUNNING=false

cleanup() {
    if [ "$OPENHOP_WAS_RUNNING" = true ]; then
        echo
        echo "Starting OpenHop..."
        sudo systemctl start "$SERVICE"
    fi
}

echo "PhillyMesh RF Sweep"
echo

read -rp "Role [host/client]: " ROLE

case "$ROLE" in
    host)
        read -rp "Mode [manual/csv]: " MODE

        case "$MODE" in
            manual)
                read -rp "Frequencies MHz [919.500]: " FREQ
                read -rp "Bandwidth kHz [500]: " BW
                read -rp "Spreading factor [10]: " SF
                read -rp "Coding rate [5]: " CR

                FREQ=${FREQ:-919.500}
                BW=${BW:-500}
                SF=${SF:-10}
                CR=${CR:-5}

                ARGS=(host --freq "$FREQ" --bw "$BW" --sf "$SF" --cr "$CR")
                ;;

            csv)
                read -rp "CSV file: " CSV

                if [ ! -f "$CSV" ]; then
                    echo "CSV file not found: $CSV"
                    exit 1
                fi

                ARGS=(host --csv "$CSV")
                ;;

            *)
                echo "Mode must be manual or csv."
                exit 1
                ;;
        esac
        ;;

    client)
        read -rp "Host IP: " HOST

        ARGS=(client "$HOST")
        ;;

    *)
        echo "Role must be host or client."
        exit 1
        ;;
esac

echo
echo

if systemctl is-active --quiet "$SERVICE"; then
    OPENHOP_WAS_RUNNING=true
    echo "Stopping OpenHop..."
    sudo systemctl stop "$SERVICE"
else
    echo "OpenHop is already stopped."
fi

trap cleanup EXIT

sleep 1

if sudo fuser "$SPI" >/dev/null 2>&1; then
    echo "ERROR: $SPI is still in use:"
    sudo fuser -v "$SPI"
    exit 1
fi

echo "$SPI is available."
echo "Starting sweep..."
echo

"$PYTHON" sweep.py "${ARGS[@]}"
