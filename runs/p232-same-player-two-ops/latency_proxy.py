#!/usr/bin/env python3
"""Userspace delaying TCP proxy for the p232 latency run.

Listens on --listen, forwards every byte stream to --target, and delays each direction by
--delay-ms using a per-direction FIFO: a chunk read at time T is written to the other side no
earlier than T + delay. FIFO order preserves TCP stream ordering, so the Minecraft protocol sees a
normal (just slow) connection. This is synthetic latency on one machine - it is NOT a second
machine, and the run README must say so.

Every connection is logged as P232_PROXY lines (open with the configured delay, close with the byte
counts in both directions) so the verdict can prove the clients really went through the delayed
path instead of straight to the server.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time


def parse_hostport(text: str) -> tuple[str, int]:
    host, _, port = text.rpartition(":")
    if not host or not port.isdigit():
        raise ValueError(f"expected host:port, got {text!r}")
    return host, int(port)


async def pump(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
               delay: float, stats: list, conn: int, direction: str,
               emit) -> None:
    queue: asyncio.Queue = asyncio.Queue()

    async def worker() -> None:
        while True:
            item = await queue.get()
            if item is None:
                return
            data, queued_at = item
            remain = delay - (time.monotonic() - queued_at)
            if remain > 0:
                await asyncio.sleep(remain)
            writer.write(data)
            await writer.drain()
            stats[0] += len(data)

    worker_task = asyncio.create_task(worker())
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            queue.put_nowait((data, time.monotonic()))
            # Traffic is reported while the connection is alive, not only at close: a hard kill
            # can drop a client before the close line is written, and the byte evidence must not
            # depend on a graceful shutdown.
            if stats[0] - stats[1] >= 200_000:
                stats[1] = stats[0]
                emit(f"P232_PROXY conn={conn} traffic dir={direction} bytes={stats[0]}")
    finally:
        await queue.put(None)
        await worker_task


async def handle(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter,
                 target: tuple[str, int], delay: float, emit, state: dict) -> None:
    state["next"] += 1
    conn = state["next"]
    opened = time.monotonic()
    emit(f"P232_PROXY conn={conn} open t={int(time.time() * 1000)} "
         f"delayMs={int(delay * 1000)} target={target[0]}:{target[1]}")
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(*target)
    except Exception as exc:
        emit(f"P232_PROXY conn={conn} upstream-fail error={exc!r}")
        client_writer.close()
        return
    up = [0, 0]
    down = [0, 0]
    tasks = [asyncio.create_task(pump(client_reader, upstream_writer, delay, up,
                                      conn, "up", emit)),
             asyncio.create_task(pump(upstream_reader, client_writer, delay, down,
                                      conn, "down", emit))]
    await asyncio.gather(*tasks, return_exceptions=True)
    for writer in (upstream_writer, client_writer):
        try:
            writer.close()
        except Exception:
            pass
    emit(f"P232_PROXY conn={conn} close upBytes={up[0]} downBytes={down[0]} "
         f"durMs={int((time.monotonic() - opened) * 1000)}")


async def amain(listen: tuple[str, int], target: tuple[str, int], delay: float, emit) -> None:
    state = {"next": 0}

    async def on_client(reader, writer):
        await handle(reader, writer, target, delay, emit, state)

    server = await asyncio.start_server(on_client, *listen)
    emit(f"P232_PROXY listening={listen[0]}:{listen[1]} delayMs={int(delay * 1000)}")
    async with server:
        await server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delaying TCP proxy used by the p232 quad-client latency run.")
    parser.add_argument("--listen", default="127.0.0.1:23110")
    parser.add_argument("--target", default="127.0.0.1:25566")
    parser.add_argument("--delay-ms", type=int, default=50)
    parser.add_argument("--log", default="proxy.log")
    args = parser.parse_args()

    listen = parse_hostport(args.listen)
    target = parse_hostport(args.target)
    delay = args.delay_ms / 1000.0
    log = open(args.log, "a", encoding="utf-8", errors="replace")

    def emit(text: str) -> None:
        log.write(text + "\n")
        log.flush()
        print(text, flush=True)

    try:
        asyncio.run(amain(listen, target, delay, emit))
    except KeyboardInterrupt:
        pass
    finally:
        log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
