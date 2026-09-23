# prm-lorasweep
Philly Radio & Mesh LoRa Sweep tool

This is a testing tool for Measureing Packet Delivery Rates(PDR), RSSI, SNR, & Listen Before Talk (LBT).
It will allow you to test multiple frequencies and configurations, and record the results in a CSV file on each end of the link for review.

# Requirements:
This was designed to run on Philly Radio & Mesh (PRM) infrastructure hardware which is raspberry pi based and utilizes a spi based hat for the LoRa radio.
It is also designed to work with two devices on the same network, publicy reachable IP, tailnet, etc. as the server and client side of the script uses that to coordinate.

In it's current configuration it assumes OpenHop Repeater is installed, running, and has ownership of your spi radio,
it will stop the Repeater service, run either the manual parameters for Frequency, BW, SF, CR, or accept multiple frequency tests to be run back to back.
at the conclusion of the test it will resume the repeater service
