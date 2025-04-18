import simpy
import math
import random
from typing import List, Tuple
from simpy.resources.store import FilterStoreGet
from Config import WIDTH_OF_AISLE, WIDTH_OF_SHELVES, NUM_OF_AREAS, NUM_OF_LOCATIONS , NUM_OF_AISLES

"""
1. 生成拣选员的对象
2. 创建拣选员队列（使用filterstore）
"""
class Robot:
    def __init__(self, idx, input_area, input_aisle, input_location):
        self.index = idx
        self.name = f"ROBOT-{idx}"
        self.area = input_area
        self.aisle = input_aisle
        self.location = input_location
        self.traveled_dis = 0

    def robot_travel_distance(self ,spot:list)->float:
        next_aisle = spot[0]
        next_location = spot[1]
        if (next_aisle == self.aisle):
            return abs(self.location - next_location) * WIDTH_OF_SHELVES
        else:
            if (NUM_OF_LOCATIONS > self.location+next_location):
                return abs(self.aisle - next_aisle) * WIDTH_OF_AISLE + (self.location + next_location)*WIDTH_OF_SHELVES
            else:
                return abs(self.aisle - next_aisle) * WIDTH_OF_AISLE + (
                        2 * NUM_OF_LOCATIONS-(self.location + next_location)) * WIDTH_OF_SHELVES

class MachineList(simpy.FilterStore):
    """
    创建拣选员队列，定义get函数获取针对订单的起始/结束点最近的拣选员并推送拣选员与起始拣选点。
    """

    def __init__(self, env: simpy.Environment, num_of_robots):
        super().__init__(env)
        Robotlimit = num_of_robots/NUM_OF_AREAS
        aislelimit = NUM_OF_AISLES/NUM_OF_AREAS
        self.items = [Robot(idx = i+1, input_area = math.floor(i/Robotlimit)+1,
                             input_aisle = int(random.randint(0,1)*(aislelimit-1)+math.floor(i/Robotlimit)*aislelimit+1), input_location=0) for i in range(num_of_robots)]
    def get_robot(self, area, spot:list) -> [FilterStoreGet]:
        self.items.sort(key=lambda Robot: Robot.robot_travel_distance(spot))
        return super().get(lambda Robot: Robot.area == area)

    def get_robotbyindex(self, index) -> [FilterStoreGet]:
        return super().get(lambda Robot: Robot.index == index)