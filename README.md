# prm-lorasweep
Philly Radio & Mesh LoRa Sweep tool

This work wouldn't be possible without the concepts introduced by [Cisien's meshcore-snr-sweep](https://github.com/Cisien/meshcore-snr-sweep) on the MeshCore Discord.
Their work inspired our own version built on our hardware and needs, but the multi-sized raw packet concept started with them.
Thank you for sharing your efforts Cisien.

Yes there are vibes in here, any use of AI was guided and reviewed by a human. 
The end goal being a basic script that does what it says on the box, doesn't have lots of external dependencies, and as human readable as possible, please don't @ me

This is a testing tool for Measuring Packet Delivery Rate (PDR), RSSI, SNR, & Listen Before Talk (LBT).
It allowed us to test multiple frequencies and configurations, and record the results in a CSV file on each end of the link for review.
It was designed for our specific mesh and equipment, no promises are expressed or implied as far as running it on your own unique setup, think of this project as a guide.

# Requirements:
This was designed to run on Philly Radio & Mesh (PRM) infrastructure hardware which is Raspberry Pi based and utilizes a SPI-based HAT for the LoRa radio.
It is also designed to work with two devices on the same network, publicly reachable IPs, tailnet, etc. as the server and client side of the script use that connection to coordinate.

OpenHop Repeater and its Python environment are currently required, as LoRaSweep uses OpenHop's SX1262 radio implementation. The script assumes OpenHop has ownership of your SPI radio, and stops that service if it is running first.
If running, it will stop the Repeater service, run either the manual parameters for Frequency, BW, SF, CR, or accept multiple frequency tests to be run back to back. If the repeater service was running before the test, it will be resumed at the conclusion of the test.

There are some hardcoded values in sweep.py, namely:
You may need to tweak these to your available ports, or specific packet sizes or volumes.

```python
PORT = 5050
SIZES = (1, 128, 255)
PACKETS = 20
SETTLE = 0.8
PACKET_DELAY = 0.1
```

And likewise, this is specific to the hardware we tested on. YMMV:

```python
radio = SX1262Radio(
    bus_id=0,
    cs_id=0,
    reset_pin=24,
    busy_pin=23,
    irq_pin=18,
    tx_power=18,
    preamble_length=32,
    use_dio2_rf=True,
    use_dio3_tcxo=True,
    dio3_tcxo_voltage=1.8,
)
```

## Installation

Create a directory for LoRaSweep, clone the repository, and enter the project directory:

```bash
git clone <YOUR-GITHUB-REPO-URL>
cd prm-lorasweep
```

Create your local `.env` from the included example:

```bash
cp .env.example .env
nano .env
```

Review and adjust the values for your system:

```bash
SERVICE="openhop-repeater"
SPI="/dev/spidev0.0"
PYTHON="/opt/openhop_repeater/venv/bin/python"
```

The `.env` file contains machine-specific settings and should **not** be committed to the repository.

Make the launcher executable:

```bash
chmod +x sweep.sh
```

Run LoRaSweep with:

```bash
./sweep.sh
```

## First Run

LoRaSweep uses one device as the **host** and the other as the **client**. The host defines the radio settings and coordinates the test, while the client connects to the host and follows the test sequence.

Start LoRaSweep on both devices:

```bash
./sweep.sh
```

### Host

On the device acting as the host, select `host` and then choose either `manual` or `csv` mode.

For a single manually configured test:

```text
Role [host/client]: host
Mode [manual/csv]: manual
Frequencies MHz [902.250]: 919.500
Bandwidth kHz [500]: 500
Spreading factor [11]: 10
Coding rate [5]: 5
```

Pressing Enter without entering a value will use the default shown in brackets.

### Client

On the second device, select `client` and enter the IP address or hostname of the host:

```text
Role [host/client]: client
Host IP: 100.x.x.x
```

The two devices must be able to reach each other over the network. This can be a local network, publicly reachable connection, tailnet, or other network arrangement that allows the client to connect to the host.

### Multiple Frequency Tests

To run multiple tests back to back, select `csv` mode on the host:

```text
Role [host/client]: host
Mode [manual/csv]: csv
CSV file: sweep-list.csv
```

The CSV file provides the radio configurations to test sequentially.

Example:

```csv
freq,bw,sf,cr
918.500,500,10,5
919.000,500,10,5
919.500,500,10,5
920.000,500,10,5
```

The client does not need a copy of the CSV. The host coordinates each test with the client automatically.
