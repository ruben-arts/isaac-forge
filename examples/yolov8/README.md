# Real YOLOv8 + Rerun demo

This example runs an actual COCO-trained **Ultralytics YOLOv8n** network through
the packaged Isaac ROS GPU pipeline:

```text
sample image -> NITROS/CUDA preprocessing -> TensorRT -> YOLOv8 decoder
             -> vision_msgs/Detection2DArray -> Rerun
```

It downloads a checksum-pinned 12 MB, 320×320 ONNX model and the Ultralytics `bus.jpg`
sample on first use. YOLOv8n is already the smallest YOLOv8 model; using its 320×320 export
instead of 640×640 reduces TensorRT activation and tactic memory substantially for an Orin
Nano. TensorRT then builds a GPU-specific engine in `.cache/`, which can take a few minutes
the first time.

```bash
cd examples/yolov8
pixi run check
pixi run demo
```

The default environment is ROS 2 Lyrical with Isaac ROS 5.0. The `jazzy` environment runs
the same demo on ROS 2 Jazzy with Isaac ROS 4.6:

```bash
pixi run -e jazzy demo
```

Both environments support x86_64 Linux and Jetson/ARM64. The ARM platform declares
JetPack 7, CUDA 13, and SM87, so Pixi selects the Orin TensorRT payload.

The demo opens the Rerun viewer with the image and 2D detection boxes, and also
writes an annotated image to `.cache/yolov8_result.png`.

For a machine without a desktop session, record the visualization instead:

```bash
pixi run demo --no-viewer
# Later, on a desktop:
pixi run rerun .cache/yolov8_result.rrd
```

## Video and webcam streaming

Run the bundled-on-demand sample traffic video until it ends:

```bash
pixi run video
```

A webcam, video file, RTSP stream, or other OpenCV-compatible URL can be used as
the source. The Rerun timeline updates with every inference result:

```bash
pixi run video --source 0             # default webcam
pixi run video --source /path/to/video.mp4
pixi run video --source /path/to/video.mp4 --loop
pixi run video --source rtsp://camera.example/stream
```

For headless processing, add `--no-viewer`; this writes
`.cache/yolov8_video.rrd`. Use `--max-frames 300` to bound a recording.

## GPU transport between processes

On Lyrical, Isaac ROS 5.0 publishes images and tensors as `rosidl::Buffer` fields, and the
environment includes the CUDA buffer backend. A subscriber in another process that accepts
CUDA receives them in GPU memory; an ordinary subscriber receives a host copy of the same
message. The backend is negotiated per subscription, so both work at once.

While `pixi run video` runs, check it from a second terminal:

```bash
pixi run transport          # both kinds of subscriber, side by side
pixi run transport cuda     # only a subscriber that accepts CUDA
pixi run transport cpu      # only an ordinary subscriber
```

```text
/yolov8_encoder/resize/image, received in this process over 10 s:
  subscriber accepting CUDA  902 x cuda (0.3 MB each)
  ordinary subscriber        946 x cpu (0.3 MB each)
```

`cuda` means the subscriber got a handle to the publisher's GPU memory instead of a copy.
The nodes inside the demo's own container exchange messages directly either way.

An NVIDIA GPU and working driver are required. Close other GPU-heavy applications while
TensorRT builds the engine on a low-memory Jetson. The downloaded model carries the
Ultralytics AGPL-3.0 license; its URL and SHA-256 are pinned in
[`yolo_demo.py`](./yolo_demo.py).
