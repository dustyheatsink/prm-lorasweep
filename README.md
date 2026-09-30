# prm-lorasweep
Philly Radio & Mesh LoRa Sweep tool

This work wouldn't be possible without the concepts introduced by Cisien on the Meshcore discord. 
Their work inspired our own version built on our hardware and needs, but the multi sized raw packet concept started with them.
Thank you for sharing your efforts Cisien.

Yes there are vibes in here, any use of AI was guided and reviewed by a human. 
The end goal being a basic script that does what it says on the box, doesn't have lots of external dependencies, and as human readable as possible, please don't @ me

This is a testing tool for Measureing Packet Delivery Rates(PDR), RSSI, SNR, & Listen Before Talk (LBT).
It allowed us to test multiple frequencies and configurations, and record the results in a CSV file on each end of the link for review.
It was designed for our specific mesh and equipment, no promises are expressed or implied as far as running it on your own unique setup, think of this project as a guide.

# Requirements:
This was designed to run on Philly Radio & Mesh (PRM) infrastructure hardware which is raspberry pi based and utilizes a spi based hat for the LoRa radio.
It is also designed to work with two devices on the same network, publicl.y reachable IP, tailnet, etc. as the server and client side of the script uses that connection. to coordinate.

In it's current configuration it assumes OpenHop Repeater is installed, running, and in that state has ownership of your SPI radio,
it will stop the Repeater service, run either the manual parameters for Frequency, BW, SF, CR, or accept multiple frequency tests to be run back to back.
at the conclusion of the test it will resume the repeater service

There are some hardcoded values in sweep.py, namely:
You maay want to need to tweak these to your available ports, or specific packet sizes or volumes.
```PORT = 5050
SIZES = (1, 128, 255)
PACKETS = 20
SETTLE = 0.8
PACKET_DELAY = 0.1```

and likewise this is specific to the hardware we tested on, ymmv:

```radio = SX1262Radio(
    bus_id=0,
    cs_id=0,
    reset_pin=24,
    busy_pin=23,
    irq_pin=18,
    tx_power=18,
    preamble_length=32,
    use_dio2_rf=True,
    use_dio3_tcxo=True,
    dio3_tcxo_voltage=1.8,```.
