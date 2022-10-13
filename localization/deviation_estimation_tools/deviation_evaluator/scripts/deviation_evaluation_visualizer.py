#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2020 Tier IV, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from pathlib import Path
from threading import Thread
from enum import Enum

from bag_load_utils import *
import numpy as np
from plot_utils import *
import rclpy
from rclpy.node import Node

PARAMS = {
    "twist_topic": "/deviation_evaluator/twist_estimator/twist_with_covariance",
    "pose_topic": "/deviation_evaluator/dead_reckoning/pose_estimator/pose_with_covariance",
    "ekf_gt_odom_topic": "/deviation_evaluator/ground_truth/ekf_localizer/kinematic_state",
    "ekf_dr_odom_topic": "/deviation_evaluator/dead_reckoning/ekf_localizer/kinematic_state",
    "scale": 3,
    "ndt_freq": 10,
}

class ThresholdState(Enum):
    GOOD = 0
    TOO_SMALL = 1
    TOO_LARGE = 2
    UNDETERMINABLE = 3

def validate_threshold(recall: float, threshold: float, lowerbound: float) -> ThresholdState:
    if threshold < lowerbound:
        print("Threshold is too small for this vehicle. Consider increasing the threshold and tolerate larger localization error.")
        return ThresholdState.TOO_SMALL
    elif recall == np.inf:
        print("No error larger than {:.3f} [m] observed. Increase cut duration.".format(threshold))
        return ThresholdState.UNDETERMINABLE
    elif recall > 0.99:
        print("Valid threhsold!")
        return ThresholdState.GOOD
    else:
        print("Covariance seems to be too optimistic. Consider increasing the covariances of the dead reckoning sensors.")
        return ThresholdState.TOO_LARGE

class DeviationEvaluationVisualizer(Node):
    def __init__(self):
        super().__init__("deviation_evaluation_visualizer")
        self.declare_parameter("save_dir", "")
        self.declare_parameter("warn_ellipse_size", 0.0)
        self.declare_parameter("warn_ellipse_size_lateral_direction", 0.0)

        save_dir = self.get_parameter("save_dir").get_parameter_value().string_value
        threshold_long_radius = self.get_parameter("warn_ellipse_size").get_parameter_value().double_value
        threshold_lateral = self.get_parameter("warn_ellipse_size_lateral_direction").get_parameter_value().double_value

        bagfile = Path(save_dir) / "ros2bag/ros2bag_0.db3"
        output_dir = Path(save_dir)

        bag_file_evaluator = BagFileEvaluator(str(bagfile), PARAMS)

        recall_lateral = bag_file_evaluator.calc_recall_lateral(threshold_lateral)
        threshold_state_lateral = validate_threshold(recall_lateral, threshold_lateral, bag_file_evaluator.results.lateral.lower_bound)

        recall_long_radius = bag_file_evaluator.calc_recall_long_radius(threshold_long_radius)
        threshold_state_long_radius = validate_threshold(recall_long_radius, threshold_long_radius, bag_file_evaluator.results.long_radius.lower_bound)

        fig = plot_bag_compare(
            output_dir / "deviation_evaluator.png",
            bag_file_evaluator.results,
        )
        plt.show()
        print("Visualization completed! Press ctrl-C to exit.")


def main(args=None):
    rclpy.init(args=args)
    print("Loading rosbag. This may take a while...")
    node = DeviationEvaluationVisualizer()
    spin_thread = Thread(target=rclpy.spin, args=(node,))
    spin_thread.start()


if __name__ == "__main__":
    main()
