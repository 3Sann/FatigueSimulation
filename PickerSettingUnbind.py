import simpy
from typing import List, Tuple
import random
from simpy.resources.store import FilterStoreGet
from Config import WIDTH_OF_AISLE, WIDTH_OF_SHELVES, NUM_OF_AISLES, NUM_OF_LOCATIONS

"""
1. 生成拣选员的对象
2. 创建拣选员队列（使用filterstore）
"""
class Picker:
    def __init__(self, idx, aisle, location):
        self.index = idx
        self.name = f"PICKER-{idx}"
        self.aisle = aisle
        self.location = location
        self.traveled_dis = 0

    def picker_travel_distance(self, spot:list)->float:
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

class PickerList(simpy.FilterStore):
    """
    创建拣选员队列，定义get函数获取针对订单的起始/结束点最近的拣选员并推送拣选员与起始拣选点。
    """

    def __init__(self, env: simpy.Environment, num_of_pickers):
        super().__init__(env)
        self.items = [Picker(idx = i+1, aisle = random.randint(1, NUM_OF_AISLES), location = random.randint(1, NUM_OF_LOCATIONS)) for i in range(num_of_pickers)]

    def get_picker(self, spot:list) -> [FilterStoreGet]:
        self.items.sort(key=lambda picker: picker.picker_travel_distance(spot))
        return super().get()

    def get_firstpicker(self,spot: list) -> [FilterStoreGet, list, list]:
        list1 = sorted(self.items, key=lambda picker: picker.picker_travel_distance(spot[0]))
        list2 = sorted(self.items, key=lambda picker: picker.picker_travel_distance(spot[1]))
        if (len(list1) >= 1) & (len(list2) >= 1):
            distance1 = Picker.picker_travel_distance(list1[0], spot[0])
            distance2 = Picker.picker_travel_distance(list2[0], spot[1])
            if (distance1 < distance2):
                self.items.sort(key=lambda picker: picker.picker_travel_distance(spot[0]))
                return super().get(), spot[0], spot[1]
            else:
                self.items.sort(key=lambda picker: picker.picker_travel_distance(spot[1]))
                return super().get(), spot[1], spot[0]
        else:
            return super().get(), spot[1], spot[0]