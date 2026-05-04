FROM ros:humble

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions \
    ros-humble-rosidl-default-generators \
    ros-humble-rosidl-default-runtime \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws

# copy workspace sources (must include puppy_control_msgs/)
COPY src/ /ws/src/

# build interfaces
RUN . /opt/ros/humble/setup.sh && colcon build --symlink-install

# convenience: auto-source overlay when using bash -lc
RUN echo "source /opt/ros/humble/setup.bash" >> /etc/bash.bashrc && \
    echo "source /ws/install/setup.bash" >> /etc/bash.bashrc
