import argparse
import asyncio
import csv
import socket
from datetime import datetime, timezone

from openhop_core.hardware.sx1262_wrapper import SX1262Radio

PORT = 5050
SIZES = (1, 128, 255)
PACKETS = 20
SETTLE = 0.8
PACKET_DELAY = 0.1

# Zebra R0 / SPI0.0
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

received = {}

irq_crc_count = 0
irq_header_count = 0


def payload(size, seq):
    if size == 1:
        return bytes([seq])
    return seq.to_bytes(2, "big") + bytes(i % 256 for i in range(size - 2))


def rx(packet):
    size = len(packet)

    if size not in SIZES:
        return

    seq = packet[0] if size == 1 else int.from_bytes(packet[:2], "big")

    if 0 <= seq < PACKETS and packet == payload(size, seq):
        received[seq] = (radio.get_last_rssi(), radio.get_last_snr())


def write_row(csvout, freq, bw, sf, cr, direction, size,
              seq, result, rssi="", snr="", lbt="", pdr="",
              crc="", header="", miss=""):

    csvout.writerow([
        datetime.now(timezone.utc).isoformat(),
        freq, bw, sf, cr,
        direction, size, seq, result,
        rssi, snr, lbt, pdr, crc, header, miss
    ])


async def tune(freq, bw, sf, cr):
    ok = radio.configure_radio(
        frequency=freq,
        bandwidth=bw,
        spreading_factor=sf,
        coding_rate=cr,
    )

    if not ok:
        raise RuntimeError(f"Failed to tune {freq}")

    await asyncio.sleep(SETTLE)


async def transmit(csvout, freq, bw, sf, cr, direction, size):
    print(f"  TX {direction} | {size} B x {PACKETS}")

    for seq in range(PACKETS):
        result = await radio.send(payload(size, seq))

        write_row(
            csvout, freq, bw, sf, cr,
            direction, size, seq, "TX",
            lbt=result.get("lbt_attempts", 0)
        )

        await asyncio.sleep(PACKET_DELAY)


async def receive(reader, writer, csvout,
                  freq, bw, sf, cr, direction, size):

    received.clear()

    crc_start = irq_crc_count
    header_start = irq_header_count

    writer.write(f"READY {size}\n".encode())
    await writer.drain()

    msg = (await reader.readline()).decode().strip()

    if msg != "DONE":
        raise RuntimeError(f"Expected DONE, got {msg!r}")

    count = len(received)
    crc = irq_crc_count - crc_start
    header = irq_header_count - header_start
    miss = max(0, PACKETS - count - crc - header)
    pdr = count / PACKETS * 100

    for seq in range(PACKETS):
        if seq in received:
            rssi, snr = received[seq]

            write_row(
                csvout, freq, bw, sf, cr,
                direction, size, seq, "RX",
                rssi, snr
            )
        else:
            write_row(
                csvout, freq, bw, sf, cr,
                direction, size, seq, "MISS"
            )

    write_row(
        csvout, freq, bw, sf, cr,
        direction, size, "", "SUMMARY",
        pdr=f"{pdr:.1f}",
        crc=crc,
        header=header,
        miss=miss
    )

    print(
        f"  RX {direction} | {size} B | "
        f"{count}/{PACKETS} ({pdr:.0f}% PDR) | "
        f"CRC {crc} | HEADER {header} | MISS {miss}"
    )


def load_tests(args):
    if args.csv:
        with open(args.csv, newline="") as f:
            rows = csv.DictReader(f)

            return [
                (
                    int(float(row["frequency"]) * 1_000_000),
                    int(row["bw"]) * 1000,
                    int(row["sf"]),
                    int(row["cr"])
                )
                for row in rows
            ]

    return [
        (
            int(float(freq) * 1_000_000),
            args.bw * 1000,
            args.sf,
            args.cr
        )
        for freq in args.freq.split()
    ]


async def host(args, csvout):
    tests = load_tests(args)
    finished = asyncio.Event()

    async def handle(reader, writer):
        print("Client connected")

        for number, (freq, bw, sf, cr) in enumerate(tests, 1):
            print(
                f"\n[{number}/{len(tests)}] "
                f"{freq / 1e6:.3f} MHz / BW{bw // 1000} / SF{sf} / CR{cr}"
            )

            await tune(freq, bw, sf, cr)

            writer.write(f"TUNE {freq} {bw} {sf} {cr}\n".encode())
            await writer.drain()

            if (await reader.readline()).decode().strip() != "READY":
                raise RuntimeError("Client failed to tune")

            for size in SIZES:

                # Client -> Host
                await receive(
                    reader, writer, csvout,
                    freq, bw, sf, cr,
                    "CLIENT-HOST", size
                )

                # Host -> Client
                if not (await reader.readline()).decode().startswith("READY"):
                    raise RuntimeError("Client not ready")

                await transmit(
                    csvout, freq, bw, sf, cr,
                    "HOST-CLIENT", size
                )

                writer.write(b"DONE\n")
                await writer.drain()

        writer.write(b"FINISHED\n")
        await writer.drain()

        print("\nSweep complete")
        writer.close()
        await writer.wait_closed()
        finished.set()

    server = await asyncio.start_server(handle, "0.0.0.0", PORT)

    print(f"Waiting for client on TCP {PORT}...")

    async with server:
        await finished.wait()


async def client(args, csvout):
    reader, writer = await asyncio.open_connection(args.host, PORT)

    print(f"Connected to {args.host}")

    while True:
        command = (await reader.readline()).decode().strip()

        if command == "FINISHED":
            break

        parts = command.split()

        if parts[0] != "TUNE":
            raise RuntimeError(f"Unexpected command: {command}")

        freq = int(parts[1])
        bw = int(parts[2])
        sf = int(parts[3])
        cr = int(parts[4])

        print(f"\n{freq / 1e6:.3f} MHz / BW{bw // 1000} / SF{sf} / CR{cr}")

        await tune(freq, bw, sf, cr)

        writer.write(b"READY\n")
        await writer.drain()

        for size in SIZES:

            # Client -> Host
            if not (await reader.readline()).decode().startswith("READY"):
                raise RuntimeError("Host not ready")

            await transmit(
                csvout, freq, bw, sf, cr,
                "CLIENT-HOST", size
            )

            writer.write(b"DONE\n")
            await writer.drain()

            # Host -> Client
            await receive(
                reader, writer, csvout,
                freq, bw, sf, cr,
                "HOST-CLIENT", size
            )

    print("\nSweep complete")
    writer.close()
    await writer.wait_closed()


async def main():
    global irq_crc_count, irq_header_count

    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(dest="role", required=True)

    h = sub.add_parser("host")
    h.add_argument("--freq")
    h.add_argument("--bw", type=int, default=500)
    h.add_argument("--sf", type=int, default=11)
    h.add_argument("--cr", type=int, default=5)
    h.add_argument("--csv")

    c = sub.add_parser("client")
    c.add_argument("host")

    args = parser.parse_args()

    if args.role == "host" and not args.freq and not args.csv:
        parser.error("host requires --freq or --csv")

    radio.set_rx_callback(rx)

    print("Initializing Zebra R0 / spi0.0...")

    if not radio.begin():
        raise SystemExit("Radio initialization failed")

    # Observe each hardware IRQ after OpenHop has read and stored its status.
    original_irq_handler = radio._handle_interrupt

    def observed_irq_handler():
        global irq_crc_count, irq_header_count

        original_irq_handler()

        irq = radio._last_irq_status

        if irq & radio.lora.IRQ_CRC_ERR:
            irq_crc_count += 1

        if irq & radio.lora.IRQ_HEADER_ERR:
            irq_header_count += 1

    radio._handle_interrupt = observed_irq_handler

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{socket.gethostname()}-{timestamp}-{args.role}.csv"

    print(f"Log: {filename}")

    with open(filename, "w", newline="", buffering=1) as f:
        csvout = csv.writer(f)

        csvout.writerow([
            "timestamp",
            "frequency",
            "bw",
            "sf",
            "cr",
            "direction",
            "size",
            "sequence",
            "result",
            "rssi",
            "snr",
            "lbt_attempts",
            "pdr",
            "crc_errors",
            "header_errors",
            "misses"
        ])

        if args.role == "host":
            await host(args, csvout)
        else:
            await client(args, csvout)


asyncio.run(main())
