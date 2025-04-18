import simpy
from simpy.resources.store import FilterStoreGet
from Config import WIDTH_OF_AISLE, WIDTH_OF_SHELVES, NUM_OF_AISLES, NUM_OF_LOCATIONS

"""
1. 生成机器人的对象
2. 创建机器人队列（使用filterstore）
"""
class Robot:
    def __init__(self, idx, aisle, location):
        self.index = idx
        self.name = f"ROBOT-{idx}"
        self.aisle = aisle
        self.location = location

    def robot_travel_distance(self, spot:list) -> float:
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
    创建机器人队列，定义get函数获取针对指定起始点最近的机器人。
    """

    def __init__(self, env: simpy.Environment, num_of_robots):
        super().__init__(env)
        self.items = [Robot(idx=i+1, aisle=1/2*NUM_OF_AISLES, location=0) for i in range(num_of_robots)]

    def get_robot(self, spot:list) -> FilterStoreGet:
        self.items.sort(key=lambda robot: Robot.robot_travel_distance(robot, spot))
        return super().get()