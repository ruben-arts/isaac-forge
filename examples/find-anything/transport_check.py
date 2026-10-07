#!/usr/bin/env python3
"""Show which buffer backend a GPU topic reaches another process with.

Run it while a demo runs. ROS 2 Lyrical negotiates the backend per subscription: the
publisher sends once, and each subscriber receives the representation it asked for.

  --backend cuda   subscribe like a GPU-aware node (acceptable_buffer_backends="cuda"):
                   the image arrives as a rosidl Buffer still in GPU memory
  --backend cpu    subscribe like an ordinary node (default options): the image arrives
                   as a host copy
  --backend both   both subscriptions side by side, from the same process

A subscriber that asks for CUDA in an environment without the cuda-buffer-backend plugin
falls back to CPU copies when the publisher has no plugin either. When only the publisher
has it, that subscriber receives nothing, so keep both sides in the same environment.
"""

import argparse
import importlib

import rclpy
from rclpy.node import Node

SUBSCRIBERS = {
    "cuda": ("subscriber accepting CUDA", "cuda"),
    "cpu": ("ordinary subscriber", None),
}


def backend_of(msg) -> str:
    # A CUDA-backed field arrives as rosidl_buffer.Buffer; a host copy as a Python array.
    return getattr(msg.data, "backend_type", "cpu")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("topic")
    parser.add_argument("--backend", choices=("both", "cuda", "cpu"), default="both")
    parser.add_argument("--type", default="sensor_msgs/msg/Image")
    parser.add_argument("--seconds", type=float, default=10.0)
    args = parser.parse_args()
    module, name = args.type.rsplit("/", 1)
    msg_type = getattr(importlib.import_module(module.replace("/", ".")), name)
    chosen = ["cuda", "cpu"] if args.backend == "both" else [args.backend]

    rclpy.init()
    node = Node("transport_check")
    received = {who: {} for who in chosen}
    sizes = {}

    def record(who):
        def callback(msg):
            backend = backend_of(msg)
            received[who][backend] = received[who].get(backend, 0) + 1
            sizes[who] = msg.step * msg.height
        return callback

    for who in chosen:
        label, accept = SUBSCRIBERS[who]
        options = {"acceptable_buffer_backends": accept} if accept else {}
        node.create_subscription(msg_type, args.topic, record(who), 10, **options)

    end = node.get_clock().now().nanoseconds + int(args.seconds * 1e9)
    while rclpy.ok() and node.get_clock().now().nanoseconds < end:
        rclpy.spin_once(node, timeout_sec=0.1)

    print(f"{args.topic}, received in this process over {args.seconds:.0f} s:")
    for who in chosen:
        label = SUBSCRIBERS[who][0]
        counts = ", ".join(f"{n} x {backend}" for backend, n in received[who].items())
        size = f" ({sizes[who] / 1e6:.1f} MB each)" if who in sizes else ""
        print(f"  {label:26s} {counts or 'nothing (is a demo running?)'}{size}")
    node.destroy_node()
    rclpy.shutdown()
    return 0 if all(received[who] for who in chosen) else 1


if __name__ == "__main__":
    raise SystemExit(main())
